#!/usr/bin/env python3
"""Power pulse and its integral from the FITTED current pulse, not the raw trace.

The raw trace carries noise and low-frequency baseline motion, so integrating it
over a long window makes the answer drift with the window length (an offset of
1 nA over 15 ms is worth 42 eV). The two-exponential fit removes both: it is
smooth, it returns to zero by construction, and its integrals have closed forms,
so the energy no longer depends on where the integration stops.

    fitted current   dI(t) = A[exp(-(t-t0)/tau_f) - exp(-(t-t0)/tau_r)],  t > t0
    power            P(t)  = I0(R_L-R0)*dI(t) + c2*R_L*dI(t)^2
    closed-form      int dI  dt = A(tau_f - tau_r)
                     int dI^2 dt = A^2[tau_f/2 + tau_r/2
                                       - 2 tau_f tau_r/(tau_f+tau_r)]

so  E = I0(R_L-R0)*A(tau_f-tau_r) + c2*R_L*A^2[...]  exactly, with no window.

The left axis of the pulse figures is in microamperes and the right axis in
femtowatts, tied by the linear coefficient I0(R_L-R0).

The fit is redone here directly in current units (the lp_fit_align checkpoints hold
amplitudes in units of each trace's own global peak, which cannot be converted
back to current without that peak), using the same model and the same free
pretrigger as the template pipeline.

Outputs (results/plots/current_power_overlay/):
    zip{det}_{series}_current_power_{chan}_{N}events.png
    zip{det}_{series}_cumulative_energy_{chan}_{N}events.png
    zip{det}_{series}_current_power_allchan_ev{N}.png
    zip{det}_{series}_cumulative_energy_allchan_ev{N}.png
    zip{det}_{series}_energies.txt

Usage (inside the CDMS singularity image):
    python3 scripts/plot_fitted_current_power.py --det 7 --series 24260617_063934
"""
import argparse
import glob
import os
import pickle

import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, filtfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- constants
ADC_PER_AMP = 3.145728e9      # 8192 BinsPerVolt * 8 driverGain * 4 LPGain * 12000 FBgain
TRIGGER_BIN = 16383           # {chan}triggerTime 26.2128 ms / 1.6 us
BASE_LO, BASE_HI = 93, 15758  # official baseline window
INT_LO_US, INT_HI_US = 500.0, 1000.0    # official integration window
FILT_ORDER, FILT_CUTOFF = 5, 20000.0    # official prefilter (raw comparison only)
FIT_LP_KHZ = 100.0            # light LP before fitting, as in lp_fit_align
PT_FREEDOM = 3000             # pretrigger search range, bins
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
ap.add_argument("--chan", default="PBS1")
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
_cfg = lambda c, f: float(cfg[f"{c}{f}"].array(library="np")[0])

bias = {}
for c in CHANS:
    i0, r0 = _cfg(c, "i0"), _cfg(c, "r0")
    if not np.isfinite(i0) or i0 == 0 or r0 <= 0:
        continue
    rl = _cfg(c, "rp") + _cfg(c, "rshunt")
    bias[c] = dict(i0=i0, r0=r0, rl=rl, dt=_cfg(c, "timePerBin"),
                   lin=i0 * (rl - r0), quad=c2_fac * rl)
DT = bias[args.chan]["dt"]
N_BINS = 32768
T_END_MS = N_BINS * DT * 1e3          # 52.4288 ms, the full trace
INT_LO = TRIGGER_BIN - int(round(INT_LO_US * 1e-6 / DT))
INT_HI = TRIGGER_BIN + int(round(INT_HI_US * 1e-6 / DT))
b20, a20 = butter(FILT_ORDER, FILT_CUTOFF / (0.5 / DT), btype="low")
b100, a100 = butter(4, FIT_LP_KHZ * 1e3 / (0.5 / DT), btype="low")

# ------------------------------------------------------------------- traces
cache = pickle.load(open(os.path.join(RAW_CACHE, f"zip{det}_series",
                                      f"{series}.pkl"), "rb"))
idx = {c: {int(e): i for i, e in enumerate(cache["event_numbers_ch"].get(c, []))}
       for c in CHANS}
if args.events:
    events = [e for e in args.events if e in idx.get(args.chan, {})]
else:
    ok = [e for e in cache["selected_event_numbers"]
          if int(e) in idx.get(args.chan, {})]
    rng = np.random.default_rng(args.seed)
    events = sorted(int(e) for e in rng.choice(ok, size=min(args.n_events, len(ok)),
                                               replace=False))
print(f"{len(events)} events: {events}")


def two_exp(x, amp, t_rise, t_fall, baseline, pretrigger):
    """Same model as the template pipeline (all five parameters free).

    x in bins, amp/baseline in amperes, t_rise/t_fall in seconds.
    """
    dt = (x - pretrigger) * DT
    with np.errstate(over="ignore", invalid="ignore"):
        pulse = amp * (np.exp(-np.clip(dt, 0.0, None) / t_fall)
                       - np.exp(-np.clip(dt, 0.0, None) / t_rise))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def _two_exp_scaled(t_ms, amp_uA, tr_ms, tf_ms, base_uA, t0_ms):
    """The same model in units that make every parameter O(1), which is what the
    fitter needs: currents in uA, times in ms, t0 relative to the trigger.
    Fitting in A/s/bins leaves amp ~1e-7 next to pretrigger ~1.6e4 and curve_fit
    converges on the first step without moving the time constants at all."""
    dt = t_ms - t0_ms
    with np.errstate(over="ignore", invalid="ignore"):
        pulse = amp_uA * (np.exp(-np.clip(dt, 0.0, None) / tf_ms)
                          - np.exp(-np.clip(dt, 0.0, None) / tr_ms))
    return np.where(t_ms <= t0_ms, base_uA, pulse + base_uA)


def fit_current(chan, evn):
    """Fit the two-exponential directly in amperes. Returns (params, di, di_f)."""
    i = idx[chan].get(evn)
    if i is None:
        return None
    tr = np.asarray(cache["raw_traces"][chan][i], dtype=np.float64)
    if tr.size != N_BINS:
        return None
    di = (tr - tr[BASE_LO:BASE_HI].mean()) / ADC_PER_AMP     # amperes
    y = filtfilt(b100, a100, di)
    lo, hi = TRIGGER_BIN - PT_FREEDOM - 500, TRIGGER_BIN + 8000
    x = np.arange(lo, hi, 4, dtype=np.float64)
    yy = y[lo:hi:4]
    t_ms = (x - TRIGGER_BIN) * DT * 1e3
    y_uA = yy * 1e6
    pk = float(np.max(y_uA))
    free_ms = PT_FREEDOM * DT * 1e3
    p0 = (pk / 0.4, 0.1, 0.5, 0.0, 0.0)
    bounds = ((0.0, 1e-3, 1e-3, -abs(pk), -free_ms),
              (100 * pk + 1e-6, 10.0, 50.0, abs(pk), free_ms))
    try:
        p, _ = curve_fit(_two_exp_scaled, t_ms, y_uA, p0=p0, bounds=bounds,
                         maxfev=20000, x_scale="jac")
    except Exception as exc:
        print(f"  fit failed {chan} ev{evn}: {exc}")
        return None
    amp = p[0] * 1e-6
    t_r, t_f = p[1] * 1e-3, p[2] * 1e-3
    base = p[3] * 1e-6
    pt0 = TRIGGER_BIN + p[4] * 1e-3 / DT
    if not (amp > 0 and 0 < t_r < t_f):
        print(f"  fit rejected {chan} ev{evn}: amp={amp:.3e} "
              f"t_rise={t_r:.2e} t_fall={t_f:.2e}")
        return None
    resid = yy - two_exp(x, amp, t_r, t_f, base, pt0)
    peak = (two_exp(np.arange(lo, hi, dtype=np.float64), amp, t_r, t_f, base, pt0).max()
            - base)
    nrmse = float(np.sqrt(np.mean(resid ** 2)) / peak) if peak > 0 else np.nan
    return dict(amp=amp, t_rise=t_r, t_fall=t_f, base=base, pt=pt0,
                nrmse=nrmse, di=di, di20=filtfilt(b20, a20, di))


def energies(chan, f):
    """Closed-form energy from the fit, plus numerical checks [eV]."""
    B, dt = bias[chan], bias[chan]["dt"]
    A, t_r, t_f = f["amp"], f["t_rise"], f["t_fall"]
    i1 = A * (t_f - t_r)                                    # int dI dt
    i2 = A ** 2 * (t_f / 2 + t_r / 2 - 2 * t_f * t_r / (t_f + t_r))   # int dI^2 dt
    e_closed = (B["lin"] * i1 + B["quad"] * i2) / J_PER_EV
    x = np.arange(N_BINS, dtype=np.float64)
    fit = two_exp(x, A, t_r, t_f, 0.0, f["pt"])             # baseline dropped
    p_fit = B["lin"] * fit + B["quad"] * fit ** 2
    e_num = p_fit.sum() * dt / J_PER_EV                     # 0 .. 52.43 ms
    raw = f["di20"]
    p_raw = B["lin"] * raw + B["quad"] * raw ** 2
    e_raw_win = p_raw[INT_LO:INT_HI].sum() * dt / J_PER_EV
    e_raw_all = p_raw.sum() * dt / J_PER_EV
    e_fit_win = p_fit[INT_LO:INT_HI].sum() * dt / J_PER_EV
    quad_frac = 100 * B["quad"] * i2 / (B["lin"] * i1 + B["quad"] * i2)
    return dict(closed=e_closed, num=e_num, fit_win=e_fit_win,
                raw_win=e_raw_win, raw_all=e_raw_all, quad=quad_frac,
                p_fit=p_fit, fit=fit, p_raw=p_raw)


def draw_pulse(ax, chan, f, e, label):
    dt = bias[chan]["dt"]
    lo = TRIGGER_BIN - int(round(1e-3 / dt))
    hi = TRIGGER_BIN + int(round(8e-3 / dt))
    t = (np.arange(lo, hi) - TRIGGER_BIN) * dt * 1e3
    ax2 = ax.twinx()
    ax.set_zorder(2)
    ax2.set_zorder(1)
    ax.patch.set_visible(False)
    ax2.axvspan((INT_LO - TRIGGER_BIN) * dt * 1e3, (INT_HI - TRIGGER_BIN) * dt * 1e3,
                color="#FFE9A8", alpha=0.5, zorder=0)
    # the raw trace goes on the lower axes so the power curve stays visible; the
    # two axes are tied by the linear coefficient, so nA * lin * 1e6 = fW
    to_fw = bias[chan]["lin"] * 1e9          # uA on the left -> fW on the right
    ax2.plot(t, f["di"][lo:hi] * 1e6 * to_fw, lw=0.4, color="#CDCDCD", zorder=1)
    ax2.plot(t, f["di20"][lo:hi] * 1e6 * to_fw, lw=0.7, color="#93A3B5", zorder=2)
    ax2.plot(t, e["p_fit"][lo:hi] * 1e15, lw=2.6, color="#E00000", zorder=3)
    ax.plot([], [], lw=0.4, color="#CDCDCD", label="raw current (not used)")
    ax.plot([], [], lw=0.7, color="#93A3B5", label="filtered raw current (not used)")
    ax.plot(t, e["fit"][lo:hi] * 1e6, lw=1.4, color="#0B1E4E", zorder=3,
            ls=(0, (5, 3.5)), label="fitted current $\\delta I$ (left)")
    ax.axhline(0, color="gray", lw=0.5, ls=":", zorder=0)
    # the axis range has to come from the RAW trace, which is the widest curve
    # here: autoscaling on the fitted pulse alone would clip the noise that goes
    # below zero, and the raw sits on ax2 whose limits are tied to ax
    span = np.concatenate([f["di"][lo:hi], e["fit"][lo:hi]]) * 1e6
    pad = 0.08 * (span.max() - span.min())
    ax.set_ylim(span.min() - pad, span.max() + pad)
    ax2.set_ylim(*(np.asarray(ax.get_ylim()) * 1e-6 * bias[chan]["lin"] * 1e15))
    ax.set_title(f"{label}   $E$ = {e['closed']:.0f} eV (closed form)   "
                 f"$\\tau_r$ = {f['t_rise'] * 1e6:.0f} $\\mu$s, "
                 f"$\\tau_f$ = {f['t_fall'] * 1e6:.0f} $\\mu$s, "
                 f"NRMSE {f['nrmse']:.3f}", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax2.tick_params(labelsize=6.5, colors="#C0392B")
    ax.grid(alpha=0.2)
    return ax2


def draw_cum(ax, chan, f, e, label):
    """Cumulative energy over the whole trace, fit vs raw."""
    dt = bias[chan]["dt"]
    t = np.arange(N_BINS) * dt * 1e3
    cum_fit = np.cumsum(e["p_fit"]) * dt / J_PER_EV
    cum_raw = np.cumsum(e["p_raw"]) * dt / J_PER_EV
    ax.plot(t, cum_raw, lw=0.9, color="#8899AA", zorder=2,
            label="from the raw trace (drifts)")
    ax.plot(t, cum_fit, lw=1.8, color="#E00000", zorder=3,
            label="from the fitted pulse")
    ax.axhline(e["closed"], color="#1B7A3D", lw=1.0, ls=(0, (5, 3)), zorder=4,
               label="closed-form energy")
    ax.axvline(TRIGGER_BIN * dt * 1e3, color="gray", lw=0.6, ls=":", zorder=1)
    ax.set_xlim(0, T_END_MS)
    ax.set_title(f"{label}   fit {e['num']:.0f} eV = closed form "
                 f"{e['closed']:.0f} eV   |   raw {e['raw_all']:.0f} eV",
                 fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.grid(alpha=0.2)


STAMP = "\n".join([
    f"Z{det} {series}, K-line events | {args.formula}: "
    f"P(t) = I0(R_L-R0)*dI(t) {c2_fac:+.0f}*R_L*(dI(t))^2 | "
    f"bias point per channel from detectorConfig, ADC/A = {ADC_PER_AMP:.6e}",
    "the current is the two-exponential FIT, refitted directly in amperes "
    f"(model A[exp(-t/tau_f)-exp(-t/tau_r)], 5 free params, pretrigger free in "
    f"{TRIGGER_BIN}+-{PT_FREEDOM}); the raw trace is drawn only for reference",
    "integration runs over the whole trace, 0 to "
    f"{T_END_MS:.2f} ms; for the fitted pulse this equals the closed-form "
    "integral, so the energy no longer depends on the window",
])

os.makedirs(OUT_DIR, exist_ok=True)
rows = []

# --------------------------------------------- figures 1 and 2: N events, 1 chan
chan = args.chan
fits = {}
for evn in events:
    f = fit_current(chan, evn)
    if f is None:
        continue
    fits[evn] = (f, energies(chan, f))
good = list(fits)
ncol = 3
nrow = int(np.ceil(len(good) / ncol))

for kind in ("pulse", "cum"):
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 2.1 * nrow),
                             squeeze=False)
    for k, evn in enumerate(good):
        ax = axes[k // ncol][k % ncol]
        f, e = fits[evn]
        if kind == "pulse":
            ax2 = draw_pulse(ax, chan, f, e, f"ev {evn}")
            if k % ncol == ncol - 1:
                ax2.set_ylabel("$P$ (fW)", fontsize=7, color="#C0392B")
            if k % ncol == 0:
                ax.set_ylabel("$\\delta I$ ($\\mu$A)", fontsize=7, color="#1F3864")
        else:
            draw_cum(ax, chan, f, e, f"ev {evn}")
            if k % ncol == 0:
                ax.set_ylabel("cumulative $E$ (eV)", fontsize=7, color="#C0392B")
        if k // ncol == nrow - 1:
            ax.set_xlabel("Time from trigger (ms)" if kind == "pulse"
                          else "Time from trace start (ms)", fontsize=7)
    for k in range(len(good), nrow * ncol):
        axes[k // ncol][k % ncol].set_axis_off()
    h, l = axes[0][0].get_legend_handles_labels()
    if kind == "pulse":
        h.append(plt.Line2D([], [], color="#E00000", lw=2.2))
        l.append("power $P$ from the fit (right axis)")
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=8, frameon=False)
    head = ("fitted current pulse (dashed navy) and the power pulse it implies "
            "(red)" if kind == "pulse" else
            "integrated power = absorbed energy, fitted pulse vs raw trace")
    fig.suptitle(f"Z{det} {chan}: {head}\n" + STAMP, fontsize=8.5, y=0.998)
    fig.tight_layout(rect=(0, 0.028, 1, 0.932))
    fn = os.path.join(OUT_DIR, f"zip{det}_{series}_"
                      f"{'current_power' if kind == 'pulse' else 'cumulative_energy'}"
                      f"_{chan}_{len(good)}events.png")
    fig.savefig(fn, dpi=160)
    plt.close(fig)
    print("saved", fn)

for evn in good:
    f, e = fits[evn]
    rows.append((evn, chan, e, f))

# --------------------------------------------- figures 3 and 4: 1 event, all chan
ev0 = good[0]
ch_fits = {}
for c in CHANS:
    if c not in bias or idx.get(c, {}).get(ev0) is None:
        continue
    f = fit_current(c, ev0)
    if f is not None:
        ch_fits[c] = (f, energies(c, f))
chans = list(ch_fits)
tot_closed = sum(ch_fits[c][1]["closed"] for c in chans)
tot_rawwin = sum(ch_fits[c][1]["raw_win"] for c in chans)
ncol2 = 4
nrow2 = int(np.ceil(len(chans) / ncol2))
for kind in ("pulse", "cum"):
    fig, axes = plt.subplots(nrow2, ncol2, figsize=(4.4 * ncol2, 2.1 * nrow2),
                             squeeze=False)
    for k, c in enumerate(chans):
        ax = axes[k // ncol2][k % ncol2]
        f, e = ch_fits[c]
        if kind == "pulse":
            ax2 = draw_pulse(ax, c, f, e, c)
            if k % ncol2 == ncol2 - 1:
                ax2.set_ylabel("$P$ (fW)", fontsize=7, color="#C0392B")
        else:
            draw_cum(ax, c, f, e, c)
        if k % ncol2 == 0:
            ax.set_ylabel("$\\delta I$ ($\\mu$A)" if kind == "pulse"
                          else "cumulative $E$ (eV)", fontsize=7)
        if k // ncol2 == nrow2 - 1:
            ax.set_xlabel("Time from trigger (ms)" if kind == "pulse"
                          else "Time from trace start (ms)", fontsize=7)
    for k in range(len(chans), nrow2 * ncol2):
        axes[k // ncol2][k % ncol2].set_axis_off()
    fig.suptitle(f"Z{det} event {ev0}, all channels: "
                 f"{'fitted current and power' if kind == 'pulse' else 'integrated power'}"
                 f"\nsum over channels from the fits: {tot_closed:.0f} eV = "
                 f"{100 * tot_closed / 10370:.1f}% of 10.37 keV   "
                 f"(official-window raw sum {tot_rawwin:.0f} eV = "
                 f"{100 * tot_rawwin / 10370:.1f}%)\n" + STAMP, fontsize=8.5, y=0.997)
    fig.tight_layout(rect=(0, 0, 1, 0.925))
    fn = os.path.join(OUT_DIR, f"zip{det}_{series}_"
                      f"{'current_power' if kind == 'pulse' else 'cumulative_energy'}"
                      f"_allchan_ev{ev0}.png")
    fig.savefig(fn, dpi=160)
    plt.close(fig)
    print("saved", fn)

# ---------------------------------------------------------------- text table
fn = os.path.join(OUT_DIR, f"zip{det}_{series}_energies.txt")
with open(fn, "w") as fh:
    fh.write(STAMP + "\n\n")
    hdr = (f"{'event':>9} {'chan':>6} {'E_closed':>9} {'E_num':>9} {'E_fitwin':>9} "
           f"{'E_rawwin':>9} {'E_rawall':>9} {'quad%':>6} {'t_r[us]':>8} "
           f"{'t_f[us]':>8} {'NRMSE':>7}\n")
    fh.write(f"[1] {len(rows)} events, channel {chan}   (energies in eV)\n" + hdr)
    for evn, c, e, f in rows:
        fh.write(f"{evn:>9} {c:>6} {e['closed']:>9.1f} {e['num']:>9.1f} "
                 f"{e['fit_win']:>9.1f} {e['raw_win']:>9.1f} {e['raw_all']:>9.1f} "
                 f"{e['quad']:>6.2f} {f['t_rise'] * 1e6:>8.0f} "
                 f"{f['t_fall'] * 1e6:>8.0f} {f['nrmse']:>7.3f}\n")
    med = lambda k: np.median([e[k] for _, _, e, _ in rows])
    fh.write(f"median: closed {med('closed'):.1f} eV, numerical {med('num'):.1f} eV, "
             f"fit-in-window {med('fit_win'):.1f} eV, "
             f"raw-in-window {med('raw_win'):.1f} eV, "
             f"raw-full-trace {med('raw_all'):.1f} eV\n")
    sc = np.array([e['closed'] for _, _, e, _ in rows])
    sr = np.array([e['raw_win'] for _, _, e, _ in rows])
    fh.write(f"spread (std/median): fitted {sc.std() / np.median(sc):.3f}, "
             f"raw-in-window {sr.std() / np.median(sr):.3f}\n")

    fh.write(f"\n[2] event {ev0}, all channels\n" + hdr)
    for c in chans:
        f, e = ch_fits[c]
        fh.write(f"{ev0:>9} {c:>6} {e['closed']:>9.1f} {e['num']:>9.1f} "
                 f"{e['fit_win']:>9.1f} {e['raw_win']:>9.1f} {e['raw_all']:>9.1f} "
                 f"{e['quad']:>6.2f} {f['t_rise'] * 1e6:>8.0f} "
                 f"{f['t_fall'] * 1e6:>8.0f} {f['nrmse']:>7.3f}\n")
    fh.write(f"\nevent {ev0} all-channel sum from the fits: {tot_closed:.1f} eV "
             f"({100 * tot_closed / 10370:.2f}% of 10.37 keV)\n")
    fh.write(f"same event, official-window raw sum:      {tot_rawwin:.1f} eV "
             f"({100 * tot_rawwin / 10370:.2f}%)\n")

    # ---- collection efficiency: every channel of every event
    fh.write(f"\n[3] collection efficiency, all channels of all {len(good)} events\n")
    fh.write(f"{'event':>9} {'nchan':>6} {'E_fit[eV]':>10} {'eta_fit':>8} "
             f"{'E_rawwin[eV]':>13} {'eta_raw':>8} {'in-window frac':>15}\n")
    eta_f, eta_r = [], []
    for evn in good:
        tc = tr = tw = 0.0
        n = 0
        for c in CHANS:
            if c not in bias or idx.get(c, {}).get(evn) is None:
                continue
            ff = fit_current(c, evn)
            if ff is None:
                continue
            ee = energies(c, ff)
            tc += ee["closed"]
            tr += ee["raw_win"]
            tw += ee["fit_win"]
            n += 1
        eta_f.append(100 * tc / 10370)
        eta_r.append(100 * tr / 10370)
        fh.write(f"{evn:>9} {n:>6} {tc:>10.1f} {eta_f[-1]:>7.2f}% "
                 f"{tr:>13.1f} {eta_r[-1]:>7.2f}% {tw / tc:>14.3f}\n")
    eta_f, eta_r = np.array(eta_f), np.array(eta_r)
    fh.write(f"\nmedian collection efficiency, fitted pulses : "
             f"{np.median(eta_f):.2f}%  (spread {eta_f.std():.2f} points)\n")
    fh.write(f"median collection efficiency, official window: "
             f"{np.median(eta_r):.2f}%  (spread {eta_r.std():.2f} points)\n")
    fh.write("the in-window fraction says how much of the fitted pulse energy "
             "falls inside the official window; the rest is the analytic tail.\n")
print("saved", fn)
