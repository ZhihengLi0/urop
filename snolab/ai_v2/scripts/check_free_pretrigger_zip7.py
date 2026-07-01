#!/usr/bin/env python3
"""
Diagnostic (NOT part of the main pipeline, does not touch the 126G pkl cache or
read_zip_all_series.py): test whether the fixed-pretrigger=16050 fit in
read_zip_all_series.py is distorting t_rise/t_fall, by re-fitting a sample of
events from raw_traces (already LP-filtered, peak-normalized, NOT pretrigger-
aligned) with pretrigger as a FREE parameter — same idea as the teacher's
NxM_cedar.ipynb two_exp_fit, where pretrigger floats during the fit and is only
overridden to a canonical value afterwards, when building the PCA dataset.

Compares old (fixed-pt, from pkl) vs new (free-pt, refit here) t_rise/t_fall/
nrmse for a sample of events drawn from the rise-fast and rise-slow KMeans
clusters (same clustering as template_from_pkl_v2.py's diagnostic plots).

Usage:
    python check_free_pretrigger_zip7.py --det 7 --n-sample 60
"""

import argparse, os, pickle, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from sklearn.cluster import KMeans

PKL_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
SAMPLERATE        = 625000
TRACELENGTH       = 32768
SECTION3_RISE_IDX = 16050
FIT_STRIDE        = 4
NRMSE_MAX         = 0.15

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
parser.add_argument('--n-sample', type=int, default=60,
                     help='events to resample per cluster per channel')
parser.add_argument('--pretrigger-window', type=int, default=1200,
                     help='samples of pretrigger jitter to allow around 16050')
args = parser.parse_args()
det        = args.det
N_SAMPLE   = args.n_sample
PT_WINDOW  = args.pretrigger_window

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                        'run', 'free_pretrigger_check'))
os.makedirs(OUT_DIR, exist_ok=True)

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
# wide fit window to tolerate pretrigger jitter in either direction
FIT_LO = SECTION3_RISE_IDX - PT_WINDOW - 300
FIT_HI = SECTION3_RISE_IDX + 5000
X_FIT  = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]


def two_exp_free_pt(x, amp, t_rise, t_fall, baseline, pretrigger):
    """Same functional form as read_zip_all_series.py's two_exp_fixed_pt,
    but pretrigger is now a free parameter (matches NxM_cedar.ipynb's two_exp_fit)."""
    dt = np.clip((x - pretrigger) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def refit_free_pretrigger(raw_trace, t_rise0, t_fall0):
    """Re-fit one raw_trace (already peak-normalized to ~1) with free pretrigger.
    Returns dict(t_rise, t_fall, pretrigger, nrmse) or None if fit fails."""
    y_fit = raw_trace[FIT_LO:FIT_HI:FIT_STRIDE].astype(np.float64)
    try:
        popt, _ = curve_fit(
            two_exp_free_pt, X_FIT, y_fit,
            p0=[1.0, t_rise0, t_fall0, 0.0, SECTION3_RISE_IDX],
            bounds=([0.0,   1e-6,  1e-5, -0.5, SECTION3_RISE_IDX - PT_WINDOW],
                    [np.inf, 8e-4,  8e-3,  0.5, SECTION3_RISE_IDX + PT_WINDOW]),
            maxfev=50000,
        )
        amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall):
            return None
        model = two_exp_free_pt(X_FIT, amp, t_rise, t_fall, bl, pt)
        nrmse = float(np.sqrt(np.mean((y_fit - model) ** 2)))
        return {"t_rise": t_rise, "t_fall": t_fall, "pretrigger": pt, "nrmse": nrmse}
    except Exception:
        return None


# ── Load pkl, collect same fit_ok+nrmse<=0.15 selection as template_from_pkl_v2 ──
series_dir = os.path.join(PKL_CACHE, f"zip{det}_series")
pkl_files = sorted([os.path.join(series_dir, f)
                     for f in os.listdir(series_dir) if f.endswith('.pkl')])
print(f"Found {len(pkl_files)} series pkl files for zip{det}")

channel_raws   = {c: [] for c in ALL_CHANS}
channel_trises = {c: [] for c in ALL_CHANS}   # old (fixed-pt) values from pkl
channel_tfalls = {c: [] for c in ALL_CHANS}
channel_nrmses = {c: [] for c in ALL_CHANS}

for pkl_path in pkl_files:
    with open(pkl_path, 'rb') as fh:
        data = pickle.load(fh)
    for c in ALL_CHANS:
        rts = data.get('raw_traces', {}).get(c, [])
        oks = data.get('fit_ok_mask', {}).get(c, [])
        fps = data.get('fit_params_ch', {}).get(c, [])
        for i in range(len(rts)):
            ok = bool(oks[i]) if i < len(oks) else False
            fp = fps[i] if i < len(fps) else None
            if not ok or fp is None or float(fp['nrmse']) > NRMSE_MAX:
                continue
            channel_raws[c].append(np.asarray(rts[i], dtype=np.float32))
            channel_trises[c].append(float(fp['t_rise']))
            channel_tfalls[c].append(float(fp['t_fall']))
            channel_nrmses[c].append(float(fp['nrmse']))

print("Loaded selection (same as template_from_pkl_v2.py fit_ok+nrmse<=0.15):")
for c in ALL_CHANS:
    print(f"  {c}: {len(channel_raws[c])} events")

# ── For each channel: cluster on OLD t_rise, sample fast/slow, refit with free pt ──
MIN_EVENTS = 20
report_lines = []
all_results = {}

for c in ALL_CHANS:
    n = len(channel_raws[c])
    if n < MIN_EVENTS:
        print(f"{c}: only {n} events, skip")
        continue

    trs_old = np.array(channel_trises[c])
    tfs_old = np.array(channel_tfalls[c])
    raws    = channel_raws[c]

    km = KMeans(n_clusters=2, n_init=10, random_state=0).fit((trs_old * 1e3).reshape(-1, 1))
    order = np.argsort(km.cluster_centers_.ravel())
    fast_idx = np.where(km.labels_ == order[0])[0]
    slow_idx = np.where(km.labels_ == order[1])[0]

    rng = np.random.default_rng(0)
    fast_sample = rng.choice(fast_idx, min(N_SAMPLE, len(fast_idx)), replace=False)
    slow_sample = rng.choice(slow_idx, min(N_SAMPLE, len(slow_idx)), replace=False)

    results = {"fast": [], "slow": []}
    for tag, sample in [("fast", fast_sample), ("slow", slow_sample)]:
        for i in sample:
            new_fit = refit_free_pretrigger(raws[i], trs_old[i], tfs_old[i])
            if new_fit is None:
                continue
            results[tag].append({
                "old_t_rise": trs_old[i], "old_t_fall": tfs_old[i],
                "old_nrmse": channel_nrmses[c][i],
                "new_t_rise": new_fit["t_rise"], "new_t_fall": new_fit["t_fall"],
                "new_pretrigger": new_fit["pretrigger"], "new_nrmse": new_fit["nrmse"],
            })
    all_results[c] = results

    line = (f"{c}: fast cluster old_t_rise median={np.median(trs_old[fast_idx])*1e3:.3f}ms, "
            f"slow cluster old_t_rise median={np.median(trs_old[slow_idx])*1e3:.3f}ms  |  "
            f"refit n_fast={len(results['fast'])} n_slow={len(results['slow'])}")
    print(line); report_lines.append(line)
    for tag in ["fast", "slow"]:
        if not results[tag]:
            continue
        old_tr = np.array([r["old_t_rise"] for r in results[tag]]) * 1e3
        new_tr = np.array([r["new_t_rise"] for r in results[tag]]) * 1e3
        old_nr = np.array([r["old_nrmse"] for r in results[tag]])
        new_nr = np.array([r["new_nrmse"] for r in results[tag]])
        new_pt = np.array([r["new_pretrigger"] for r in results[tag]])
        line2 = (f"    [{tag}] t_rise old_median={np.median(old_tr):.3f}ms -> "
                 f"new_median={np.median(new_tr):.3f}ms  |  "
                 f"nrmse old_median={np.median(old_nr):.3f} -> new_median={np.median(new_nr):.3f}  |  "
                 f"fitted pretrigger offset from 16050: median={np.median(new_pt - SECTION3_RISE_IDX):.1f} samples "
                 f"({np.median(new_pt - SECTION3_RISE_IDX)/SAMPLERATE*1e3:.3f}ms), "
                 f"std={np.std(new_pt - SECTION3_RISE_IDX):.1f} samples")
        print(line2); report_lines.append(line2)

with open(os.path.join(OUT_DIR, f"zip{det}_free_pretrigger_report.txt"), "w") as fh:
    fh.write("\n".join(report_lines) + "\n")

# ── Plot: old vs new t_rise, and pretrigger-offset distribution, per channel ──
active = [c for c in all_results if all_results[c]["fast"] or all_results[c]["slow"]]
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 3, figsize=(16, 3.3 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} — fixed-pretrigger (old) vs free-pretrigger (refit) comparison\n"
                 f"blue=rise-fast cluster, red=rise-slow cluster", fontsize=10)
    for row, c in enumerate(active):
        res = all_results[c]
        ax1, ax2, ax3 = axes[row, 0], axes[row, 1], axes[row, 2]
        for tag, color in [("fast", "steelblue"), ("slow", "crimson")]:
            if not res[tag]:
                continue
            old_tr = np.array([r["old_t_rise"] for r in res[tag]]) * 1e3
            new_tr = np.array([r["new_t_rise"] for r in res[tag]]) * 1e3
            old_nr = np.array([r["old_nrmse"] for r in res[tag]])
            new_nr = np.array([r["new_nrmse"] for r in res[tag]])
            new_pt = np.array([r["new_pretrigger"] for r in res[tag]])
            ax1.scatter(old_tr, new_tr, s=8, alpha=0.5, color=color, label=tag)
            ax2.scatter(old_nr, new_nr, s=8, alpha=0.5, color=color, label=tag)
            ax3.hist((new_pt - SECTION3_RISE_IDX) / SAMPLERATE * 1e3, bins=20,
                     alpha=0.5, color=color, label=tag)
        lims = ax1.get_xlim()
        ax1.plot(lims, lims, 'k--', lw=0.8, alpha=0.5)
        ax1.set_xlabel("old t_rise (ms, fixed pt)", fontsize=7)
        ax1.set_ylabel("new t_rise (ms, free pt)", fontsize=7)
        ax1.set_title(f"{c} t_rise: old vs new", fontsize=8)
        ax1.legend(fontsize=6); ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)

        lims2 = ax2.get_xlim()
        ax2.plot(lims2, lims2, 'k--', lw=0.8, alpha=0.5)
        ax2.set_xlabel("old NRMSE (fixed pt)", fontsize=7)
        ax2.set_ylabel("new NRMSE (free pt)", fontsize=7)
        ax2.set_title(f"{c} NRMSE: old vs new", fontsize=8)
        ax2.legend(fontsize=6); ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)

        ax3.axvline(0, color='k', lw=0.8, ls=':')
        ax3.set_xlabel("fitted pretrigger - 16050 (ms)", fontsize=7)
        ax3.set_title(f"{c} pretrigger offset (free fit)", fontsize=8)
        ax3.legend(fontsize=6); ax3.tick_params(labelsize=6); ax3.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, f"zip{det}_free_pretrigger_comparison.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"\nSaved: {OUT_DIR}/zip{det}_free_pretrigger_comparison.png")
    print(f"Saved: {OUT_DIR}/zip{det}_free_pretrigger_report.txt")

print("\nDone.")
print("INTERPRETATION:")
print("  - If 'slow' cluster's new_t_rise (free pt) drops down close to 'fast' cluster's range,")
print("    AND the fitted pretrigger offset for 'slow' events is large/non-zero,")
print("    -> the bimodal t_rise peak is mostly a FIXED-PRETRIGGER FITTING ARTIFACT.")
print("  - If 'slow' cluster's new_t_rise stays clearly separated from 'fast' even with free pt,")
print("    AND pretrigger offset is small for both clusters,")
print("    -> the bimodal t_rise peak reflects a REAL physical second population (e.g. surface vs bulk).")
