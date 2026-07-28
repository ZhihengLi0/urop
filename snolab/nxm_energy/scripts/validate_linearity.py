#!/usr/bin/env python3
"""Linearity check for the min-variance energy combination.

The weights are trained on one mono-energetic line, so they could in
principle be a degenerate projection that maps everything onto 10.37 keV.
This script applies them to CONTROL events selected in other PTOFamps bands
(i.e. other energies) and asks whether the reconstructed energy tracks
PTOFamps proportionally.

Output: results/plots/zip{N}_linearity.png

Usage: python3 validate_linearity.py --det 7
"""

import argparse
import glob
import os
import sys

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
ADDISON_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
               "/Processed/Default/Default_tag/Unmerged")
PROMPT_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed"
              "/Prompt/Prompt_V07-02_C0.4.5/Submerged")
SENTINEL = -999999
E_LINE = 10.37

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--n-series", type=int, default=8)
args = parser.parse_args()
det = args.det

wd = np.load(os.path.join(RES, f"weights_zip{det}.npz"), allow_pickle=True)
w, chans, scale = wd["w"], list(wd["chans"]), float(wd["scale"])

rows_X, rows_p = [], []
for path in sorted(glob.glob(os.path.join(ADDISON_DIR, "*_Addison.root")))[:args.n_series]:
    series = os.path.basename(path).replace("_Addison.root", "")
    prompt = os.path.join(PROMPT_DIR, f"Prompt_V07-02_C0.4.5_{series}.root")
    if not os.path.exists(prompt):
        continue
    h = uproot.open(path)
    if "rqDir" not in h or f"zip{det}" not in h["rqDir"]:
        continue
    z = h[f"rqDir/zip{det}"]
    with uproot.open(prompt) as hp:
        p_ev = hp["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        p_amp = hp[f"rqDir/zip{det}/PTOFamps"].array(library="np")
    pmap = dict(zip(p_ev.tolist(), p_amp.tolist()))
    evs = h["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
    ptof = np.array([pmap.get(int(e), np.nan) for e in evs])
    A = np.stack([np.stack([z[f"PTOFnxm{c}tem{k}amps"].array(library="np")
                            for k in range(5)], axis=1) for c in chans], axis=1)
    keep = (np.isfinite(ptof) & (ptof > 5e-7) & (ptof < 3e-5)
            & np.all(A[:, :, 0] != SENTINEL, axis=1)
            & np.all(np.isfinite(A), axis=(1, 2)))
    if keep.any():
        rows_X.append(A[keep].reshape(keep.sum(), -1)); rows_p.append(ptof[keep])
    print(f"  {series}: {int(keep.sum())} control events")

X, ptof = np.concatenate(rows_X), np.concatenate(rows_p)
E = (X @ w) / scale
print(f"\n{len(E)} control events over PTOFamps {ptof.min():.2e}..{ptof.max():.2e}")

# median reconstructed energy in PTOFamps bands
edges = np.geomspace(max(ptof.min(), 5e-7), ptof.max(), 12)
cx, cy, cn = [], [], []
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (ptof >= lo) & (ptof < hi)
    if m.sum() >= 20:
        cx.append(float(np.median(ptof[m]))); cy.append(float(np.median(E[m])))
        cn.append(int(m.sum()))
cx, cy = np.array(cx), np.array(cy)
kline = E_LINE / (2.0e-6)                       # keV per A, from the line
print(f"{'PTOFamps':>12} {'median E (keV)':>15} {'E / (PTOF*k)':>14} {'n':>6}")
for x, y, n in zip(cx, cy, cn):
    print(f"{x:>12.3e} {y:>15.2f} {y/(x*kline):>14.2f} {n:>6d}")

fig, ax = plt.subplots(figsize=(9.5, 5.0))
ax.plot(ptof, E, ".", ms=1.5, alpha=0.25, color="steelblue", label="events")
ax.plot(cx, cy, "o-", color="crimson", label="median per PTOFamps band")
xs = np.geomspace(cx.min(), cx.max(), 50)
ax.plot(xs, xs * kline, "--", color="black", lw=1.0,
        label="proportional to PTOFamps (fixed at the K-line)")
ax.axhline(E_LINE, color="gray", lw=0.8, ls=":")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("PTOFamps (A)"); ax.set_ylabel("energy from the NxM combination (keV)")
ax.set_title(f"Zip{det}: do the K-line weights extrapolate to other energies?",
             fontsize=12)
ax.legend(fontsize=9); ax.grid(alpha=0.3, which="both")
fig.tight_layout()
out = os.path.join(RES, "plots", f"zip{det}_linearity.png")
fig.savefig(out, dpi=150, bbox_inches="tight")
print("saved", out)
