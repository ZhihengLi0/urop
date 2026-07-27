#!/usr/bin/env python3
"""100-event zoom fan for the slide after the NRMSE before/after page.

100 randomly drawn curves (fixed seed) from the Z7 PBS1 population that
passes fit_ok AND NRMSE <= 0.4, peak-normalized at the common pretrigger,
zoomed to 25-27 ms so individual curves are visible.
Output: figures/fan_zip7_PBS1_100zoom.png
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
        if fp is not None and fp["fit_ok"] and fp["nrmse"] <= 0.4:
            fits.append(fp)

rng = np.random.default_rng(42)
sample = [fits[i] for i in rng.choice(len(fits), 100, replace=False)]

lo, hi = int(25.6e-3 * SAMPLERATE), int(26.5e-3 * SAMPLERATE)
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
fig, ax = plt.subplots(figsize=(10.5, 4.8))
for fp in sample:
    y = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"], 0.0,
                        float(RISE_REF_IDX))
    pk = float(np.max(y))
    if pk > 0 and np.isfinite(pk):
        ax.plot(t_ms, y / pk, lw=0.7, alpha=0.4, color="steelblue")
ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
ax.set_title(f"Z{DET} {CHAN}: 100 of the {len(fits)} kept curves, zoom 25.6-26.5 ms",
             fontsize=12)
ax.set_xlabel("Time (ms)", fontsize=11)
ax.set_ylabel("Norm. amp.", fontsize=11)
ax.set_xlim(25.6, 26.5)
ax.grid(alpha=0.25)
fig.tight_layout()
out = os.path.join(HERE, "figures", "fan_zip7_PBS1_100zoom.png")
fig.savefig(out, dpi=160, bbox_inches="tight")
print(f"Saved: {out}  (100 of {len(fits)})")
