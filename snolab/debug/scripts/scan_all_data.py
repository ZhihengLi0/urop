#!/usr/bin/env python3
"""
Full data characterisation scan — ALL zips, ALL channels, ALL series.

For every raw event passing the PTOFamps cut, computes every diagnostic
metric used across v1-v10 of the template pipeline and outputs:

  all_zips_event_stats.tsv  — one row per (zip,series,event,channel), 50+ cols
  all_zips_summary.txt      — per-zip/channel aggregate stats PLUS every
                              individual event listed with all key metrics

One MIDAS pass per series covers all 13 detectors simultaneously.

Usage (inside Singularity):
    python3 -u scan_all_data.py
    Set SCAN_RUN_DIR env var to choose output directory.
"""

import os, sys, csv, datetime, warnings
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

try:
    import rawio
except ImportError:
    raise RuntimeError("rawio required — run inside CDMS Singularity image")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

SAMPLERATE    = 625000
TRACELENGTH   = 32768
FILTER_KHZ    = 100.0

ALIGN_PEAK_LO       = 15000
ALIGN_PEAK_HI       = 18000
NEGATIVE_FRACTION   = 0.05
NEGATIVE_TAIL_SAMP  = 12000
MIN_SNR             = 4.0
MAX_FIT_RMSE_FRAC   = 0.50
CANONICAL_PT        = 16250

# 2-exp fit window (relative to estimated pretrigger)
FIT_WIN_LO = -300
FIT_WIN_HI = 5000
FIT_STRIDE = 4

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
ALL_ZIPS  = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

PTOF_RANGES = {
     1: (2.96e-7, 5.40e-7),   4: (4.44e-7, 8.10e-7),
     6: (3.33e-7, 6.08e-7),   7: (1.48e-6, 2.70e-6),
     9: (5.93e-7, 1.08e-6),  10: (5.93e-7, 1.08e-6),
    13: (1.19e-6, 2.16e-6),  15: (7.41e-6, 1.35e-5),
    16: (1.33e-6, 2.43e-6),  18: (1.04e-6, 1.89e-6),
    19: (4.44e-7, 8.10e-7),  22: (3.70e-7, 6.75e-7),
    24: (4.44e-7, 8.10e-7),
}

SERIES_EXCLUSIONS = {
     1: ["24260621_075659"],
    13: ["24260617_063934"],
    15: ["24260619_093653", "24260619_144815", "24260619_230219"],
    18: ["24260617_063934", "24260617_175849", "24260617_190838",
         "24260617_234805", "24260618_013000", "24260618_062713",
         "24260618_073543"],
    22: ["24260620_032928", "24260621_021444", "24260621_041432",
         "24260621_075659", "24260621_111527", "24260621_145024"],
}

ALL_SERIES = [
    "24260617_063934", "24260617_175849", "24260617_190838", "24260617_234805",
    "24260618_013000", "24260618_062713", "24260618_073543", "24260618_202553",
    "24260619_023225", "24260619_061249", "24260619_075448", "24260619_093653",
    "24260619_144815", "24260619_174938", "24260619_210312", "24260619_230219",
    "24260620_032928", "24260621_021444", "24260621_041432", "24260621_075659",
    "24260621_111527", "24260621_145024", "24260622_022708", "24260622_042718",
    "24260622_073439", "24260622_210215", "24260622_232541", "24260623_012553",
    "24260623_035656", "24260623_064608",
]

# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL PROCESSING HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)

def two_exp(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt    = np.clip((x - pretrigger) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)

def do_2exp_fit(y_lp, peak, peak_idx):
    T_RISE0 = 6.0e-5
    T_FALL0 = 2.8e-4
    dt2peak = (np.log(T_FALL0 / T_RISE0) /
               (1.0 / T_RISE0 - 1.0 / T_FALL0))
    pt_est  = float(np.clip(peak_idx - dt2peak * SAMPLERATE, 14000, 20000))
    fit_lo  = max(0,           int(pt_est) + FIT_WIN_LO)
    fit_hi  = min(TRACELENGTH, int(pt_est) + FIT_WIN_HI)
    pt_lo   = max(fit_lo, pt_est - 600)
    pt_hi   = min(fit_hi - 1, pt_est + 600)
    x_fit   = X_FULL[fit_lo:fit_hi:FIT_STRIDE]
    y_fit   = y_lp[fit_lo:fit_hi:FIT_STRIDE]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(
                two_exp, x_fit, y_fit,
                p0=[peak, T_RISE0, T_FALL0, 0.0, pt_est],
                bounds=([0,  1e-6,  1e-5, -0.5*peak, pt_lo],
                        [np.inf, 8e-4, 8e-3,  0.5*peak, pt_hi]),
                maxfev=30000,
            )
        amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall and np.isfinite(pt)):
            return None
        y_model   = two_exp(x_fit, *popt)
        residuals = (y_fit - y_model) / peak
        nrmse     = float(np.sqrt(np.mean(residuals**2)))
        rmse_abs  = float(np.sqrt(np.mean((y_fit - y_model)**2)))
        return dict(amp=amp, t_rise=t_rise, t_fall=t_fall,
                    baseline=bl, pretrigger=pt,
                    nrmse=nrmse, rmse_abs=rmse_abs)
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════════════════
# MAIN METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════
def compute_metrics(pulse_raw, baseline_rq, ptofamps, ptof_delay):
    y   = pulse_raw.astype(np.float64)
    nan = np.nan

    # ── 1. Raw pre-trigger noise ──────────────────────────────────────────────
    raw_pre       = y[:5000]
    noise_std     = float(np.std(raw_pre))
    noise_mean    = float(np.mean(raw_pre))
    noise_rms     = float(np.sqrt(np.mean(raw_pre**2)))
    noise_p2p     = float(np.max(raw_pre) - np.min(raw_pre))
    noise_skew    = float(np.mean(((raw_pre - noise_mean)/noise_std)**3)) if noise_std>0 else nan
    # split into two halves to check drift
    noise_h1_mean = float(np.mean(y[:2500]))
    noise_h2_mean = float(np.mean(y[2500:5000]))
    baseline_drift = noise_h2_mean - noise_h1_mean

    # ── 2. Baseline ───────────────────────────────────────────────────────────
    if np.isfinite(baseline_rq) and baseline_rq != -999999:
        bs        = float(baseline_rq)
        bs_source = "rq"
    else:
        bs        = noise_mean
        bs_source = "raw_mean"
    bs_residual = noise_mean - bs   # how much RQ baseline differs from raw mean

    y_bs = y - bs

    # ── 3. Raw (unfiltered) peak ──────────────────────────────────────────────
    peak_raw     = float(np.max(y_bs))
    peak_idx_raw = int(np.argmax(y_bs))
    min_raw      = float(np.min(y_bs))

    # ── 4. LP-filtered trace ──────────────────────────────────────────────────
    y_lp = butter_lp(y_bs)

    # Pre-trigger LP stats: 14000-15500 (right before expected pulse)
    pre_lp        = y_lp[14000:15500]
    pretrig_mean  = float(np.mean(pre_lp))
    pretrig_std   = float(np.std(pre_lp))
    pretrig_p2p   = float(np.max(pre_lp) - np.min(pre_lp))
    # Even closer to pulse: 15000-16000
    pre_close     = y_lp[15000:16000]
    pretrig_close_std  = float(np.std(pre_close))
    pretrig_close_mean = float(np.mean(pre_close))

    y_lp -= pretrig_mean   # remove residual LP baseline

    # ── 5. LP peak ────────────────────────────────────────────────────────────
    search_lo    = max(0, ALIGN_PEAK_LO - 1500)
    search_hi    = min(TRACELENGTH, ALIGN_PEAK_HI + 2000)
    peak_lp      = float(np.max(y_lp[search_lo:search_hi]))
    peak_idx_lp  = int(search_lo + np.argmax(y_lp[search_lo:search_hi]))
    if peak_lp <= 0:
        peak_idx_lp = -1

    # ── 6. Quality flags ──────────────────────────────────────────────────────
    peak_in_win  = int(ALIGN_PEAK_LO <= peak_idx_lp <= ALIGN_PEAK_HI)
    snr          = peak_lp / noise_std if (noise_std > 0 and peak_lp > 0) else 0.0
    snr_pass     = int(snr >= MIN_SNR)

    # ── 7. Undershoot ─────────────────────────────────────────────────────────
    if peak_lp > 0 and peak_idx_lp >= 0:
        tail_end       = min(TRACELENGTH, peak_idx_lp + NEGATIVE_TAIL_SAMP)
        tail           = y_lp[peak_idx_lp:tail_end]
        min_tail       = float(np.min(tail)) if len(tail) else 0.0
        min_tail_idx   = int(peak_idx_lp + np.argmin(tail)) if len(tail) else -1
        undershoot_frac = min_tail / peak_lp
        undershoot_pass = int(undershoot_frac >= -NEGATIVE_FRACTION)
    else:
        min_tail = min_tail_idx = undershoot_frac = nan
        undershoot_pass = 0

    # ── 8. Waveform shape times ───────────────────────────────────────────────
    rise_10_90 = rise_20_80 = fall_1e = fall_half = fall_tenth = nan
    peak_to_half_rise = nan
    if peak_lp > 0 and peak_idx_lp > 0:
        pre = y_lp[:peak_idx_lp + 1]
        for lo_frac, hi_frac, attr in [(0.10, 0.90, "rise_10_90"),
                                        (0.20, 0.80, "rise_20_80")]:
            i_lo = np.where(pre >= lo_frac * peak_lp)[0]
            i_hi = np.where(pre >= hi_frac * peak_lp)[0]
            if len(i_lo) and len(i_hi):
                val = (i_hi[0] - i_lo[0]) / SAMPLERATE * 1e3
                if attr == "rise_10_90": rise_10_90 = float(val)
                else:                    rise_20_80 = float(val)
        # half-rise: sample where LP first reaches 50% of peak
        i_half = np.where(pre >= 0.5 * peak_lp)[0]
        peak_to_half_rise = float((peak_idx_lp - i_half[0]) / SAMPLERATE * 1e3) if len(i_half) else nan

        post = y_lp[peak_idx_lp:]
        for frac, attr in [(1.0/np.e, "fall_1e"), (0.5, "fall_half"), (0.1, "fall_tenth")]:
            ie = np.where(post <= frac * peak_lp)[0]
            val = float(ie[0] / SAMPLERATE * 1e3) if len(ie) else nan
            if attr == "fall_1e":     fall_1e     = val
            elif attr == "fall_half": fall_half   = val
            else:                     fall_tenth  = val

    # ── 9. Pulse integral and energy proxy ────────────────────────────────────
    if peak_lp > 0 and peak_idx_lp > 0:
        int_lo = max(0, peak_idx_lp - 1000)
        int_hi = min(TRACELENGTH, peak_idx_lp + 20000)
        pulse_integral = float(np.sum(y_lp[int_lo:int_hi])) / SAMPLERATE
        # amplitude at fixed offsets from peak (shape characterisation)
        amp_at = {}
        for dt_ms, label in [(0.5,"0p5ms"),(1.0,"1ms"),(2.0,"2ms"),(5.0,"5ms"),(10.0,"10ms")]:
            idx = peak_idx_lp + int(dt_ms * 1e-3 * SAMPLERATE)
            amp_at[label] = float(y_lp[idx] / peak_lp) if 0 <= idx < TRACELENGTH else nan
    else:
        pulse_integral = nan
        amp_at = {k: nan for k in ["0p5ms","1ms","2ms","5ms","10ms"]}

    # ── 10. Pre-trigger pulse check (noise spike / pileup) ─────────────────────
    pretrig_peak     = float(np.max(np.abs(y_lp[5000:ALIGN_PEAK_LO - 500]))) if ALIGN_PEAK_LO > 5500 else nan
    pretrig_peak_snr = pretrig_peak / noise_std if (np.isfinite(pretrig_peak) and noise_std > 0) else nan

    # ── 11. Sign changes in tail (ringing indicator) ─────────────────────────
    if peak_lp > 0 and peak_idx_lp >= 0:
        tail_sg = y_lp[peak_idx_lp:min(TRACELENGTH, peak_idx_lp + 15000)]
        sign_changes = int(np.sum(np.diff(np.sign(tail_sg)) != 0)) if len(tail_sg) > 1 else 0
    else:
        sign_changes = -1

    # ── 12. 2-exp fit ─────────────────────────────────────────────────────────
    f2 = None
    if peak_lp > 0 and peak_in_win:
        f2 = do_2exp_fit(y_lp, peak_lp, peak_idx_lp)

    if f2:
        fit2_ok         = 1
        fit2_amp        = f2["amp"]
        fit2_t_rise_ms  = f2["t_rise"] * 1e3
        fit2_t_fall_ms  = f2["t_fall"] * 1e3
        fit2_pretrigger = f2["pretrigger"]
        fit2_baseline   = f2["baseline"]
        fit2_nrmse      = f2["nrmse"]
        fit2_rmse_abs   = f2["rmse_abs"]
        fit2_pt_dist    = f2["pretrigger"] - CANONICAL_PT
        fit2_ratio      = f2["t_fall"] / f2["t_rise"] if f2["t_rise"] > 0 else nan
        fit2_rmse_pass  = int(fit2_nrmse < MAX_FIT_RMSE_FRAC)
    else:
        fit2_ok = 0
        fit2_amp = fit2_t_rise_ms = fit2_t_fall_ms = fit2_pretrigger = nan
        fit2_baseline = fit2_nrmse = fit2_rmse_abs = fit2_pt_dist = fit2_ratio = nan
        fit2_rmse_pass = 0

    # ── 13. PTOFdelay alignment ───────────────────────────────────────────────
    if np.isfinite(ptof_delay):
        delay_samp      = -round(ptof_delay * SAMPLERATE)
        aligned_peak    = (peak_idx_lp + delay_samp) if peak_idx_lp >= 0 else -1
        dist_canonical  = (peak_idx_lp - CANONICAL_PT) if peak_idx_lp >= 0 else nan
        dist_after_align = (aligned_peak - CANONICAL_PT) if aligned_peak >= 0 else nan
    else:
        delay_samp = aligned_peak = 0
        dist_canonical = dist_after_align = nan

    # ── 14. Combined pass ─────────────────────────────────────────────────────
    all_pass = int(peak_in_win and snr_pass and undershoot_pass)

    return {
        # identification / selection
        "ptofamps":            ptofamps,
        "ptof_delay_s":        ptof_delay,
        # raw noise
        "noise_std":           noise_std,
        "noise_mean":          noise_mean,
        "noise_rms":           noise_rms,
        "noise_p2p":           noise_p2p,
        "noise_skewness":      noise_skew,
        "baseline_drift_h1h2": baseline_drift,
        # baseline
        "baseline_rq":         baseline_rq,
        "baseline_source":     bs_source,
        "baseline_residual":   bs_residual,
        # raw peak
        "peak_raw_adu":        peak_raw,
        "peak_idx_raw":        peak_idx_raw,
        "min_raw_adu":         min_raw,
        # LP pre-trigger
        "pretrig_lp_mean":     pretrig_mean,
        "pretrig_lp_std":      pretrig_std,
        "pretrig_lp_p2p":      pretrig_p2p,
        "pretrig_close_std":   pretrig_close_std,
        "pretrig_close_mean":  pretrig_close_mean,
        # LP peak
        "peak_lp_adu":         peak_lp,
        "peak_idx_lp":         peak_idx_lp,
        "peak_idx_dist_canonical": (peak_idx_lp - CANONICAL_PT) if peak_idx_lp >= 0 else nan,
        # quality flags
        "snr":                 snr,
        "peak_in_window":      peak_in_win,
        "snr_pass":            snr_pass,
        "undershoot_frac":     undershoot_frac,
        "undershoot_min_adu":  min_tail,
        "undershoot_min_idx":  min_tail_idx,
        "undershoot_pass":     undershoot_pass,
        # waveform shape
        "rise_10_90_ms":       rise_10_90,
        "rise_20_80_ms":       rise_20_80,
        "half_rise_from_peak_ms": peak_to_half_rise,
        "fall_1e_ms":          fall_1e,
        "fall_half_ms":        fall_half,
        "fall_tenth_ms":       fall_tenth,
        # amplitude at fixed offsets (normalised to peak)
        "amp_norm_0p5ms":      amp_at["0p5ms"],
        "amp_norm_1ms":        amp_at["1ms"],
        "amp_norm_2ms":        amp_at["2ms"],
        "amp_norm_5ms":        amp_at["5ms"],
        "amp_norm_10ms":       amp_at["10ms"],
        # pulse integral
        "pulse_integral_adu_s": pulse_integral,
        # pileup / noise spike check
        "pretrig_peak_abs":    pretrig_peak,
        "pretrig_peak_snr":    pretrig_peak_snr,
        "tail_sign_changes":   sign_changes,
        # 2-exp fit
        "fit2_ok":             fit2_ok,
        "fit2_amp":            fit2_amp,
        "fit2_t_rise_ms":      fit2_t_rise_ms,
        "fit2_t_fall_ms":      fit2_t_fall_ms,
        "fit2_t_ratio":        fit2_ratio,
        "fit2_pretrigger":     fit2_pretrigger,
        "fit2_pt_dist_canonical": fit2_pt_dist,
        "fit2_baseline":       fit2_baseline,
        "fit2_nrmse":          fit2_nrmse,
        "fit2_rmse_abs":       fit2_rmse_abs,
        "fit2_rmse_pass":      fit2_rmse_pass,
        # alignment
        "delay_samples":       delay_samp,
        "aligned_peak_idx":    aligned_peak,
        "dist_canonical_raw":  dist_canonical,
        "dist_canonical_aligned": dist_after_align,
        # combined
        "all_cuts_pass":       all_pass,
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
RUN_DIR  = os.environ.get("SCAN_RUN_DIR", os.path.abspath("debug/run"))
os.makedirs(RUN_DIR, exist_ok=True)

TSV_PATH = os.path.join(RUN_DIR, "all_zips_event_stats.tsv")
SUM_PATH = os.path.join(RUN_DIR, "all_zips_summary.txt")
LOG_PATH = os.path.join(RUN_DIR, "scan.log")

# All metric column names (order matters for TSV)
METRIC_COLS = [
    "ptofamps","ptof_delay_s",
    "noise_std","noise_mean","noise_rms","noise_p2p","noise_skewness","baseline_drift_h1h2",
    "baseline_rq","baseline_source","baseline_residual",
    "peak_raw_adu","peak_idx_raw","min_raw_adu",
    "pretrig_lp_mean","pretrig_lp_std","pretrig_lp_p2p",
    "pretrig_close_std","pretrig_close_mean",
    "peak_lp_adu","peak_idx_lp","peak_idx_dist_canonical",
    "snr","peak_in_window","snr_pass",
    "undershoot_frac","undershoot_min_adu","undershoot_min_idx","undershoot_pass",
    "rise_10_90_ms","rise_20_80_ms","half_rise_from_peak_ms",
    "fall_1e_ms","fall_half_ms","fall_tenth_ms",
    "amp_norm_0p5ms","amp_norm_1ms","amp_norm_2ms","amp_norm_5ms","amp_norm_10ms",
    "pulse_integral_adu_s",
    "pretrig_peak_abs","pretrig_peak_snr","tail_sign_changes",
    "fit2_ok","fit2_amp","fit2_t_rise_ms","fit2_t_fall_ms","fit2_t_ratio",
    "fit2_pretrigger","fit2_pt_dist_canonical","fit2_baseline",
    "fit2_nrmse","fit2_rmse_abs","fit2_rmse_pass",
    "delay_samples","aligned_peak_idx",
    "dist_canonical_raw","dist_canonical_aligned",
    "all_cuts_pass",
]
TSV_COLS = ["zip","series","event","channel"] + METRIC_COLS

# Accumulator: acc[det][chan] = list of full row dicts (including series, event)
acc = {det: {c: [] for c in ALL_CHANS} for det in ALL_ZIPS}

def log(msg):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as lf:
        lf.write(line + "\n")

log(f"=== scan_all_data.py started {datetime.datetime.now()} ===")
log(f"Output: {RUN_DIR}")

# ── detect channels per zip ───────────────────────────────────────────────────
_ref = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{ALL_SERIES[0]}.root")
zip_chans = {}
with uproot.open(_ref) as _f:
    for det in ALL_ZIPS:
        try:
            _keys = list(_f[f"rqDir/zip{det}"].keys())
            zip_chans[det] = [c for c in ALL_CHANS if f"{c}OFdelay" in _keys]
        except Exception:
            zip_chans[det] = []
for det in ALL_ZIPS:
    log(f"  Zip{det} channels: {zip_chans[det]}")

# ── open TSV ─────────────────────────────────────────────────────────────────
tsv_fh = open(TSV_PATH, "w", newline="")
writer  = csv.DictWriter(tsv_fh, fieldnames=TSV_COLS, delimiter="\t",
                         extrasaction="ignore")
writer.writeheader()
tsv_fh.flush()

total_rows = 0

# ══════════════════════════════════════════════════════════════════════════════
# SERIES LOOP
# ══════════════════════════════════════════════════════════════════════════════
for s_idx, series in enumerate(ALL_SERIES):
    log(f"\n── {s_idx+1}/{len(ALL_SERIES)}  {series} ──")
    proc_path = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(proc_path):
        log(f"  processed file missing"); continue

    # load selected events for all zips
    sel_info = {}   # det -> {evnum: {ptofamps, chans: {chan: {delay, bs}}}}
    try:
        with uproot.open(proc_path) as f:
            trig  = f["rqDir/eventTree/TriggerType"].array(library="np")
            evnum = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
            for det in ALL_ZIPS:
                if series in SERIES_EXCLUSIONS.get(det, []):
                    continue
                chans = zip_chans.get(det, [])
                if not chans: continue
                try:
                    ptof = f[f"rqDir/zip{det}/PTOFamps"].array(library="np")
                except Exception: continue
                lo, hi = PTOF_RANGES[det]
                mask   = (trig == 1) & (ptof != -999999) & (ptof > lo) & (ptof < hi)
                evs    = evnum[mask]
                if len(evs) == 0: continue
                ptof_sel = ptof[mask]
                per_ev   = {}
                for i, ev in enumerate(evs.tolist()):
                    chan_data = {}
                    for c in chans:
                        try: dl = float(f[f"rqDir/zip{det}/{c}OFdelay"].array(library="np")[mask][i])
                        except: dl = np.nan
                        try: bs = float(f[f"rqDir/zip{det}/{c}bs"].array(library="np")[mask][i])
                        except: bs = np.nan
                        chan_data[c] = {"delay": dl, "bs": bs}
                    per_ev[int(ev)] = {"ptofamps": float(ptof_sel[i]), "chans": chan_data}
                sel_info[det] = per_ev
                log(f"    Zip{det}: {len(evs)} events")
    except Exception as exc:
        log(f"  ERROR reading processed file: {exc}"); continue

    if not sel_info: continue

    needed = {}
    for det, pev in sel_info.items():
        for ev in pev:
            needed.setdefault(ev, []).append(det)

    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        log(f"  raw dir missing"); continue
    try:
        reader  = rawio.RawDataReader(raw_dir)
        nb      = reader.get_nb_events()
        total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
        events  = reader.read_events(
            output_format=2, skip_empty=True, trigger_types=[1],
            nb_events=total_e,
            detector_nums=list(sel_info.keys()),
            channel_names=ALL_CHANS,
        )
    except Exception as exc:
        log(f"  rawio error: {exc}"); continue

    n_rows_series = 0
    for event in events:
        evn = int(event["event"]["EventNumber"])
        if evn not in needed: continue
        for det in needed[evn]:
            z_key   = f"Z{det}"
            ev_info = sel_info[det].get(evn)
            if ev_info is None: continue
            chans   = zip_chans.get(det, [])
            for chan in chans:
                try:    pulse = event[z_key][chan]
                except: continue
                ci = ev_info["chans"].get(chan, {})
                try:
                    m = compute_metrics(pulse, ci.get("bs", np.nan),
                                        ev_info["ptofamps"], ci.get("delay", np.nan))
                except Exception as exc:
                    m = {k: np.nan for k in METRIC_COLS}
                    m["ptofamps"] = ev_info["ptofamps"]
                    m["baseline_source"] = f"error:{exc}"

                row = {"zip": det, "series": series, "event": evn, "channel": chan}
                row.update(m)

                out = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out[k] = f"{v:.6g}" if np.isfinite(v) else "nan"
                    else:
                        out[k] = v
                writer.writerow(out)
                n_rows_series += 1
                total_rows += 1

                # accumulate full row for summary
                m["_series"] = series
                m["_event"]  = evn
                acc[det][chan].append(m)

        if total_rows % 1000 == 0:
            tsv_fh.flush()

    log(f"  wrote {n_rows_series} rows")

tsv_fh.flush()
tsv_fh.close()
log(f"\nTSV done: {total_rows} rows total → {TSV_PATH}")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY FILE — per-zip, per-channel: aggregates + every individual event
# ══════════════════════════════════════════════════════════════════════════════
log("Writing summary...")

def fv(v, fmt=".4g"):
    if v is None: return "N/A"
    try:
        return "nan" if not np.isfinite(float(v)) else f"{float(v):{fmt}}"
    except: return str(v)

def agg(rows, key, unit="", fmt=".4g"):
    vals = np.array([r[key] for r in rows
                     if isinstance(r.get(key),(int,float)) and np.isfinite(r.get(key,np.nan))],
                    dtype=float)
    if len(vals) == 0:
        return f"    {key}: NO DATA"
    return (f"    {key} (n={len(vals)}):"
            f"  median={vals.mean():{fmt}}{unit}"
            f"  mean={vals.mean():{fmt}}{unit}"
            f"  std={vals.std():{fmt}}{unit}"
            f"  [p5={np.percentile(vals,5):{fmt}}  p16={np.percentile(vals,16):{fmt}}"
            f"  p84={np.percentile(vals,84):{fmt}}  p95={np.percentile(vals,95):{fmt}}]{unit}"
            f"  min={vals.min():{fmt}}  max={vals.max():{fmt}}{unit}")

def pct(n, d): return f"{n/d*100:.1f}%" if d > 0 else "N/A"

lines = []
H = "=" * 90
h = "-" * 70

lines += [H,
    f"ALL-ZIPS DATA SCAN SUMMARY   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    H, "",
    f"PTOF ranges (Ge K-shell peak selection):"]
for det, (lo, hi) in PTOF_RANGES.items():
    excl = SERIES_EXCLUSIONS.get(det, [])
    lines.append(f"  Zip{det:2d}: [{lo:.3e}, {hi:.3e}]  excluded={excl or 'none'}")
lines += ["",
    "Series list (30 total):", f"  {ALL_SERIES}", "",
    f"Total event-channel rows written to TSV: {total_rows}", ""]

for det in ALL_ZIPS:
    lines += [H, f"ZIP {det}   PTOFamps [{PTOF_RANGES[det][0]:.3e}, {PTOF_RANGES[det][1]:.3e}]", H]
    chans = zip_chans.get(det, [])
    if not chans:
        lines += ["  No channels.", ""]; continue

    for chan in chans:
        rows = acc[det][chan]
        n    = len(rows)
        lines += ["", h, f"  ZIP{det}  {chan}  (total events: {n})", h]

        if n == 0:
            lines += ["    NO DATA — dead channel or all series excluded", ""]; continue

        # cut counts
        n_win    = sum(1 for r in rows if r.get("peak_in_window")==1)
        n_snr    = sum(1 for r in rows if r.get("snr_pass")==1)
        n_ush    = sum(1 for r in rows if r.get("undershoot_pass")==1)
        n_fit    = sum(1 for r in rows if r.get("fit2_ok")==1)
        n_all    = sum(1 for r in rows if r.get("all_cuts_pass")==1)
        ok_rows  = [r for r in rows if r.get("fit2_ok")==1]

        lines += [
            "  --- CUT SUMMARY ---",
            f"    peak in window [{ALIGN_PEAK_LO},{ALIGN_PEAK_HI}]: {n_win}/{n} ({pct(n_win,n)})",
            f"    SNR >= {MIN_SNR}:                    {n_snr}/{n} ({pct(n_snr,n)})",
            f"    undershoot > -{NEGATIVE_FRACTION*100:.0f}%:          {n_ush}/{n} ({pct(n_ush,n)})",
            f"    2-exp fit converged:         {n_fit}/{n} ({pct(n_fit,n)})",
            f"    ALL cuts pass:               {n_all}/{n} ({pct(n_all,n)})",
            "",
            "  --- NOISE & BASELINE ---",
        ]
        for k,u in [("noise_std"," ADU"),("noise_rms"," ADU"),("noise_p2p"," ADU"),
                    ("noise_skewness",""),("baseline_drift_h1h2"," ADU"),
                    ("baseline_residual"," ADU"),
                    ("pretrig_lp_std"," ADU"),("pretrig_close_std"," ADU")]:
            lines.append(agg(rows, k, u))
        lines += ["", "  --- PEAK ---"]
        for k,u in [("peak_lp_adu"," ADU"),("peak_idx_lp"," samp"),
                    ("peak_idx_dist_canonical"," samp"),("snr",""),
                    ("peak_raw_adu"," ADU"),("pulse_integral_adu_s"," ADU·s")]:
            lines.append(agg(rows, k, u))
        lines += ["", "  --- UNDERSHOOT ---"]
        for k,u in [("undershoot_frac",""),("undershoot_min_adu"," ADU"),
                    ("undershoot_min_idx"," samp")]:
            lines.append(agg(rows, k, u))
        lines += ["", "  --- WAVEFORM SHAPE TIMES ---"]
        for k,u in [("rise_10_90_ms"," ms"),("rise_20_80_ms"," ms"),
                    ("fall_1e_ms"," ms"),("fall_half_ms"," ms"),("fall_tenth_ms"," ms")]:
            lines.append(agg(rows, k, u))
        lines += ["", "  --- AMPLITUDE AT FIXED OFFSETS (normalised to peak) ---"]
        for k in ["amp_norm_0p5ms","amp_norm_1ms","amp_norm_2ms","amp_norm_5ms","amp_norm_10ms"]:
            lines.append(agg(rows, k))
        lines += ["", "  --- 2-EXP FIT ---"]
        if ok_rows:
            for k,u in [("fit2_t_rise_ms"," ms"),("fit2_t_fall_ms"," ms"),
                        ("fit2_t_ratio",""),("fit2_pretrigger"," samp"),
                        ("fit2_pt_dist_canonical"," samp"),
                        ("fit2_nrmse",""),("fit2_rmse_abs"," ADU")]:
                lines.append(agg(ok_rows, k, u))
            n_nrmse = sum(1 for r in ok_rows if r.get("fit2_nrmse",1) > 0.3)
            T_LB, T_UB = 1e-3, 0.8
            n_lb = sum(1 for r in ok_rows if r.get("fit2_t_rise_ms",99) <= T_LB*1.01)
            n_ub = sum(1 for r in ok_rows if r.get("fit2_t_rise_ms",0)  >= T_UB*0.99)
            lines += [f"    nrmse>0.3: {n_nrmse}/{n_fit} ({pct(n_nrmse,n_fit)})",
                      f"    t_rise at lower bound ({T_LB} ms): {n_lb}/{n_fit}",
                      f"    t_rise at upper bound ({T_UB} ms): {n_ub}/{n_fit}"]
        else:
            lines.append("    No successful fits.")
        lines += ["", "  --- ALIGNMENT ---"]
        for k,u in [("delay_samples"," samp"),("dist_canonical_raw"," samp"),
                    ("dist_canonical_aligned"," samp"),("aligned_peak_idx"," samp")]:
            lines.append(agg(rows, k, u))

        # auto flags
        flags = []
        if n < 20:       flags.append(f"VERY FEW EVENTS ({n})")
        if n_win < n*0.5: flags.append(f"PEAK OUT OF WINDOW {100-n_win/n*100:.0f}%")
        if n_snr < n*0.5: flags.append(f"LOW SNR {100-n_snr/n*100:.0f}% fail")
        if n_ush < n*0.7: flags.append(f"HIGH UNDERSHOOT RATE {100-n_ush/n*100:.0f}%")
        if n_fit < n*0.4: flags.append(f"HIGH FIT FAIL RATE {100-n_fit/n*100:.0f}%")
        if ok_rows:
            mn = float(np.median([r["fit2_nrmse"] for r in ok_rows]))
            if mn > 0.25: flags.append(f"POOR FIT quality median nrmse={mn:.3f}")
        lines += ["",
            f"  *** FLAGS: {' | '.join(flags)}" if flags else "  STATUS: OK",
            ""]

        # ── PER-EVENT LISTING ─────────────────────────────────────────────────
        lines += ["  --- EVERY EVENT ---",
                  "  series              ev      ptofamps    peak_lp   peak_idx  snr    "
                  "undershoot  rise10_90  fall_1e  fit_ok  t_rise_ms  t_fall_ms  "
                  "fit_pt    nrmse  all_pass"]
        for r in sorted(rows, key=lambda x: (x.get("_series",""), x.get("_event",0))):
            lines.append(
                f"  {r.get('_series','?'):20s}  "
                f"{r.get('_event',0):7d}  "
                f"{fv(r.get('ptofamps'), '.4e'):12s}  "
                f"{fv(r.get('peak_lp_adu'), '.3e'):10s}  "
                f"{fv(r.get('peak_idx_lp'), '.0f'):8s}  "
                f"{fv(r.get('snr'), '.2f'):6s}  "
                f"{fv(r.get('undershoot_frac'), '.4f'):11s}  "
                f"{fv(r.get('rise_10_90_ms'), '.4f'):10s}  "
                f"{fv(r.get('fall_1e_ms'), '.4f'):8s}  "
                f"{r.get('fit2_ok',0):6d}  "
                f"{fv(r.get('fit2_t_rise_ms'), '.4f'):10s}  "
                f"{fv(r.get('fit2_t_fall_ms'), '.4f'):10s}  "
                f"{fv(r.get('fit2_pretrigger'), '.1f'):8s}  "
                f"{fv(r.get('fit2_nrmse'), '.4f'):7s}  "
                f"{r.get('all_cuts_pass',0):1d}"
            )
        lines.append("")

lines += [H,
    "METRIC REFERENCE",
    H,
    "noise_std            raw pre-trigger std (samples 0-5000), ADU",
    "noise_p2p            raw pre-trigger peak-to-peak, ADU",
    "noise_skewness       skewness of pre-trigger distribution (0=Gaussian)",
    "baseline_drift_h1h2  mean(2500-5000) - mean(0-2500), ADU  (drift indicator)",
    "baseline_residual    noise_mean - baseline_rq  (RQ accuracy check)",
    "pretrig_lp_std       LP filtered std, samples 14000-15500",
    "pretrig_close_std    LP filtered std, samples 15000-16000 (nearest to pulse)",
    "peak_lp_adu          LP-filtered baseline-subtracted peak amplitude, ADU",
    "peak_idx_lp          sample index of LP peak (expected 15000-18000)",
    "peak_idx_dist_canonical  peak_idx_lp - 16250  (misalignment from canonical)",
    "snr                  peak_lp / noise_std",
    "undershoot_frac      min(tail)/peak  (negative = undershoot, cut: > -0.05)",
    "rise_10_90_ms        10%-90% rise time from LP waveform, ms",
    "fall_1e_ms           peak to 1/e amplitude fall time, ms",
    "fall_half_ms         peak to 50% amplitude fall time, ms",
    "amp_norm_Xms         LP amplitude at X ms after peak, normalised to peak",
    "pulse_integral       integral of LP trace ±window around peak, ADU·s",
    "pretrig_peak_snr     largest |amplitude| in 5000-14500 / noise_std  (pileup check)",
    "tail_sign_changes    sign changes in tail after peak  (ringing indicator)",
    "fit2_t_rise_ms       2-exp rise time constant, ms",
    "fit2_t_fall_ms       2-exp fall time constant, ms",
    "fit2_t_ratio         t_fall/t_rise",
    "fit2_pretrigger      fitted pulse start sample index",
    "fit2_pt_dist_canonical  fit2_pretrigger - 16250",
    "fit2_nrmse           normalised RMS fit residual  (<0.2 good, >0.3 poor)",
    "dist_canonical_raw   peak_idx_lp - 16250  (before PTOFdelay alignment)",
    "dist_canonical_aligned  aligned_peak_idx - 16250  (after PTOFdelay shift)",
    "all_cuts_pass        peak_in_window AND snr_pass AND undershoot_pass",
    "",
    "THRESHOLDS (v10/v11 standard):",
    f"  peak window: [{ALIGN_PEAK_LO}, {ALIGN_PEAK_HI}]  |  SNR >= {MIN_SNR}",
    f"  undershoot >= -{NEGATIVE_FRACTION}  |  canonical pretrigger: {CANONICAL_PT}",
    f"  fit nrmse < {MAX_FIT_RMSE_FRAC}  |  LP filter: {FILTER_KHZ} kHz",
]

with open(SUM_PATH, "w") as f:
    f.write("\n".join(lines) + "\n")

log(f"Summary written: {SUM_PATH}")
log(f"=== SCAN COMPLETE {datetime.datetime.now()} ===")
