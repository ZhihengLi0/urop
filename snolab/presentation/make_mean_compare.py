#!/usr/bin/env python3
"""Weighted vs plain mean of the same fit_ok fitted curves (Z7 PBS1).

One combined figure, each curve computed over EXACTLY the population of
its deliverable:
  solid red    — NRMSE-weighted mean, w = 1/max(NRMSE,0.01)^2, over ALL fit_ok
                 curves (exactly how the delivered 1x1 template is built)
  dashed navy  — plain mean, no weights, over the PCA input population
                 fit_ok + NRMSE <= 0.4 + t_rise <= 0.3 ms (exactly nxm0)
Both peak-normalized; zoom kept tight on the pulse (the late tail is flat and
carries no information). Output: figures/mean_compare_zip7_PBS1.png
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

fig, ax = plt.subplots(figsize=(11.5, 3.0))
ax.plot(t_ms, mw, lw=2.6, color="#C0392B",
        label="NRMSE-weighted mean of all fit_ok curves (n = 2008)  =  the 1x1 template")
ax.plot(t_ms, mp, lw=2.2, ls=(0, (6, 4)), color="#1F3864",
        label="plain mean of the PCA input curves (n = 1931)  =  nxm0")
ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
ax.set_title(f"Z{DET} {CHAN}: the two averages, drawn on top of each other", fontsize=12)
ax.set_xlabel("Time (ms)", fontsize=11)
ax.set_ylabel("Norm. amp.", fontsize=11)
ax.legend(fontsize=10)
ax.grid(alpha=0.25)
fig.tight_layout()
out = os.path.join(HERE, "figures", "mean_compare_zip7_PBS1.png")
fig.savefig(out, dpi=170, bbox_inches="tight")
print(f"saved {out}")
print(f"weighted: n={n_w} (all fit_ok) | plain: n={n_p} (NRMSE<=0.4 & t_rise<=0.3ms)")
