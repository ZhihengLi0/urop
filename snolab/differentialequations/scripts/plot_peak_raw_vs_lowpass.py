#!/usr/bin/env python3
"""One event, one channel, zoomed on the peak: raw samples, the low-pass traces
and the fitted pulse, read simultaneously in ADC, current and power.

The point of the figure is why the pulse height must come from the fit and not
from the largest raw sample. Around the rounded top of the pulse many samples sit
at nearly the same true height; taking the maximum picks whichever of them caught
the largest upward noise excursion, so it is biased high. The fit uses every
sample of the rise, the top and the decay, so the noise averages out.

Everything is drawn against the baseline of the official Eabs definition (mean of
bins 93..15758). Three axes carry the same curves: ADC on the left, current in
microamperes on the right, and absorbed power in femtowatts on a second right
axis. The power axis uses the exact transform

    P = I0(R_L-R0)*dI + c2*R_L*dI^2        (method1, c2 = 2)

inverted through the quadratic formula, so it is not a rescaled current axis: its
ticks are genuinely non-uniform, which is the 2% nonlinearity made visible.

Output: results/plots/current_power_overlay/zip{det}_{series}_peak_raw_vs_lp_{chan}_ev{N}.png

Usage (inside the CDMS singularity image):
    python3 scripts/plot_peak_raw_vs_lowpass.py --det 7 --chan PBS1 --event 30646
"""
import argparse
import glob
import os
import pickle

import numpy as np
import uproot
from scipy.signal import butter, filtfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ADC_PER_AMP = 3.145728e9
TRIGGER_BIN = 16383
BASE_LO, BASE_HI = 93, 15758      # official baseline window
DT = 1.6e-6
N_BINS = 32768
LP_FIT_KHZ = 100.0                # the filter the template pipeline fits through
LP_OFF_KHZ = 20.0                 # the official Eabs prefilter, 5 poles
TOP_FRAC = 0.90                   # "the top of the pulse" for the sample count

RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
PROC_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
            "/Processed/Default/Default_tag/Unmerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "results", "plots", "current_power_overlay")
FIT_CACHE = os.path.join(HERE, "run", "fit_cache")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--series", default="24260617_063934")
ap.add_argument("--chan", default="PBS1")
ap.add_argument("--event", type=int, default=30646)
ap.add_argument("--lo-ms", type=float, default=-0.35, help="zoom start, ms from trigger")
ap.add_argument("--hi-ms", type=float, default=0.95, help="zoom end, ms from trigger")
ap.add_argument("--formula", default="method1",
                choices=["method1", "method2", "exact"])
args = ap.parse_args()
det, series, chan, evn = args.det, args.series, args.chan, args.event
C2 = {"method1": 2.0, "method2": -1.0, "exact": 1.0}[args.formula]

# ------------------------------------------------------------------ the trace
cache = pickle.load(open(os.path.join(RAW_CACHE, f"zip{det}_series",
                                      f"{series}.pkl"), "rb"))
idx = {int(e): i for i, e in enumerate(cache["event_numbers_ch"][chan])}
trace = np.asarray(cache["raw_traces"][chan][idx[evn]], dtype=np.float64)
assert trace.size == N_BINS, trace.size
base = trace[BASE_LO:BASE_HI].mean()
raw = trace - base
sigma = float(trace[BASE_LO:BASE_HI].std())

b100, a100 = butter(4, LP_FIT_KHZ * 1e3 / (0.5 / DT), btype="low")
b20, a20 = butter(5, LP_OFF_KHZ * 1e3 / (0.5 / DT), btype="low")
lp100 = filtfilt(b100, a100, raw)
lp20 = filtfilt(b20, a20, raw)

# ------------------------------------------------- bias point, current -> power
cfgf = (sorted(glob.glob(os.path.join(PROC_DIR, f"{series}_Addison.root")))
        + sorted(glob.glob(os.path.join(PROC_DIR,
                                        f"UMN.Addison.*_{series}_F*.root"))))
cfg = uproot.open(cfgf[0])[f"detectorConfigDir/detectorConfigZip{det}"]
_c = lambda f: float(cfg[f"{chan}{f}"].array(library="np")[0])
I0, R0, RL = _c("i0"), _c("r0"), _c("rp") + _c("rshunt")
LIN, QUAD = I0 * (RL - R0), C2 * RL           # V and Ohm


def power_fW(adc):
    """ADC above baseline -> absorbed power in fW (exact, both terms)."""
    di = np.asarray(adc) / ADC_PER_AMP
    return (LIN * di + QUAD * di * di) * 1e15


def fW_to_adc(p_fW):
    """Inverse of power_fW: solve QUAD*dI^2 + LIN*dI - P = 0 for the branch that
    passes through the origin."""
    p = np.asarray(p_fW) * 1e-15
    disc = np.maximum(LIN * LIN + 4.0 * QUAD * p, 0.0)
    return (-LIN + np.sqrt(disc)) / (2.0 * QUAD) * ADC_PER_AMP


# ------------------------------------------------------------------- the fit
rec = pickle.load(open(os.path.join(FIT_CACHE, f"zip{det}",
                                    f"{series}.pkl"), "rb"))["fits"][chan][evn]
A, t_r, t_f, t0_ms = rec["amp"], rec["t_r"], rec["t_f"], rec["t0_ms"]
x = np.arange(N_BINS, dtype=np.float64)
t_ms = (x - TRIGGER_BIN) * DT * 1e3
dt_s = np.clip(t_ms - t0_ms, 0.0, None) * 1e-3
fit_adc = np.where(t_ms <= t0_ms, 0.0,
                   A * (np.exp(-dt_s / t_f) - np.exp(-dt_s / t_r))) * ADC_PER_AMP

i1 = A * (t_f - t_r)
i2 = A * A * (t_f / 2 + t_r / 2 - 2 * t_f * t_r / (t_f + t_r))
E_EV = (LIN * i1 + QUAD * i2) / 1.602176634e-19

lo = TRIGGER_BIN + int(round(args.lo_ms * 1e-3 / DT))
hi = TRIGGER_BIN + int(round(args.hi_ms * 1e-3 / DT))
sl = slice(lo, hi)
tt = t_ms[sl]

pk_fit = float(fit_adc.max())
i_raw = int(np.argmax(raw))
pk_raw = float(raw[i_raw])
pk_100 = float(lp100.max())
pk_20 = float(lp20.max())
n_top = int((fit_adc > TOP_FRAC * pk_fit).sum())
top_lo = t_ms[np.argmax(fit_adc > TOP_FRAC * pk_fit)]
top_hi = t_ms[N_BINS - 1 - np.argmax((fit_adc > TOP_FRAC * pk_fit)[::-1])]

# ------------------------------------------------------------------- figure
fig, ax = plt.subplots(figsize=(13.5, 7.2))

# background: the baseline noise band, and the flat top of the pulse
ax.axhspan(-sigma, sigma, color="#E8E8E8", zorder=0)
ax.axvspan(top_lo, top_hi, color="#FFF3C4", zorder=0)
ax.axhline(0, color="#777777", lw=0.8, zorder=1)
ax.fill_between(tt, fit_adc[sl] - sigma, fit_adc[sl] + sigma, color="#C0392B",
                alpha=0.13, lw=0, zorder=1)

# the four curves, thin and visually distinct
ax.plot(tt, raw[sl], ls="none", marker="o", ms=1.9, color="#7F8C8D",
        alpha=0.85, zorder=2, label="raw samples, one per 1.6 $\\mu$s")
ax.plot(tt, lp100[sl], lw=0.9, color="#1F77B4", zorder=3,
        label=f"low pass {LP_FIT_KHZ:.0f} kHz (what the fit sees)")
ax.plot(tt, lp20[sl], lw=1.1, color="#2E8B57", zorder=4,
        label=f"low pass {LP_OFF_KHZ:.0f} kHz (official Eabs prefilter)")
ax.plot(tt, fit_adc[sl], lw=1.7, color="#C0392B", zorder=5,
        label="two-exponential fit")
ax.plot([], [], color="#C0392B", alpha=0.25, lw=8,
        label=f"fit $\\pm$ 1$\\sigma$ noise ($\\sigma$ = {sigma:.0f} ADC)")

# the four candidate heights: faint guide lines, numbers collected in one box
for y, c in [(pk_raw, "#7F8C8D"), (pk_100, "#1F77B4"),
             (pk_20, "#2E8B57"), (pk_fit, "#C0392B")]:
    ax.axhline(y, color=c, lw=0.8, ls=(0, (6, 5)), alpha=0.75, zorder=3)
ax.plot([t_ms[i_raw]], [pk_raw], marker="v", ms=9, color="#34495E", zorder=7)

rows = [("raw max", pk_raw, "#7F8C8D"),
        (f"LP {LP_FIT_KHZ:.0f} kHz", pk_100, "#1F77B4"),
        (f"LP {LP_OFF_KHZ:.0f} kHz", pk_20, "#2E8B57"),
        ("fit peak", pk_fit, "#C0392B")]
box_x, box_y, dy = 0.985, 0.975, 0.052
ax.text(box_x, box_y, f"{'pulse height':<12}{'ADC':>8}{'uA':>10}{'fW':>9}"
        f"{'vs fit':>9}", transform=ax.transAxes, ha="right", va="top",
        family="monospace", fontsize=10, weight="bold", zorder=8, bbox=dict(facecolor="white", alpha=0.88, edgecolor="none", pad=1.5), )
for k, (lab, y, c) in enumerate(rows):
    ax.text(box_x, box_y - (k + 1) * dy,
            f"{lab:<12}{y:8.1f}{y / ADC_PER_AMP * 1e6:10.4f}"
            f"{float(power_fW(y)):9.1f}"
            + (f"{(y - pk_fit) / sigma:+8.2f}$\\sigma$" if y != pk_fit else
               f"{'-':>9}"),
            transform=ax.transAxes, ha="right", va="top", color=c,
            family="monospace", fontsize=10, zorder=8, bbox=dict(facecolor="white", alpha=0.88, edgecolor="none", pad=1.5), )
ax.text(box_x, box_y - 5.2 * dy,
        f"{'energy (closed form)':<20}{E_EV:8.1f} eV", transform=ax.transAxes,
        ha="right", va="top", color="#C0392B", family="monospace", fontsize=10,
        weight="bold", zorder=8, bbox=dict(facecolor="white", alpha=0.88, edgecolor="none", pad=1.5), )

ax.annotate(f"largest single sample, {pk_raw - pk_fit:.0f} ADC "
            f"({(pk_raw - pk_fit) / sigma:.2f}$\\sigma$) above the fit",
            xy=(t_ms[i_raw], pk_raw), xytext=(0.015, 0.965),
            textcoords="axes fraction", fontsize=10, color="#34495E",
            arrowprops=dict(arrowstyle="->", color="#34495E", lw=1.0))
ax.annotate(f"flat top:\n{n_top} samples within\n{100 * (1 - TOP_FRAC):.0f}% of the peak",
            xy=(top_lo, 0.62 * pk_fit),
            xytext=(0.015, 0.50), textcoords="axes fraction", fontsize=10,
            color="#8A6D00",
            arrowprops=dict(arrowstyle="->", color="#8A6D00", lw=1.0))

ax.set_xlim(args.lo_ms, args.hi_ms)
ax.set_ylim(-2.6 * sigma, 1.32 * pk_raw)
ax.set_xlabel("Time from trigger (ms)", fontsize=12)
ax.set_ylabel("pulse height above baseline (ADC)", fontsize=12)
sec = ax.secondary_yaxis("right",
                         functions=(lambda a: a / ADC_PER_AMP * 1e6,
                                    lambda u: u * 1e-6 * ADC_PER_AMP))
sec.set_ylabel("current $\\delta I$ ($\\mu$A)", fontsize=12, color="#1F3864")
sec.tick_params(colors="#1F3864")
pw = ax.secondary_yaxis(1.075, functions=(power_fW, fW_to_adc))
pw.set_ylabel(f"absorbed power $P$ (fW), {args.formula}", fontsize=12,
              color="#7B241C")
pw.tick_params(colors="#7B241C")
ax.grid(alpha=0.22)
ax.legend(fontsize=9.5, loc="lower left", ncol=2, framealpha=0.93)
ax.set_title(f"Z{det} {chan}, event {evn} ({series}): one pulse read three ways, "
             f"as ADC, as current and as power", fontsize=12.5)
ax.text(0.5, -0.105,
        f"baseline = mean of bins {BASE_LO}-{BASE_HI} = {base:.1f} ADC, "
        f"subtracted   |   1 ADC = {1e9 / ADC_PER_AMP:.4f} nA   |   "
        f"power axis is exact, so its ticks are not evenly spaced\n"
        f"$P = I_0(R_L-R_0)\\,\\delta I + c_2R_L\\,\\delta I^2$   "
        f"({args.formula}, $c_2$={C2:.0f}):   "
        f"$I_0$={I0 * 1e6:.3f} $\\mu$A,  $R_0$={R0 * 1e3:.3f} m$\\Omega$,  "
        f"$R_L$={RL * 1e3:.3f} m$\\Omega$   "
        f"$\\Rightarrow$  {LIN:.4e} V  and  {QUAD:.5f} $\\Omega$",
        transform=ax.transAxes, ha="center", va="top", fontsize=9.5,
        color="#444444")
fig.tight_layout(rect=(0, 0.075, 1, 1))
os.makedirs(OUT_DIR, exist_ok=True)
fn = os.path.join(OUT_DIR,
                  f"zip{det}_{series}_peak_raw_vs_lp_{chan}_ev{evn}.png")
fig.savefig(fn, dpi=160)
plt.close(fig)
print("saved", fn)
print(f"baseline {base:.2f} ADC, sigma {sigma:.2f} ADC")
print(f"coefficients: linear {LIN:.6e} V, quadratic {QUAD:.6f} Ohm (c2={C2:.0f})")
for lab, v in [("raw max", pk_raw), (f"{LP_FIT_KHZ:.0f} kHz max", pk_100),
               (f"{LP_OFF_KHZ:.0f} kHz max", pk_20), ("fit peak", pk_fit)]:
    print(f"  {lab:>14}: {v:8.2f} ADC = {v / ADC_PER_AMP * 1e6:.4f} uA = "
          f"{float(power_fW(v)):7.2f} fW"
          f"   ({v - pk_fit:+7.2f} ADC = {(v - pk_fit) / sigma:+.2f} sigma vs fit)")
print(f"  closed-form energy from the fit: {E_EV:.2f} eV")
print(f"  samples above {100 * TOP_FRAC:.0f}% of the peak: {n_top} "
      f"({top_lo:.3f} .. {top_hi:.3f} ms)")
