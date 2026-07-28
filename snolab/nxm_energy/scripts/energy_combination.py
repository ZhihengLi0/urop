#!/usr/bin/env python3
"""Combine the NxM amplitudes of an event into an energy estimate.

Every event gives n_chan x 5 amplitudes (55 numbers on Z7). The K-line
sample is mono-energetic (10.37 keV), so it both CALIBRATES a combination
and MEASURES its resolution.

Estimators compared:
  PTOFamps       official total OF amplitude, scaled to the line  (reference)
  sum OFamps     plain sum of the per-channel 1x1 OF amplitudes, scaled
  nxm0 only      sum_c a_c0 * I_c0        (I = template time integral)
  physics NxM    sum_ck a_ck * I_ck       -> the reconstructed pulse integral,
                 i.e. the total collected phonon signal; one overall constant
  min-variance   w = E0 * S^-1 mu / (mu' S^-1 mu), the smallest-variance
                 combination with the right mean; trained on half the events
                 and evaluated on the other half

Output: results/plots/zip{N}_energy_estimators.png
        results/plots/zip{N}_minvar_weights.png
        results/zip{N}_energy_summary.txt

Usage: python3 energy_combination.py --det 7
"""

import argparse
import os
import sys

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
E_LINE = 10.37                                   # keV, Ge activation K-line

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--nrmse-max", type=float, default=0.4,
                    help="keep events whose median fit NRMSE is below this "
                         "(0 disables the quality cut)")
args = parser.parse_args()
det = args.det

d = np.load(os.path.join(RES, f"dataset_zip{det}.npz"), allow_pickle=True)
A, ptof, ofamps, chans = d["A"], d["ptof"], d["ofamps"], list(d["chans"])
med_nrmse = d["med_nrmse"]
n_all = A.shape[0]
if args.nrmse_max > 0:
    good = np.isfinite(med_nrmse) & (med_nrmse <= args.nrmse_max)
    A, ptof, ofamps, med_nrmse = A[good], ptof[good], ofamps[good], med_nrmse[good]
    print(f"quality cut: median fit NRMSE <= {args.nrmse_max} keeps "
          f"{A.shape[0]} of {n_all} events")
n_ev, n_ch, n_k = A.shape
print(f"zip{det}: {n_ev} events x {n_ch} channels x {n_k} amplitudes")

# template time integrals (peak-normalized templates -> integral in samples)
DELIV = os.path.join(HERE, "..", "..", "deliverables")
tf = uproot.open(os.path.join(DELIV, "nxm", "root_files",
                              f"Templates_SNOLAB_R4_zip{det}_nxm_pca.root"))
I = np.array([[float(np.sum(tf[f"nxm{k}_zip{det}_{c}"].values()))
               for k in range(n_k)] for c in chans])       # (n_ch, n_k)


from scipy.optimize import curve_fit


def peak_model(x, amp, mu, sig, b0, b1):
    return amp * np.exp(-0.5 * ((x - mu) / sig) ** 2) + b0 + b1 * (x - E_LINE)


def stats(x):
    """Scale to the line, then fit a Gaussian + linear background.

    The selection window holds the K-line peak on top of a continuum, so the
    resolution is the width of the FITTED PEAK, not the spread of everything.
    """
    x = x / float(np.median(x)) * E_LINE
    lo, hi = np.percentile(x, [2, 98])
    bins = np.linspace(lo, hi, 60)
    ctr = 0.5 * (bins[1:] + bins[:-1])
    h, _ = np.histogram(x, bins=bins)
    p0 = [h.max(), ctr[np.argmax(h)], 0.1 * E_LINE, np.median(h), 0.0]
    try:
        popt, _ = curve_fit(peak_model, ctr, h, p0=p0, maxfev=20000,
                            bounds=([0, lo, 0.005 * E_LINE, 0, -np.inf],
                                    [np.inf, hi, 0.5 * E_LINE, np.inf, np.inf]))
        mu, sig = float(popt[1]), abs(float(popt[2]))
        frac = float(popt[0] * sig * np.sqrt(2 * np.pi) /
                     (bins[1] - bins[0]) / len(x))
    except Exception:
        mu, sig, frac, popt = float(np.median(x)), float("nan"), float("nan"), None
    return x, mu, sig, sig / mu * 100, frac, popt, bins


estimators = {}
estimators["PTOFamps"] = stats(ptof)
estimators["sum OFamps"] = stats(ofamps.sum(axis=1))
E_nxm0 = (A[:, :, 0] * I[:, 0]).sum(axis=1)
estimators["nxm0 only"] = stats(E_nxm0)
estimators["physics NxM"] = stats((A * I).sum(axis=(1, 2)))

# ---- minimum-variance combination, honest train/test split ----------------
X = A.reshape(n_ev, n_ch * n_k)
rng = np.random.default_rng(args.seed)
perm = rng.permutation(n_ev)
tr, te = perm[: n_ev // 2], perm[n_ev // 2:]

# the weights must be trained on the LINE, not on the continuum: take the
# events inside +-2 sigma of the nxm0 peak as the mono-energetic sample
_, mu0, sig0, _, _, _, _ = estimators["nxm0 only"]
core_all = np.abs(E_nxm0 / np.median(E_nxm0) * E_LINE - mu0) < 2 * sig0
core_tr = tr[core_all[tr]]
print(f"weights trained on {len(core_tr)} core events "
      f"(|E - {mu0:.2f}| < 2 x {sig0:.2f} keV)")

mu = X[core_tr].mean(axis=0)
S = np.cov(X[core_tr], rowvar=False)
S += np.eye(S.shape[0]) * 1e-4 * np.trace(S) / S.shape[0]     # ridge
Sinv_mu = np.linalg.solve(S, mu)
w = E_LINE * Sinv_mu / float(mu @ Sinv_mu)
estimators["min-variance (test half)"] = stats(X[te] @ w)
np.savez(os.path.join(RES, f"weights_zip{det}.npz"), w=w, chans=np.array(chans),
         scale=float(np.median(X[te] @ w)) / E_LINE)

lines = [f"zip{det}: {n_ev} K-line events (median fit NRMSE <= "
         f"{args.nrmse_max}, from {n_all} in the window), "
         f"{n_ch} channels x {n_k} amplitudes "
         f"= {n_ch * n_k} numbers per event", "",
         "peak = Gaussian + linear background fitted to the scaled spectrum",
         "",
         f"{'estimator':<26} {'peak (keV)':>11} {'sigma (keV)':>12} {'sigma/E':>9} {'in peak':>9}"]
for name, (x, m, s, r, frac, _, _) in estimators.items():
    lines.append(f"{name:<26} {m:>11.2f} {s:>12.3f} {r:>8.2f}% {frac*100:>8.0f}%")
summary = "\n".join(lines)
print("\n" + summary)
with open(os.path.join(RES, f"zip{det}_energy_summary.txt"), "w") as fh:
    fh.write(summary + "\n")

# ---- plots ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10.5, 5.2))
bins = np.linspace(E_LINE * 0.5, E_LINE * 1.5, 120)
for (name, (x, m, s, r, frac, popt, fb)), col in zip(
        estimators.items(),
        ["gray", "darkorange", "royalblue", "crimson", "forestgreen"]):
    ax.hist(x, bins=bins, histtype="step", lw=1.5, color=col,
            label=f"{name}:  peak {m:.2f} keV, σ/E = {r:.2f}%")
    if popt is not None:
        xs = np.linspace(fb[0], fb[-1], 400)
        scale = (bins[1] - bins[0]) / (fb[1] - fb[0])
        ax.plot(xs, peak_model(xs, *popt) * scale, lw=1.0, ls="--", color=col,
                alpha=0.8)
ax.axvline(E_LINE, color="black", lw=1.0, ls=":")
ax.set_xlabel("Reconstructed energy (keV)")
ax.set_ylabel("Events")
ax.set_title(f"Zip{det}: K-line energy from the NxM amplitudes "
             f"({n_ch}×{n_k} = {n_ch * n_k} numbers per event), all scaled to "
             f"{E_LINE} keV", fontsize=12)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)
fig.tight_layout()
out1 = os.path.join(RES, "plots", f"zip{det}_energy_estimators.png")
fig.savefig(out1, dpi=150, bbox_inches="tight")
print("saved", out1)

W = w.reshape(n_ch, n_k)
Wn = W * X[core_tr].mean(axis=0).reshape(n_ch, n_k)     # contribution to E
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
im = axes[0].imshow(Wn, cmap="RdBu_r",
                    vmin=-np.max(np.abs(Wn)), vmax=np.max(np.abs(Wn)))
axes[0].set_xticks(range(n_k)); axes[0].set_xticklabels([f"nxm{k}" for k in range(n_k)])
axes[0].set_yticks(range(n_ch)); axes[0].set_yticklabels(chans, fontsize=8)
axes[0].set_title("min-variance: mean keV contributed per amplitude", fontsize=11)
plt.colorbar(im, ax=axes[0])
axes[1].bar(np.arange(n_ch) - 0.2, Wn.sum(axis=1), width=0.4, label="min-variance")
phys = (A * I).mean(axis=0)
phys = phys / phys.sum() * E_LINE
axes[1].bar(np.arange(n_ch) + 0.2, phys.sum(axis=1), width=0.4, label="physics weights")
axes[1].set_xticks(range(n_ch)); axes[1].set_xticklabels(chans, rotation=45, fontsize=8)
axes[1].set_ylabel("keV from this channel")
axes[1].set_title("energy shared out over the channels", fontsize=11)
axes[1].legend(fontsize=9); axes[1].grid(alpha=0.25, axis="y")
fig.tight_layout()
out2 = os.path.join(RES, "plots", f"zip{det}_minvar_weights.png")
fig.savefig(out2, dpi=150, bbox_inches="tight")
print("saved", out2)
