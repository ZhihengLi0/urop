#!/usr/bin/env python3
"""Energy of every K-line event on one channel (PBS1), as a histogram.

For each cached K-line event of Z7, the PBS1 trace is fitted with the
two-exponential model directly in current units, and the absorbed energy is the
closed-form integral of the power pulse (see plot_fitted_current_power.py):

    dI(t) = A[exp(-(t-t0)/tau_f) - exp(-(t-t0)/tau_r)]
    E = I0(R_L-R0)*A(tau_f-tau_r)
        + c2*R_L*A^2[tau_f/2 + tau_r/2 - 2 tau_f tau_r/(tau_f+tau_r)]

The histogram of E over all events is the deliverable (x axis = energy). The
official-window raw-trace energy is drawn alongside as a cross-check, and a
Gaussian is fitted to the peak of each distribution.

Outputs (results/plots/current_power_overlay/):
    zip{det}_kline_energy_hist_{chan}.png
    zip{det}_kline_energy_hist_{chan}.txt

Usage (inside the CDMS singularity image):
    python3 scripts/pbs1_kline_energy_hist.py --det 7 --chan PBS1
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
NRMSE_MAX = 0.2               # drop unusable fits (normal fits sit at 0.03-0.07)
J_PER_EV = 1.602176634e-19
N_BINS = 32768

RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
PROC_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
            "/Processed/Default/Default_tag/Unmerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "results", "plots", "current_power_overlay")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--chan", default="PBS1")
ap.add_argument("--formula", default="method1",
                choices=["method1", "method2", "exact"])
args = ap.parse_args()
det, chan = args.det, args.chan
c2_fac = {"method1": 2.0, "method2": -1.0, "exact": 1.0}[args.formula]


def two_exp_uA(t_ms, amp_uA, tr_ms, tf_ms, base_uA, t0_ms):
    dt = t_ms - t0_ms
    with np.errstate(over="ignore", invalid="ignore"):
        pulse = amp_uA * (np.exp(-np.clip(dt, 0.0, None) / tf_ms)
                          - np.exp(-np.clip(dt, 0.0, None) / tr_ms))
    return np.where(t_ms <= t0_ms, base_uA, pulse + base_uA)


series_list = sorted(os.path.basename(f)[:-4] for f in
                     glob.glob(os.path.join(RAW_CACHE, f"zip{det}_series", "*.pkl")))
print(f"{len(series_list)} cached series")

# bias point from the first series that has this detector (constants verified
# stable across series to <=0.2%)
cfgf = (sorted(glob.glob(os.path.join(PROC_DIR, f"{series_list[0]}_Addison.root")))
        + sorted(glob.glob(os.path.join(PROC_DIR,
                                        f"UMN.Addison.*_{series_list[0]}_F*.root"))))
cfg = uproot.open(cfgf[0])[f"detectorConfigDir/detectorConfigZip{det}"]
_c = lambda f: float(cfg[f"{chan}{f}"].array(library="np")[0])
i0, r0, rl, DT = _c("i0"), _c("r0"), _c("rp") + _c("rshunt"), _c("timePerBin")
LIN, QUAD = i0 * (rl - r0), c2_fac * rl
print(f"{chan}: I0 {i0 * 1e6:.3f} uA, R0 {r0 * 1e3:.3f} mOhm, RL {rl * 1e3:.3f} mOhm")

b20, a20 = butter(FILT_ORDER, FILT_CUTOFF / (0.5 / DT), btype="low")
b100, a100 = butter(4, FIT_LP_KHZ * 1e3 / (0.5 / DT), btype="low")
INT_LO = TRIGGER_BIN - int(round(INT_LO_US * 1e-6 / DT))
INT_HI = TRIGGER_BIN + int(round(INT_HI_US * 1e-6 / DT))
lo_fit, hi_fit = TRIGGER_BIN - PT_FREEDOM - 500, TRIGGER_BIN + 8000
x_fit = np.arange(lo_fit, hi_fit, 4, dtype=np.float64)
t_ms_fit = (x_fit - TRIGGER_BIN) * DT * 1e3
free_ms = PT_FREEDOM * DT * 1e3

rows = []          # (series, event, E_fit, E_rawwin, nrmse, t_r, t_f)
n_skip = 0
for s in series_list:
    cache = pickle.load(open(os.path.join(RAW_CACHE, f"zip{det}_series",
                                          f"{s}.pkl"), "rb"))
    idx = {int(e): i for i, e in
           enumerate(cache["event_numbers_ch"].get(chan, []))}
    for evn in sorted(int(e) for e in cache["selected_event_numbers"]):
        i = idx.get(evn)
        if i is None:
            n_skip += 1
            continue
        tr = np.asarray(cache["raw_traces"][chan][i], dtype=np.float64)
        if tr.size != N_BINS:
            n_skip += 1
            continue
        di = (tr - tr[BASE_LO:BASE_HI].mean()) / ADC_PER_AMP
        y_uA = filtfilt(b100, a100, di)[lo_fit:hi_fit:4] * 1e6
        pk = float(np.max(y_uA))
        try:
            p, _ = curve_fit(two_exp_uA, t_ms_fit, y_uA,
                             p0=(pk / 0.4, 0.1, 0.5, 0.0, 0.0),
                             bounds=((0.0, 1e-3, 1e-3, -abs(pk), -free_ms),
                                     (100 * pk + 1e-6, 10.0, 50.0, abs(pk),
                                      free_ms)),
                             maxfev=20000, x_scale="jac")
        except Exception:
            n_skip += 1
            continue
        amp, t_r, t_f = p[0] * 1e-6, p[1] * 1e-3, p[2] * 1e-3
        if not (amp > 0 and 0 < t_r < t_f):
            n_skip += 1
            continue
        model = two_exp_uA(t_ms_fit, *p)
        peak = model.max() - p[3]
        nrmse = float(np.sqrt(np.mean((y_uA - model) ** 2)) / peak)
        if nrmse > NRMSE_MAX:
            n_skip += 1
            continue
        i1 = amp * (t_f - t_r)
        i2 = amp ** 2 * (t_f / 2 + t_r / 2 - 2 * t_f * t_r / (t_f + t_r))
        e_fit = (LIN * i1 + QUAD * i2) / J_PER_EV
        raw = filtfilt(b20, a20, di)
        e_raw = ((LIN * raw + QUAD * raw ** 2)[INT_LO:INT_HI].sum()
                 * DT / J_PER_EV)
        rows.append((s, evn, e_fit, e_raw, nrmse, t_r, t_f))
    print(f"  {s}: cumulative {len(rows)} events")

E = np.array([r[2] for r in rows])
Eraw = np.array([r[3] for r in rows])
print(f"\n{len(rows)} events fitted, {n_skip} skipped")


def gauss_fit(v):
    """Iterative Gaussian fit to the core of the distribution."""
    mu, sig = np.median(v), v.std()
    for _ in range(8):
        m = np.abs(v - mu) < 2 * sig
        mu, sig = v[m].mean(), v[m].std()
    return mu, sig, int(m.sum())


mu_f, sig_f, nc_f = gauss_fit(E)
mu_r, sig_r, nc_r = gauss_fit(Eraw)

fig, ax = plt.subplots(figsize=(10, 6))
bins = np.arange(0, 600, 10.0)
ax.hist(Eraw, bins=bins, histtype="step", lw=1.4, color="#8899AA",
        label=(f"official-window raw energy: $\\mu$ = {mu_r:.1f} eV, "
               f"$\\sigma$ = {sig_r:.1f} eV ({100 * sig_r / mu_r:.1f}%)"))
ax.hist(E, bins=bins, histtype="stepfilled", lw=1.6, color="#C0392B",
        alpha=0.35, edgecolor="#C0392B",
        label=(f"fitted-pulse closed-form energy: $\\mu$ = {mu_f:.1f} eV, "
               f"$\\sigma$ = {sig_f:.1f} eV ({100 * sig_f / mu_f:.1f}%)"))
xg = np.linspace(0, 600, 600)
core = np.abs(E - mu_f) < 2 * sig_f
ax.plot(xg, core.sum() * 10.0 / (sig_f * np.sqrt(2 * np.pi))
        * np.exp(-0.5 * ((xg - mu_f) / sig_f) ** 2) * (nc_f / core.sum()),
        lw=1.6, color="#7B241C", ls=(0, (5, 3)), label="Gaussian fit to the core")
ax.axvline(mu_f, color="#7B241C", lw=1.0, ls=":")
ax.set_xlabel("absorbed energy per event, %s (eV)" % chan, fontsize=12)
ax.set_ylabel("K-line events per 10 eV", fontsize=12)
ax.set_title(
    f"Z{det} {chan}: energy of every K-line event "
    f"({len(rows)} events, {len(series_list)} series)\n"
    f"two-exponential fit per event in current units, closed-form power "
    f"integral, {args.formula} quadratic; NRMSE $\\leq$ {NRMSE_MAX} "
    f"({n_skip} events dropped)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(alpha=0.25)
fig.tight_layout()
os.makedirs(OUT_DIR, exist_ok=True)
f1 = os.path.join(OUT_DIR, f"zip{det}_kline_energy_hist_{chan}.png")
fig.savefig(f1, dpi=150)
plt.close(fig)
print("saved", f1)

f2 = os.path.join(OUT_DIR, f"zip{det}_kline_energy_hist_{chan}.txt")
with open(f2, "w") as fh:
    fh.write(f"Z{det} {chan} K-line event energies | {args.formula} | "
             f"{len(rows)} events over {len(series_list)} series, "
             f"{n_skip} skipped (missing trace or NRMSE > {NRMSE_MAX})\n")
    fh.write(f"fitted-pulse closed form: mean {mu_f:.2f} eV, sigma {sig_f:.2f} eV "
             f"({100 * sig_f / mu_f:.2f}%), median {np.median(E):.2f} eV\n")
    fh.write(f"official-window raw:      mean {mu_r:.2f} eV, sigma {sig_r:.2f} eV "
             f"({100 * sig_r / mu_r:.2f}%), median {np.median(Eraw):.2f} eV\n\n")
    fh.write(f"{'series':>16} {'event':>8} {'E_fit[eV]':>10} {'E_rawwin[eV]':>13} "
             f"{'NRMSE':>7} {'t_r[us]':>8} {'t_f[us]':>8}\n")
    for s, evn, ef, er, nr, t_r, t_f in rows:
        fh.write(f"{s:>16} {evn:>8} {ef:>10.1f} {er:>13.1f} {nr:>7.3f} "
                 f"{t_r * 1e6:>8.0f} {t_f * 1e6:>8.0f}\n")
print("saved", f2)
