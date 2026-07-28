#!/usr/bin/env python3
"""Build the NxM amplitude dataset for the energy-combination study.

For every K-line event of a detector (the PTOFamps window of the Prompt
processing, i.e. exactly the population cached as raw traces) that the UMN
(Addison) NxM processing produced amplitudes for,
collect the full amplitude vector

    A[event, channel, k]   k = 0..4   (PTOFnxm{CHAN}tem{k}amps)

together with PTOFamps, the per-channel 1x1 OF amplitudes, and the NxM chisq.
Events are selected directly on the processed file's PTOFamps, using the same
window recorded in the raw cache, so the huge trace caches are not touched.

Output: results/dataset_zip{N}.npz

Usage (inside the CDMS singularity image):
    python3 build_dataset.py --det 7
"""

import argparse
import glob
import os
import pickle
import sys

import numpy as np
import uproot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lp_fit_align", "scripts"))
from lp_fit_align import ALL_CHANS                       # noqa: E402

ADDISON_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
               "/Processed/Default/Default_tag/Unmerged")
PROMPT_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed"
              "/Prompt/Prompt_V07-02_C0.4.5/Submerged")
CACHE_DIR = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
CKPT_DIR = os.path.join(HERE, "..", "..", "lp_fit_align", "run", "checkpoints")
SENTINEL = -999999

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
args = parser.parse_args()
det = args.det

# the PTOFamps window that defined the K-line selection (from any cache file)
cpaths = sorted(glob.glob(os.path.join(CACHE_DIR, f"zip{det}_series", "*.pkl")))
if not cpaths:
    raise SystemExit(f"no cache for zip{det}")
with open(cpaths[0], "rb") as fh:
    ptof_lo, ptof_hi = pickle.load(fh)["ptof_range"]
print(f"zip{det}: PTOFamps window {ptof_lo:.3e} .. {ptof_hi:.3e}")

rows_A, rows_ptof, rows_of, rows_chisq, rows_ev, rows_series = [], [], [], [], [], []
rows_nrmse = []
chans = None
for path in sorted(glob.glob(os.path.join(ADDISON_DIR, "*_Addison.root"))):
    series = os.path.basename(path).replace("_Addison.root", "")
    h = uproot.open(path)
    if "rqDir" not in h or f"zip{det}" not in h["rqDir"]:
        continue
    z = h[f"rqDir/zip{det}"]
    keys = set(z.keys())
    if chans is None:
        chans = [c for c in ALL_CHANS
                 if f"PTOFnxm{c}tem0amps" in keys and f"{c}OFamps" in keys]
        print("channels with NxM amplitudes:", chans)
    # the K-line selection is defined by the PROMPT PTOFamps (same as the raw
    # cache); Addison re-processed with our templates, so its PTOFamps differ
    prompt = os.path.join(PROMPT_DIR, f"Prompt_V07-02_C0.4.5_{series}.root")
    if not os.path.exists(prompt):
        continue
    with uproot.open(prompt) as hp:
        p_ev = hp["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        p_amp = hp[f"rqDir/zip{det}/PTOFamps"].array(library="np")
    sel_ev = set(p_ev[(p_amp > ptof_lo) & (p_amp < ptof_hi)
                      & (p_amp != SENTINEL)].tolist())
    prompt_by_ev = dict(zip(p_ev.tolist(), p_amp.tolist()))

    # our own quality measure: median NRMSE over the fit_ok channels of the
    # free-pretrigger 2-exp fit (same number the NRMSE cut uses)
    med_nrmse = {}
    ck = os.path.join(CKPT_DIR, f"zip{det}", f"{series}_fit.pkl")
    cpk = os.path.join(CACHE_DIR, f"zip{det}_series", f"{series}.pkl")
    if os.path.exists(ck) and os.path.exists(cpk):
        with open(ck, "rb") as fh:
            fits = pickle.load(fh)["fits"]
        with open(cpk, "rb") as fh:
            cnums = pickle.load(fh)["event_numbers_ch"]
        per_ev = {}
        for c, lst in fits.items():
            nums = [int(e) for e in cnums.get(c, [])]
            for i, fp in enumerate(lst or []):
                if fp is not None and fp["fit_ok"] and i < len(nums):
                    per_ev.setdefault(nums[i], []).append(fp["nrmse"])
        med_nrmse = {e: float(np.median(v)) for e, v in per_ev.items()}

    evs = h["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
    ptof = np.array([prompt_by_ev.get(int(e), np.nan) for e in evs])
    nrmse = np.array([med_nrmse.get(int(e), np.nan) for e in evs])
    A = np.stack([np.stack([z[f"PTOFnxm{c}tem{k}amps"].array(library="np")
                            for k in range(5)], axis=1)
                  for c in chans], axis=1)               # (n_ev, n_chan, 5)
    of = np.stack([z[f"{c}OFamps"].array(library="np") for c in chans], axis=1)
    chisq = z["PTOFnxmchisq"].array(library="np")

    # four 2026-06-21 series were partially re-processed with overlapping
    # event ranges, so an event can appear several times (often once as a
    # sentinel row from the failed job and once with valid amplitudes).
    # Keep exactly one row per event, preferring a row with valid amplitudes.
    row_valid = (np.all(A[:, :, 0] != SENTINEL, axis=1)
                 & np.all(np.isfinite(A), axis=(1, 2)))
    choice = {}
    for i, e in enumerate(evs):
        e = int(e)
        if e not in choice or (row_valid[i] and not row_valid[choice[e]]):
            choice[e] = i
    chosen = np.zeros(len(evs), dtype=bool)
    chosen[list(choice.values())] = True
    in_sel = np.array([int(e) in sel_ev for e in evs])
    keep = chosen & in_sel & row_valid
    if not keep.any():
        continue
    rows_A.append(A[keep]); rows_ptof.append(ptof[keep])
    rows_of.append(of[keep]); rows_chisq.append(chisq[keep])
    rows_ev.append(evs[keep]); rows_nrmse.append(nrmse[keep])
    rows_series += [series] * int(keep.sum())
    print(f"  {series}: {int(keep.sum())} events")

A = np.concatenate(rows_A)
out = os.path.join(HERE, "..", "results", f"dataset_zip{det}.npz")
np.savez_compressed(out, A=A, ptof=np.concatenate(rows_ptof),
                    ofamps=np.concatenate(rows_of),
                    chisq=np.concatenate(rows_chisq),
                    events=np.concatenate(rows_ev),
                    med_nrmse=np.concatenate(rows_nrmse),
                    series=np.array(rows_series), chans=np.array(chans))
print(f"\nSaved {os.path.abspath(out)}")
print(f"  {A.shape[0]} events x {A.shape[1]} channels x 5 amplitudes "
      f"= {A.shape[1] * 5} numbers per event")
