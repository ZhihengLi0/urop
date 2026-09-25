#!/usr/bin/env python3
"""Before/after fans for the NRMSE-cut comparison slide (Z7 PBS1), ALL curves
drawn, no sampling:

  figures/fan_zip7_PBS1_before_all.png : every fit_ok fitted curve (n = 2008)
  figures/fan_zip7_PBS1_after_all.png  : fit_ok AND NRMSE <= 0.4  (n = 1931)

Peak-normalized at the common pretrigger 16050, zoomed to the pulse.
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
fits = []
for f in sorted(os.listdir(ck)):
    if not f.endswith("_fit.pkl"):
        continue
    for fp in pickle.load(open(os.path.join(ck, f), "rb"))["fits"].get(CHAN) or []:
        if fp is not None and fp["fit_ok"]:
            fits.append(fp)

lo, hi = RISE_REF_IDX - 300, RISE_REF_IDX + 1800
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3

for sel, ttl, fname in [
        (lambda fp: True, "all fit_ok curves", "fan_zip7_PBS1_before_all.png"),
        (lambda fp: fp["nrmse"] <= 0.4, "after NRMSE ≤ 0.4",
         "fan_zip7_PBS1_after_all.png")]:
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    n = 0
    for fp in fits:
        if not sel(fp):
            continue
        y = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"], 0.0,
                            float(RISE_REF_IDX))
        pk = float(np.max(y))
        if pk > 0 and np.isfinite(pk):
            ax.plot(t_ms, y / pk, lw=0.45, alpha=0.14, color="steelblue")
            n += 1
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
    ax.set_title(f"Z{DET} {CHAN}: {ttl}   (n = {n})", fontsize=12)
    ax.set_xlabel("Time (ms)", fontsize=11)
    ax.set_ylabel("Norm. amp.", fontsize=11)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out = os.path.join(HERE, "figures", fname)
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}  (n={n})")
