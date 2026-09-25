#!/usr/bin/env python3
"""Temporary solution for the Z7 PDS2 low-frequency artifact: replace the
PDS2 template with a copy of the PDS1 template (same detector side, clean
channel). Applied to the Z7 deliverable ROOT files:

  deliverables/1x1/root_files/Templates_SNOLAB_R4_zip7_2expfit_weighted.root
  deliverables/nxm/root_files/Templates_SNOLAB_R4_zip7_nxm_pca.root

The cdmsbats deployment files are regenerated downstream (normalize / direct
rewrite) so their PDS2 entries and the PT/PS1/PS2 sums pick up the
substitution. Histogram titles record the substitution.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import TRACELENGTH
import ROOT
from ROOT import TFile, TH1D

DELIV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables"))

def read_all(path):
    f = TFile(path); out = {}
    for k in f.GetListOfKeys():
        h = k.ReadObj()
        out[k.GetName()] = (h.GetTitle(),
                            np.array([h.GetBinContent(i+1) for i in range(h.GetNbinsX())]))
    f.Close(); return out

def write_all(path, hists):
    f = TFile(path, "RECREATE")
    for name, (title, arr) in hists.items():
        h = TH1D(name, title, len(arr), -0.5, len(arr) - 0.5)
        for j, v in enumerate(arr):
            h.SetBinContent(j+1, float(v))
        h.Write()
    f.Close()

SUB = " [PDS2 replaced by PDS1 template: PDS2 low-frequency artifact, temporary solution]"

p1 = os.path.join(DELIV, "1x1", "root_files", "Templates_SNOLAB_R4_zip7_2expfit_weighted.root")
h = read_all(p1)
h["t2exp_zip7_PDS2"] = (h["t2exp_zip7_PDS1"][0].replace("PDS1", "PDS2") + SUB,
                        h["t2exp_zip7_PDS1"][1].copy())
write_all(p1, h)
print("1x1 root: PDS2 <- PDS1 done")

p2 = os.path.join(DELIV, "nxm", "root_files", "Templates_SNOLAB_R4_zip7_nxm_pca.root")
h = read_all(p2)
for k in range(5):
    src, dst = f"nxm{k}_zip7_PDS1", f"nxm{k}_zip7_PDS2"
    h[dst] = (h[src][0].replace("PDS1", "PDS2") + SUB, h[src][1].copy())
write_all(p2, h)
print("nxm root: PDS2 <- PDS1 (nxm0-4) done")
