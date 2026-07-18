#!/usr/bin/env python3
"""Write the 2-exp fit templates to ROOT.

For every channel of a zip, the template is the NRMSE-weighted mean of all
fit_ok fitted 2-exp curves (each curve evaluated at the common pretrigger
16050, peak-normalized; weight w = 1/max(NRMSE, 0.01)^2 — the same orange
curve shown in the aligned_overlay figures), finally re-normalized to peak 1
and stored as a TH1D over the full 32768-sample trace window.

Output: deliverables/1x1/root_files/Templates_SNOLAB_R4_zip{N}_2expfit_weighted.root
        one TH1D per channel, named t2exp_zip{N}_{chan}

Reads only the fit checkpoints; requires PyROOT (run inside the CDMS
singularity image).

Usage:
    python3 write_2exp_templates_root.py --det 7
"""

import argparse
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (ALL_CHANS, BASE_DIR, CKPT_DIR, RISE_REF_IDX,
                          TRACELENGTH, nrmse_weighted_fit_mean)

import ROOT
from ROOT import TFile, TH1D

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
args = parser.parse_args()
det = args.det

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
ckpts = sorted(f for f in os.listdir(ckpt_dir) if f.endswith("_fit.pkl"))
if not ckpts:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

fits_all = {c: [] for c in ALL_CHANS}
for fname in ckpts:
    with open(os.path.join(ckpt_dir, fname), "rb") as fh:
        fits = pickle.load(fh)["fits"]
    for c in ALL_CHANS:
        fits_all[c] += [fp for fp in (fits.get(c) or [])
                        if fp is not None and fp["fit_ok"]]

DELIV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables"))
out_dir = os.path.join(DELIV, "1x1", "root_files")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(
    out_dir, f"Templates_SNOLAB_R4_zip{det}_2expfit_weighted.root")

tf = TFile(out_path, "RECREATE")
n_written = 0
for c in ALL_CHANS:
    fits = fits_all[c]
    if not fits:
        print(f"  {c}: no fits, skipped")
        continue
    template = nrmse_weighted_fit_mean(fits, 0, TRACELENGTH)
    peak = float(np.max(template))
    if peak > 0:
        template = template / peak          # final normalization: peak = 1
    hist = TH1D(f"t2exp_zip{det}_{c}",
                f"Zip{det} {c} 2-exp fit template "
                f"(NRMSE-weighted mean of {len(fits)} fit_ok fits, "
                f"pretrigger {RISE_REF_IDX}, peak-normalized)",
                TRACELENGTH, -0.5, TRACELENGTH - 0.5)
    for j, v in enumerate(template):
        hist.SetBinContent(j + 1, float(v))
    hist.Write()
    n_written += 1
    print(f"  {c}: template from {len(fits)} fits")
tf.Close()
print(f"Saved ROOT: {out_path}  ({n_written} channels)")
