#!/usr/bin/env python3
"""Overlay the DELIVERED 1x1 template (read from the ROOT file) on top of the
fan of fitted curves it is the weighted mean of — one figure instead of two.

The fan is a rendered PNG, so its pixel->data mapping is calibrated from the
axis ticks (verified against the dotted common-pretrigger line at 25.68 ms).
"""
import os
import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
ROOTF = os.path.join(HERE, "..", "lp_fit_align", "results", "root_files",
                     "Templates_SNOLAB_R4_zip7_2expfit_weighted.root")
FAN = os.path.join(FIG, "fan_zip7_PBS1_after.png")
OUT = os.path.join(FIG, "template_overlay_zip7_PBS1.png")

SAMPLERATE = 625000.0

# --- pixel -> data calibration of the fan PNG (1193 x 360) -------------------
# x: tick 26 ms at px 245.2, 115.7 px per ms ; y: amp 0 at px 299.4, 260.6 px/amp
X26, PX_PER_MS = 245.2, 115.7
Y0, PX_PER_AMP = 299.4, 260.6
img = mpimg.imread(FAN)
H, W = img.shape[0], img.shape[1]
left = 26 + (0 - X26) / PX_PER_MS
right = 26 + (W - X26) / PX_PER_MS
top = (Y0 - 0) / PX_PER_AMP
bottom = (Y0 - H) / PX_PER_AMP

# --- delivered template ------------------------------------------------------
vals = uproot.open(ROOTF)["t2exp_zip7_PBS1"].values()
t_ms = np.arange(len(vals)) / SAMPLERATE * 1e3
m = (t_ms >= 24.55) & (t_ms <= 34.05)          # stay inside the plot frame

fig, ax = plt.subplots(figsize=(W / 130, H / 130), dpi=200)
ax.imshow(img, extent=[left, right, bottom, top], aspect="auto",
          interpolation="antialiased")
ax.plot(t_ms[m], vals[m], lw=2.2, color="#C0392B", zorder=5,
        label="1x1 template — NRMSE-weighted mean of all fit_ok curves (delivered)")
ax.set_xlim(left, right)
ax.set_ylim(bottom, top)
ax.legend(loc="center right", fontsize=8, framealpha=0.92,
          bbox_to_anchor=(1.0, 0.42))
ax.axis("off")
fig.subplots_adjust(0, 0, 1, 1)
fig.savefig(OUT, dpi=200, bbox_inches="tight", pad_inches=0)
print(f"saved {OUT}")
