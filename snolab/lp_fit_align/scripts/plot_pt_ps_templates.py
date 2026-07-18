#!/usr/bin/env python3
"""1x1 summed templates PT / PS1 / PS2, one folder per template type.

Reads the deployed cdmsbats-format PCA template files
(SNOLAB_R4_{date}_ZhihengLi_pca_zip{N}.root) and writes:

  deliverables/1x1/plots/PT/zip{N}_PT.png     (13 figures)
  deliverables/1x1/plots/PS1/zip{N}_PS1.png   (13 figures)
  deliverables/1x1/plots/PS2/zip{N}_PS2.png   (13 figures)
  deliverables/1x1/plots/PT_PS1_PS2_all_zips.png  (overview grid)

PT  = peak-normalized average of ALL channel nxm0 templates
PS1 = same over side-1 channels only; PS2 = side-2 channels only.

Usage:  python3 plot_pt_ps_templates.py --date 20260707
"""

import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path, RISE_REF_IDX,
                          SAMPLERATE)

import ROOT

CB_DIR = ("/projects/standard/yanliusp/shared/software"
          "/cdmsbats_config/PulseTemplates/files")
ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]
KINDS = [("PT", "black"), ("PS1", "crimson"), ("PS2", "royalblue")]

parser = argparse.ArgumentParser()
parser.add_argument("--date", default="20260707")
args = parser.parse_args()

lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 8000
t_ms = np.arange(lo, hi) / SAMPLERATE * 1e3

data = {}   # (det, kind) -> array
for det in ZIPS:
    path = os.path.join(CB_DIR,
                        f"SNOLAB_R4_{args.date}_ZhihengLi_pca_zip{det}.root")
    if not os.path.exists(path):
        continue
    f = ROOT.TFile(path)
    for kind, _ in KINDS:
        h = f.Get(f"zip{det}/{kind}")
        if h:
            data[(det, kind)] = np.array(
                [h.GetBinContent(i + 1) for i in range(lo, hi)])
    f.Close()

# per-type sub-folders, one figure per zip
for kind, color in KINDS:
    for det in ZIPS:
        arr = data.get((det, kind))
        if arr is None:
            continue
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(t_ms, arr, lw=1.6, color=color)
        ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.8, ls=":")
        ax.set_title(f"zip{det} {kind} 1x1 template", fontsize=12)
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("Norm. amp.")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        add_pipeline_note(fig, f"{kind} 1x1 template of zip{det}: peak-normalized "
                          "average of the per-channel nxm0 PCA templates "
                          f"({'all channels' if kind == 'PT' else ('side-1 channels' if kind == 'PS1' else 'side-2 channels')}); "
                          "channel nxm0 = mean of the clean fitted-curve "
                          "population (fit_ok, NRMSE<=0.4, t_rise<=0.3ms)")
        deliv_plots = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables", "1x1", "plots"))
        os.makedirs(os.path.join(deliv_plots, kind), exist_ok=True)
        out = os.path.join(deliv_plots, kind, f"zip{det}_{kind}.png")
        fig.savefig(out, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")

# overview grid
fig, axes = plt.subplots(5, 3, figsize=(15, 16), squeeze=False)
fig.suptitle("1x1 summed templates PT / PS1 / PS2 per zip", fontsize=13)
flat = axes.ravel()
for k, det in enumerate(ZIPS):
    ax = flat[k]
    for kind, color in KINDS:
        arr = data.get((det, kind))
        if arr is not None:
            ax.plot(t_ms, arr, lw=1.3, color=color, label=kind, alpha=0.85)
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.7, ls=":")
    ax.set_title(f"zip{det}", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    ax.tick_params(labelsize=7)
for k in range(len(ZIPS), len(flat)):
    flat[k].axis("off")
fig.tight_layout()
add_pipeline_note(fig, "overview of the 1x1 summed templates: PT = peak-normalized "
                  "average of ALL channel nxm0 PCA templates, PS1/PS2 = side-1/"
                  "side-2 only; per-zip single-template curves for the 1x1 "
                  "optimal filter")
deliv_plots = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables", "1x1", "plots"))
out = os.path.join(deliv_plots, "PT_PS1_PS2_all_zips.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print(f"Saved: {out}")
