#!/usr/bin/env python3
"""Energy of every K-line event, per channel, as a histogram.

One number per event per channel: the trace is fitted with the two-exponential
model in current units and the absorbed energy is the closed-form integral of the
power pulse (same procedure as plot_fitted_current_power.py):

    dI(t) = A[exp(-(t-t0)/tau_f) - exp(-(t-t0)/tau_r)]
    E = I0(R_L-R0)*A(tau_f-tau_r)
        + c2*R_L*A^2[tau_f/2 + tau_r/2 - 2 tau_f tau_r/(tau_f+tau_r)]

The histogram of those energies is the deliverable (x axis = energy). For the
single-channel figure the official-window raw-trace energy is overlaid as a
cross-check. A Gaussian is fitted to the core of each distribution, so its centre
is the typical energy that channel collects from a 10.37 keV event and its width
is that channel's single-channel resolution.

Fits are cached per series under run/fit_cache/zip{det}/{series}.pkl (physical
units: amperes and seconds, plus the raw-window energy), so reruns and any later
analysis built on the same fits cost seconds instead of an hour. Delete a series
file to force a refit.

Outputs (results/plots/current_power_overlay/):
    zip{det}_kline_energy_hist_{chan}.png     one channel, with the cross-check
    zip{det}_kline_energy_hist_allchan.png    every channel on one grid
    zip{det}_kline_energy_hist_{tag}.txt      per-channel summary, then every event

Usage (inside the CDMS singularity image):
    python3 scripts/kline_energy_hist.py --det 7 --chan PBS1
    python3 scripts/kline_energy_hist.py --det 7 --chan all
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

ADC_PER_AMP = 3.145728e9
TRIGGER_BIN = 16383
BASE_LO, BASE_HI = 93, 15758
INT_LO_US, INT_HI_US = 500.0, 1000.0
FILT_ORDER, FILT_CUTOFF = 5, 20000.0
FIT_LP_KHZ = 100.0
PT_FREEDOM = 3000
FIT_STRIDE = 4
NRMSE_MAX = 0.2               # drop unusable fits (normal fits sit at 0.03-0.07)
ACCEPT_MIN = 0.90             # a channel joins the summed energy only if it fits
                              # this fraction of the events (see the sum figure)
J_PER_EV = 1.602176634e-19
N_BINS = 32768
E_TRUE = 10370.0              # K-line energy, eV
ALL_CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
             "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]

RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
PROC_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
            "/Processed/Default/Default_tag/Unmerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "results", "plots", "current_power_overlay")
FIT_CACHE = os.path.join(HERE, "run", "fit_cache")
CACHE_SCHEMA = "kline_2exp_fit_v1"   # bump when the fit procedure changes

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--chan", default="PBS1",
                help='channel name, or "all" for every channel')
ap.add_argument("--formula", default="method1",
                choices=["method1", "method2", "exact"])
args = ap.parse_args()
det = args.det
c2_fac = {"method1": 2.0, "method2": -1.0, "exact": 1.0}[args.formula]


def two_exp_uA(t_ms, amp_uA, tr_ms, tf_ms, base_uA, t0_ms):
    """The template model, in units that keep every parameter O(1)."""
    dt = t_ms - t0_ms
    with np.errstate(over="ignore", invalid="ignore"):
        pulse = amp_uA * (np.exp(-np.clip(dt, 0.0, None) / tf_ms)
                          - np.exp(-np.clip(dt, 0.0, None) / tr_ms))
    return np.where(t_ms <= t0_ms, base_uA, pulse + base_uA)


series_list = sorted(os.path.basename(f)[:-4] for f in
                     glob.glob(os.path.join(RAW_CACHE, f"zip{det}_series", "*.pkl")))
print(f"{len(series_list)} cached series")

cfgf = (sorted(glob.glob(os.path.join(PROC_DIR, f"{series_list[0]}_Addison.root")))
        + sorted(glob.glob(os.path.join(PROC_DIR,
                                        f"UMN.Addison.*_{series_list[0]}_F*.root"))))
cfg = uproot.open(cfgf[0])[f"detectorConfigDir/detectorConfigZip{det}"]
_c = lambda ch, f: float(cfg[f"{ch}{f}"].array(library="np")[0])

bias = {}
for ch in ALL_CHANS:
    i0, r0 = _c(ch, "i0"), _c(ch, "r0")
    if not np.isfinite(i0) or i0 == 0 or r0 <= 0:
        continue
    rl = _c(ch, "rp") + _c(ch, "rshunt")
    bias[ch] = dict(lin=i0 * (rl - r0), quad=c2_fac * rl, dt=_c(ch, "timePerBin"))
chans = ([c for c in ALL_CHANS if c in bias] if args.chan == "all"
         else [args.chan])
print("channels:", " ".join(chans))

DT = bias[chans[0]]["dt"]
b20, a20 = butter(FILT_ORDER, FILT_CUTOFF / (0.5 / DT), btype="low")
b100, a100 = butter(4, FIT_LP_KHZ * 1e3 / (0.5 / DT), btype="low")
INT_LO = TRIGGER_BIN - int(round(INT_LO_US * 1e-6 / DT))
INT_HI = TRIGGER_BIN + int(round(INT_HI_US * 1e-6 / DT))
LO_FIT, HI_FIT = TRIGGER_BIN - PT_FREEDOM - 500, TRIGGER_BIN + 8000
X_FIT = np.arange(LO_FIT, HI_FIT, FIT_STRIDE, dtype=np.float64)
T_FIT = (X_FIT - TRIGGER_BIN) * DT * 1e3
FREE_MS = PT_FREEDOM * DT * 1e3


def fit_trace(trace):
    """Fit one trace. Returns the formula-independent record that goes into the
    fit cache, or None if the fit is unusable:
        dict(amp, t_r, t_f [A, s], base [A], t0_ms, nrmse,
             i1w, i2w [integrals of dI and dI^2 over the official window])
    """
    di = (trace - trace[BASE_LO:BASE_HI].mean()) / ADC_PER_AMP
    y_uA = filtfilt(b100, a100, di)[LO_FIT:HI_FIT:FIT_STRIDE] * 1e6
    pk = float(np.max(y_uA))
    try:
        p, _ = curve_fit(two_exp_uA, T_FIT, y_uA,
                         p0=(pk / 0.4, 0.1, 0.5, 0.0, 0.0),
                         bounds=((0.0, 1e-3, 1e-3, -abs(pk), -FREE_MS),
                                 (100 * pk + 1e-6, 10.0, 50.0, abs(pk), FREE_MS)),
                         maxfev=20000, x_scale="jac")
    except Exception:
        return None
    amp, t_r, t_f = p[0] * 1e-6, p[1] * 1e-3, p[2] * 1e-3
    if not (amp > 0 and 0 < t_r < t_f):
        return None
    model = two_exp_uA(T_FIT, *p)
    peak = model.max() - p[3]
    if peak <= 0:
        return None
    nrmse = float(np.sqrt(np.mean((y_uA - model) ** 2)) / peak)
    if nrmse > NRMSE_MAX:
        return None
    raw = filtfilt(b20, a20, di)[INT_LO:INT_HI]
    return dict(amp=amp, t_r=t_r, t_f=t_f, base=p[3] * 1e-6, t0_ms=float(p[4]),
                nrmse=nrmse, i1w=float(raw.sum() * DT),
                i2w=float((raw ** 2).sum() * DT))


def energies_from(chan, rec):
    """(E_closed, E_rawwindow) for the requested formula, from a cache record."""
    lin, quad = bias[chan]["lin"], bias[chan]["quad"]
    amp, t_r, t_f = rec["amp"], rec["t_r"], rec["t_f"]
    i1 = amp * (t_f - t_r)
    i2 = amp ** 2 * (t_f / 2 + t_r / 2 - 2 * t_f * t_r / (t_f + t_r))
    e_fit = (lin * i1 + quad * i2) / J_PER_EV
    e_raw = (lin * rec["i1w"] + quad * rec["i2w"]) / J_PER_EV
    return e_fit, e_raw


rows = {c: [] for c in chans}
n_skip = {c: 0 for c in chans}
cache_dir = os.path.join(FIT_CACHE, f"zip{det}")
os.makedirs(cache_dir, exist_ok=True)
for s in series_list:
    ckpt_path = os.path.join(cache_dir, f"{s}.pkl")
    ckpt = dict(schema=CACHE_SCHEMA, fits={})
    if os.path.exists(ckpt_path):
        loaded = pickle.load(open(ckpt_path, "rb"))
        if loaded.get("schema") == CACHE_SCHEMA:
            ckpt = loaded
    dirty = False
    raw = {}                # raw-trace pkl, loaded only if a fit is missing

    def _load_raw():
        if "cache" not in raw:
            c_ = pickle.load(open(os.path.join(
                RAW_CACHE, f"zip{det}_series", f"{s}.pkl"), "rb"))
            raw["cache"] = c_
            raw["idx"] = {c: {int(e): i for i, e in
                              enumerate(c_["event_numbers_ch"].get(c, []))}
                          for c in ALL_CHANS}
        return raw["cache"], raw["idx"]

    if "events" not in ckpt:
        c_, _ = _load_raw()
        ckpt["events"] = sorted(int(e) for e in c_["selected_event_numbers"])
        dirty = True
    events = ckpt["events"]
    for chan in chans:
        fits = ckpt["fits"].setdefault(chan, {})
        for evn in events:
            if evn not in fits:
                c_, idx_ = _load_raw()
                i = idx_[chan].get(evn)
                if i is None:
                    fits[evn] = None
                else:
                    tr = np.asarray(c_["raw_traces"][chan][i],
                                    dtype=np.float64)
                    fits[evn] = (fit_trace(tr) if tr.size == N_BINS else None)
                dirty = True
            rec = fits[evn]
            if rec is None:
                n_skip[chan] += 1
                continue
            e_fit, e_raw = energies_from(chan, rec)
            rows[chan].append((s, evn, e_fit, e_raw, rec["nrmse"],
                               rec["t_r"], rec["t_f"]))
    if dirty:
        tmp = ckpt_path + ".tmp"
        with open(tmp, "wb") as fh:
            pickle.dump(ckpt, fh, protocol=4)
        os.replace(tmp, ckpt_path)
    print(f"  {s}: " + ", ".join(f"{c} {len(rows[c])}" for c in chans)
          + ("" if dirty else "  (from fit cache)"), flush=True)


def gauss_core(v):
    """Iterative Gaussian fit to the core: mean, sigma, n used."""
    mu, sig = float(np.median(v)), float(v.std())
    m = np.ones(v.shape, bool)
    for _ in range(8):
        m = np.abs(v - mu) < 2 * sig
        if m.sum() < 10:
            break
        mu, sig = float(v[m].mean()), float(v[m].std())
    return mu, sig, int(m.sum())


stats = {}
for c in chans:
    E = np.array([r[2] for r in rows[c]])
    Er = np.array([r[3] for r in rows[c]])
    if E.size < 10:
        print(f"  {c}: only {E.size} events, skipping")
        continue
    mu, sig, nc = gauss_core(E)
    mur, sigr, _ = gauss_core(Er)
    stats[c] = dict(n=E.size, mu=mu, sig=sig, nc=nc, mur=mur, sigr=sigr,
                    mean=float(E.mean()), med=float(np.median(E)),
                    E=E, Er=Er, skip=n_skip[c])
    print(f"{c}: n {E.size:5d}  mu {mu:7.1f} eV  sigma {sig:6.1f} eV "
          f"({100 * sig / mu:5.2f}%)  raw {mur:7.1f}/{sigr:6.1f}")

BIN_W = 10.0
# each channel gets a range covering its own tail: sharing one range would squeeze
# the good channels into the left edge, because PDS2 runs out past 2 keV
for c, st in stats.items():
    hi = float(np.ceil(np.percentile(st["E"], 99.8) / 100.0) * 100.0)
    st["hi"] = max(400.0, hi)
    st["bins"] = np.arange(0, st["hi"] + BIN_W, BIN_W)
print("per-channel histogram range: "
      + ", ".join(f"{c} 0-{st['hi']:.0f} eV" for c, st in stats.items()))
os.makedirs(OUT_DIR, exist_ok=True)

# events that produced at least one usable fit; a channel's acceptance is measured
# against these, because the events where nothing fits (late pulses) are lost to
# every channel alike and say nothing about this channel
per_event = {}
for c in stats:
    for s_, evn, ef, _, _, _, _ in rows[c]:
        per_event.setdefault((s_, evn), {})[c] = ef
N_EV = max(len(per_event), 1)
for c, st in stats.items():
    st["accept"] = sum(1 for d in per_event.values() if c in d) / N_EV
    st["in_sum"] = st["accept"] >= ACCEPT_MIN


def gauss_curve(x, mu, sig, n, width):
    return n * width / (sig * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((x - mu) / sig) ** 2)


# ------------------------------------------------ one figure per single channel
if len(chans) == 1:
    c = chans[0]
    st = stats[c]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(st["Er"], bins=st["bins"], histtype="step", lw=1.4, color="#8899AA",
            label=(f"official-window raw energy: $\\mu$ = {st['mur']:.1f} eV, "
                   f"$\\sigma$ = {st['sigr']:.1f} eV "
                   f"({100 * st['sigr'] / st['mur']:.1f}%)"))
    ax.hist(st["E"], bins=st["bins"], histtype="stepfilled", lw=1.6, color="#C0392B",
            alpha=0.35, edgecolor="#C0392B",
            label=(f"fitted-pulse closed-form energy: $\\mu$ = {st['mu']:.1f} eV, "
                   f"$\\sigma$ = {st['sig']:.1f} eV "
                   f"({100 * st['sig'] / st['mu']:.1f}%)"))
    xg = np.linspace(0, st["hi"], 600)
    ax.plot(xg, gauss_curve(xg, st["mu"], st["sig"], st["nc"], BIN_W), lw=1.6,
            color="#7B241C", ls=(0, (5, 3)), label="Gaussian fit to the core")
    ax.axvline(st["mu"], color="#7B241C", lw=1.0, ls=":")
    ax.set_xlabel(f"absorbed energy per event, {c} (eV)", fontsize=12)
    ax.set_ylabel("K-line events per 10 eV", fontsize=12)
    ax.set_title(f"Z{det} {c}: energy of every K-line event "
                 f"({st['n']} events, {len(series_list)} series)\n"
                 f"two-exponential fit per event in current units, closed-form "
                 f"power integral, {args.formula} quadratic; "
                 f"NRMSE $\\leq$ {NRMSE_MAX} ({st['skip']} events dropped)",
                 fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fn = os.path.join(OUT_DIR, f"zip{det}_kline_energy_hist_{c}.png")
    fig.savefig(fn, dpi=150)
    plt.close(fig)
    print("saved", fn)

# --------------------------------------------------- grid over all the channels
if len(chans) > 1:
    ncol = 4
    nrow = int(np.ceil(len(stats) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.3 * ncol, 2.9 * nrow),
                             squeeze=False)
    tot_mu = 0.0
    for k, c in enumerate(stats):
        ax = axes[k // ncol][k % ncol]
        st = stats[c]
        tot_mu += st["mean"]
        ax.hist(st["E"], bins=st["bins"], histtype="stepfilled", color="#C0392B",
                alpha=0.35, edgecolor="#C0392B", lw=1.3)
        ax.set_xlim(0, st["hi"])
        xg = np.linspace(0, st["hi"], 600)
        ax.plot(xg, gauss_curve(xg, st["mu"], st["sig"], st["nc"], BIN_W), lw=1.4,
                color="#7B241C", ls=(0, (5, 3)))
        ax.axvline(st["mu"], color="#7B241C", lw=0.9, ls=":")
        drop = not st["in_sum"]
        ax.set_title(f"{c}   peak {st['mu']:.0f}, mean {st['mean']:.0f} eV\n"
                     f"$\\sigma$ {st['sig']:.0f} eV "
                     f"({100 * st['sig'] / st['mu']:.1f}%), n = {st['n']} "
                     f"({100 * st['accept']:.0f}% fitted)"
                     + ("\nLEFT OUT OF THE SUM" if drop else ""),
                     fontsize=9, color="#7B241C" if drop else "black")
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=8)
        if k % ncol == 0:
            ax.set_ylabel("events per 10 eV", fontsize=9)
    for k in range(len(stats), nrow * ncol):
        axes[k // ncol][k % ncol].set_axis_off()
    for k in range(len(stats)):
        axes[k // ncol][k % ncol].set_xlabel("absorbed energy per event (eV)",
                                             fontsize=9)
    fig.suptitle(
        f"Z{det}: energy of every K-line event, one panel per channel "
        f"({len(series_list)} series)\n"
        f"each entry is one event: its trace fitted with the two-exponential and "
        f"the power integrated in closed form, {args.formula} quadratic\n"
        f"the dashed curve is a Gaussian fit to the core, so its centre is the "
        f"PEAK; these distributions are right skewed, so peaks must not be added "
        f"(the plain means do add, to {tot_mu:.0f} eV = "
        f"{100 * tot_mu / E_TRUE:.1f}% of the {E_TRUE / 1e3:.2f} keV K line)",
        fontsize=11, y=0.998)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fn = os.path.join(OUT_DIR, f"zip{det}_kline_energy_hist_allchan.png")
    fig.savefig(fn, dpi=150)
    plt.close(fig)
    print("saved", fn)

# ------------------------- per-event sum over channels: the collection efficiency
sum_stats = None
if len(stats) > 1:
    n_ev = N_EV
    accept = {c: stats[c]["accept"] for c in stats}
    # Demanding every channel would cost most of the statistics and bias the
    # sample: a channel with a low fit acceptance (PDS2, whose low-frequency
    # artefact fails the NRMSE cut) then decides which events survive. The sum is
    # therefore taken over the channels that accept nearly every event, and the
    # channels left out are reported with the share of the energy they carry.
    core = [c for c in stats if stats[c]["in_sum"]]
    left_out = [c for c in stats if c not in core]
    print("\nfit acceptance per channel: "
          + ", ".join(f"{c} {100 * accept[c]:.0f}%" for c in stats))
    print(f"core channels for the sum ({len(core)}): {' '.join(core)}"
          + (f"   left out: {' '.join(left_out)}" if left_out else ""))

    keys_core = [k for k, d in per_event.items() if all(c in d for c in core)]
    Es = np.array([sum(per_event[k][c] for c in core) for k in keys_core])
    keys_all = [k for k in keys_core
                if all(c in per_event[k] for c in stats)]
    Es_all = np.array([sum(per_event[k].values()) for k in keys_all])
    mu_s, sig_s, nc_s = gauss_core(Es)
    mu_a, sig_a, nc_a = (gauss_core(Es_all) if Es_all.size > 10
                         else (np.nan, np.nan, 0))
    # bias test: the core sum restricted to the all-channel subsample against the
    # core sum over everything. If they agree, dropping a channel costs no bias.
    Es_sub = np.array([sum(per_event[k][c] for c in core) for k in keys_all])
    mu_sub = gauss_core(Es_sub)[0] if Es_sub.size > 10 else np.nan
    sum_stats = dict(n=Es.size, mu=mu_s, sig=sig_s, nc=nc_s, core=core,
                     left_out=left_out, accept=accept, n_all=Es_all.size,
                     mu_all=mu_a, sig_all=sig_a, nc_all=nc_a, mu_sub=mu_sub,
                     n_ev=n_ev)
    print(f"core sum over {len(core)} channels: {Es.size} events "
          f"({100 * Es.size / n_ev:.0f}% of all), mu {mu_s:.1f} eV "
          f"({100 * mu_s / E_TRUE:.2f}% of {E_TRUE:.0f} eV), "
          f"sigma {sig_s:.1f} eV ({100 * sig_s / mu_s:.2f}%)")
    if Es_all.size > 10:
        print(f"all {len(stats)} channels: {Es_all.size} events "
              f"({100 * Es_all.size / n_ev:.0f}%), mu {mu_a:.1f} eV "
              f"({100 * mu_a / E_TRUE:.2f}%), sigma {sig_a:.1f} eV "
              f"({100 * sig_a / mu_a:.2f}%)")
        print(f"bias check: core sum is {mu_s:.1f} eV over all events and "
              f"{mu_sub:.1f} eV on the all-channel subsample "
              f"({100 * (mu_sub / mu_s - 1):+.1f}%)")

    fig, ax = plt.subplots(figsize=(10, 6))
    sbins = np.arange(0, 8000, 100.0)
    ax.hist(Es, bins=sbins, histtype="stepfilled", color="#1F3864", alpha=0.35,
            edgecolor="#1F3864", lw=1.6,
            label=(f"sum over the {len(core)} core channels, {Es.size} events: "
                   f"$\\mu$ = {mu_s:.0f} eV, $\\sigma$ = {sig_s:.0f} eV "
                   f"({100 * sig_s / mu_s:.1f}%)"))
    if Es_all.size > 10:
        ax.hist(Es_all, bins=sbins, histtype="step", lw=1.5, color="#1B7A3D",
                label=(f"sum over all {len(stats)} channels, {Es_all.size} events "
                       f"({100 * Es_all.size / n_ev:.0f}%): "
                       f"$\\mu$ = {mu_a:.0f} eV, $\\sigma$ = {sig_a:.0f} eV "
                       f"({100 * sig_a / mu_a:.1f}%)"))
    xg = np.linspace(0, 8000, 800)
    ax.plot(xg, gauss_curve(xg, mu_s, sig_s, nc_s, 100.0), lw=1.8,
            color="#0B1E4E", ls=(0, (5, 3)), label="Gaussian fit to the core")
    ax.axvline(mu_s, color="#0B1E4E", lw=1.0, ls=":")
    ax.axvline(E_TRUE, color="#C0392B", lw=1.8,
               label=f"true event energy {E_TRUE / 1e3:.2f} keV "
                     f"(all of it, before collection losses)")
    ax.set_xlabel("summed absorbed energy per event (eV)", fontsize=12)
    ax.set_ylabel("K-line events per 100 eV", fontsize=12)
    ax.set_title(
        f"Z{det}: total energy absorbed by the TESs per K-line event\n"
        f"core sum ({len(core)} channels, fit acceptance $\\geq$ "
        f"{100 * ACCEPT_MIN:.0f}%): collection efficiency = {mu_s:.0f} / "
        f"{E_TRUE:.0f} = {100 * mu_s / E_TRUE:.1f}%, spread "
        f"{100 * sig_s / mu_s:.1f}%"
        + (f"\nleft out: {', '.join(left_out)} (fit acceptance "
           f"{', '.join(f'{100 * accept[c]:.0f}%' for c in left_out)}); "
           f"the full efficiency lies between {100 * mu_a / E_TRUE:.1f}% and "
           f"{100 * (mu_s + mu_a - mu_sub) / E_TRUE:.1f}% "
           f"(see the text file for why it is a bracket, not one number)"
           if left_out and Es_all.size > 10 else ""), fontsize=11)
    top = ax.secondary_xaxis("top", functions=(lambda e: 100 * e / E_TRUE,
                                               lambda p: p * E_TRUE / 100))
    top.set_xlabel("collection efficiency (% of 10.37 keV)", fontsize=11)
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fn = os.path.join(OUT_DIR, f"zip{det}_kline_energy_sum_hist.png")
    fig.savefig(fn, dpi=150)
    plt.close(fig)
    print("saved", fn)

# ------------------------------------------------------------------- text table
tag = "allchan" if len(chans) > 1 else chans[0]
fn = os.path.join(OUT_DIR, f"zip{det}_kline_energy_hist_{tag}.txt")
with open(fn, "w") as fh:
    fh.write(f"Z{det} K-line event energies | {args.formula} | "
             f"{len(series_list)} series | per event: 2-exp fit in current units, "
             f"closed-form power integral | NRMSE <= {NRMSE_MAX}\n\n")
    fh.write("mu is the Gaussian PEAK of that channel's distribution. The single-"
             "channel distributions are right skewed (an event close to a channel "
             "gives it a large share), so mu sits below the plain mean and the "
             "peaks must NOT be added up: only the plain means add.\n\n")
    fh.write(f"{'chan':>6} {'n':>6} {'skip':>6} {'mu[eV]':>8} {'sigma[eV]':>10} "
             f"{'sigma/mu':>9} {'mean[eV]':>9} {'median[eV]':>11} "
             f"{'mu_raw[eV]':>11} {'sigma_raw':>10} {'mean/10.37keV':>14}\n")
    for c, st in stats.items():
        fh.write(f"{c:>6} {st['n']:>6} {st['skip']:>6} {st['mu']:>8.1f} "
                 f"{st['sig']:>10.1f} {100 * st['sig'] / st['mu']:>8.2f}% "
                 f"{st['mean']:>9.1f} {st['med']:>11.1f} "
                 f"{st['mur']:>11.1f} {st['sigr']:>10.1f} "
                 f"{100 * st['mean'] / E_TRUE:>13.2f}%\n")
    if len(stats) > 1:
        tot = sum(st["mean"] for st in stats.values())
        totp = sum(st["mu"] for st in stats.values())
        fh.write(f"\nsum of the {len(stats)} channel plain means = {tot:.1f} eV = "
                 f"{100 * tot / E_TRUE:.2f}% of {E_TRUE:.0f} eV\n")
        fh.write(f"(for contrast, summing the Gaussian peaks would give "
                 f"{totp:.1f} eV, which is wrong by {100 * (1 - totp / tot):.0f}% "
                 f"for the reason above)\n")
    if sum_stats:
        ss = sum_stats
        fh.write(f"\nfit acceptance per channel: "
                 + ", ".join(f"{c} {100 * ss['accept'][c]:.0f}%" for c in stats)
                 + "\n")
        fh.write(f"\ncore sum over the {len(ss['core'])} channels with acceptance "
                 f">= {100 * ACCEPT_MIN:.0f}% ({' '.join(ss['core'])}):\n")
        fh.write(f"  {ss['n']} events ({100 * ss['n'] / ss['n_ev']:.0f}% of all), "
                 f"mu {ss['mu']:.1f} eV, sigma {ss['sig']:.1f} eV "
                 f"({100 * ss['sig'] / ss['mu']:.2f}%)\n")
        fh.write(f"  collection efficiency over the core = {ss['mu']:.1f} / "
                 f"{E_TRUE:.0f} = {100 * ss['mu'] / E_TRUE:.2f}%\n")
        if ss['left_out'] and ss['n_all'] > 10:
            pds = ss['mu_all'] - ss['mu_sub']
            best = ss['mu'] + pds
            fh.write(f"\nleft out: {' '.join(ss['left_out'])} "
                     f"(acceptance "
                     + ", ".join(f"{100 * ss['accept'][c]:.0f}%"
                                 for c in ss['left_out']) + ")\n")
            fh.write(f"  all {len(stats)} channels, {ss['n_all']} events "
                     f"({100 * ss['n_all'] / ss['n_ev']:.0f}%): mu "
                     f"{ss['mu_all']:.1f} eV, sigma {ss['sig_all']:.1f} eV "
                     f"({100 * ss['sig_all'] / ss['mu_all']:.2f}%), "
                     f"= {100 * ss['mu_all'] / E_TRUE:.2f}%\n")
            fh.write(f"  bias: on that subsample the core sum is "
                     f"{ss['mu_sub']:.1f} eV against {ss['mu']:.1f} eV over all "
                     f"events ({100 * (ss['mu_sub'] / ss['mu'] - 1):+.1f}%), so "
                     f"requiring those channels to fit selects events that put "
                     f"less energy in the core.\n")
            fh.write(f"  their share on that subsample is {ss['mu_all']:.1f} - "
                     f"{ss['mu_sub']:.1f} = {pds:.1f} eV.\n")
            fh.write("\nThe full efficiency is therefore a bracket, not a single "
                     "number:\n")
            fh.write(f"  lower  {100 * ss['mu_all'] / E_TRUE:.2f}%  "
                     f"({ss['mu_all']:.1f} eV): the all-channel sum taken as it "
                     f"stands. Reads low if that subsample is not representative, "
                     f"and it is not: its core sum is "
                     f"{100 * (ss['mu_sub'] / ss['mu'] - 1):+.1f}% off.\n")
            fh.write(f"  upper  {100 * best / E_TRUE:.2f}%  ({best:.1f} eV): the "
                     f"unbiased core sum plus that share. Reads high because a "
                     f"subsample whose core is low has its energy sitting closer "
                     f"to the left-out channel, so {pds:.1f} eV overstates the "
                     f"typical share.\n")
            fh.write(f"  => collection efficiency = "
                     f"{50 * (ss['mu_all'] + best) / E_TRUE:.0f} +- "
                     f"{50 * (best - ss['mu_all']) / E_TRUE:.0f} %, and the way to "
                     f"collapse the bracket is to make PDS2 fittable (its "
                     f"low-frequency artefact is what fails the NRMSE cut), not "
                     f"more statistics.\n")
    for c, st in stats.items():
        fh.write(f"\n--- {c} ---\n")
        fh.write(f"{'series':>16} {'event':>8} {'E_fit[eV]':>10} "
                 f"{'E_rawwin[eV]':>13} {'NRMSE':>7} {'t_r[us]':>8} "
                 f"{'t_f[us]':>8}\n")
        for s, evn, ef, er, nr, t_r, t_f in rows[c]:
            fh.write(f"{s:>16} {evn:>8} {ef:>10.1f} {er:>13.1f} {nr:>7.3f} "
                     f"{t_r * 1e6:>8.0f} {t_f * 1e6:>8.0f}\n")
print("saved", fn)
