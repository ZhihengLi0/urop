#!/usr/bin/env python3
"""One figure combining three views per channel (teacher-requested):

  1. gray-blue : shift-aligned MEASURED low-pass traces (fit_ok, no cut),
                 WITHOUT the mean line
  2. green     : fitted smooth 2-exp curves (common pretrigger 16050,
                 peak-normalized) for events PASSING the NRMSE cut
  3. red       : same fitted curves for events REJECTED by the NRMSE cut

Median NRMSE of the pass / rejected populations is stamped in the top-right
corner of every panel.

Measured traces come from the raw cache (only as many series as needed to
fill the display quota); fitted curves come from the fit checkpoints.

Usage:
    python3 plot_overlay_fan_cut.py --det 7 [--nrmse-max 0.4]
"""

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
                          ALL_CHANS, CACHE_DIR_DEFAULT, CKPT_DIR, RISE_REF_IDX,
                          SAMPLERATE, X_FULL, normalize_trace, shift_align,
                          two_exp_free_pt)

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--nrmse-max", type=float, default=0.4)
parser.add_argument("--n-traces", type=int, default=120,
                    help="measured traces drawn per channel")
parser.add_argument("--n-curves", type=int, default=120,
                    help="fitted curves drawn per group per channel")
parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
args = parser.parse_args()
det, CUT = args.det, args.nrmse_max

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
series_list = sorted(f[:-len("_fit.pkl")] for f in os.listdir(ckpt_dir)
                     if f.endswith("_fit.pkl"))
if not series_list:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

# ── collect fit params (all series) and measured traces (until quota) ────────
fits_all = {c: [] for c in ALL_CHANS}          # every fit_ok fit of the zip
measured = {c: [] for c in ALL_CHANS}          # shifted measured traces (quota)

for series in series_list:
    with open(os.path.join(ckpt_dir, f"{series}_fit.pkl"), "rb") as fh:
        fits = pickle.load(fh)["fits"]
    for c in ALL_CHANS:
        fits_all[c] += [fp for fp in (fits.get(c) or [])
                        if fp is not None and fp["fit_ok"]]

    if all(len(measured[c]) >= args.n_traces for c in ALL_CHANS
           if fits.get(c)):
        continue  # display quota already filled; only fits were needed
    raw_path = os.path.join(args.cache_dir, f"zip{det}_series", f"{series}.pkl")
    if not os.path.exists(raw_path):
        continue
    with open(raw_path, "rb") as fh:
        raw_traces = pickle.load(fh)["raw_traces"]
    for c in ALL_CHANS:
        traces = raw_traces.get(c, [])
        for i, fp in enumerate(fits.get(c) or []):
            if len(measured[c]) >= args.n_traces:
                break
            if fp is None or not fp["fit_ok"] or i >= len(traces):
                continue
            y_norm = normalize_trace(traces[i])
            if y_norm is None:
                continue
            measured[c].append(
                shift_align(y_norm, fp["pretrigger"]).astype(np.float32))
    del raw_traces

# ── figure ────────────────────────────────────────────────────────────────────
lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 5000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
rng = np.random.default_rng(0)
chans = [c for c in ALL_CHANS if fits_all[c]]

fig, axes = plt.subplots(len(chans), 1, figsize=(11, 3.0 * len(chans)),
                         squeeze=False)
fig.suptitle(f"Zip{det} — aligned measured traces + fitted curves split by "
             f"NRMSE cut {CUT}", fontsize=11)
for row, c in enumerate(chans):
    ax = axes[row, 0]
    for tr in measured[c]:
        ax.plot(t_ms, tr[lo:hi], lw=0.4, alpha=0.18, color="lightsteelblue",
                zorder=1)
    keep = [fp for fp in fits_all[c] if fp["nrmse"] <= CUT]
    rej = [fp for fp in fits_all[c] if fp["nrmse"] > CUT]
    for fps, color, z in [(rej, "crimson", 2), (keep, "seagreen", 3)]:
        if not fps:
            continue
        for i in rng.choice(len(fps), min(args.n_curves, len(fps)),
                            replace=False):
            fp = fps[i]
            y = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"],
                                0.0, float(RISE_REF_IDX))
            pk = float(np.max(y))
            if pk > 0:
                ax.plot(t_ms, y / pk, lw=0.5, alpha=0.25, color=color,
                        zorder=z)
    ax.axvline(t_ms[RISE_REF_IDX - lo], color="k", lw=0.8, ls=":", zorder=4)
    med_keep = np.median([fp["nrmse"] for fp in keep]) if keep else float("nan")
    med_rej = np.median([fp["nrmse"] for fp in rej]) if rej else float("nan")
    ax.text(0.995, 0.97,
            f"median NRMSE\npass {med_keep:.3f} (n={len(keep)})\n"
            f"rejected {med_rej:.3f} (n={len(rej)})",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            family="monospace",
            bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"))
    handles = [plt.Line2D([], [], color="lightsteelblue", lw=1.5),
               plt.Line2D([], [], color="seagreen", lw=1.5),
               plt.Line2D([], [], color="crimson", lw=1.5)]
    ax.legend(handles,
              [f"measured, aligned (showing {len(measured[c])})",
               f"fit curves, NRMSE<={CUT}",
               f"fit curves, NRMSE>{CUT} (cut away)"],
              fontsize=7, loc="upper left")
    ax.set_title(f"{c}", fontsize=9)
    ax.set_xlabel("Time (ms)", fontsize=8)
    ax.set_ylabel("Norm. amp.", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)
fig.tight_layout()
add_pipeline_note(fig, "three views in one panel: shift-aligned MEASURED LP traces "
                  "(gray-blue, fit_ok, NO mean line) + SMOOTH fitted 2-exp curves at "
                  "common pretrigger 16050, peak-normalized, split by the NRMSE cut: "
                  f"green = NRMSE<={CUT} (kept), red = NRMSE>{CUT} (cut away); "
                  "top-right box = median NRMSE and counts of each population")
out = plot_path("overlay_fan_cut", f"zip{det}_overlay_fan_cut_nrmse{CUT}.png")
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved: {out}")
