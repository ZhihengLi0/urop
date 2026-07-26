#!/usr/bin/env python3
"""Weighted vs plain mean of the same fit_ok fitted curves (Z7 PBS1).

Two separate single-panel figures (placed side by side on the NxM slide),
each computed over EXACTLY the population of its deliverable:
  figures/mean_weighted_zip7_PBS1.png — NRMSE-weighted mean, w = 1/max(NRMSE,0.01)^2,
      over ALL fit_ok curves (exactly how the delivered 1x1 template is built)
  figures/mean_plain_zip7_PBS1.png    — plain mean, no weights, over the PCA input
      population fit_ok + NRMSE <= 0.4 + t_rise <= 0.3 ms (exactly nxm0)
Both peak-normalized; zoom kept tight on the pulse (the late tail is flat and
carries no information). Dashed gray = the other mean, for comparison.
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
lo, hi = RISE_REF_IDX - 200, RISE_REF_IDX + 1300
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3

acc_w = np.zeros(hi - lo); wsum = 0.0
acc_p = np.zeros(hi - lo); n_w = 0; n_p = 0
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
        n_w += 1
        if fp["nrmse"] <= 0.4 and fp["t_rise"] <= 3e-4:   # the PCA input cut
            acc_p += y; n_p += 1
mw = acc_w / wsum; mw /= mw.max()
mp = acc_p / n_p;  mp /= mp.max()

for arr, other, ttl, col, fname in [
        (mw, mp, "NRMSE-weighted mean  (the 1x1 template)", "#C0392B",
         "mean_weighted_zip7_PBS1.png"),
        (mp, mw, "plain mean, no weights  (= nxm0)", "#1F3864",
         "mean_plain_zip7_PBS1.png")]:
    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    ax.plot(t_ms, arr, lw=2.4, color=col)
    ax.plot(t_ms, other, lw=1.0, ls="--", color="gray", alpha=0.8,
            label="the other mean (dashed) for comparison")
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
    ax.set_title(f"Z{DET} {CHAN}: {ttl}", fontsize=12)
    ax.set_xlabel("Time (ms)", fontsize=11)
    ax.set_ylabel("Norm. amp.", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out = os.path.join(HERE, "figures", fname)
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")
print(f"weighted: n={n_w} (all fit_ok) | plain: n={n_p} (NRMSE<=0.4 & t_rise<=0.3ms)")
