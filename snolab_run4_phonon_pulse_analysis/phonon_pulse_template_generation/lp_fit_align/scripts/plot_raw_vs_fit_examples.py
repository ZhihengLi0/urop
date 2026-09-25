#!/usr/bin/env python3
"""Overlay raw pulse, 100kHz LP pulse, and fitted 2-exp curve for a few
example events. Standalone diagnostic; reuses lp_fit_align helpers."""

import argparse
import os
import pickle
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path,
                          ALL_CHANS, BASELINE_HI, BASELINE_LO, CACHE_DIR_DEFAULT,
                          PLOT_DIR, RISE_REF_IDX, SAMPLERATE, TRACELENGTH,
                          X_FULL, fit_trace, lowpass, two_exp_free_pt)

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, default=7)
parser.add_argument("--series", default=None)
parser.add_argument("--n", type=int, default=6)
args = parser.parse_args()

series_dir = os.path.join(CACHE_DIR_DEFAULT, f"zip{args.det}_series")
series = args.series or sorted(f for f in os.listdir(series_dir)
                               if f.endswith(".pkl"))[0][:-4]
with open(os.path.join(series_dir, f"{series}.pkl"), "rb") as fh:
    payload = pickle.load(fh)

examples = []
for c in ALL_CHANS:
    traces = payload["raw_traces"].get(c, [])
    events = payload["event_numbers_ch"].get(c, [])
    best = None
    for i, tr in enumerate(traces[:15]):
        tr = np.asarray(tr, dtype=np.float64)
        if tr.size != TRACELENGTH:
            continue
        y_lp = lowpass(tr)
        baseline = float(np.median(y_lp[BASELINE_LO:BASELINE_HI]))
        peak = float(np.max(y_lp - baseline))
        if peak <= 0:
            continue
        y_norm = (y_lp - baseline) / peak
        fp = fit_trace(y_norm)
        if fp is None or not fp["fit_ok"]:
            continue
        raw_norm = (tr - baseline) / peak
        if best is None or fp["nrmse"] < best[4]["nrmse"]:
            best = (c, int(events[i]), raw_norm, y_norm, fp)
    if best is not None:
        examples.append(best)

# prefer genuinely good fits; if the detector has too few (noise-dominated
# selection), fall back to its best available fits so the plot still shows
# honestly what this detector looks like
examples.sort(key=lambda e: e[4]["nrmse"])
good = [e for e in examples if e[4]["nrmse"] < 0.3]
examples = (good if len(good) >= args.n else examples)[:args.n]

lo, hi = RISE_REF_IDX - 600, RISE_REF_IDX + 4500
t_ms = X_FULL / SAMPLERATE * 1e3
ncols, nrows = 2, (len(examples) + 1) // 2
fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.6 * nrows), squeeze=False)
fig.suptitle(f"Zip{args.det} series {series} — raw pulse vs 100kHz LP vs "
             f"free-pretrigger 2-exp fit", fontsize=11)
for k, (c, ev, raw_norm, y_norm, fp) in enumerate(examples):
    ax = axes[k // ncols, k % ncols]
    model = two_exp_free_pt(X_FULL, fp["amp"], fp["t_rise"], fp["t_fall"],
                            fp["baseline"], fp["pretrigger"])
    ax.plot(t_ms[lo:hi], raw_norm[lo:hi], lw=0.5, alpha=0.45, color="gray",
            label="raw (unfiltered)")
    ax.plot(t_ms[lo:hi], y_norm[lo:hi], lw=0.9, color="steelblue",
            label="100kHz LP")
    ax.plot(t_ms[lo:hi], model[lo:hi], lw=1.6, color="crimson",
            label="2-exp fit (free pretrigger)")
    ax.axvline(fp["pretrigger"] / SAMPLERATE * 1e3, color="crimson", lw=0.8,
               ls="--", alpha=0.6)
    ax.axvline(t_ms[RISE_REF_IDX], color="k", lw=0.8, ls=":", alpha=0.6)
    ax.set_title(f"{c}  event {ev}   t_rise={fp['t_rise']*1e3:.3f}ms  "
                 f"t_fall={fp['t_fall']*1e3:.3f}ms\n"
                 f"pretrigger={fp['pretrigger']:.1f}  NRMSE={fp['nrmse']:.3f}",
                 fontsize=8)
    ax.set_xlabel("Time (ms)", fontsize=8)
    ax.set_ylabel("Norm. amp.", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)
    if k == 0:
        ax.legend(fontsize=8)
for k in range(len(examples), nrows * ncols):
    axes[k // ncols, k % ncols].axis("off")
fig.tight_layout()
add_pipeline_note(fig, "RAW unfiltered trace (gray) + 100kHz LP (blue) + fitted 2-exp "
                  "curve (red); one example per channel = lowest-NRMSE fit_ok event of "
                  "first 15 traces (falls back to best available on noise detectors); "
                  "red dashed = fitted pretrigger, black dotted = 16050 reference")
out = plot_path("raw_vs_fit_examples", f"zip{args.det}_raw_vs_fit_examples.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print(f"Saved: {out}  ({len(examples)} examples)")
