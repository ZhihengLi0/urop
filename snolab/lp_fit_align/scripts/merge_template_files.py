#!/usr/bin/env python3
"""Merge the per-detector cdmsbats template files into one all-detector file.

Each source file SNOLAB_R4_{date}_ZhihengLi[_pca]_zip{N}.root holds one
zip{N} TDirectory; the merged file holds all 13 zip{N} directories with the
histograms cloned unchanged.

Usage (inside the CDMS singularity image):
    python3 merge_template_files.py --date 20260706 --out SNOLAB_R4_20260727_ZhihengLi_2exp_all.root
    python3 merge_template_files.py --date 20260707 --out SNOLAB_R4_20260727_ZhihengLi_all.root
"""

import argparse
import os

import ROOT
from ROOT import TFile

FILES_DIR = ("/projects/standard/yanliusp/shared/software"
             "/cdmsbats_config/PulseTemplates/files")
ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="source set date, e.g. 20260707")
parser.add_argument("--infix", default="", help="e.g. 'pca_' for the pca copies")
parser.add_argument("--out", required=True)
args = parser.parse_args()

out_path = os.path.join(FILES_DIR, args.out)
fout = TFile(out_path, "RECREATE")
total = 0
for z in ZIPS:
    src_path = os.path.join(
        FILES_DIR, f"SNOLAB_R4_{args.date}_ZhihengLi_{args.infix}zip{z}.root")
    fsrc = TFile(src_path)
    d = fsrc.Get(f"zip{z}")
    if not d:
        raise SystemExit(f"no zip{z} dir in {src_path}")
    odir = fout.mkdir(f"zip{z}")
    n = 0
    for key in d.GetListOfKeys():
        obj = key.ReadObj()
        odir.cd()
        obj.Write(key.GetName())
        n += 1
    fsrc.Close()
    total += n
    print(f"  zip{z}: {n} objects")
fout.Close()
print(f"Saved {out_path}  ({total} objects, {len(ZIPS)} detectors)")
