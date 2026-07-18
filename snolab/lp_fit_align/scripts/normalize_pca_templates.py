#!/usr/bin/env python3
"""Peak-normalize the already-built PCA templates to unit peak (post-process).

Reads results/root_files/Templates_SNOLAB_R4_zip{N}_nxm_pca.root (nxm1-4 are
raw unit-norm PCA components with tiny amplitude), scales each nxm1-4 to unit
peak-abs (nxm0 already peak=1), and writes:
  - local ROOT (overwrite, normalized)    nxm{k}_zip{N}_{chan}
  - cdmsbats format ROOT (official layout) zip{N}/{chan},{chan}nxm0..4,PT/PS1/PS2
  - plot results/plots/pca_templates/zip{N}_pca_templates.png (normalized shapes)

Pure ROOT scaling, no PCA recomputed. Runs in seconds.

Usage: python3 normalize_pca_templates.py --det 7 --date 20260707
"""

import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path,
                          ALL_CHANS, BASE_DIR, RISE_REF_IDX, SAMPLERATE,
                          TRACELENGTH, X_FULL)

import ROOT
from ROOT import TFile, TH1D

OUT_DIR_DEFAULT = ("/projects/standard/yanliusp/shared/software"
                   "/cdmsbats_config/PulseTemplates/files")
PCA_LO, PCA_HI = RISE_REF_IDX - 500, RISE_REF_IDX + 8000
N_PC = 4

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--date", required=True)
parser.add_argument("--out-dir", default=OUT_DIR_DEFAULT)
args = parser.parse_args()
det = args.det

DELIV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables"))
src_path = os.path.join(DELIV, "nxm", "root_files",
                        f"Templates_SNOLAB_R4_zip{det}_nxm_pca.root")
if not os.path.exists(src_path):
    raise SystemExit(f"no existing PCA ROOT: {src_path}")

templates = {}
fsrc = TFile(src_path)
for c in ALL_CHANS:
    tmpl, ok = [], True
    for k in range(N_PC + 1):
        h = fsrc.Get(f"nxm{k}_zip{det}_{c}")
        if not h:
            ok = False
            break
        arr = np.array([h.GetBinContent(i + 1) for i in range(TRACELENGTH)])
        if k >= 1:
            m = float(np.max(np.abs(arr)))
            if m > 0:
                arr = arr / m
        tmpl.append(arr)
    if ok:
        templates[c] = tmpl
fsrc.Close()
if not templates:
    raise SystemExit(f"zip{det}: no channels found in {src_path}")
print(f"zip{det}: normalized {len(templates)} channels")


def write_hist(name, title, arr):
    h = TH1D(name, title, TRACELENGTH, -0.5, TRACELENGTH - 0.5)
    for j, v in enumerate(arr):
        h.SetBinContent(j + 1, float(v))
    h.Write()


f1 = TFile(src_path, "RECREATE")
for c, tmpl in templates.items():
    for k, arr in enumerate(tmpl):
        write_hist(f"nxm{k}_zip{det}_{c}",
                   f"Zip{det} {c} nxm{k} (peak-normalized to 1)", arr)
f1.Close()
print(f"Saved local ROOT: {src_path}")


def peak_norm_avg(chans):
    arrs = [templates[c][0] for c in chans if c in templates]
    if not arrs:
        return None
    avg = np.mean(arrs, axis=0)
    pk = float(np.max(avg))
    return avg / pk if pk > 0 else avg


cb_path = os.path.join(args.out_dir,
                       f"SNOLAB_R4_{args.date}_ZhihengLi_zip{det}.root")
f2 = TFile(cb_path, "RECREATE")
zdir = f2.mkdir(f"zip{det}")
zdir.cd()
for c, tmpl in templates.items():
    write_hist(c, f"Zip{det} {c} 1x1=nxm0 (peak-normalized)", tmpl[0])
    for k, arr in enumerate(tmpl):
        write_hist(c + f"nxm{k}", f"Zip{det} {c} nxm{k} (peak-normalized)", arr)
for name, chans in [("PT", ALL_CHANS),
                    ("PS1", [c for c in ALL_CHANS if c.endswith("1")]),
                    ("PS2", [c for c in ALL_CHANS if c.endswith("2")])]:
    avg = peak_norm_avg(chans)
    if avg is not None:
        write_hist(name, f"Zip{det} {name} = peak-norm avg of channel nxm0", avg)
f2.Close()
print(f"Saved cdmsbats ROOT: {cb_path}")


t_ms = X_FULL[PCA_LO:PCA_HI] / SAMPLERATE * 1e3
chans = list(templates.keys())
colors = ["black", "crimson", "royalblue", "darkorange", "forestgreen"]
labels = ["nxm0 (mean)", "nxm1 (PC1)", "nxm2 (PC2)", "nxm3 (PC3)", "nxm4 (PC4)"]
fig, axes = plt.subplots(len(chans), 1, figsize=(10, 3.0 * len(chans)),
                         squeeze=False)
fig.suptitle(f"Zip{det} - NxM PCA templates (all peak-normalized to 1)",
             fontsize=12)
for row, c in enumerate(chans):
    ax = axes[row, 0]
    for k, arr in enumerate(templates[c]):
        ax.plot(t_ms, arr[PCA_LO:PCA_HI], lw=1.1, color=colors[k],
                label=labels[k], alpha=0.85)
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.7, ls=":")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    ax.set_title(c, fontsize=9)
    ax.set_xlabel("Time (ms)", fontsize=8)
    ax.set_ylabel("Norm. amp.", fontsize=8)
    ax.legend(fontsize=7, ncol=5)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)
fig.tight_layout()
add_pipeline_note(fig, "NxM PCA templates, ALL peak-normalized to unit peak-abs "
                  "(nxm0 mean + nxm1-4 PCA components 1-4). Population = fitted 2-exp "
                  "curves with fit_ok AND NRMSE<=0.4 AND t_rise<=0.30ms at common "
                  "pretrigger 16050; per-channel PCA. Real pulse = sum_i amp_i * nxm_i.")
plot_dir = os.path.join(DELIV, "nxm", "plots")
os.makedirs(plot_dir, exist_ok=True)
out = os.path.join(plot_dir, f"zip{det}_pca_templates.png")
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved plot: {out}")
