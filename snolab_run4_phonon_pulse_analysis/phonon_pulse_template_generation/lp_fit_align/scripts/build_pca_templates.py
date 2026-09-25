#!/usr/bin/env python3
"""NxM PCA templates from the clean fitted-curve population.

Input population (same material as fitted_curves_overlay, then cleaned):
  fit_ok  AND  NRMSE <= --nrmse-max  AND  t_rise <= --trise-max
The second cut removes the smooth slow-drift noise that leaks through the
NRMSE cut on noisy detectors (verified in slow_events/); the fast-pulse
population (t_rise ~ 0.1 ms) is kept.

Each surviving event's fitted 2-exp curve is regenerated at the common
pretrigger 16050 and peak-normalized (identical to fitted_curves_overlay).
PCA is then run per channel on these curves (teacher's NxM_cedar.ipynb method:
templates ARE the PCA components, oscillating basis vectors — not physical
pulses). Templates written:
  nxm0 = mean curve (physical, positive)
  nxm1..nxm4 = PCA components 1..4 (can be negative)
A real pulse is fit as sum_i amp_i * nxm_i by the optimal filter.

Outputs:
  deliverables/nxm/plots/zip{N}_pca_templates.png
  deliverables/nxm/root_files/Templates_SNOLAB_R4_zip{N}_nxm_pca.root
      (nxm{k}_zip{N}_{chan}, 32768 bins, PCA window embedded, zero elsewhere)

Usage:
    python3 build_pca_templates.py --det 7 [--nrmse-max 0.4] [--trise-max 3e-4]
"""

import argparse
import os
import pickle
import sys
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path,
                          ALL_CHANS, BASE_DIR, CKPT_DIR, RISE_REF_IDX,
                          SAMPLERATE, TRACELENGTH, X_FULL, two_exp_free_pt)

import ROOT
from ROOT import TFile, TH1D

PCA_LO, PCA_HI = RISE_REF_IDX - 500, RISE_REF_IDX + 8000   # PCA window
N_PC = 4                    # nxm1..nxm4 ; plus nxm0 = mean
MAX_PCA = 3000              # cap curves per channel fed to PCA (random, seeded)
MIN_EVENTS = 10

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--nrmse-max", type=float, default=0.4)
parser.add_argument("--trise-max", type=float, default=3e-4)
args = parser.parse_args()
det, NR, TR = args.det, args.nrmse_max, args.trise_max

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
ckpts = sorted(f for f in os.listdir(ckpt_dir) if f.endswith("_fit.pkl"))
if not ckpts:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

# ── collect clean fitted curves per channel (PCA window) ──────────────────────
xw = X_FULL[PCA_LO:PCA_HI]
curves = {c: [] for c in ALL_CHANS}
for fname in ckpts:
    with open(os.path.join(ckpt_dir, fname), "rb") as fh:
        fits = pickle.load(fh)["fits"]
    for c in ALL_CHANS:
        for fp in fits.get(c) or []:
            if fp is None or not fp["fit_ok"]:
                continue
            if fp["nrmse"] > NR or fp["t_rise"] > TR:
                continue
            y = two_exp_free_pt(xw, fp["amp"], fp["t_rise"], fp["t_fall"],
                                0.0, float(RISE_REF_IDX))
            pk = float(np.max(y))
            if pk > 0:
                curves[c].append((y / pk).astype(np.float64))

# ── PCA per channel ───────────────────────────────────────────────────────────
def embed(win_arr):
    """Place a PCA-window vector into a full 32768 trace, zero elsewhere."""
    full = np.zeros(TRACELENGTH)
    full[PCA_LO:PCA_HI] = win_arr
    return full

templates = {}         # chan -> [nxm0..nxm4] full-length
var_exp = {}
rng = np.random.default_rng(42)
for c in ALL_CHANS:
    arr = curves[c]
    if len(arr) < MIN_EVENTS:
        print(f"  {c}: only {len(arr)} clean curves, skipped")
        continue
    arr = np.array(arr)
    if len(arr) > MAX_PCA:
        arr = arr[rng.choice(len(arr), MAX_PCA, replace=False)]
    mean_w = arr.mean(axis=0)
    pk = float(np.max(mean_w))
    if pk > 0:
        mean_w = mean_w / pk
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pca = PCA(n_components=N_PC, svd_solver="full").fit(arr)
    templates[c] = [embed(mean_w)] + [embed(pca.components_[i])
                                      for i in range(N_PC)]
    var_exp[c] = pca.explained_variance_ratio_.tolist()
    print(f"  {c}: {len(arr)} curves -> PCA var {[f'{v:.3f}' for v in var_exp[c]]}")

if not templates:
    raise SystemExit(f"zip{det}: no channel had enough clean curves")

# ── ROOT ──────────────────────────────────────────────────────────────────────
DELIV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deliverables"))
root_dir = os.path.join(DELIV, "nxm", "root_files")
os.makedirs(root_dir, exist_ok=True)
root_path = os.path.join(root_dir, f"Templates_SNOLAB_R4_zip{det}_nxm_pca.root")
tf = TFile(root_path, "RECREATE")
for c, tmpl in templates.items():
    for k, arr in enumerate(tmpl):
        h = TH1D(f"nxm{k}_zip{det}_{c}",
                 f"Zip{det} {c} nxm{k} "
                 f"({'mean' if k == 0 else f'PCA comp {k}'}, "
                 f"fit_ok+NRMSE<={NR}+t_rise<={TR*1e3:.2f}ms)",
                 TRACELENGTH, -0.5, TRACELENGTH - 0.5)
        for j, v in enumerate(arr):
            h.SetBinContent(j + 1, float(v))
        h.Write()
tf.Close()
print(f"Saved ROOT: {root_path}")

# ── plot ──────────────────────────────────────────────────────────────────────
t_ms = xw / SAMPLERATE * 1e3
chans = list(templates.keys())
fig, axes = plt.subplots(len(chans), 1, figsize=(10, 3.0 * len(chans)),
                         squeeze=False)
fig.suptitle(f"Zip{det} — NxM PCA templates (teacher's method: components are "
             "oscillating basis vectors)", fontsize=12)
colors = ["black", "crimson", "royalblue", "darkorange", "forestgreen"]
labels = ["nxm0 (mean)", "nxm1 (PC1)", "nxm2 (PC2)", "nxm3 (PC3)", "nxm4 (PC4)"]
for row, c in enumerate(chans):
    ax = axes[row, 0]
    for k, arr in enumerate(templates[c]):
        seg = arr[PCA_LO:PCA_HI].astype(np.float64).copy()
        if k >= 1:
            # each PCA component (a unit-norm basis vector) is tiny in
            # amplitude; normalize it to unit peak-abs FOR DISPLAY ONLY so the
            # waveform shape is visible. The ROOT templates keep the raw
            # (unit-norm) components.
            m = float(np.max(np.abs(seg)))
            if m > 0:
                seg = seg / m
        ax.plot(t_ms, seg, lw=1.1, color=colors[k],
                label=labels[k], alpha=0.85)
    ax.axvline(RISE_REF_IDX / SAMPLERATE * 1e3, color="gray", lw=0.7, ls=":")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    v = var_exp[c]
    ax.set_title(f"{c}  n={len(curves[c])}  "
                 f"var: {'  '.join(f'PC{i+1}:{x:.2f}' for i, x in enumerate(v))}",
                 fontsize=8)
    ax.set_xlabel("Time (ms)", fontsize=8)
    ax.set_ylabel("Amp.", fontsize=8)
    ax.legend(fontsize=7, ncol=5)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)
fig.tight_layout()
add_pipeline_note(fig, "NxM PCA templates: population = fitted 2-exp curves with "
                  f"fit_ok AND NRMSE<={NR} AND t_rise<={TR*1e3:.2f}ms (removes smooth "
                  "slow-drift noise leaking through NRMSE), each curve at common "
                  "pretrigger 16050 peak-normalized; per-channel PCA (svd_solver=full); "
                  "nxm0 = mean curve, nxm1-4 = PCA components 1-4 (basis vectors, may "
                  "be negative); a real pulse = sum_i amp_i * nxm_i in the optimal filter. "
                  "PLOT ONLY: nxm1-4 each normalized to unit peak-abs so the shape is "
                  "visible (ROOT templates keep the raw unit-norm components)")
plot_dir = os.path.join(DELIV, "nxm", "plots")
os.makedirs(plot_dir, exist_ok=True)
out = os.path.join(plot_dir, f"zip{det}_pca_templates.png")
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved: {out}")
