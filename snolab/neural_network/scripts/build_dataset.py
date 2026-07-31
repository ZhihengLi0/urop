#!/usr/bin/env python3
"""Build the training set: the 55 NxM amplitudes of an event against the energy
that event actually absorbed.

Inputs per event
    the NxM optimal-filter amplitudes of the UMN (Addison) processing of our
    delivered templates, PTOFnxm{chan}tem{k}amps, 11 channels x 5 templates on
    Z7. Sentinel rows are dropped and events that appear in more than one
    re-processed subfile are kept once, preferring the row with valid amplitudes.

Target per event
    the absorbed energy from the physics: each channel's trace is fitted with the
    two-exponential and its power integrated in closed form (method 1), and the
    channel energies are summed. The fits are read from the cache built by
    differentialequations/scripts/kline_energy_hist.py, so nothing is refitted
    here. The target is the energy of that individual event, not the nominal
    10.37 keV of the line.

    Channels whose fit acceptance is below ACCEPT_MIN are left out of the sum
    (on Z7 that is PDS2, which fits 42% of events because of its low-frequency
    artefact); requiring every channel would keep 41% of the events and bias the
    sample, since the events where PDS2 fits put 4.8% less energy in the others.
    Their amplitudes stay in the inputs: an amplitude is a measurement whether or
    not our fit of that trace converged.

Output: results/dataset_zip{det}.npz with X (n, 55), y (n,), and the metadata
needed to trace any row back to its event.

Usage (inside the CDMS singularity image):
    python3 scripts/build_dataset.py --det 7
"""
import argparse
import glob
import os
import pickle

import numpy as np
import uproot

SENTINEL = -999999
J_PER_EV = 1.602176634e-19
ACCEPT_MIN = 0.90            # a channel joins the target sum above this
C2 = {"method1": 2.0, "method2": -1.0, "exact": 1.0}
ALL_CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
             "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]

ADDISON_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
               "/Processed/Default/Default_tag/Unmerged")
PROMPT_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed"
              "/Prompt/Prompt_V07-02_C0.4.5/Submerged")
RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIT_CACHE = os.path.join(HERE, "..", "differentialequations", "run", "fit_cache")
OUT_DIR = os.path.join(HERE, "results")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--formula", default="method1", choices=sorted(C2))
args = ap.parse_args()
det = args.det
c2_fac = C2[args.formula]

# ------------------------------------------------- bias point, per channel
cfg_files = sorted(glob.glob(os.path.join(ADDISON_DIR, "*_Addison.root")))
cfg = uproot.open(cfg_files[0])[f"detectorConfigDir/detectorConfigZip{det}"]
_c = lambda ch, f: float(cfg[f"{ch}{f}"].array(library="np")[0])
bias = {}
for ch in ALL_CHANS:
    i0, r0 = _c(ch, "i0"), _c(ch, "r0")
    if not np.isfinite(i0) or i0 == 0 or r0 <= 0:
        continue
    rl = _c(ch, "rp") + _c(ch, "rshunt")
    bias[ch] = dict(lin=i0 * (rl - r0), quad=c2_fac * rl)

# ------------------------------------------------- target: energy per event
fits = {}                    # (series, event) -> {chan: energy_eV}
t0s = {}                     # (series, event) -> [fitted pulse start, ms]
for path in sorted(glob.glob(os.path.join(FIT_CACHE, f"zip{det}", "*.pkl"))):
    s = os.path.basename(path)[:-4]
    ck = pickle.load(open(path, "rb"))
    for ch, per_ev in ck["fits"].items():
        if ch not in bias:
            continue
        lin, quad = bias[ch]["lin"], bias[ch]["quad"]
        for evn, rec in per_ev.items():
            if rec is None:
                continue
            A_, tr_, tf_ = rec["amp"], rec["t_r"], rec["t_f"]
            i1 = A_ * (tf_ - tr_)
            i2 = A_ * A_ * (tf_ / 2 + tr_ / 2 - 2 * tf_ * tr_ / (tf_ + tr_))
            key = (s, int(evn))
            fits.setdefault(key, {})[ch] = (lin * i1 + quad * i2) / J_PER_EV
            t0s.setdefault(key, []).append(rec["t0_ms"])
n_ev_fit = len(fits)
accept = {ch: sum(1 for d in fits.values() if ch in d) / n_ev_fit
          for ch in bias}
core = sorted((ch for ch, a in accept.items() if a >= ACCEPT_MIN),
              key=ALL_CHANS.index)
left_out = sorted((ch for ch in accept if ch not in core), key=ALL_CHANS.index)
print(f"fit cache: {n_ev_fit} events")
print("  acceptance: " + ", ".join(f"{c} {100 * accept[c]:.0f}%"
                                   for c in sorted(accept, key=ALL_CHANS.index)))
print(f"  target sums {len(core)} channels: {' '.join(core)}"
      + (f"   left out: {' '.join(left_out)}" if left_out else ""))

# ------------------------------------------------- inputs: the NxM amplitudes
with open(os.path.join(RAW_CACHE, f"zip{det}_series",
                       sorted(os.listdir(os.path.join(RAW_CACHE,
                                                      f"zip{det}_series")))[0]),
          "rb") as fh:
    ptof_lo, ptof_hi = pickle.load(fh)["ptof_range"]
print(f"K-line window from the raw cache: {ptof_lo:.3e} .. {ptof_hi:.3e} A")

rows_X, rows_y, rows_ev, rows_se, rows_t0, rows_nch = [], [], [], [], [], []
chans = None
for path in sorted(glob.glob(os.path.join(ADDISON_DIR, "*_Addison.root"))):
    series = os.path.basename(path).replace("_Addison.root", "")
    h = uproot.open(path)
    if f"rqDir/zip{det}" not in h:
        continue
    z = h[f"rqDir/zip{det}"]
    keys = set(z.keys())
    if chans is None:
        chans = [c for c in ALL_CHANS
                 if f"PTOFnxm{c}tem0amps" in keys and f"{c}OFamps" in keys]
        print(f"channels with NxM amplitudes: {len(chans)}  {' '.join(chans)}")
    evs = h["rqDir/eventTree/EventNumber"].array(library="np").astype(int)

    # the K-line selection is the Prompt PTOFamps, as in the template pipeline
    pr = os.path.join(PROMPT_DIR, f"Prompt_V07-02_C0.4.5_{series}.root")
    if not os.path.exists(pr):
        continue
    ph = uproot.open(pr)
    p_ev = ph["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
    p_amp = ph[f"rqDir/zip{det}"]["PTOFamps"].array(library="np")
    sel = set(p_ev[(p_amp >= ptof_lo) & (p_amp <= ptof_hi)
                   & (p_amp != SENTINEL)].tolist())
    if not sel:
        continue

    A = np.stack([np.stack([z[f"PTOFnxm{c}tem{k}amps"].array(library="np")
                            for k in range(5)], axis=1) for c in chans], axis=1)
    # one row per event: an event can appear in several re-processed subfiles,
    # usually once as a sentinel row and once with valid amplitudes
    row_valid = np.all(A[:, :, 0] != SENTINEL, axis=1) & np.all(np.isfinite(A),
                                                                axis=(1, 2))
    choice = {}
    for i, e in enumerate(evs):
        e = int(e)
        if e not in choice or (row_valid[i] and not row_valid[choice[e]]):
            choice[e] = i
    for e, i in choice.items():
        if e not in sel or not row_valid[i]:
            continue
        per_ch = fits.get((series, e))
        if per_ch is None or any(c not in per_ch for c in core):
            continue
        rows_X.append(A[i].ravel())
        rows_y.append(sum(per_ch[c] for c in core))
        rows_ev.append(e)
        rows_se.append(series)
        rows_nch.append(len(per_ch))
        rows_t0.append(float(np.median(t0s[(series, e)])))
    print(f"  {series}: {len(rows_X)} events so far", flush=True)

X = np.asarray(rows_X, dtype=np.float64)
y = np.asarray(rows_y, dtype=np.float64)
print(f"\ndataset: X {X.shape}, y {y.shape}")
t0 = np.asarray(rows_t0)
print(f"  fitted pulse start t0: median {np.median(t0):+.3f} ms, "
      f"|t0| > 0.5 ms on {(np.abs(t0) > 0.5).sum()} events, "
      f"> 1 ms on {(np.abs(t0) > 1.0).sum()}")
print(f"  target energy: mean {y.mean():.1f} eV, median {np.median(y):.1f} eV, "
      f"std {y.std():.1f} eV ({100 * y.std() / y.mean():.2f}%), "
      f"range {y.min():.1f} .. {y.max():.1f} eV")

os.makedirs(OUT_DIR, exist_ok=True)
fn = os.path.join(OUT_DIR, f"dataset_zip{det}.npz")
np.savez_compressed(fn, X=X, y=y, events=np.asarray(rows_ev),
                    series=np.asarray(rows_se), n_chan_fitted=np.asarray(rows_nch),
                    t0_ms=np.asarray(rows_t0),
                    chans=np.asarray(chans), core=np.asarray(core),
                    formula=args.formula, ptof_range=np.array([ptof_lo, ptof_hi]))
print("saved", fn)
