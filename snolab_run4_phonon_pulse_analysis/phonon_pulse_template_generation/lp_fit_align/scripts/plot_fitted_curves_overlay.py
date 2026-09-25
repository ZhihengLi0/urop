#!/usr/bin/env python3
"""Overlay of fitted smooth 2-exp curves, all regenerated from a common
pretrigger = 16050 (teacher's NxM_cedar.ipynb cell 27 style plot).

Reads only the per-series fit checkpoints written by lp_fit_align.py —
no raw pkl access, so it runs in seconds.
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
                          ALL_CHANS, CKPT_DIR, PLOT_DIR, RISE_REF_IDX,
                          SAMPLERATE, X_FULL, two_exp_free_pt)

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--max-curves", type=int, default=200)
parser.add_argument("--nrmse-max", type=float, default=None,
                    help="optionally keep only fits with NRMSE below this")
parser.add_argument("--trise-max", type=float, default=None,
                    help="optionally keep only fits with t_rise (s) below this")
args = parser.parse_args()

ckpt_dir = os.path.join(CKPT_DIR, f"zip{args.det}")
ckpts = sorted(f for f in os.listdir(ckpt_dir) if f.endswith("_fit.pkl"))
if not ckpts:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

params = {c: [] for c in ALL_CHANS}
for fname in ckpts:
    with open(os.path.join(ckpt_dir, fname), "rb") as fh:
        fits = pickle.load(fh)["fits"]
    for c in ALL_CHANS:
        for fp in fits.get(c) or []:
            if fp is None or not fp["fit_ok"]:
                continue
            if args.nrmse_max is not None and fp["nrmse"] > args.nrmse_max:
                continue
            if args.trise_max is not None and fp["t_rise"] > args.trise_max:
                continue
            params[c].append(fp)

lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 5000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
chans = [c for c in ALL_CHANS if params[c]]
cut = "fit_ok"
if args.nrmse_max is not None:
    cut += f", NRMSE<={args.nrmse_max}"
if args.trise_max is not None:
    cut += f", t_rise<={args.trise_max*1e3:.2f}ms"

fig, axes = plt.subplots(len(chans), 1, figsize=(10, 3.2 * len(chans)),
                         squeeze=False)
fig.suptitle(f"Zip{args.det} — fitted 2-exp curves, common pretrigger="
             f"{RISE_REF_IDX}, peak-normalized ({cut})", fontsize=11)
rng = np.random.default_rng(0)
for row, c in enumerate(chans):
    ax = axes[row, 0]
    fps = params[c]
    sel = rng.choice(len(fps), min(args.max_curves, len(fps)), replace=False)
    for i in sel:
        fp = fps[i]
        curve = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"],
                                0.0, float(RISE_REF_IDX))
        pk = float(np.max(curve))
        if pk <= 0:
            continue
        ax.plot(t_ms, curve / pk, lw=0.5, alpha=0.25, color="steelblue")
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="k", lw=0.8, ls=":")
    ax.set_title(f"{c}  showing {len(sel)} of {len(fps)} fits", fontsize=8)
    ax.set_xlabel("Time (ms)", fontsize=8)
    ax.set_ylabel("Norm. amp.", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)
fig.tight_layout()
add_pipeline_note(fig, "SMOOTH fitted 2-exp curves only (no measured data): each fit_ok "
                  "event's fitted (amp, t_rise, t_fall) re-evaluated at COMMON "
                  f"pretrigger=16050, peak-normalized; cut: {cut}")
suffix = f"_nrmse{args.nrmse_max}" if args.nrmse_max else ""
if args.trise_max is not None:
    suffix += f"_trise{args.trise_max*1e3:.2f}ms"
out = plot_path("fitted_curves_overlay", f"zip{args.det}_fitted_curves_overlay{suffix}.png")
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved: {out}")
