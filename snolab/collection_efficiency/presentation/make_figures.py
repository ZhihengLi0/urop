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
    "peak_top.png": os.path.join(SRC, f"{S}_peak_raw_vs_lp_PBS1_ev30646_top.png"),
    "peak_bottom.png": os.path.join(SRC, f"{S}_peak_raw_vs_lp_PBS1_ev30646_bottom.png"),
    "pulse_15events.png": os.path.join(SRC, f"{S}_current_power_PBS1_15events.png"),
    "cum_15events.png": os.path.join(SRC, f"{S}_cumulative_energy_PBS1_15events.png"),
    "allchan_pulses.png": os.path.join(SRC, f"{S}_current_power_allchan_ev30646.png"),
    "allchan_cum.png": os.path.join(SRC, f"{S}_cumulative_energy_allchan_ev30646.png"),
    "spectrum_zip7.png": os.path.join(SPEC, "ops_spectrum_zip7.png"),
    # redrawn with full axes by plot_fitted_current_power.py, not cropped
    "raw_cum_slide.png": os.path.join(SRC, f"{S}_raw_and_cumulative_PBS1_slide.png"),
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
ax.text(0.5, 0.86, r"$\delta P(t) \;=\; I_0\,(R_L - R_0)\;\delta I(t) \;+\; 2\,R_L\;(\delta I(t))^2$",
        ha="center", va="center", fontsize=30, color=NAVY)
ax.text(0.30, 0.66, "linear term", ha="center", fontsize=15, color=NAVY)
ax.text(0.71, 0.66, "quadratic term", ha="center", fontsize=15, color=NAVY)
ax.text(0.5, 0.50, r"$E \;=\; \int \delta P(t)\,dt \;=\; I_0(R_L-R_0)\,A(\tau_f-\tau_r)"
        r"\;+\;2R_L\,A^2\left(\frac{\tau_f+\tau_r}{2}-\frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right)$",
        ha="center", va="center", fontsize=21, color=NAVY)
ax.text(0.5, 0.325, r"for the fitted pulse $\delta I(t) = A\,[\,e^{-t/\tau_f} - e^{-t/\tau_r}\,]$"
        "  integrated from $-\\infty$ to $+\\infty$: zero before it starts, decays to zero after",
        ha="center", va="center", fontsize=15, color=GRAY)
ax.text(0.5, 0.215, "Z7 PBS1:   $I_0$ = $-$18.07 $\\mu$A,   $R_0$ = 44.16 m$\\Omega$,   "
        "$R_L$ = $R_p$ + $R_{sh}$ = 14.24 m$\\Omega$ + 5.00 m$\\Omega$ = 19.24 m$\\Omega$",
        ha="center", va="center", fontsize=14.5, color=RED)
ax.text(0.5, 0.125, "linear coefficient:   $I_0(R_L-R_0)$ = ($-$18.07 $\\mu$A) $\\times$ "
        "(19.24 m$\\Omega$ $-$ 44.16 m$\\Omega$) = 0.45 $\\mu$V",
        ha="center", va="center", fontsize=14.5, color=RED)
ax.text(0.5, 0.04, "quadratic coefficient:   $2R_L$ = 2 $\\times$ 19.24 m$\\Omega$ = 38.5 m$\\Omega$ = 0.0385 $\\Omega$",
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
         "current pulse\n$\\delta I(t)$  [ADC]", "power pulse\n$\\delta P(t)$  [fW]",
         "energy\n$E=\\int \\delta P\\,dt$  [eV]", "efficiency\n$E$ / 10.37 keV"]
xs = [0.08, 0.25, 0.42, 0.59, 0.76, 0.93]
for i, (x, s) in enumerate(zip(xs, steps)):
    col = RED if i == 5 else NAVY
    ax.text(x, 0.55, s, ha="center", va="center", fontsize=15, color=col,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=col, lw=1.6))
    if i < 5:
        ax.annotate("", xy=(xs[i + 1] - 0.072, 0.55), xytext=(x + 0.072, 0.55),
                    arrowprops=dict(arrowstyle="->", lw=1.6, color=GRAY))
ax.text(0.505, 0.12, "the TES equations\n(Irwin & Hilton)", ha="center", va="center", fontsize=11.5, color=GRAY)
ax.text(0.76, 0.12, "summed over\nall channels", ha="center", va="center", fontsize=11.5, color=NAVY)
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
ax.text(0.31, 0.50, "$V = I_b R_{sh}$", ha="left", va="center", fontsize=12.5,
        color=GRAY, zorder=4)
# R_L on the top wire
ax.add_patch(plt.Rectangle((0.34, 0.735), 0.16, 0.09, fc="white", ec=NAVY, lw=LW, zorder=3))
ax.text(0.42, 0.78, "$R_L$", ha="center", va="center", fontsize=16, color=NAVY, zorder=4)
ax.text(0.63, 0.90, "$R_L = R_p + R_{sh}$   fixed", ha="center", va="center",
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
ax.text(0.60, 0.33, "rises when the film\nis heated by phonons", ha="center",
        va="center", fontsize=12.5, color=RED)
# current arrow
ax.annotate("", xy=(0.30, 0.78), xytext=(0.22, 0.78),
            arrowprops=dict(arrowstyle="-|>", lw=2.0, color="#1B7A3D"))
ax.text(0.245, 0.855, "$I(t) = I_0 + \\delta I(t)$", ha="center", va="center",
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
     r"$E = \int \delta P\,dt ,\quad \delta P = I_0 (R_L - R_0)\,\delta I + R_L\,(\delta I)^2$"),
]
y = 0.955
for lab, eq in STEPS:
    ax.text(0.035, y, lab, ha="left", va="center", fontsize=13, color=GRAY)
    ax.text(0.5, y - 0.080, eq, ha="center", va="center", fontsize=18, color=NAVY)
    y -= 0.180
ax.plot([0.03, 0.97], [0.062, 0.062], color="#CCCCCC", lw=1.2)
ax.text(0.5, 0.028, "the note's Method 1 puts $2R_L$ in the second term, not $R_L$: "
        "+0.58 % in energy", ha="center", va="center", fontsize=12.5, color=RED)
fig.savefig(os.path.join(OUT, "derivation.png"), dpi=150)
plt.close(fig)
print("derivation.png         drawn")

# ---------------------------------------------- derivation backup (en and zh)
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf")
ZH_FAMILY = ["DejaVu Sans", "Droid Sans Fallback"]

DERIV_TEXT = {
    "en": dict(
        h1="1.  From the current to the absorbed power",
        h2="2.  Energy of the fitted pulse",
        h3="3.  Symbols (Z7 PBS1 values) and assumptions",
        left=[
            ("heat balance of the TES", r"$C\,\dot T = P(t) + P_J - P_{bath}$"),
            (r"over the whole pulse $\int C\,\dot T\,dt = 0$; the change in bath heat flow is not included",
             r"$E = \int P\,dt = -\int \delta P_J\,dt$"),
            (r"the circuit; at the bias point $V = I_0(R_L + R_0)$",
             r"$V_{TES} = V - I R_L - L\,\dot I, \quad P_J = I\,V_{TES}$"),
            (r"put $I = I_0 + \delta I$ and subtract the value at the bias point",
             r"$\delta P_J = V\,\delta I - R_L\,(2I_0\,\delta I + (\delta I)^2) - L\,I\,\dot{\delta I}$"),
            (r"integrate: the $L$ term gives $L\,[I_0\,\delta I + (\delta I)^2/2]$, which is 0 at both ends",
             r"$E = \int \delta P\,dt, \quad \delta P = I_0(R_L - R_0)\,\delta I + c_2\,R_L\,(\delta I)^2$"),
            (r"$c_2$ = 1 from this derivation,  2 in Method 1 (used here),  $-1$ in Method 2", ""),
        ],
        right=[
            (r"the fit, with $t$ counted from the pulse start $t_0$",
             r"$\delta I(t) = A\,[\,e^{-t/\tau_f} - e^{-t/\tau_r}\,]$"),
            ("the only integral needed", r"$\int_0^{\infty} e^{-t/\tau}\,dt = \tau$"),
            ("linear term", r"$\int \delta I\,dt = A\,(\tau_f - \tau_r)$"),
            ("quadratic term: expand the square, integrate each exponential",
             r"$\int (\delta I)^2 dt = A^2\left[\frac{\tau_f+\tau_r}{2} - \frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right]$"),
            (r"so, with $c_2 = 2$",
             r"$E = I_0(R_L-R_0)\,A(\tau_f-\tau_r) + 2R_L\,A^2\left[\frac{\tau_f+\tau_r}{2} - \frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right]$"),
            (r"PBS1, event 30646: $A$ = 1.39 $\mu$A, $\tau_r$ = 136 $\mu$s, $\tau_f$ = 213 $\mu$s $\Rightarrow$ $E$ = 305.2 eV", ""),
        ],
        symbols=[
            r"$I_b$: bias current    $R_{sh}$: shunt resistor, 5.00 m$\Omega$    $V = I_b R_{sh}$: bias voltage, $-1.146$ $\mu$V    $R_p$: parasitic resistance, 14.24 m$\Omega$",
            r"$R_L = R_p + R_{sh}$: load resistance, 19.24 m$\Omega$    $R_0$: TES resistance at the bias point, 44.16 m$\Omega$    $I_0 = V/(R_L+R_0)$: TES current, $-18.07$ $\mu$A",
            r"$L$: inductance (unknown)    $\delta I$: current change    $A$: amplitude    $\tau_r$, $\tau_f$: rise and fall time constants    $t_0$: pulse start",
            r"Assumptions: detector at 0 V (no NTL effect);  the heat flow to the bath is not included;",
            r"the $L$ term cancels only after integration, so $\delta P(t)$ is not the exact power at each moment; only its integral is used",
        ],
    ),
    "zh": dict(
        h1="1.  从电流到吸收的功率",
        h2="2.  拟合脉冲的能量",
        h3="3.  符号（Z7 PBS1 的数值）和假设",
        left=[
            ("TES 的热平衡", r"$C\,\dot T = P(t) + P_J - P_{bath}$"),
            ("对整个脉冲积分，∫C·dT/dt dt = 0；不考虑流到热浴的热量的变化",
             r"$E = \int P\,dt = -\int \delta P_J\,dt$"),
            ("电路方程；在工作点 V = I₀(R_L + R₀)",
             r"$V_{TES} = V - I R_L - L\,\dot I, \quad P_J = I\,V_{TES}$"),
            ("代入 I = I₀ + δI，减去工作点的值",
             r"$\delta P_J = V\,\delta I - R_L\,(2I_0\,\delta I + (\delta I)^2) - L\,I\,\dot{\delta I}$"),
            ("积分：电感项积出来是 L·[I₀·δI + (δI)²/2]，脉冲两端都是 0",
             r"$E = \int \delta P\,dt, \quad \delta P = I_0(R_L - R_0)\,\delta I + c_2\,R_L\,(\delta I)^2$"),
            ("c₂ = 1 是这个推导的结果，2 是 Method 1（本报告用），−1 是 Method 2", ""),
        ],
        right=[
            ("拟合函数，t 从脉冲开始的时刻 t₀ 算起",
             r"$\delta I(t) = A\,[\,e^{-t/\tau_f} - e^{-t/\tau_r}\,]$"),
            ("只需要这一个积分", r"$\int_0^{\infty} e^{-t/\tau}\,dt = \tau$"),
            ("线性项", r"$\int \delta I\,dt = A\,(\tau_f - \tau_r)$"),
            ("二次项：把平方展开，每个指数分别积分",
             r"$\int (\delta I)^2 dt = A^2\left[\frac{\tau_f+\tau_r}{2} - \frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right]$"),
            ("所以，取 c₂ = 2",
             r"$E = I_0(R_L-R_0)\,A(\tau_f-\tau_r) + 2R_L\,A^2\left[\frac{\tau_f+\tau_r}{2} - \frac{2\tau_f\tau_r}{\tau_f+\tau_r}\right]$"),
            ("PBS1，事件 30646：A = 1.39 μA，τr = 136 μs，τf = 213 μs  ⇒  E = 305.2 eV", ""),
        ],
        symbols=[
            "I_b：偏置电流    R_sh：分流电阻，5.00 mΩ    V = I_b·R_sh：偏置电压，−1.146 μV    R_p：寄生电阻，14.24 mΩ",
            "R_L = R_p + R_sh：负载电阻，19.24 mΩ    R₀：工作点的 TES 电阻，44.16 mΩ    I₀ = V / (R_L + R₀)：工作点的 TES 电流，−18.07 μA",
            "L：电感（未知）    δI：电流变化    A：幅度    τr、τf：上升和下降时间常数    t₀：脉冲开始的时刻",
            "假设：探测器在 0 V（没有 NTL 效应）；不包括流到热浴的热量；",
            "电感项只有积分以后才为 0，所以 δP(t) 不是每一时刻的精确功率，我们只用它的积分",
        ],
    ),
}

for lang, D in DERIV_TEXT.items():
    fp = dict(family=ZH_FAMILY) if lang == "zh" else {}
    fig = plt.figure(figsize=(14.0, 7.3), dpi=150)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    for x, head in ((0.015, D["h1"]), (0.515, D["h2"])):
        ax.text(x, 0.965, head, ha="left", va="center", fontsize=16.5, color=NAVY,
                weight="bold", **fp)
    ax.plot([0.5, 0.5], [0.30, 0.94], color="#CCCCCC", lw=1.2)
    for x0, items in ((0.015, D["left"]), (0.515, D["right"])):
        y = 0.91
        for lab, eq in items:
            ax.text(x0, y, lab, ha="left", va="center", fontsize=12.5, color=GRAY, **fp)
            if eq:
                ax.text(x0 + 0.235, y - 0.048, eq, ha="center", va="center",
                        fontsize=14.5, color=NAVY)
                y -= 0.108
            else:
                y -= 0.06
    ax.plot([0.015, 0.985], [0.285, 0.285], color="#CCCCCC", lw=1.2)
    ax.text(0.015, 0.255, D["h3"], ha="left", va="center", fontsize=15, color=NAVY,
            weight="bold", **fp)
    y = 0.205
    for k, line in enumerate(D["symbols"]):
        ax.text(0.015, y, line, ha="left", va="center", fontsize=12.2,
                color=RED if k >= 3 else "#333333", **fp)
        y -= 0.046
    fig.savefig(os.path.join(OUT, f"derivation_backup_{lang}.png"), dpi=150)
    plt.close(fig)
    print(f"derivation_backup_{lang}.png drawn")
