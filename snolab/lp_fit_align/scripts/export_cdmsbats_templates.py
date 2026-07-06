#!/usr/bin/env python3
"""Export the 2-exp fit templates in the cdmsbats PulseTemplates format.

Format (matches e.g. Templates_1x1_Z1Z3_0V_R37.root):
  top level      : one TDirectory per zip, named "zip{N}"
  inside the dir : {chan}      — 1x1 template (peak-normalized, 32768 bins)
                   {chan}nxm0  — same curve under the NxM mean-template name
                   PT, PS1, PS2 — peak-normalized average of the available
                                  channel templates (all / side 1 / side 2)

Template content = NRMSE-weighted mean of all fit_ok fitted 2-exp curves
(common pretrigger 16050, w = 1/max(NRMSE,0.01)^2), peak-normalized — the
same curve stored in results/root_files/ and drawn orange in aligned_overlay.

Usage:
    python3 export_cdmsbats_templates.py --det 7 --date 20260706 \
        [--out-dir /projects/.../PulseTemplates/files]
"""

import argparse
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (ALL_CHANS, CKPT_DIR, RISE_REF_IDX, TRACELENGTH,
                          nrmse_weighted_fit_mean)

import ROOT
from ROOT import TFile, TH1D

OUT_DIR_DEFAULT = ("/projects/standard/yanliusp/shared/software"
                   "/cdmsbats_config/PulseTemplates/files")

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--date", required=True, help="YYYYMMDD used in the filename")
parser.add_argument("--out-dir", default=OUT_DIR_DEFAULT)
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

templates = {}
for c in ALL_CHANS:
    if not fits_all[c]:
        print(f"  {c}: no fits, skipped")
        continue
    t = nrmse_weighted_fit_mean(fits_all[c], 0, TRACELENGTH)
    peak = float(np.max(t))
    if peak > 0:
        t = t / peak
    templates[c] = t
    print(f"  {c}: template from {len(fits_all[c])} fits")


def peak_normalized_average(chans):
    arrs = [templates[c] for c in chans if c in templates]
    if not arrs:
        return None
    avg = np.mean(arrs, axis=0)
    peak = float(np.max(avg))
    return avg / peak if peak > 0 else avg


def write_hist(name, title, arr):
    hist = TH1D(name, title, TRACELENGTH, -0.5, TRACELENGTH - 0.5)
    for j, v in enumerate(arr):
        hist.SetBinContent(j + 1, float(v))
    hist.Write()


out_path = os.path.join(args.out_dir,
                        f"SNOLAB_R4_{args.date}_ZhihengLi_zip{det}.root")
tf = TFile(out_path, "RECREATE")
zdir = tf.mkdir(f"zip{det}")
zdir.cd()
base_title = (f"Zip{det} {{}} 2-exp fit template (NRMSE-weighted mean of "
              f"fit_ok fits, pretrigger {RISE_REF_IDX}, peak-normalized)")
for c, t in templates.items():
    write_hist(c, base_title.format(c), t)              # 1x1 template
    write_hist(c + "nxm0", base_title.format(c), t)     # NxM mean-template name
for name, chans in [("PT", ALL_CHANS),
                    ("PS1", [c for c in ALL_CHANS if c.endswith("1")]),
                    ("PS2", [c for c in ALL_CHANS if c.endswith("2")])]:
    avg = peak_normalized_average(chans)
    if avg is not None:
        write_hist(name, f"Zip{det} {name} = peak-normalized average of "
                   "available channel templates", avg)
tf.Close()
print(f"Saved: {out_path}")
