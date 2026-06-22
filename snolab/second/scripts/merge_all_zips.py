#!/usr/bin/env python3
"""Merge per-zip ROOT template files into one single ROOT file."""

import os
import ROOT

SRC_DIR  = os.environ.get("R4_RUN_DIR",
           "/users/9/li004628/urop/snolab/runs/r4_fixed_v2_20260621/root_files")
OUT_FILE = os.path.join(
           "/users/9/li004628/urop/snolab/root_files",
           "Templates_SNOLAB_R4_AllZips_1x1.root")

ZIPS = [1, 4, 6, 7, 10, 15, 16, 18]

out = ROOT.TFile(OUT_FILE, "RECREATE")

for det in ZIPS:
    src_path = os.path.join(SRC_DIR, f"Templates_SNOLAB_R4_zip{det}_1x1.root")
    if not os.path.exists(src_path):
        print(f"  Zip{det}: file not found, skipping")
        continue

    src = ROOT.TFile.Open(src_path, "READ")
    if not src or src.IsZombie():
        print(f"  Zip{det}: could not open {src_path}")
        continue

    out.mkdir(f"zip{det}").cd()
    zip_dir = src.Get(f"zip{det}")
    if not zip_dir:
        print(f"  Zip{det}: directory 'zip{det}' not found inside ROOT file")
        src.Close()
        continue

    n = 0
    for key in zip_dir.GetListOfKeys():
        obj = key.ReadObj()
        obj.Write()
        n += 1
    print(f"  Zip{det}: {n} objects written")
    src.Close()

out.Close()
print(f"\nDone. Saved: {os.path.abspath(OUT_FILE)}")
