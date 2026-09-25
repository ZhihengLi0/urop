#!/usr/bin/env python3
"""Plot the DELIVERED 1x1 template (one curve) straight from the ROOT file, so
the template-family-1 slide shows the product, not only the input population.

Reads results/root_files/Templates_SNOLAB_R4_zip{N}_2expfit_weighted.root
(t2exp_zip{N}_{chan}) and writes figures/template_1x1_zip7_PBS1.png
"""
import os
import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOTF = os.path.join(HERE, "..", "deliverables", "1x1", "root_files",
                     "Templates_SNOLAB_R4_zip7_2expfit_weighted.root")
OUT = os.path.join(HERE, "figures", "template_1x1_zip7_PBS1.png")

SAMPLERATE = 625000.0          # Hz, same as the pipeline
RISE_REF = 16050               # common pretrigger

vals = uproot.open(ROOTF)["t2exp_zip7_PBS1"].values()
t_ms = np.arange(len(vals)) / SAMPLERATE * 1e3

# same zoom window as the fan plots: pulse region only
lo, hi = RISE_REF - 700, RISE_REF + 6000
fig, ax = plt.subplots(figsize=(7.4, 3.5))
ax.plot(t_ms[lo:hi], vals[lo:hi], lw=2.6, color="#C0392B")
ax.axvline(RISE_REF / SAMPLERATE * 1e3, color="gray", lw=0.9, ls=":")
ax.axhline(0, color="gray", lw=0.6, ls="--")
ax.set_xlabel("Time (ms)", fontsize=11)
ax.set_ylabel("Norm. amp.", fontsize=11)
ax.set_title("Z7 PBS1 — the delivered 1x1 template (one curve)", fontsize=12)
ax.tick_params(labelsize=9)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print(f"saved {OUT}  (peak={vals.max():.3f}, bins={len(vals)})")
