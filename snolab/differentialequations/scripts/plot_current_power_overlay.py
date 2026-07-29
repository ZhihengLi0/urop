#!/usr/bin/env python3
"""Current pulse vs power pulse overlay for Z7 K-line events (Method 1).

The trace y-axis is CURRENT, so the raw pulse area is charge, not energy. The
electro-thermal equations turn the measured current into the absorbed power,

    P(t) = -dP_J(t) = I0*(R_L - R0)*dI(t) + c2*dI(t)^2

with dI(t) the baseline-subtracted current, I0/R0/R_L the bias point from the
per-channel detectorConfig, and the quadratic coefficient set by the formula:

    Method 1 (Noah, CollEff wiki p.2) : c2 = +2*R_L      <-- used here
    Method 2 (Watkins, CollEff wiki)  : c2 = -1*R_L      (opposite dI sign conv.)
    exact expansion of dP_J           : c2 = +1*R_L

Method 1 is the better of the two published forms: its linear coefficient is
identical to the exact one and only the quadratic coefficient is off (a ~0.5%
effect on 10 keV pulses), whereas Method 2 also flips the quadratic sign.

Conventions follow the official Eabs RQ (reproduced to 0.2%, see NOTES.md 6d):
trigger bin 16383, baseline = mean of bins 93..15758, 5-pole 20 kHz Butterworth
prefilter, integration window -500 us .. +1000 us around the trigger.

Outputs (results/plots/current_power_overlay/):
    zip{det}_{series}_current_power_{chan}_15events.png   15 events, one channel
    zip{det}_{series}_current_power_allchan_ev{N}.png     one event, all channels
    zip{det}_{series}_current_power_energies.txt          per-event energy table

Usage (inside the CDMS singularity image):
    python3 scripts/plot_current_power_overlay.py --det 7 --series 24260617_063934
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

# ---------------------------------------------------------------- constants
ADC_PER_AMP = 3.145728e9      # 8192 BinsPerVolt * 8 driverGain * 4 LPGain * 12000 FBgain
TRIGGER_BIN = 16383           # {chan}triggerTime 26.2128 ms / 1.6 us
BASE_LO, BASE_HI = 93, 15758  # 150 us from start .. 1000 us before trigger
INT_LO_US, INT_HI_US = 500.0, 1000.0   # official integration window around trigger
FILT_ORDER, FILT_CUTOFF = 5, 20000.0   # official prefilter
J_PER_EV = 1.602176634e-19
CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
         "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]
QUAD_COEF = {"method1": 2.0, "method2": -1.0, "exact": 1.0}

RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
PROC_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
            "/Processed/Default/Default_tag/Unmerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "results", "plots", "current_power_overlay")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--series", default="24260617_063934")
ap.add_argument("--chan", default="PBS1", help="channel for the 15-event figure")
ap.add_argument("--n-events", type=int, default=15)
ap.add_argument("--events", type=int, nargs="+", default=None)
ap.add_argument("--formula", default="method1", choices=sorted(QUAD_COEF))
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()
det, series = args.det, args.series
c2_fac = QUAD_COEF[args.formula]

# ------------------------------------------------------- bias point per channel
cfg_paths = (sorted(glob.glob(os.path.join(PROC_DIR, f"{series}_Addison.root")))
             + sorted(glob.glob(os.path.join(PROC_DIR,
                                             f"UMN.Addison.*_{series}_F*.root"))))
cfg = uproot.open(cfg_paths[0])[f"detectorConfigDir/detectorConfigZip{det}"]


def _cfg(chan, field):
    return float(cfg[f"{chan}{field}"].array(library="np")[0])


bias = {}
for c in CHANS:
    i0 = _cfg(c, "i0")                       # signed, negative
    r0, rp, rsh = _cfg(c, "r0"), _cfg(c, "rp"), _cfg(c, "rshunt")
    dt = _cfg(c, "timePerBin")
    if not np.isfinite(i0) or i0 == 0 or r0 <= 0:
        continue
    rl = rp + rsh
    bias[c] = dict(i0=i0, r0=r0, rl=rl, dt=dt,
                   lin=i0 * (rl - r0),        # V, positive (both factors negative)
                   quad=c2_fac * rl)
print(f"bias point read for {len(bias)} channels; dt = "
      f"{bias[args.chan]['dt'] * 1e6:.2f} us")

# ------------------------------------------------------------------- traces
cache = pickle.load(open(os.path.join(RAW_CACHE, f"zip{det}_series",
                                      f"{series}.pkl"), "rb"))
idx = {c: {int(e): i for i, e in enumerate(cache["event_numbers_ch"].get(c, []))}
       for c in CHANS}
selected = [int(e) for e in cache["selected_event_numbers"]]

if args.events:
    events = [e for e in args.events if e in idx.get(args.chan, {})]
else:
    ok = [e for e in selected if e in idx.get(args.chan, {})]
    rng = np.random.default_rng(args.seed)
    events = sorted(rng.choice(ok, size=min(args.n_events, len(ok)),
                               replace=False).tolist())
print(f"{len(events)} events: {events}")

DT = bias[args.chan]["dt"]
b_lp, a_lp = butter(FILT_ORDER, FILT_CUTOFF / (0.5 / DT), btype="low")
INT_LO = TRIGGER_BIN - int(round(INT_LO_US * 1e-6 / DT))
INT_HI = TRIGGER_BIN + int(round(INT_HI_US * 1e-6 / DT))


def current_and_power(chan, evn):
    """Baseline-subtracted filtered current [A] and power [W] for one trace."""
    i = idx[chan].get(evn)
    if i is None:
        return None
    tr = np.asarray(cache["raw_traces"][chan][i], dtype=np.float64)
    if tr.size < TRIGGER_BIN:
        return None
    di = (tr - tr[BASE_LO:BASE_HI].mean()) / ADC_PER_AMP
    di_f = filtfilt(b_lp, a_lp, di)
    p = bias[chan]["lin"] * di_f + bias[chan]["quad"] * di_f ** 2
    return di, di_f, p


def energies(chan, p, di_f):
    """Energy in the official window and in a wide 16 ms window [eV], and the
    quadratic-term share of the official-window energy [%]."""
    dt = bias[chan]["dt"]
    e_off = p[INT_LO:INT_HI].sum() * dt / J_PER_EV
    hi16 = min(TRIGGER_BIN + int(round(16e-3 / dt)), p.size)
    e_16 = p[INT_LO:hi16].sum() * dt / J_PER_EV
    quad = bias[chan]["quad"] * (di_f[INT_LO:INT_HI] ** 2).sum() * dt / J_PER_EV
    return e_off, e_16, 100.0 * quad / e_off if e_off else np.nan


QUAD_MAG = 20            # magnification of the dI^2 term so its shape is visible


def draw(ax, chan, evn, label, t_lo_ms=-1.0, t_hi_ms=8.0):
    res = current_and_power(chan, evn)
    if res is None:
        ax.set_axis_off()
        return None
    di, di_f, p = res
    dt = bias[chan]["dt"]
    lo = TRIGGER_BIN + int(round(t_lo_ms * 1e-3 / dt))
    hi = min(TRIGGER_BIN + int(round(t_hi_ms * 1e-3 / dt)), di.size)
    t = (np.arange(lo, hi) - TRIGGER_BIN) * dt * 1e3

    ax2 = ax.twinx()
    ax.set_zorder(2)                 # keep the current curves on top of ax2
    ax2.set_zorder(1)
    ax.patch.set_visible(False)
    ax2.axvspan((INT_LO - TRIGGER_BIN) * dt * 1e3,
                (INT_HI - TRIGGER_BIN) * dt * 1e3,
                color="#FFE9A8", alpha=0.5, zorder=0)
    ax2.plot(t, p[lo:hi] * 1e15, lw=3.4, color="#C0392B", alpha=0.55, zorder=1,
             solid_capstyle="round")
    ax2.plot(t, bias[chan]["quad"] * di_f[lo:hi] ** 2 * QUAD_MAG * 1e15,
             lw=0.9, ls=(0, (4, 2)), color="#6C3483", zorder=2)
    ax.plot(t, di[lo:hi] * 1e9, lw=0.45, color="#AAAAAA", alpha=0.7, zorder=1,
            label="current, unfiltered")
    ax.plot(t, di_f[lo:hi] * 1e9, lw=1.2, color="#1F3864", zorder=3,
            label="current $\\delta I$, filtered (left)")
    ax.axhline(0, color="gray", lw=0.5, ls=":", zorder=0)
    # tie the power axis to the current axis through the linear coefficient
    # I0*(R_L-R0): the two curves then coincide except for the quadratic term,
    # so every visible blue/red separation is the dI^2 contribution.
    ax2.set_ylim(*(np.asarray(ax.get_ylim()) * 1e-9 * bias[chan]["lin"] * 1e15))
    e_off, e_16, quad = energies(chan, p, di_f)
    ax.set_title(f"{label}   $E$ = {e_off:.0f} eV (win) / {e_16:.0f} eV (16 ms),"
                 f" quad {quad:+.2f}%", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax2.tick_params(labelsize=6.5, colors="#C0392B")
    ax.grid(alpha=0.2)
    return e_off, e_16, quad, ax2


STAMP = "\n".join([
    f"Z{det} {series}, K-line events | {args.formula}: "
    f"P(t) = I0(R_L-R0)*dI(t) {c2_fac:+.0f}*R_L*dI(t)^2 | "
    f"bias point per channel from detectorConfig, ADC/A = {ADC_PER_AMP:.6e}",
    f"trigger bin {TRIGGER_BIN}, baseline bins {BASE_LO}-{BASE_HI}, "
    f"{FILT_ORDER}-pole {FILT_CUTOFF / 1e3:.0f} kHz Butterworth prefilter, "
    f"shaded band = official integration window "
    f"(-{INT_LO_US:.0f}/+{INT_HI_US:.0f} us)",
    "the power axis is tied to the current axis by the linear coefficient "
    f"I0(R_L-R0), so any blue/red separation is the dI^2 term "
    f"(dashed purple, magnified x{QUAD_MAG})",
])

os.makedirs(OUT_DIR, exist_ok=True)
rows_ev = []        # the N-event, one-channel figure
rows_ch = []        # the one-event, all-channel figure

# ---------------------------------------- figure 1: N events, one channel
chan = args.chan
ncol = 3
nrow = int(np.ceil(len(events) / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 2.1 * nrow),
                         squeeze=False)
for k, evn in enumerate(events):
    ax = axes[k // ncol][k % ncol]
    out = draw(ax, chan, evn, f"ev {evn}")
    if out:
        rows_ev.append((evn, chan, out[0], out[1], out[2]))
    if k // ncol == nrow - 1:
        ax.set_xlabel("Time from trigger (ms)", fontsize=7)
    if k % ncol == 0:
        ax.set_ylabel("$\\delta I$ (nA)", fontsize=7, color="#1F3864")
    if k % ncol == ncol - 1 and out:
        out[3].set_ylabel("$P$ (fW)", fontsize=7, color="#C0392B")
for k in range(len(events), nrow * ncol):
    axes[k // ncol][k % ncol].set_axis_off()
h, l = axes[0][0].get_legend_handles_labels()
fig.suptitle(f"Z{det} {chan}: measured current pulse (blue) and the power pulse "
             f"it implies (red), {args.formula}\n" + STAMP, fontsize=8.5, y=0.998)
fig.legend(h + [plt.Line2D([], [], color="#C0392B", lw=3.4, alpha=0.55),
                plt.Line2D([], [], color="#6C3483", lw=1.0, ls=(0, (4, 2)))],
           l + ["power $P$ (right axis)",
                f"$\\delta I^2$ term only, $\\times${QUAD_MAG}"],
           loc="lower center", ncol=4, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, 0.026, 1, 0.935))
f1 = os.path.join(OUT_DIR,
                  f"zip{det}_{series}_current_power_{chan}_{len(events)}events.png")
fig.savefig(f1, dpi=160)
plt.close(fig)
print("saved", f1)

# ---------------------------------------- figure 2: one event, all channels
ev0 = events[0]
chans = [c for c in CHANS if c in bias and idx.get(c, {}).get(ev0) is not None
         and np.asarray(cache["raw_traces"][c][idx[c][ev0]]).size > TRIGGER_BIN]
ncol2 = 4
nrow2 = int(np.ceil(len(chans) / ncol2))
fig, axes = plt.subplots(nrow2, ncol2, figsize=(4.4 * ncol2, 2.1 * nrow2),
                         squeeze=False)
tot_off = tot_16 = 0.0
for k, c in enumerate(chans):
    ax = axes[k // ncol2][k % ncol2]
    out = draw(ax, c, ev0, c)
    if out:
        tot_off += out[0]
        tot_16 += out[1]
        rows_ch.append((ev0, c, out[0], out[1], out[2]))
    if k // ncol2 == nrow2 - 1:
        ax.set_xlabel("Time from trigger (ms)", fontsize=7)
    if k % ncol2 == 0:
        ax.set_ylabel("$\\delta I$ (nA)", fontsize=7, color="#1F3864")
    if k % ncol2 == ncol2 - 1 and out:
        out[3].set_ylabel("$P$ (fW)", fontsize=7, color="#C0392B")
for k in range(len(chans), nrow2 * ncol2):
    axes[k // ncol2][k % ncol2].set_axis_off()
fig.suptitle(f"Z{det} event {ev0}, all channels: current (blue) vs power (red), "
             f"{args.formula}\nsum over channels: {tot_off:.0f} eV in the "
             f"official window ({100 * tot_off / 10370:.1f}% of 10.37 keV), "
             f"{tot_16:.0f} eV out to 16 ms "
             f"({100 * tot_16 / 10370:.1f}%)\n" + STAMP, fontsize=8.5, y=0.997)
fig.tight_layout(rect=(0, 0, 1, 0.945))
f2 = os.path.join(OUT_DIR, f"zip{det}_{series}_current_power_allchan_ev{ev0}.png")
fig.savefig(f2, dpi=160)
plt.close(fig)
print("saved", f2)

# ---------------------------------------------------------------- text table
f3 = os.path.join(OUT_DIR, f"zip{det}_{series}_current_power_energies.txt")
with open(f3, "w") as fh:
    fh.write(STAMP.replace(" | ", "\n") + "\n\n")
    hdr = (f"{'event':>9} {'chan':>6} {'E_window[eV]':>13} "
           f"{'E_16ms[eV]':>11} {'quad[%]':>8}\n")

    fh.write(f"[1] {len(rows_ev)} events, channel {chan}\n" + hdr)
    for evn, c, e_off, e_16, q in rows_ev:
        fh.write(f"{evn:>9} {c:>6} {e_off:>13.1f} {e_16:>11.1f} {q:>8.2f}\n")
    fh.write(f"{chan} median: {np.median([r[2] for r in rows_ev]):.1f} eV "
             f"(window), {np.median([r[3] for r in rows_ev]):.1f} eV (16 ms)\n")

    fh.write(f"\n[2] event {ev0}, all channels\n" + hdr)
    for evn, c, e_off, e_16, q in rows_ch:
        fh.write(f"{evn:>9} {c:>6} {e_off:>13.1f} {e_16:>11.1f} {q:>8.2f}\n")
    fh.write(f"\nevent {ev0} all-channel sum: {tot_off:.1f} eV "
             f"({100 * tot_off / 10370:.2f}% of 10.37 keV), "
             f"16 ms: {tot_16:.1f} eV ({100 * tot_16 / 10370:.2f}%)\n")

    # the three quadratic coefficients side by side, same events and window
    fh.write(f"\nquadratic-coefficient comparison, {chan}, official window, "
             f"median over {len(events)} events:\n")
    dt = bias[chan]["dt"]
    lin = bias[chan]["lin"]
    ref = None
    for name in ["method1", "exact", "method2"]:
        e = []
        for evn in events:
            res = current_and_power(chan, evn)
            if res is None:
                continue
            di_f = res[1]
            p = lin * di_f + QUAD_COEF[name] * bias[chan]["rl"] * di_f ** 2
            e.append(p[INT_LO:INT_HI].sum() * dt / J_PER_EV)
        med = float(np.median(e))
        ref = med if ref is None else ref
        fh.write(f"  {name:>8} (c2 = {QUAD_COEF[name]:+.0f}*R_L): "
                 f"{med:8.2f} eV   ratio to method1 {med / ref:.4f}\n")
print("saved", f3)
