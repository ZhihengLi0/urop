#!/usr/bin/env python3
"""
Full data scan: ALL series → ALL events → ALL zips → ALL channels.

For every event passing the PTOFamps Ge K-shell cut:
  - reads the raw trace for each channel
  - computes ~55 metrics individually
  - writes one TSV row immediately (no buffering)

Outputs (in $SCAN_RUN_DIR):
  all_zips_event_stats.tsv   one row per (zip, series, event, channel)
  all_zips_summary.txt       per-channel aggregate stats + per-event listing
  scan.log                   timestamped progress
"""

import os, csv, datetime, warnings
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

try:
    import rawio
except ImportError:
    raise RuntimeError("run inside CDMS Singularity image")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

FS          = 625000        # samples per second
NSAMP       = 32768         # trace length
LP_KHZ      = 100.0        # low-pass cutoff
PEAK_LO     = 15000        # expected peak window start
PEAK_HI     = 18000        # expected peak window end
CANONICAL   = 16250        # canonical pretrigger index
MIN_SNR     = 4.0
MAX_UNDER   = -0.05        # undershoot fraction floor

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

ALL_ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

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

# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_LP_SOS = butter(4, LP_KHZ * 1000, btype="low", fs=FS, output="sos")

def lp_filter(y):
    return sosfilt(_LP_SOS, y)

def two_exp_model(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = np.clip((x - pretrigger) / FS, 0.0, None)
    pulse = amp * (np.exp(-dt / t_fall) - np.exp(-dt / t_rise))
    return np.where(x < pretrigger, baseline, pulse + baseline)

X = np.arange(NSAMP, dtype=np.float64)

# ─────────────────────────────────────────────────────────────────────────────
# 2-EXP FIT
# ─────────────────────────────────────────────────────────────────────────────
def fit_2exp(y_lp, peak_amp, peak_idx):
    """
    Fit 2-exp model to LP-filtered trace.
    Returns dict of fit params, or None on failure.
    """
    # Estimate pretrigger from expected time-to-peak formula
    T_R0, T_F0 = 6e-5, 2.8e-4
    dt2pk = np.log(T_F0 / T_R0) / (1.0 / T_R0 - 1.0 / T_F0)
    pt_est = float(np.clip(peak_idx - dt2pk * FS, 14000, 20000))

    # Fit window: from 300 before pretrigger to 5000 after, stride 4
    fit_lo = max(0,    int(pt_est) - 300)
    fit_hi = min(NSAMP, int(pt_est) + 5000)
    if fit_hi - fit_lo < 50:
        return None

    x_fit = X[fit_lo:fit_hi:4]
    y_fit = y_lp[fit_lo:fit_hi:4]

    # Pretrigger is a free parameter but bounded ±600 samples around estimate
    pt_lo = max(fit_lo, pt_est - 600)
    pt_hi = min(fit_hi - 1, pt_est + 600)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(
                two_exp_model, x_fit, y_fit,
                p0   = [peak_amp, T_R0, T_F0, 0.0, pt_est],
                bounds = (
                    [0,     1e-6,  1e-5, -0.5 * peak_amp, pt_lo],
                    [1e9,   8e-4,  8e-3,  0.5 * peak_amp, pt_hi],
                ),
                maxfev = 5000,
            )
    except Exception:
        return None

    amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]

    # sanity checks on fit result
    if amp <= 0 or t_rise <= 0 or t_fall <= t_rise:
        return None
    if not np.isfinite(pt):
        return None

    y_model = two_exp_model(x_fit, *popt)
    residuals = y_fit - y_model
    nrmse = float(np.sqrt(np.mean((residuals / peak_amp) ** 2)))
    rmse  = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "amp":        amp,
        "t_rise":     t_rise,
        "t_fall":     t_fall,
        "baseline":   bl,
        "pretrigger": pt,
        "nrmse":      nrmse,
        "rmse":       rmse,
    }

# ─────────────────────────────────────────────────────────────────────────────
# PER-CHANNEL METRIC COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
NAN = np.nan

def metrics(raw_trace, baseline_rq, ptofamps, ptof_delay):
    """
    Compute all metrics for one raw trace (one event, one channel).
    Returns a flat dict.  Never raises — returns error string on failure.
    """
    result = {}

    # ── validate input ────────────────────────────────────────────────────────
    if raw_trace is None or len(raw_trace) != NSAMP:
        result["error"] = f"bad_trace_len_{len(raw_trace) if raw_trace is not None else 'None'}"
        return result

    y = raw_trace.astype(np.float64)

    # ── 1. Baseline ───────────────────────────────────────────────────────────
    # Use RQ baseline if valid, else raw mean of first 5000 samples
    pre_raw = y[:5000]
    raw_mean = float(np.mean(pre_raw))
    raw_std  = float(np.std(pre_raw))

    if np.isfinite(baseline_rq) and abs(baseline_rq) < 1e7 and baseline_rq != -999999.0:
        bs = float(baseline_rq)
        bs_src = "rq"
    else:
        bs = raw_mean
        bs_src = "raw"

    result["baseline_used"]     = bs
    result["baseline_source"]   = bs_src
    result["baseline_rq"]       = float(baseline_rq) if np.isfinite(float(baseline_rq)) else NAN
    result["baseline_residual"] = raw_mean - bs   # should be ~0 if rq is good

    # ── 2. Raw pre-trigger noise (samples 0–5000) ─────────────────────────────
    result["noise_mean"]  = raw_mean
    result["noise_std"]   = raw_std
    result["noise_rms"]   = float(np.sqrt(np.mean((pre_raw - raw_mean) ** 2)))
    result["noise_p2p"]   = float(np.max(pre_raw) - np.min(pre_raw))
    if raw_std > 0:
        result["noise_skew"] = float(np.mean(((pre_raw - raw_mean) / raw_std) ** 3))
    else:
        result["noise_skew"] = NAN
    # baseline drift: compare first and second half of pre-trigger
    result["baseline_drift"] = float(np.mean(y[2500:5000]) - np.mean(y[:2500]))

    # ── 3. Baseline subtract ──────────────────────────────────────────────────
    y0 = y - bs

    # ── 4. Raw peak ───────────────────────────────────────────────────────────
    result["peak_raw"]     = float(np.max(y0))
    result["peak_idx_raw"] = int(np.argmax(y0))
    result["min_raw"]      = float(np.min(y0))

    # ── 5. LP filter ──────────────────────────────────────────────────────────
    y_lp = lp_filter(y0)

    # local baseline from LP pre-trigger region 14000–15500
    lp_pre = y_lp[14000:15500]
    lp_pre_mean = float(np.mean(lp_pre))
    result["pretrig_lp_mean"] = lp_pre_mean
    result["pretrig_lp_std"]  = float(np.std(lp_pre))
    result["pretrig_lp_p2p"]  = float(np.max(lp_pre) - np.min(lp_pre))

    # tighter window 15000–15800 (closest to pulse onset)
    lp_close = y_lp[15000:15800]
    result["pretrig_close_std"]  = float(np.std(lp_close))
    result["pretrig_close_mean"] = float(np.mean(lp_close))

    # subtract LP pre-trigger mean so LP baseline is 0
    y_lp -= lp_pre_mean

    # ── 6. LP peak ────────────────────────────────────────────────────────────
    # search in [PEAK_LO - 1500, PEAK_HI + 2000]
    search_lo = max(0,    PEAK_LO - 1500)
    search_hi = min(NSAMP, PEAK_HI + 2000)
    lp_window = y_lp[search_lo:search_hi]
    peak_lp   = float(np.max(lp_window))
    peak_idx  = int(search_lo + np.argmax(lp_window))

    result["peak_lp"]      = peak_lp
    result["peak_idx_lp"]  = peak_idx
    result["peak_in_win"]  = int(PEAK_LO <= peak_idx <= PEAK_HI)
    result["peak_dist_canonical"] = (peak_idx - CANONICAL) if peak_lp > 0 else NAN

    # ── 7. SNR ────────────────────────────────────────────────────────────────
    snr = (peak_lp / raw_std) if (raw_std > 0 and peak_lp > 0) else 0.0
    result["snr"]      = float(snr)
    result["snr_pass"] = int(snr >= MIN_SNR)

    # ── 8. Undershoot ─────────────────────────────────────────────────────────
    if peak_lp > 0:
        tail_end = min(NSAMP, peak_idx + 12000)
        tail = y_lp[peak_idx:tail_end]
        if len(tail) > 0:
            min_tail     = float(np.min(tail))
            min_tail_idx = int(peak_idx + int(np.argmin(tail)))
            under_frac   = min_tail / peak_lp
        else:
            min_tail = min_tail_idx = NAN
            under_frac = NAN
    else:
        min_tail = min_tail_idx = under_frac = NAN

    result["undershoot_frac"]  = under_frac
    result["undershoot_min"]   = min_tail
    result["undershoot_idx"]   = min_tail_idx
    result["undershoot_pass"]  = int(under_frac >= MAX_UNDER) if np.isfinite(under_frac) else 0

    # ── 9. Rise / fall times (measured on LP trace) ───────────────────────────
    rise_10_90 = rise_20_80 = fall_1e = fall_half = fall_tenth = NAN
    half_rise  = NAN

    if peak_lp > 0 and peak_idx > 0:
        # rise: search only last 3000 samples before peak to avoid noise triggers
        rl = max(0, peak_idx - 3000)
        pre = y_lp[rl:peak_idx + 1]   # pre[−1] = peak

        def _rise_time(lo_f, hi_f):
            idx_lo = np.where(pre >= lo_f * peak_lp)[0]
            idx_hi = np.where(pre >= hi_f * peak_lp)[0]
            if len(idx_lo) == 0 or len(idx_hi) == 0:
                return NAN
            dt = idx_hi[0] - idx_lo[0]
            if dt <= 0:   # should not happen on a clean rising edge
                return NAN
            return float(dt / FS * 1e3)

        rise_10_90 = _rise_time(0.10, 0.90)
        rise_20_80 = _rise_time(0.20, 0.80)

        # half-rise = distance from first 50% crossing to peak
        i50 = np.where(pre >= 0.5 * peak_lp)[0]
        if len(i50) > 0:
            half_rise = float((len(pre) - 1 - i50[0]) / FS * 1e3)

        # fall: from peak onwards
        post = y_lp[peak_idx:]

        def _fall_time(frac):
            idx = np.where(post <= frac * peak_lp)[0]
            return float(idx[0] / FS * 1e3) if len(idx) > 0 else NAN

        fall_1e    = _fall_time(1.0 / np.e)
        fall_half  = _fall_time(0.5)
        fall_tenth = _fall_time(0.1)

    result["rise_10_90_ms"]  = rise_10_90
    result["rise_20_80_ms"]  = rise_20_80
    result["half_rise_ms"]   = half_rise
    result["fall_1e_ms"]     = fall_1e
    result["fall_half_ms"]   = fall_half
    result["fall_tenth_ms"]  = fall_tenth

    # ── 10. Amplitude at fixed offsets (normalised to peak) ───────────────────
    if peak_lp > 0:
        for dt_ms, label in [(0.5,"0p5ms"),(1.0,"1ms"),(2.0,"2ms"),
                             (5.0,"5ms"),(10.0,"10ms")]:
            idx = peak_idx + int(dt_ms * 1e-3 * FS)
            if 0 <= idx < NSAMP:
                result[f"amp_norm_{label}"] = float(y_lp[idx] / peak_lp)
            else:
                result[f"amp_norm_{label}"] = NAN
    else:
        for label in ["0p5ms","1ms","2ms","5ms","10ms"]:
            result[f"amp_norm_{label}"] = NAN

    # ── 11. Pulse integral ────────────────────────────────────────────────────
    if peak_lp > 0:
        int_lo = max(0,    peak_idx - 1000)
        int_hi = min(NSAMP, peak_idx + 20000)
        result["pulse_integral"] = float(np.sum(y_lp[int_lo:int_hi])) / FS
    else:
        result["pulse_integral"] = NAN

    # ── 12. Pre-trigger pileup check (5000–14500) ─────────────────────────────
    pileup_region = y_lp[5000:PEAK_LO - 500]
    if len(pileup_region) > 0:
        pileup_abs = float(np.max(np.abs(pileup_region)))
        result["pileup_abs"] = pileup_abs
        result["pileup_snr"] = pileup_abs / raw_std if raw_std > 0 else NAN
    else:
        result["pileup_abs"] = NAN
        result["pileup_snr"] = NAN

    # ── 13. Tail sign changes (ringing) ───────────────────────────────────────
    if peak_lp > 0:
        tail_sg = y_lp[peak_idx:min(NSAMP, peak_idx + 15000)]
        result["tail_sign_changes"] = float(np.sum(np.diff(np.sign(tail_sg)) != 0))
    else:
        result["tail_sign_changes"] = NAN

    # ── 14. 2-exp fit ─────────────────────────────────────────────────────────
    if peak_lp > 0 and result["peak_in_win"] == 1:
        fit = fit_2exp(y_lp, peak_lp, peak_idx)
    else:
        fit = None

    if fit is not None:
        result["fit_ok"]         = 1
        result["fit_amp"]        = fit["amp"]
        result["fit_t_rise_ms"]  = fit["t_rise"] * 1e3
        result["fit_t_fall_ms"]  = fit["t_fall"] * 1e3
        result["fit_ratio"]      = fit["t_fall"] / fit["t_rise"]
        result["fit_pretrigger"] = fit["pretrigger"]
        result["fit_pt_dist"]    = fit["pretrigger"] - CANONICAL
        result["fit_baseline"]   = fit["baseline"]
        result["fit_nrmse"]      = fit["nrmse"]
        result["fit_rmse"]       = fit["rmse"]
        result["fit_nrmse_pass"] = int(fit["nrmse"] < 0.50)
    else:
        result["fit_ok"]         = 0
        result["fit_amp"]        = NAN
        result["fit_t_rise_ms"]  = NAN
        result["fit_t_fall_ms"]  = NAN
        result["fit_ratio"]      = NAN
        result["fit_pretrigger"] = NAN
        result["fit_pt_dist"]    = NAN
        result["fit_baseline"]   = NAN
        result["fit_nrmse"]      = NAN
        result["fit_rmse"]       = NAN
        result["fit_nrmse_pass"] = 0

    # ── 15. PTOFdelay alignment ───────────────────────────────────────────────
    if np.isfinite(float(ptof_delay)):
        delay_samp = int(-round(float(ptof_delay) * FS))
        aligned    = peak_idx + delay_samp if peak_lp > 0 else None
        result["delay_samp"]        = delay_samp
        result["aligned_peak_idx"]  = aligned if aligned is not None else NAN
        result["dist_before_align"] = float(peak_idx - CANONICAL) if peak_lp > 0 else NAN
        result["dist_after_align"]  = float(aligned - CANONICAL)  if aligned is not None else NAN
    else:
        result["delay_samp"]        = NAN
        result["aligned_peak_idx"]  = NAN
        result["dist_before_align"] = NAN
        result["dist_after_align"]  = NAN

    # ── 16. PTOFamps ──────────────────────────────────────────────────────────
    result["ptofamps"]   = float(ptofamps)
    result["ptof_delay"] = float(ptof_delay) if np.isfinite(float(ptof_delay)) else NAN

    # ── 17. Combined pass flag ────────────────────────────────────────────────
    result["all_pass"] = int(
        result["peak_in_win"] == 1 and
        result["snr_pass"]    == 1 and
        result["undershoot_pass"] == 1
    )

    result["error"] = ""
    return result

# ─────────────────────────────────────────────────────────────────────────────
# TSV COLUMN ORDER
# ─────────────────────────────────────────────────────────────────────────────
ID_COLS  = ["zip","series","event","channel"]
MET_COLS = [
    "ptofamps","ptof_delay",
    "baseline_used","baseline_source","baseline_rq","baseline_residual",
    "noise_mean","noise_std","noise_rms","noise_p2p","noise_skew","baseline_drift",
    "peak_raw","peak_idx_raw","min_raw",
    "pretrig_lp_mean","pretrig_lp_std","pretrig_lp_p2p",
    "pretrig_close_std","pretrig_close_mean",
    "peak_lp","peak_idx_lp","peak_in_win","peak_dist_canonical",
    "snr","snr_pass",
    "undershoot_frac","undershoot_min","undershoot_idx","undershoot_pass",
    "rise_10_90_ms","rise_20_80_ms","half_rise_ms",
    "fall_1e_ms","fall_half_ms","fall_tenth_ms",
    "amp_norm_0p5ms","amp_norm_1ms","amp_norm_2ms","amp_norm_5ms","amp_norm_10ms",
    "pulse_integral",
    "pileup_abs","pileup_snr","tail_sign_changes",
    "fit_ok","fit_amp","fit_t_rise_ms","fit_t_fall_ms","fit_ratio",
    "fit_pretrigger","fit_pt_dist","fit_baseline","fit_nrmse","fit_rmse","fit_nrmse_pass",
    "delay_samp","aligned_peak_idx","dist_before_align","dist_after_align",
    "all_pass","error",
]
ALL_COLS = ID_COLS + MET_COLS

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
RUN_DIR  = os.environ.get("SCAN_RUN_DIR", os.path.abspath("debug/run"))
os.makedirs(RUN_DIR, exist_ok=True)

TSV_PATH = os.path.join(RUN_DIR, "all_zips_event_stats.tsv")
SUM_PATH = os.path.join(RUN_DIR, "all_zips_summary.txt")
LOG_PATH = os.path.join(RUN_DIR, "scan.log")

def log(msg):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as fh:
        fh.write(line + "\n")

def fmt_val(v):
    """Format a value for TSV: floats to 6 sig figs, nan → 'nan', else str."""
    if v is None:
        return ""
    if isinstance(v, float) or (hasattr(v, "dtype") and np.issubdtype(type(v), np.floating)):
        return "nan" if not np.isfinite(v) else f"{v:.6g}"
    return str(v)

# ─────────────────────────────────────────────────────────────────────────────
# ACCUMULATOR  (in-memory, for summary file)
# ─────────────────────────────────────────────────────────────────────────────
# acc[det][chan] = list of dicts, each dict = metric row + "_series" + "_event"
acc = {det: {c: [] for c in ALL_CHANS} for det in ALL_ZIPS}

# ─────────────────────────────────────────────────────────────────────────────
# DETECT AVAILABLE CHANNELS PER ZIP  (from first series ROOT file)
# ─────────────────────────────────────────────────────────────────────────────
log(f"=== scan_all_data.py  {datetime.datetime.now()} ===")
log(f"Output dir: {RUN_DIR}")

ref_root = None
for _s in ALL_SERIES:
    _p = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{_s}.root")
    if os.path.exists(_p):
        ref_root = _p
        break
if ref_root is None:
    raise FileNotFoundError("No processed ROOT files found — check PROCESSED_DIR")
log(f"Channel detection from: {ref_root}")

zip_chans = {}
with uproot.open(ref_root) as rf:
    for det in ALL_ZIPS:
        try:
            keys = list(rf[f"rqDir/zip{det}"].keys())
            zip_chans[det] = [c for c in ALL_CHANS if f"{c}OFdelay" in keys]
        except Exception:
            zip_chans[det] = []
        log(f"  Zip{det:2d}: {zip_chans[det]}")

# ─────────────────────────────────────────────────────────────────────────────
# OPEN TSV
# ─────────────────────────────────────────────────────────────────────────────
tsv_fh = open(TSV_PATH, "w", newline="")
writer  = csv.writer(tsv_fh, delimiter="\t")
writer.writerow(ALL_COLS)
tsv_fh.flush()

total_rows = 0

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP: series → events → zips → channels
# ─────────────────────────────────────────────────────────────────────────────
for s_idx, series in enumerate(ALL_SERIES):
    log(f"\n[{s_idx+1:02d}/{len(ALL_SERIES)}] series {series}")

    proc_path = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(proc_path):
        log(f"  SKIP: processed ROOT not found")
        continue

    # ── Step 1: load event selection + RQ values from processed ROOT ──────────
    # sel[det] = { event_number: { ptofamps, delay[chan], bs[chan] } }
    sel = {}

    try:
        with uproot.open(proc_path) as rf:
            trig  = rf["rqDir/eventTree/TriggerType"].array(library="np")
            evnum = rf["rqDir/eventTree/EventNumber"].array(library="np").astype(int)

            for det in ALL_ZIPS:
                if series in SERIES_EXCLUSIONS.get(det, []):
                    continue
                chans = zip_chans.get(det, [])
                if not chans:
                    continue

                # PTOFamps selection
                try:
                    ptof = rf[f"rqDir/zip{det}/PTOFamps"].array(library="np")
                except Exception as e:
                    log(f"  Zip{det}: cannot read PTOFamps: {e}")
                    continue

                lo, hi = PTOF_RANGES[det]
                mask = (trig == 1) & (ptof != -999999) & (ptof > lo) & (ptof < hi)
                n_sel = int(np.sum(mask))
                if n_sel == 0:
                    continue

                evs_sel      = evnum[mask]
                ptof_sel     = ptof[mask]

                # read per-channel RQ arrays once (vectorised, outside event loop)
                delay_arr = {}
                bs_arr    = {}
                for c in chans:
                    try:
                        delay_arr[c] = rf[f"rqDir/zip{det}/{c}OFdelay"].array(library="np")[mask]
                    except Exception:
                        delay_arr[c] = np.full(n_sel, NAN)
                    try:
                        bs_arr[c] = rf[f"rqDir/zip{det}/{c}bs"].array(library="np")[mask]
                    except Exception:
                        bs_arr[c] = np.full(n_sel, NAN)

                # build per-event lookup dict
                det_sel = {}
                for i in range(n_sel):
                    ev = int(evs_sel[i])
                    det_sel[ev] = {
                        "ptofamps": float(ptof_sel[i]),
                        "delay":    {c: float(delay_arr[c][i]) for c in chans},
                        "bs":       {c: float(bs_arr[c][i])    for c in chans},
                    }
                sel[det] = det_sel
                log(f"  Zip{det:2d}: {n_sel} events selected")

    except Exception as e:
        log(f"  ERROR reading processed ROOT: {e}")
        continue

    if not sel:
        log(f"  no events selected in any zip, skipping rawio")
        continue

    # set of all event numbers needed across all zips
    needed_events = set()
    for det_sel in sel.values():
        needed_events.update(det_sel.keys())
    log(f"  total unique events to find in raw: {len(needed_events)}")

    # ── Step 2: read raw MIDAS files ─────────────────────────────────────────
    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        log(f"  SKIP: raw dir not found: {raw_dir}")
        continue

    try:
        reader  = rawio.RawDataReader(raw_dir)
        nb      = reader.get_nb_events()
        total_e = nb.get("NbEvents", nb.get("NbEventsNotEmpty", 10_000_000))
        events  = reader.read_events(
            output_format  = 2,
            skip_empty     = True,
            trigger_types  = [1],
            nb_events      = total_e,
            detector_nums  = list(sel.keys()),
            channel_names  = ALL_CHANS,
        )
    except Exception as e:
        log(f"  ERROR opening rawio: {e}")
        continue

    n_found = 0
    n_rows_this_series = 0

    # ── Step 3: iterate events one by one ────────────────────────────────────
    for event in events:
        try:
            evn = int(event["event"]["EventNumber"])
        except Exception:
            continue

        if evn not in needed_events:
            continue

        n_found += 1

        # iterate every zip that wants this event
        for det, det_sel in sel.items():
            if evn not in det_sel:
                continue

            ev_info = det_sel[evn]
            z_key   = f"Z{det}"
            chans   = zip_chans[det]

            # iterate every channel for this zip
            for chan in chans:
                # ── get raw trace ──────────────────────────────────────────
                try:
                    pulse = event[z_key][chan]
                except Exception:
                    pulse = None

                # ── compute metrics ────────────────────────────────────────
                try:
                    m = metrics(
                        raw_trace  = pulse,
                        baseline_rq = ev_info["bs"].get(chan, NAN),
                        ptofamps    = ev_info["ptofamps"],
                        ptof_delay  = ev_info["delay"].get(chan, NAN),
                    )
                except Exception as e:
                    m = {"error": str(e)}

                # ── write TSV row ──────────────────────────────────────────
                row = [det, series, evn, chan]
                for col in MET_COLS:
                    row.append(fmt_val(m.get(col, "")))
                writer.writerow(row)
                n_rows_this_series += 1
                total_rows += 1

                # flush every 500 rows
                if total_rows % 500 == 0:
                    tsv_fh.flush()

                # ── accumulate for summary ─────────────────────────────────
                m["_series"] = series
                m["_event"]  = evn
                acc[det][chan].append(m)

    log(f"  events found in raw: {n_found}/{len(needed_events)}  rows written: {n_rows_this_series}")

tsv_fh.flush()
tsv_fh.close()
log(f"\nTSV complete: {total_rows} rows → {TSV_PATH}")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY FILE
# ─────────────────────────────────────────────────────────────────────────────
log("Writing summary...")

def _agg(rows, key, unit="", fmt=".4g"):
    """Aggregate a metric across rows, return formatted string."""
    vals = []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            fv = float(v)
            if np.isfinite(fv):
                vals.append(fv)
        except Exception:
            pass
    if not vals:
        return f"    {key}: NO DATA"
    a = np.array(vals)
    return (
        f"    {key} (n={len(a)}):  "
        f"median={np.median(a):{fmt}}{unit}  "
        f"mean={a.mean():{fmt}}{unit}  "
        f"std={a.std():{fmt}}{unit}  "
        f"[p5={np.percentile(a,5):{fmt}}  p16={np.percentile(a,16):{fmt}}  "
        f"p84={np.percentile(a,84):{fmt}}  p95={np.percentile(a,95):{fmt}}]{unit}  "
        f"min={a.min():{fmt}}  max={a.max():{fmt}}{unit}"
    )

def _pct(n, d):
    return f"{n/d*100:.1f}%" if d > 0 else "N/A"

def _fv(v, fmt=".4g"):
    if v is None or v == "":
        return "N/A"
    try:
        f = float(v)
        return f"{f:{fmt}}" if np.isfinite(f) else "nan"
    except Exception:
        return str(v)

def _iv(v):
    try:
        f = float(v)
        return int(f) if np.isfinite(f) else 0
    except Exception:
        return 0

SEP  = "=" * 90
sep  = "-" * 70

lines = [
    SEP,
    f"ALL-ZIPS SCAN SUMMARY   generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    SEP, "",
    f"Total TSV rows: {total_rows}",
    f"Series ({len(ALL_SERIES)}): {ALL_SERIES}",
    "",
    "PTOFamps ranges (Ge K-shell selection):",
]
for det in ALL_ZIPS:
    lo, hi = PTOF_RANGES[det]
    excl   = SERIES_EXCLUSIONS.get(det, [])
    lines.append(f"  Zip{det:2d}: [{lo:.3e}, {hi:.3e}]  excluded_series={excl or 'none'}")
lines.append("")

for det in ALL_ZIPS:
    chans = zip_chans.get(det, [])
    lines += [SEP, f"ZIP {det}   [{PTOF_RANGES[det][0]:.3e}, {PTOF_RANGES[det][1]:.3e}]", SEP]
    if not chans:
        lines += ["  No active channels.", ""]
        continue

    for chan in chans:
        rows = acc[det][chan]
        n    = len(rows)
        lines += ["", sep, f"  ZIP{det}  {chan}   total_events = {n}", sep]

        if n == 0:
            lines += ["    NO DATA", ""]
            continue

        # cut counts
        n_win  = sum(1 for r in rows if _iv(r.get("peak_in_win"))  == 1)
        n_snr  = sum(1 for r in rows if _iv(r.get("snr_pass"))     == 1)
        n_ush  = sum(1 for r in rows if _iv(r.get("undershoot_pass")) == 1)
        n_fit  = sum(1 for r in rows if _iv(r.get("fit_ok"))       == 1)
        n_all  = sum(1 for r in rows if _iv(r.get("all_pass"))     == 1)
        n_err  = sum(1 for r in rows if r.get("error","") not in ("","None","nan","0"))
        ok_rows = [r for r in rows if _iv(r.get("fit_ok")) == 1]

        lines += [
            "  --- CUT SUMMARY ---",
            f"    peak in window [{PEAK_LO},{PEAK_HI}]: {n_win}/{n} ({_pct(n_win,n)})",
            f"    SNR >= {MIN_SNR}:             {n_snr}/{n} ({_pct(n_snr,n)})",
            f"    undershoot > {MAX_UNDER:.0%}:    {n_ush}/{n} ({_pct(n_ush,n)})",
            f"    2-exp fit converged:    {n_fit}/{n} ({_pct(n_fit,n)})",
            f"    ALL cuts pass:          {n_all}/{n} ({_pct(n_all,n)})",
            f"    compute errors:         {n_err}/{n}",
            "",
            "  --- NOISE & BASELINE ---",
        ]
        for k, u in [("noise_std"," ADU"),("noise_rms"," ADU"),("noise_p2p"," ADU"),
                     ("noise_skew",""),("baseline_drift"," ADU"),
                     ("baseline_residual"," ADU"),
                     ("pretrig_lp_std"," ADU"),("pretrig_close_std"," ADU")]:
            lines.append(_agg(rows, k, u))

        lines += ["", "  --- PEAK ---"]
        for k, u in [("peak_lp"," ADU"),("peak_idx_lp"," samp"),
                     ("peak_dist_canonical"," samp"),("snr",""),
                     ("peak_raw"," ADU"),("pulse_integral"," ADU·s")]:
            lines.append(_agg(rows, k, u))

        lines += ["", "  --- UNDERSHOOT ---"]
        for k, u in [("undershoot_frac",""),("undershoot_min"," ADU"),
                     ("undershoot_idx"," samp")]:
            lines.append(_agg(rows, k, u))

        lines += ["", "  --- WAVEFORM SHAPE ---"]
        for k, u in [("rise_10_90_ms"," ms"),("rise_20_80_ms"," ms"),
                     ("half_rise_ms"," ms"),
                     ("fall_1e_ms"," ms"),("fall_half_ms"," ms"),("fall_tenth_ms"," ms")]:
            lines.append(_agg(rows, k, u))

        lines += ["", "  --- NORMALISED AMPLITUDE AT FIXED OFFSETS ---"]
        for k in ["amp_norm_0p5ms","amp_norm_1ms","amp_norm_2ms",
                  "amp_norm_5ms","amp_norm_10ms"]:
            lines.append(_agg(rows, k))

        lines += ["", "  --- 2-EXP FIT (converged events only) ---"]
        if ok_rows:
            for k, u in [("fit_t_rise_ms"," ms"),("fit_t_fall_ms"," ms"),
                         ("fit_ratio",""),("fit_pretrigger"," samp"),
                         ("fit_pt_dist"," samp"),
                         ("fit_nrmse",""),("fit_rmse"," ADU")]:
                lines.append(_agg(ok_rows, k, u))
            n_hi_nrmse = sum(1 for r in ok_rows
                             if np.isfinite(float(r.get("fit_nrmse", NAN)))
                             and float(r["fit_nrmse"]) > 0.30)
            lines += [
                f"    fit_nrmse > 0.30: {n_hi_nrmse}/{n_fit} ({_pct(n_hi_nrmse,n_fit)})",
            ]
        else:
            lines.append("    No successful fits.")

        lines += ["", "  --- PTOFdelay ALIGNMENT ---"]
        for k, u in [("delay_samp"," samp"),("dist_before_align"," samp"),
                     ("dist_after_align"," samp"),("aligned_peak_idx"," samp")]:
            lines.append(_agg(rows, k, u))

        # auto-flags
        flags = []
        if n < 20:             flags.append(f"VERY_FEW_EVENTS({n})")
        if n_win < n * 0.5:   flags.append(f"PEAK_OUT_OF_WINDOW_{100-n_win/n*100:.0f}pct")
        if n_snr < n * 0.5:   flags.append(f"LOW_SNR_{100-n_snr/n*100:.0f}pct_fail")
        if n_ush < n * 0.7:   flags.append(f"HIGH_UNDERSHOOT_{100-n_ush/n*100:.0f}pct")
        if n_fit < n * 0.4:   flags.append(f"HIGH_FIT_FAIL_{100-n_fit/n*100:.0f}pct")
        if ok_rows:
            mn = np.median([float(r["fit_nrmse"]) for r in ok_rows
                            if np.isfinite(float(r.get("fit_nrmse", NAN)))])
            if np.isfinite(mn) and mn > 0.25:
                flags.append(f"POOR_FIT_nrmse_median={mn:.3f}")
        lines += [
            "",
            f"  *** FLAGS: {' | '.join(flags)}" if flags else "  STATUS: OK",
            "",
        ]

        # per-event listing
        hdr = (f"  {'series':20s}  {'ev':>7s}  {'ptofamps':>12s}  "
               f"{'peak_lp':>10s}  {'peak_idx':>8s}  {'snr':>6s}  "
               f"{'undershoot':>11s}  {'rise10_90':>9s}  {'fall_1e':>7s}  "
               f"{'fit_ok':>6s}  {'t_rise_ms':>9s}  {'t_fall_ms':>9s}  "
               f"{'fit_pt':>8s}  {'nrmse':>7s}  {'all'}")
        lines += ["  --- EVERY EVENT ---", hdr]

        for r in sorted(rows, key=lambda x: (x.get("_series",""), x.get("_event", 0))):
            lines.append(
                f"  {r.get('_series','?'):20s}  "
                f"{r.get('_event', 0):>7d}  "
                f"{_fv(r.get('ptofamps'),'.4e'):>12s}  "
                f"{_fv(r.get('peak_lp'),'.3e'):>10s}  "
                f"{_fv(r.get('peak_idx_lp'),'.0f'):>8s}  "
                f"{_fv(r.get('snr'),'.2f'):>6s}  "
                f"{_fv(r.get('undershoot_frac'),'.4f'):>11s}  "
                f"{_fv(r.get('rise_10_90_ms'),'.4f'):>9s}  "
                f"{_fv(r.get('fall_1e_ms'),'.4f'):>7s}  "
                f"{_iv(r.get('fit_ok')):>6d}  "
                f"{_fv(r.get('fit_t_rise_ms'),'.4f'):>9s}  "
                f"{_fv(r.get('fit_t_fall_ms'),'.4f'):>9s}  "
                f"{_fv(r.get('fit_pretrigger'),'.1f'):>8s}  "
                f"{_fv(r.get('fit_nrmse'),'.4f'):>7s}  "
                f"{_iv(r.get('all_pass'))}"
            )
        lines.append("")

lines += [
    SEP, "METRIC REFERENCE", SEP,
    "noise_std            raw pre-trigger (0-5000) std, ADU",
    "noise_skew           pre-trigger skewness  (0=Gaussian, large→non-normal noise)",
    "baseline_drift       mean(2500-5000) - mean(0-2500), ADU  (slow drift check)",
    "baseline_residual    raw_mean - rq_baseline  (RQ accuracy check, should be ~0)",
    "pretrig_lp_std       LP-filtered std, samples 14000-15500",
    "pretrig_close_std    LP-filtered std, samples 15000-15800  (closest to pulse)",
    "peak_lp              LP peak amplitude, baseline-subtracted, ADU",
    "peak_idx_lp          sample index of LP peak  (nominal 15000-18000)",
    "peak_dist_canonical  peak_idx_lp - 16250",
    "snr                  peak_lp / noise_std",
    "undershoot_frac      min(tail 0-12000samp after peak) / peak  (> -0.05 required)",
    "rise_10_90_ms        10%-90% rise time, ms  (window: 3000 samp before peak)",
    "fall_1e_ms           time from peak to 1/e amplitude, ms",
    "fall_half_ms         time from peak to 50% amplitude, ms",
    "amp_norm_Xms         LP amplitude X ms after peak, normalised to peak",
    "pulse_integral       sum of LP trace in ±window around peak, ADU·s",
    "pileup_snr           max|LP| in 5000-14500 / noise_std  (pileup indicator)",
    "tail_sign_changes    sign flips in tail after peak  (ringing: higher = worse)",
    "fit_t_rise_ms        2-exp rise time constant, ms",
    "fit_t_fall_ms        2-exp fall time constant, ms",
    "fit_ratio            t_fall / t_rise",
    "fit_pretrigger       fitted pulse start sample  (floating ±600 from estimate)",
    "fit_pt_dist          fit_pretrigger - 16250  (should be small for good events)",
    "fit_nrmse            normalised RMS residual  (< 0.20 excellent, > 0.30 poor)",
    "dist_before_align    peak_idx_lp - 16250  (raw misalignment)",
    "dist_after_align     (peak_idx_lp + delay_samp) - 16250  (after PTOFdelay correction)",
    "all_pass             peak_in_win AND snr_pass AND undershoot_pass",
    "",
    f"Config: LP={LP_KHZ}kHz  peak_win=[{PEAK_LO},{PEAK_HI}]  SNR>={MIN_SNR}  "
    f"undershoot>{MAX_UNDER}  canonical={CANONICAL}",
]

with open(SUM_PATH, "w") as fh:
    fh.write("\n".join(lines) + "\n")

log(f"Summary written → {SUM_PATH}")
log(f"=== DONE {datetime.datetime.now()} ===")
