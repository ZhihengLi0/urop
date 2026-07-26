#!/usr/bin/env python3
"""Weighted vs plain mean of the same fit_ok fitted curves (Z7 PBS1).

Left:  NRMSE-weighted mean, w = 1/max(NRMSE,0.01)^2  (the 1x1 template)
Right: plain mean, no weights  (= nxm0, the NxM mean template)
Both peak-normalized, zoomed to the pulse so the difference is visible.
Output: figures/mean_compare_zip7_PBS1.png
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
lo, hi = RISE_REF_IDX - 300, RISE_REF_IDX + 3200
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3

acc_w = np.zeros(hi - lo); wsum = 0.0
acc_p = np.zeros(hi - lo); n = 0
ck = os.path.join(CKPT_DIR, f"zip{DET}")
for f in sorted(os.listdir(ck)):
    if not f.endswith("_fit.pkl"):
        continue
    for fp in pickle.load(open(os.path.join(ck, f), "rb"))["fits"].get(CHAN) or []:
        if fp is None or not fp["fit_ok"]:
            continue
        y = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"], 0.0,
                            float(RISE_REF_IDX))
        pk = float(np.max(y))
        if pk <= 0 or not np.isfinite(pk):
            continue
        y = y / pk
        w = 1.0 / max(fp["nrmse"], 0.01) ** 2
        acc_w += y * w; wsum += w
        acc_p += y; n += 1
mw = acc_w / wsum; mw /= mw.max()
mp = acc_p / n;    mp /= mp.max()

fig, axes = plt.subplots(1, 2, figsize=(12.6, 3.9), sharey=True)
for ax, arr, ttl, col in [
        (axes[0], mw, f"NRMSE-weighted mean  (the 1x1 template)", "#C0392B"),
        (axes[1], mp, f"plain mean, no weights  (= nxm0)", "#1F3864")]:
    ax.plot(t_ms, arr, lw=2.4, color=col)
    ax.plot(t_ms, mw if arr is mp else mp, lw=1.0, ls="--", color="gray",
            alpha=0.8, label="the other mean (dashed) for comparison")
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
    ax.set_title(f"Z{DET} {CHAN}: {ttl}", fontsize=12)
    ax.set_xlabel("Time (ms)", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
axes[0].set_ylabel("Norm. amp.", fontsize=11)
fig.tight_layout()
out = os.path.join(HERE, "figures", "mean_compare_zip7_PBS1.png")
fig.savefig(out, dpi=170, bbox_inches="tight")
print(f"saved {out}  (n={n} curves)")
