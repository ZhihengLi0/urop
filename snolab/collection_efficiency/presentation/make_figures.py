#!/usr/bin/env python3
"""Slide-sized figures for the collection-efficiency talk.

Crops the versioned result figures in ../results/plots/current_power_overlay/
(and the Z7 spectrum in ../../kline_population/results/plots/) into panels that
stay legible on a 16:9 slide, and draws the formula card. Nothing is re-fitted or
re-computed here; every number on the slides comes from the result text files.

Run inside the CDMS singularity image (matplotlib + PIL):
    python3 make_figures.py
"""
import os
import shutil

from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "results", "plots", "current_power_overlay")
SPEC = os.path.join(HERE, "..", "..", "kline_population", "results", "plots")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

S = "zip7_24260617_063934"
CROPS = {
    # (source, box in source pixels)
    "peak_top.png": (f"{S}_peak_raw_vs_lp_PBS1_ev30646.png", (0, 150, 2160, 1040)),
    "peak_bottom.png": (f"{S}_peak_raw_vs_lp_PBS1_ev30646.png", (0, 1060, 2160, 1630)),
    "pulse_ev30646.png": (f"{S}_current_power_PBS1_15events.png", (15, 248, 745, 492)),
    "pulse_ev100231.png": (f"{S}_current_power_PBS1_15events.png", (1430, 520, 2200, 778)),
    "pulse_legend.png": (f"{S}_current_power_PBS1_15events.png", (440, 1630, 1780, 1680)),
    "hist_PBS1_panel.png": ("zip7_kline_energy_hist_allchan.png", (718, 200, 1305, 545)),
    "hist_PFS1_panel.png": ("zip7_kline_energy_hist_allchan.png", (718, 575, 1305, 920)),
    "hist_PES1_panel.png": ("zip7_kline_energy_hist_allchan.png", (0, 575, 665, 920)),
    "hist_PDS2_panel.png": ("zip7_kline_energy_hist_allchan.png", (718, 930, 1305, 1295)),
}
for name, (src, box) in CROPS.items():
    im = Image.open(os.path.join(SRC, src))
    im.crop(box).save(os.path.join(OUT, name))
    print(f"{name:<22} {box}  <- {src}")

COPY = {
    "hist_PBS1.png": os.path.join(SRC, "zip7_kline_energy_hist_PBS1.png"),
    "hist_allchan.png": os.path.join(SRC, "zip7_kline_energy_hist_allchan.png"),
    "hist_sum.png": os.path.join(SRC, "zip7_kline_energy_sum_hist.png"),
    "peak_full.png": os.path.join(SRC, f"{S}_peak_raw_vs_lp_PBS1_ev30646.png"),
    "pulse_15events.png": os.path.join(SRC, f"{S}_current_power_PBS1_15events.png"),
    "cum_15events.png": os.path.join(SRC, f"{S}_cumulative_energy_PBS1_15events.png"),
    "allchan_pulses.png": os.path.join(SRC, f"{S}_current_power_allchan_ev30646.png"),
    "allchan_cum.png": os.path.join(SRC, f"{S}_cumulative_energy_allchan_ev30646.png"),
    "spectrum_zip7.png": os.path.join(SPEC, "ops_spectrum_zip7.png"),
    # redrawn with full axes by plot_fitted_current_power.py, not cropped
    "cum_slide.png": os.path.join(SRC, f"{S}_cumulative_energy_PBS1_slide.png"),
    "allchan_slide.png": os.path.join(SRC, f"{S}_current_power_allchan_ev30646_slide.png"),
}
for name, src in COPY.items():
    shutil.copyfile(src, os.path.join(OUT, name))
    print(f"{name:<22} copied")

# ------------------------------------------------------------ formula card
fig = plt.figure(figsize=(12.0, 4.6), dpi=150)
fig.patch.set_facecolor("white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()
NAVY, RED, GRAY = "#1F3864", "#C0392B", "#555555"
ax.text(0.5, 0.86, r"$P(t) \;=\; I_0\,(R_L - R_0)\;\delta I(t) \;+\; 2\,R_L\;(\delta I(t))^2$",
        ha="center", va="center", fontsize=30, color=NAVY)
ax.text(0.30, 0.66, "linear term", ha="center", fontsize=15, color=NAVY)
ax.text(0.71, 0.66, "quadratic term", ha="center", fontsize=15, color=NAVY)
ax.text(0.5, 0.50, r"$E \;=\; \int P(t)\,dt \;=\; I_0(R_L-R_0)\,A(\tau_f-\tau_r)"
        r"\;+\;2R_L\,A^2\left(\frac{\tau_f+\tau_r}{2}-\frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right)$",
        ha="center", va="center", fontsize=21, color=NAVY)
ax.text(0.5, 0.33, r"for the fitted pulse $\delta I(t) = A\,[\,e^{-t/\tau_f} - e^{-t/\tau_r}\,]$"
        "  integrated from $-\\infty$ to $+\\infty$: zero before it starts, decays to zero after",
        ha="center", va="center", fontsize=15, color=GRAY)
ax.text(0.5, 0.19, "Z7 PBS1 bias point (measured, from detectorConfig):  $I_0$ = -18.07 $\\mu$A,  "
        "$R_0$ = 44.16 m$\\Omega$,  $R_L$ = $R_p$ + $R_{sh}$ = 19.24 m$\\Omega$",
        ha="center", va="center", fontsize=14.5, color=RED)
ax.text(0.5, 0.07, "$\\Rightarrow$  $I_0(R_L-R_0)$ = 4.50$\\times$10$^{-7}$ V   and   $2R_L$ = 0.0385 $\\Omega$",
        ha="center", va="center", fontsize=14.5, color=RED)
fig.savefig(os.path.join(OUT, "formula.png"), dpi=150)
plt.close(fig)
print("formula.png            drawn")

# ------------------------------------------------------------ chain card
fig = plt.figure(figsize=(12.0, 2.6), dpi=150)
fig.patch.set_facecolor("white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()
steps = ["10.37 keV\nin the crystal", "phonons reach\nthe TES films",
         "current pulse\n$\\delta I(t)$  [ADC]", "power pulse\n$P(t)$  [fW]",
         "energy\n$E=\\int P\\,dt$  [eV]", "efficiency\n$E$ / 10.37 keV"]
xs = [0.08, 0.25, 0.42, 0.59, 0.76, 0.93]
for i, (x, s) in enumerate(zip(xs, steps)):
    col = RED if i == 5 else NAVY
    ax.text(x, 0.55, s, ha="center", va="center", fontsize=15, color=col,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=col, lw=1.6))
    if i < 5:
        ax.annotate("", xy=(xs[i + 1] - 0.072, 0.55), xytext=(x + 0.072, 0.55),
                    arrowprops=dict(arrowstyle="->", lw=1.6, color=GRAY))
ax.text(0.505, 0.12, "the TES equations\n(Irwin & Hilton)", ha="center", va="center", fontsize=11.5, color=GRAY)
ax.text(0.675, 0.90, "closed-form integral\nof the fitted pulse", ha="center", va="center", fontsize=11.5, color=GRAY)
ax.text(0.335, 0.90, "fit a two-exponential", ha="center", va="center", fontsize=11.5, color=GRAY)
fig.savefig(os.path.join(OUT, "chain.png"), dpi=150)
plt.close(fig)
print("chain.png              drawn")

# ------------------------------------------------------- circuit card (slide 3)
fig = plt.figure(figsize=(5.6, 4.4), dpi=150)
fig.patch.set_facecolor("white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_axis_off()
LW = 1.8
# the loop
for x0, y0, x1, y1 in [(0.16, 0.22, 0.16, 0.78), (0.16, 0.78, 0.84, 0.78),
                       (0.84, 0.78, 0.84, 0.22), (0.16, 0.22, 0.84, 0.22)]:
    ax.plot([x0, x1], [y0, y1], color=NAVY, lw=LW, zorder=1, solid_capstyle="round")
# voltage source
ax.add_patch(plt.Circle((0.16, 0.50), 0.075, fc="white", ec=NAVY, lw=LW, zorder=3))
ax.plot([0.16, 0.16], [0.425, 0.575], color="white", lw=LW + 2, zorder=2)
ax.text(0.16, 0.50, "$V$", ha="center", va="center", fontsize=17, color=NAVY, zorder=4)
ax.text(0.16, 0.375, "$V = I_b R_{sh}$", ha="center", va="center", fontsize=12,
        color=GRAY, zorder=4)
# R_L on the top wire
ax.add_patch(plt.Rectangle((0.34, 0.735), 0.16, 0.09, fc="white", ec=NAVY, lw=LW, zorder=3))
ax.text(0.42, 0.78, "$R_L$", ha="center", va="center", fontsize=16, color=NAVY, zorder=4)
ax.text(0.44, 0.90, "$R_L = R_p + R_{sh}$   fixed", ha="center", va="center",
        fontsize=12, color=GRAY)
# inductor on the top wire, right of R_L
import numpy as np
for k in range(3):
    th = np.linspace(np.pi, 0, 40)
    ax.plot(0.60 + 0.026 * k + 0.013 + 0.013 * np.cos(th), 0.78 + 0.026 * np.sin(th),
            color=NAVY, lw=LW, zorder=3)
ax.plot([0.585, 0.60], [0.78, 0.78], color=NAVY, lw=LW, zorder=3)
ax.text(0.64, 0.70, "$L$", ha="center", va="center", fontsize=16, color=NAVY)
# R_TES on the right wire
ax.add_patch(plt.Rectangle((0.795, 0.42), 0.09, 0.16, fc="#FDF3F2", ec=RED,
                           lw=LW, ls=(0, (4, 2)), zorder=3))
ax.text(0.84, 0.50, "$R_{TES}$", ha="center", va="center", fontsize=15, color=RED, zorder=4)
ax.text(0.84, 0.345, "rises when the film\nis heated by phonons", ha="center",
        va="center", fontsize=12, color=RED)
# current arrow
ax.annotate("", xy=(0.30, 0.78), xytext=(0.22, 0.78),
            arrowprops=dict(arrowstyle="-|>", lw=2.0, color="#1B7A3D"))
ax.text(0.255, 0.66, "$I(t) = I_0 + \\delta I(t)$", ha="center", va="center",
        fontsize=13.5, color="#1B7A3D")
ax.text(0.5, 0.10, "one loop: the voltage source, the fixed load, the coil,\n"
        "and the TES whose resistance carries the signal",
        ha="center", va="center", fontsize=12.5, color=GRAY)
fig.savefig(os.path.join(OUT, "circuit.png"), dpi=150)
plt.close(fig)
print("circuit.png            drawn")

# ---------------------------------------------------- derivation card (slide 3)
fig = plt.figure(figsize=(8.6, 5.6), dpi=150)
fig.patch.set_facecolor("white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_axis_off()
STEPS = [
    ("1.  heat flow in the film",
     r"$C\,\dot T \;=\; P(t) \;+\; P_J \;-\; P_{bath}$"),
    ("2.  the film ends where it started, so $\int C\,\dot T\,dt = 0$",
     r"$E \;=\; \int P\,dt \;=\; -\int \delta P_J\,dt$"),
    ("3.  the loop gives the voltage on the TES, and its Joule power",
     r"$V_{TES} = V - I R_L - L\,\dot I$ ,      $P_J = I\,V_{TES}$"),
    ("4.  put $I = I_0 + \delta I$ and expand",
     r"$\delta P_J = V\,\delta I - R_L\,(2 I_0 \delta I + (\delta I)^2) - L\,I\,\dot{\delta I}$"),
    ("5.  integrate over the pulse: the $L$ piece cancels at the two ends, and $V = I_0(R_L + R_0)$",
     r"$E \;=\; I_0 (R_L - R_0) \int \delta I\,dt \;+\; R_L \int (\delta I)^2 dt$"),
]
y = 0.93
for lab, eq in STEPS:
    ax.text(0.035, y, lab, ha="left", va="center", fontsize=13.5, color=GRAY)
    ax.text(0.5, y - 0.083, eq, ha="center", va="center", fontsize=19, color=NAVY)
    y -= 0.185
ax.plot([0.03, 0.97], [0.085, 0.085], color="#CCCCCC", lw=1.2)
ax.text(0.5, 0.042, "the note's Method 1 carries $2R_L$ in the second term instead of $R_L$: "
        "+0.58 % in energy, and that is the version used here",
        ha="center", va="center", fontsize=12.5, color=RED)
fig.savefig(os.path.join(OUT, "derivation.png"), dpi=150)
plt.close(fig)
print("derivation.png         drawn")
