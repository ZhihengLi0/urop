#!/usr/bin/env python3
"""Two NxM template figures for the NxM results slide (Z7 PBS1), zoomed to
the pulse — the late tail carries no information:

  figures/nxm_plain_zip7_PBS1.png    — nxm0 (plain mean, as delivered) + nxm1-4
  figures/nxm_weighted_zip7_PBS1.png — NRMSE-weighted mean (the 1x1 template)
                                        drawn with the same nxm1-4 components

Curves are read back from the delivered ROOT files. Run inside the CDMS
singularity image (needs PyROOT).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import ROOT
from ROOT import TFile

HERE = os.path.dirname(os.path.abspath(__file__))
DELIV = os.path.join(HERE, "..", "deliverables")
DET, CHAN = 7, "PBS1"
SAMPLERATE = 625000.0
RISE_REF_IDX = 16050
LO, HI = RISE_REF_IDX - 200, RISE_REF_IDX + 1300
t_ms = np.arange(LO, HI) / SAMPLERATE * 1e3


def read_hist(tf, name):
    h = tf.Get(name)
    if not h:
        raise SystemExit(f"missing {name}")
    return np.array([h.GetBinContent(i + 1) for i in range(LO, HI)])


f_pca = TFile(os.path.join(DELIV, "nxm", "root_files",
                           f"Templates_SNOLAB_R4_zip{DET}_nxm_pca.root"))
nxm = [read_hist(f_pca, f"nxm{k}_zip{DET}_{CHAN}") for k in range(5)]
f_pca.Close()

f_1x1 = TFile(os.path.join(DELIV, "1x1", "root_files",
                           f"Templates_SNOLAB_R4_zip{DET}_2expfit_weighted.root"))
wmean = read_hist(f_1x1, f"t2exp_zip{DET}_{CHAN}")
f_1x1.Close()

pc_colors = ["crimson", "royalblue", "darkorange", "forestgreen"]
for mean_curve, mean_label, mean_color, fname in [
        (nxm[0], "nxm0 = plain mean (delivered)", "black",
         "nxm_plain_zip7_PBS1.png"),
        (wmean, "NRMSE-weighted mean (= 1x1 template)", "#C0392B",
         "nxm_weighted_zip7_PBS1.png")]:
    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    ax.plot(t_ms, mean_curve, lw=2.2, color=mean_color, label=mean_label)
    for k, arr in enumerate(nxm[1:], start=1):
        ax.plot(t_ms, arr, lw=1.1, color=pc_colors[k - 1], alpha=0.9,
                label=f"nxm{k} (PC{k})")
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    ax.set_title(f"Z{DET} {CHAN}: {mean_label} + PCA components", fontsize=11)
    ax.set_xlabel("Time (ms)", fontsize=10)
    ax.set_ylabel("Norm. amp.", fontsize=10)
    ax.legend(fontsize=7.5, ncol=1, loc="upper right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out = os.path.join(HERE, "figures", fname)
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")
