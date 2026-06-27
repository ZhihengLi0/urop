#!/usr/bin/env python3
"""
Read ALL series for one zip, all channels.
No event quality cuts — only PTOFamps window selection.
2-exp fit with pretrigger pinned to SECTION3_RISE_IDX.
Saves pkl: raw LP-filtered (norm) + analytical fit (norm) per channel.

Usage:
    python read_zip_all_series.py --det 19
"""

import argparse, os, pickle
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

try:
    import rawio
except ImportError as exc:
    raise RuntimeError("rawio is required inside the CDMS singularity environment") from exc

# ── paths ─────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

# ── constants ─────────────────────────────────────────────────────────────────
SAMPLERATE        = 625000
TRACELENGTH       = 32768
FILTER_KHZ        = 100.0
SECTION3_RISE_IDX = 16050
FIT_LO            = SECTION3_RISE_IDX - 300   # 15750
FIT_HI            = SECTION3_RISE_IDX + 5000  # 21050
FIT_STRIDE        = 4

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

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

PTOF_RANGES = {
     1: (2.96e-7, 5.40e-7),
     4: (4.44e-7, 8.10e-7),
     6: (3.33e-7, 6.08e-7),
     7: (1.48e-6, 2.70e-6),
     9: (5.93e-7, 1.08e-6),
    10: (5.93e-7, 1.08e-6),
    13: (1.19e-6, 2.16e-6),
    15: (7.41e-6, 1.35e-5),
    16: (1.33e-6, 2.43e-6),
    18: (1.04e-6, 1.89e-6),
    19: (4.44e-7, 8.10e-7),
    22: (3.70e-7, 6.75e-7),
    24: (4.44e-7, 8.10e-7),
}

# ── helpers ───────────────────────────────────────────────────────────────────
def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)

def two_exp_fixed_pt(x, amp, t_rise, t_fall, baseline):
    """2-exp pulse pinned to SECTION3_RISE_IDX — pretrigger is NOT a free param."""
    dt = np.clip((x - SECTION3_RISE_IDX) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= SECTION3_RISE_IDX, baseline, pulse + baseline)

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
X_FIT  = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]

def process_pulse(pulse_raw, baseline_rq):
    """
    Returns (raw_lp_norm, analytical_norm, fit_ok, reason, fit_params).
    fit_params = dict(t_rise, t_fall, nrmse) if fit succeeded, else None.
    """
    y = pulse_raw.astype(np.float64)
    if len(y) < TRACELENGTH:
        return None, None, False, f"short_trace_{len(y)}", None

    if np.isfinite(baseline_rq) and baseline_rq != -999999:
        bs = float(baseline_rq)
    else:
        bs = float(np.mean(y[:5000]))
    y -= bs

    y_lp = butter_lp(y)

    pre_base = float(np.median(y_lp[SECTION3_RISE_IDX - 700:SECTION3_RISE_IDX]))
    y_lp -= pre_base

    peak = float(np.max(y_lp[SECTION3_RISE_IDX:SECTION3_RISE_IDX + 5000]))
    if not np.isfinite(peak) or peak <= 0:
        return None, None, False, "bad_peak", None

    raw_lp_norm = (y_lp / peak).astype(np.float32)

    y_fit = y_lp[FIT_LO:FIT_HI:FIT_STRIDE]
    try:
        popt, _ = curve_fit(
            two_exp_fixed_pt, X_FIT, y_fit,
            p0=[peak, 6e-5, 2.8e-4, 0.0],
            bounds=([0.0,  1e-6,  1e-5, -0.5 * peak],
                    [np.inf, 8e-4,  8e-3,  0.5 * peak]),
            maxfev=50000,
        )
        amp, t_rise, t_fall, bl = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall):
            raise ValueError("unphysical")
        y_ana = two_exp_fixed_pt(X_FULL, amp, t_rise, t_fall, 0.0)
        ana_peak = float(np.max(y_ana))
        if ana_peak <= 0:
            raise ValueError("zero_ana_peak")
        analytical_norm = (y_ana / ana_peak).astype(np.float32)
        residuals = y_fit / peak - two_exp_fixed_pt(X_FIT, amp/peak, t_rise, t_fall, bl/peak)
        nrmse = float(np.sqrt(np.mean(residuals**2)))
        fit_params = {"t_rise": t_rise, "t_fall": t_fall, "nrmse": nrmse}
        return raw_lp_norm, analytical_norm, True, None, fit_params
    except Exception as exc:
        return raw_lp_norm, None, False, str(exc), None


# ── main ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
args = parser.parse_args()
det = args.det

RUN_DIR   = os.environ.get("RAW_WF_RUN_DIR", os.path.abspath("raw_without_filter/run"))
CACHE_DIR = os.path.join(RUN_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

cache_file = os.path.join(CACHE_DIR, f"zip{det}_all_series.pkl")

if det not in PTOF_RANGES:
    raise ValueError(f"zip{det} not in PTOF_RANGES")

ptof_lo, ptof_hi = PTOF_RANGES[det]
excluded = set(SERIES_EXCLUSIONS.get(det, []))
series_list = [s for s in ALL_SERIES if s not in excluded]
print(f"=== Zip{det}  PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}] ===")
print(f"Series to process ({len(series_list)}): {series_list}")

# ── step 1: collect selected event numbers from processed ROOT files ───────────
sel = {}   # series -> {evnum: baseline_rq per channel}
for series in series_list:
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(fpath):
        print(f"  {series}: processed file missing, skipping")
        continue
    try:
        with uproot.open(fpath) as f:
            trig   = f["rqDir/eventTree/TriggerType"].array(library="np")
            evnum  = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
            ptof   = f[f"rqDir/zip{det}/PTOFamps"].array(library="np")
            mask   = (trig == 1) & (ptof != -999999) & (ptof > ptof_lo) & (ptof < ptof_hi)
            evs    = evnum[mask]

            # find which channels exist for this detector
            if not series_list.index(series):  # first series only
                try:
                    _keys = list(f[f"rqDir/zip{det}"].keys())
                    chans = [c for c in ALL_CHANS if f"{c}OFdelay" in _keys]
                except Exception:
                    chans = ALL_CHANS

            baselines = {}
            for c in ALL_CHANS:
                try:
                    bs_arr = f[f"rqDir/zip{det}/{c}bs"].array(library="np")[mask]
                    baselines[c] = dict(zip(evs.tolist(), bs_arr.tolist()))
                except Exception:
                    baselines[c] = {}

        sel[series] = {"evnums": set(int(e) for e in evs), "baselines": baselines}
        print(f"  {series}: {len(evs)} events in PTOFamps window")
    except Exception as exc:
        print(f"  {series}: ERROR — {exc}")

# detect channels from first available series
chans = ALL_CHANS  # fallback; will be confirmed below

# ── step 2: read raw traces series by series ───────────────────────────────────
raw_traces    = {c: [] for c in ALL_CHANS}
ana_traces    = {c: [] for c in ALL_CHANS}
fit_ok_mask   = {c: [] for c in ALL_CHANS}
fit_params_ch = {c: [] for c in ALL_CHANS}  # list of dicts: t_rise, t_fall, nrmse
fail_reasons  = {c: {} for c in ALL_CHANS}  # reason -> count

for series, info in sel.items():
    evnum_set = info["evnums"]
    if not evnum_set:
        continue
    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        print(f"  {series}: raw directory missing, skipping")
        continue

    try:
        reader  = rawio.RawDataReader(raw_dir)
        nb      = reader.get_nb_events()
        total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
        events  = reader.read_events(
            output_format=2, skip_empty=True, trigger_types=[1],
            nb_events=total_e, detector_nums=[det], channel_names=ALL_CHANS,
        )
    except Exception as exc:
        print(f"  {series}: rawio error — {exc}")
        continue

    n_found = 0
    z_key = f"Z{det}"
    for event in events:
        evn = int(event["event"]["EventNumber"])
        if evn not in evnum_set:
            continue
        n_found += 1

        for chan in ALL_CHANS:
            try:
                pulse = event[z_key][chan]
            except KeyError:
                continue
            baseline_rq = info["baselines"].get(chan, {}).get(evn, np.nan)
            raw_n, ana_n, ok, reason, fpar = process_pulse(pulse, baseline_rq)
            if raw_n is None:
                fail_reasons[chan][reason] = fail_reasons[chan].get(reason, 0) + 1
                continue
            raw_traces[chan].append(raw_n)
            ana_traces[chan].append(ana_n)
            fit_ok_mask[chan].append(ok)
            fit_params_ch[chan].append(fpar)  # None if fit failed
            if not ok and reason:
                fail_reasons[chan][reason] = fail_reasons[chan].get(reason, 0) + 1

    print(f"  {series}: found {n_found}/{len(evnum_set)} events in raw files")

# ── step 3: summary ────────────────────────────────────────────────────────────
for c in ALL_CHANS:
    n_total  = len(raw_traces[c])
    n_fit_ok = sum(fit_ok_mask[c])
    if n_total:
        print(f"  {c}: {n_total} raw traces, {n_fit_ok} fit OK ({n_fit_ok/n_total*100:.0f}%)")

# ── step 4: save pkl ───────────────────────────────────────────────────────────
# Replace None ana entries with zeros so pkl stores uniform arrays cleanly.
# fit_ok_mask tracks which ones actually converged.
ana_traces_clean = {}
for c in ALL_CHANS:
    ana_clean = []
    for tr in ana_traces[c]:
        ana_clean.append(tr if tr is not None else np.zeros(TRACELENGTH, dtype=np.float32))
    ana_traces_clean[c] = ana_clean

with open(cache_file, "wb") as f:
    pickle.dump({
        "det":          det,
        "ptof_lo":      ptof_lo,
        "ptof_hi":      ptof_hi,
        "series_list":  series_list,
        "chans":        [c for c in ALL_CHANS if raw_traces[c]],
        "samplerate":   SAMPLERATE,
        "tracelength":  TRACELENGTH,
        "rise_idx":     SECTION3_RISE_IDX,
        "raw_traces":   {c: np.array(raw_traces[c], dtype=np.float32)
                         for c in ALL_CHANS if raw_traces[c]},
        "ana_traces":   {c: np.array(ana_traces_clean[c], dtype=np.float32)
                         for c in ALL_CHANS if raw_traces[c]},
        "fit_ok":       {c: np.array(fit_ok_mask[c], dtype=bool)
                         for c in ALL_CHANS if raw_traces[c]},
    }, f, protocol=pickle.HIGHEST_PROTOCOL)

print(f"\nSaved: {cache_file}")

# ── step 5: plot this zip (all channels, raw + analytical overlay) ─────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLOT_DIR = os.path.join(RUN_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

t_ms = X_FULL / SAMPLERATE * 1e3

WINDOWS = [
    ("full", SECTION3_RISE_IDX - 600,  SECTION3_RISE_IDX + 5500),
    ("zoom", SECTION3_RISE_IDX - 80,   SECTION3_RISE_IDX + 800),
]

active_chans = [c for c in ALL_CHANS if raw_traces[c]]
nrows = len(active_chans)

if nrows == 0:
    print("No traces to plot.")
else:
    fig, axes = plt.subplots(nrows, 4,   # 4 cols: raw-full, raw+ana-full, raw-zoom, raw+ana-zoom
                             figsize=(24, 3.5 * nrows),
                             squeeze=False)
    fig.suptitle(
        f"Zip{det}  —  blue=raw LP-filtered  red dashed=2-exp analytical fit\n"
        f"PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}]  |  pretrigger pinned @ {SECTION3_RISE_IDX}  |  no quality cuts",
        fontsize=9,
    )

    for row, chan in enumerate(active_chans):
        raw_arr = np.array(raw_traces[chan], dtype=np.float32)
        ana_arr = ana_traces_clean[chan]
        ok_arr  = np.array(fit_ok_mask[chan], dtype=bool)
        n_ev     = len(raw_arr)
        n_fit_ok = int(ok_arr.sum())

        for win_idx, (win_tag, lo, hi) in enumerate(WINDOWS):
            # col 0,2: raw only  |  col 1,3: raw + analytical overlay
            col_raw = win_idx * 2
            col_ov  = win_idx * 2 + 1

            ax_r = axes[row, col_raw]
            ax_o = axes[row, col_ov]

            for tr in raw_arr:
                ax_r.plot(t_ms[lo:hi], tr[lo:hi], lw=0.5, alpha=0.15, color="steelblue")
            ax_r.axvline(t_ms[SECTION3_RISE_IDX], color="k", lw=0.8, ls=":", alpha=0.5)
            ax_r.set_title(f"{chan} raw [{win_tag}]  n={n_ev}", fontsize=7)
            ax_r.set_xlabel("Time (ms)", fontsize=7)
            ax_r.set_ylabel("Norm. amp.", fontsize=7)
            ax_r.grid(alpha=0.2, ls=":")
            ax_r.tick_params(labelsize=6)

            for tr_r, tr_a, ok in zip(raw_arr, ana_arr, ok_arr):
                ax_o.plot(t_ms[lo:hi], tr_r[lo:hi], lw=0.5, alpha=0.15, color="steelblue")
                if ok:
                    ax_o.plot(t_ms[lo:hi], tr_a[lo:hi], lw=0.8, alpha=0.35,
                              color="crimson", ls="--")
            ax_o.axvline(t_ms[SECTION3_RISE_IDX], color="k", lw=0.8, ls=":", alpha=0.5)
            ax_o.set_title(f"{chan} raw+fit [{win_tag}]  fit_ok={n_fit_ok}/{n_ev}", fontsize=7)
            ax_o.set_xlabel("Time (ms)", fontsize=7)
            ax_o.grid(alpha=0.2, ls=":")
            ax_o.tick_params(labelsize=6)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_png = os.path.join(PLOT_DIR, f"zip{det}_all_channels_raw_vs_ana.png")
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot: {out_png}")

print(f"Done. Zip{det} complete.")

# ── step 6: write text summary ────────────────────────────────────────────────
import datetime
txt_path = os.path.join(PLOT_DIR, f"zip{det}_summary.txt")
lines = []
lines.append("=" * 70)
lines.append(f"SUMMARY: Zip{det}   (generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})")
lines.append("=" * 70)
lines.append(f"PTOFamps range : [{ptof_lo:.3e}, {ptof_hi:.3e}]")
lines.append(f"Series used    : {len(series_list)}  (excluded: {sorted(excluded) if excluded else 'none'})")
lines.append(f"Series list    : {series_list}")
lines.append(f"Pretrigger     : pinned to sample {SECTION3_RISE_IDX}  ({SECTION3_RISE_IDX/SAMPLERATE*1e3:.3f} ms)")
lines.append(f"Fit window     : samples [{FIT_LO}, {FIT_HI}]  stride={FIT_STRIDE}")
lines.append(f"LP filter      : {FILTER_KHZ} kHz  (display only, no events rejected)")
lines.append("")

total_raw = sum(len(raw_traces[c]) for c in ALL_CHANS)
total_ok  = sum(sum(fit_ok_mask[c]) for c in ALL_CHANS)
lines.append(f"TOTALS across all channels:")
lines.append(f"  Raw traces stored : {total_raw}")
lines.append(f"  Fit succeeded     : {total_ok}  ({total_ok/max(total_raw,1)*100:.1f}%)")
lines.append("")
lines.append("-" * 70)
lines.append("PER-CHANNEL STATISTICS")
lines.append("-" * 70)

T_RISE_BOUND_LO = 1e-6   # lower bound in fit
T_RISE_BOUND_HI = 8e-4

for chan in ALL_CHANS:
    n_raw = len(raw_traces[chan])
    if n_raw == 0:
        lines.append(f"\n{chan}: NO DATA")
        continue

    ok_arr  = np.array(fit_ok_mask[chan], dtype=bool)
    n_ok    = int(ok_arr.sum())
    n_fail  = n_raw - n_ok
    pct_ok  = n_ok / n_raw * 100

    good_params = [p for p in fit_params_ch[chan] if p is not None]

    lines.append(f"\n{chan}:")
    lines.append(f"  Events (raw traces)   : {n_raw}")
    lines.append(f"  Fit succeeded         : {n_ok} / {n_raw}  ({pct_ok:.1f}%)")
    lines.append(f"  Fit failed            : {n_fail}")
    if fail_reasons[chan]:
        for r, cnt in sorted(fail_reasons[chan].items(), key=lambda x: -x[1]):
            lines.append(f"    reason '{r}': {cnt}")

    if good_params:
        t_rises = np.array([p["t_rise"] * 1e3 for p in good_params])  # ms
        t_falls = np.array([p["t_fall"] * 1e3 for p in good_params])  # ms
        nrmses  = np.array([p["nrmse"]        for p in good_params])

        n_rise_lo  = int(np.sum(t_rises <= T_RISE_BOUND_LO * 1e3 * 1.01))
        n_rise_hi  = int(np.sum(t_rises >= T_RISE_BOUND_HI * 1e3 * 0.99))
        n_bad_nrms = int(np.sum(nrmses > 0.3))

        lines.append(f"  t_rise (ms)  median={np.median(t_rises):.4f}  std={np.std(t_rises):.4f}"
                     f"  [p16={np.percentile(t_rises,16):.4f}, p84={np.percentile(t_rises,84):.4f}]"
                     f"  min={t_rises.min():.4f}  max={t_rises.max():.4f}")
        lines.append(f"  t_fall (ms)  median={np.median(t_falls):.4f}  std={np.std(t_falls):.4f}"
                     f"  [p16={np.percentile(t_falls,16):.4f}, p84={np.percentile(t_falls,84):.4f}]"
                     f"  min={t_falls.min():.4f}  max={t_falls.max():.4f}")
        lines.append(f"  t_fall/t_rise ratio  median={np.median(t_falls/t_rises):.2f}")
        lines.append(f"  nrmse        median={np.median(nrmses):.4f}  max={nrmses.max():.4f}"
                     f"  (n>{0.3}: {n_bad_nrms}/{n_ok}  = {n_bad_nrms/n_ok*100:.1f}%)")
        lines.append(f"  t_rise at lower bound ({T_RISE_BOUND_LO*1e3:.4f} ms): {n_rise_lo}/{n_ok}")
        lines.append(f"  t_rise at upper bound ({T_RISE_BOUND_HI*1e3:.3f} ms): {n_rise_hi}/{n_ok}")

        # flag assessment
        flags = []
        if n_raw < 10:
            flags.append("VERY FEW EVENTS — possibly dead channel")
        if pct_ok < 50:
            flags.append(f"LOW FIT RATE ({pct_ok:.0f}%) — pulse shape may not match 2-exp")
        if n_rise_lo > n_ok * 0.3:
            flags.append(f"t_rise hitting lower bound in {n_rise_lo/n_ok*100:.0f}% events — rise too fast or misfit")
        if np.median(nrmses) > 0.25:
            flags.append(f"HIGH median nrmse={np.median(nrmses):.3f} — poor fit quality")
        if np.std(t_rises) > np.median(t_rises):
            flags.append(f"t_rise highly variable (std/median={np.std(t_rises)/np.median(t_rises):.2f}) — inconsistent pulses")
        if flags:
            lines.append(f"  *** FLAGS: {' | '.join(flags)}")
        else:
            lines.append(f"  STATUS: OK")

lines.append("")
lines.append("=" * 70)
lines.append("INTERPRETATION GUIDE")
lines.append("=" * 70)
lines.append("t_rise   : phonon pulse rise time (detector response, ~0.04-0.3 ms typical)")
lines.append("t_fall   : phonon pulse fall time (thermal relaxation, ~0.1-3 ms typical)")
lines.append("nrmse    : normalised RMS fit residual; <0.2 good, 0.2-0.3 acceptable, >0.3 poor")
lines.append("t_rise at lower/upper bound: fit hitting constraint — result unreliable")
lines.append("Fit failed: pulse shape not captured by 2-exp; check plot for that channel")
lines.append("")
lines.append("NEXT STEP DECISION:")
lines.append("  If nrmse < 0.25 and fit rate > 80% and t_rise stable:")
lines.append("    → 2-exp model is good, use median t_rise/t_fall as template seed")
lines.append("  If t_rise hits lower bound often:")
lines.append("    → actual rise faster than 2-exp allows, or pretrigger offset wrong")
lines.append("  If fit rate < 50% or nrmse > 0.3 for most channels:")
lines.append("    → consider different model or check pretrigger index for this zip")

with open(txt_path, "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved summary: {txt_path}")
