#!/usr/bin/env python3
"""Fan of ALL fitted curves for one channel, absolutely no cuts.

Every converged fit is drawn (fit_ok true or false; no NRMSE, no rise-time
requirement) at the common pretrigger 16050, peak-normalized. Nothing is
sampled, so the count on the figure equals the curves drawn.
Output: figures/fan_zip7_PBS1_allfits.png
"""
import os, pickle, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lp_fit_align", "scripts"))
from lp_fit_align import CKPT_DIR, RISE_REF_IDX, SAMPLERATE, X_FULL, two_exp_free_pt

DET, CHAN = 7, "PBS1"
ck = os.path.join(CKPT_DIR, f"zip{DET}")
fits, n_traces = [], 0
for f in sorted(os.listdir(ck)):
    if not f.endswith("_fit.pkl"):
        continue
    for fp in pickle.load(open(os.path.join(ck, f), "rb"))["fits"].get(CHAN) or []:
        n_traces += 1
        if fp is not None:
            fits.append(fp)

lo, hi = RISE_REF_IDX - 300, RISE_REF_IDX + 3200
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
fig, ax = plt.subplots(figsize=(9.2, 4.6))
n_drawn = 0
for fp in fits:
    y = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"], 0.0,
                        float(RISE_REF_IDX))
    pk = float(np.max(y))
    if pk > 0 and np.isfinite(pk):
        ax.plot(t_ms, y / pk, lw=0.45, alpha=0.16, color="steelblue")
        n_drawn += 1
ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
ax.set_title(f"Z{DET} {CHAN}: every fitted event, no cuts   "
             f"(n = {n_drawn} events)", fontsize=12)
ax.set_xlabel("Time (ms)", fontsize=11)
ax.set_ylabel("Norm. amp.", fontsize=11)
ax.grid(alpha=0.25)
fig.tight_layout()
out = os.path.join(HERE, "figures", "fan_zip7_PBS1_allfits.png")
fig.savefig(out, dpi=160, bbox_inches="tight")
print(f"Saved: {out}  (drawn {n_drawn} of {n_traces} traces)")
