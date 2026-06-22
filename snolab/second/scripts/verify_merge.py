#!/usr/bin/env python3
"""Verify merged ROOT file matches individual per-zip ROOT files."""

import os
import numpy as np
import ROOT

SRC_DIR   = "/users/9/li004628/urop/snolab/runs/r4_fixed_v2_20260621/root_files"
MERGED    = "/users/9/li004628/urop/snolab/root_files/Templates_SNOLAB_R4_AllZips_1x1.root"
ZIPS      = [1, 4, 6, 7, 10, 15, 16, 18]

merged = ROOT.TFile.Open(MERGED, "READ")
all_ok = True

for det in ZIPS:
    src_path = os.path.join(SRC_DIR, f"Templates_SNOLAB_R4_zip{det}_1x1.root")
    src = ROOT.TFile.Open(src_path, "READ")

    src_dir    = src.Get(f"zip{det}")
    merged_dir = merged.Get(f"zip{det}")

    if not src_dir:
        print(f"Zip{det}: ERROR — no dir in source")
        all_ok = False
        continue
    if not merged_dir:
        print(f"Zip{det}: ERROR — no dir in merged")
        all_ok = False
        continue

    src_keys    = sorted(k.GetName() for k in src_dir.GetListOfKeys())
    merged_keys = sorted(k.GetName() for k in merged_dir.GetListOfKeys())

    if src_keys != merged_keys:
        missing = set(src_keys) - set(merged_keys)
        extra   = set(merged_keys) - set(src_keys)
        print(f"Zip{det}: KEY MISMATCH  missing={missing}  extra={extra}")
        all_ok = False
        src.Close()
        continue

    zip_ok = True
    for name in src_keys:
        h_src = src_dir.Get(name)
        h_mrg = merged_dir.Get(name)
        n = h_src.GetNbinsX()
        vals_src = np.array([h_src.GetBinContent(i+1) for i in range(n)])
        vals_mrg = np.array([h_mrg.GetBinContent(i+1) for i in range(n)])
        if not np.allclose(vals_src, vals_mrg, atol=0, rtol=0):
            diff = np.max(np.abs(vals_src - vals_mrg))
            print(f"  Zip{det}/{name}: VALUES DIFFER  max_diff={diff:.2e}")
            zip_ok = False
            all_ok = False

    status = "OK" if zip_ok else "FAIL"
    print(f"Zip{det}: [{status}]  {len(src_keys)} objects checked")
    src.Close()

merged.Close()
print("\n" + ("ALL MATCH" if all_ok else "DIFFERENCES FOUND"))
