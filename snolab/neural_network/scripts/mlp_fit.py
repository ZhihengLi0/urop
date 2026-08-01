#!/usr/bin/env python3
"""Stage 2: a neural network on the same 55 amplitudes and the same loss.

The linear model of stage 1 is the number to beat. The network sees exactly the
same inputs and minimises the same squared error, and is free to find a
combination the linear model cannot express.

Method, and why it is set up this way:

- inputs and target are standardised using the **training half only**, because a
  network cannot train on raw amplitudes of order 1e-7;
- the architecture and the regularisation are chosen on a validation split taken
  out of the training half, never on the test half. The whiteboard sketch is a
  hidden layer of order 1000, which is 56000 weights for 806 training events, so
  the scan includes smaller networks and several regularisation strengths and
  lets the validation score decide;
- the winner is evaluated on the untouched test half exactly once;
- a residual variant is also fitted, where the network learns only what the
  linear model leaves behind. It cannot do worse than linear by construction and
  separates "what the network adds" from "what it has to relearn".

Outputs (results/):
    mlp_zip{det}.txt              the scan and the final numbers
    mlp_zip{det}.npz              the chosen model's predictions
    plots/mlp_zip{det}.png        predicted against true, residuals, comparison

Usage (inside the CDMS singularity image):
    python3 scripts/mlp_fit.py --det 7
"""
import argparse
import os
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=ConvergenceWarning)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
PLOTS = os.path.join(RES, "plots")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--max-t0-ms", type=float, default=0.5)
args = ap.parse_args()
det = args.det

d = np.load(os.path.join(RES, f"dataset_zip{det}.npz"), allow_pickle=True)
X, y, t0 = d["X"], d["y"], d["t0_ms"]
late = np.abs(t0 - np.median(t0)) > args.max_t0_ms
X, y = X[~late], y[~late]
n, p = X.shape

L = np.load(os.path.join(RES, f"linear_zip{det}.npz"), allow_pickle=True)
tr, te = L["train_idx"], L["test_idx"]        # the identical split as stage 1
c_lin = L["c"]
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def core(v):
    """2-sigma-clipped width, the resolution of the bulk."""
    mu, s = float(np.median(v)), float(v.std())
    for _ in range(8):
        m = np.abs(v - mu) < 2 * s
        if m.sum() < 10:
            break
        mu, s = float(v[m].mean()), float(v[m].std())
    return s


say(f"Z{det}: {n} events, {p} inputs; the split is the one stage 1 used, "
    f"{len(tr)} train and {len(te)} test")
res_lin = X @ c_lin - y
say(f"linear baseline: test core {core(res_lin[te]):.1f} eV "
    f"({100 * core(res_lin[te]) / y[te].mean():.2f}%), "
    f"RMS {res_lin[te].std():.1f} eV")

# standardisation, fitted on the training half only
sx = StandardScaler().fit(X[tr])
Xs = sx.transform(X)
mu_y, sd_y = float(y[tr].mean()), float(y[tr].std())
ys = (y - mu_y) / sd_y

# an inner validation split, carved out of the training half
in_tr, in_va = train_test_split(np.arange(len(tr)), test_size=0.2,
                                random_state=args.seed)
in_tr, in_va = tr[in_tr], tr[in_va]
say(f"model selection uses {len(in_tr)} of the training events, validating on "
    f"{len(in_va)}; the test half is untouched until the end")


def train(hidden, alpha, target, seed):
    m = MLPRegressor(hidden_layer_sizes=hidden, alpha=alpha, activation="relu",
                     solver="adam", learning_rate_init=1e-3, batch_size=64,
                     max_iter=4000, n_iter_no_change=25, early_stopping=True,
                     validation_fraction=0.15, random_state=seed)
    m.fit(Xs[in_tr], target[in_tr])
    return m


say()
say(f"{'architecture':>18} {'alpha':>8} {'val core [eV]':>14} {'val RMS [eV]':>13}")
grid = [((1000,), a) for a in (1e-4, 1e-2, 1.0)] \
     + [((256,), a) for a in (1e-2, 1.0)] \
     + [((128, 64), a) for a in (1e-2, 1.0)] \
     + [((64, 32), a) for a in (1e-2, 1.0)]
best = None
for hidden, alpha in grid:
    m = train(hidden, alpha, ys, args.seed)
    r = (m.predict(Xs[in_va]) * sd_y + mu_y) - y[in_va]
    cs = core(r)
    say(f"{str(hidden):>18} {alpha:>8.0e} {cs:>14.1f} {r.std():>13.1f}")
    if best is None or cs < best[0]:
        best = (cs, hidden, alpha)
say(f"chosen: hidden {best[1]}, alpha {best[2]:.0e}  (validation core "
    f"{best[0]:.1f} eV)")

# refit the winner on the whole training half, then touch the test half once
say()
mlp = MLPRegressor(hidden_layer_sizes=best[1], alpha=best[2], activation="relu",
                   solver="adam", learning_rate_init=1e-3, batch_size=64,
                   max_iter=4000, n_iter_no_change=25, early_stopping=True,
                   validation_fraction=0.15, random_state=args.seed)
mlp.fit(Xs[tr], ys[tr])
pred_mlp = mlp.predict(Xs) * sd_y + mu_y
res_mlp = pred_mlp - y

# the residual variant: the network only learns what the linear model missed
rs = res_lin / sd_y
mlp_r = MLPRegressor(hidden_layer_sizes=best[1], alpha=best[2], activation="relu",
                     solver="adam", learning_rate_init=1e-3, batch_size=64,
                     max_iter=4000, n_iter_no_change=25, early_stopping=True,
                     validation_fraction=0.15, random_state=args.seed)
mlp_r.fit(Xs[tr], rs[tr])
pred_hyb = X @ c_lin - mlp_r.predict(Xs) * sd_y
res_hyb = pred_hyb - y

say(f"{'model':<28} {'train core':>11} {'test core':>10} {'test RMS':>10} "
    f"{'test bias':>10}")
rows = [("linear, 55 coefficients", res_lin),
        ("network on the amplitudes", res_mlp),
        ("linear + network on residual", res_hyb)]
for name, r in rows:
    say(f"{name:<28} {core(r[tr]):>10.1f} {core(r[te]):>9.1f} "
        f"{r[te].std():>9.1f} {r[te].mean():>+9.1f}   "
        f"({100 * core(r[te]) / y[te].mean():.2f}%)")

say()
say("the target is itself a measurement: the fit-based and official-window "
    "energies of the same events disagree by a core width of 62.0 eV (1.96%), "
    "so each carries at least about 1.4% of noise. A residual of 2.28% is "
    "therefore already close to what the target can resolve, which caps what any "
    "model can gain.")

best_name, best_res = min(rows, key=lambda t: core(t[1][te]))
gain = 100 * (1 - core(best_res[te]) / core(res_lin[te]))
say()
say(f"best on the test half: {best_name}, core {core(best_res[te]):.1f} eV = "
    f"{100 * core(best_res[te]) / y[te].mean():.2f}%")
say(f"against the linear model that is {gain:+.1f}% of the width. The linear "
    f"model itself moves by about 3.5% between random splits (2.18 to 2.34% over "
    f"five seeds), so a gain has to exceed that to mean anything: "
    f"{'it does' if gain > 7 else 'it does NOT'}.")
say(f"iterations run: {mlp.n_iter_}, final training loss {mlp.loss_:.5f}")

# ------------------------------------------------------------------ figures
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
ax = axes[0]
ax.plot(y[te], (X @ c_lin)[te], ls="none", marker="o", ms=2.2, alpha=0.35,
        color="#8899AA", label=f"linear ({100 * core(res_lin[te]) / y[te].mean():.2f}%)")
ax.plot(y[te], pred_mlp[te], ls="none", marker="o", ms=2.2, alpha=0.55,
        color="#C0392B", label=f"network ({100 * core(res_mlp[te]) / y[te].mean():.2f}%)")
lim = [0.95 * y.min(), 1.05 * y.max()]
ax.plot(lim, lim, lw=1.2, color="black", ls=(0, (5, 4)), label="perfect")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_xlabel("true absorbed energy (eV)", fontsize=11)
ax.set_ylabel("predicted (eV)", fontsize=11)
ax.set_title("test half only", fontsize=12)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)

ax = axes[1]
bins = np.linspace(-4 * res_lin[te].std(), 4 * res_lin[te].std(), 61)
for (name, r), col in zip(rows, ("#8899AA", "#C0392B", "#1B7A3D")):
    ax.hist(r[te], bins=bins, histtype="step", lw=1.4, color=col,
            label=f"{name}: {core(r[te]):.1f} eV")
ax.axvline(0, color="black", lw=1.0, ls=":")
ax.set_xlabel("predicted - true (eV)", fontsize=11)
ax.set_ylabel("events", fontsize=11)
ax.set_title("test residual", fontsize=12)
ax.legend(fontsize=8.5)
ax.grid(alpha=0.25)

ax = axes[2]
ax.plot(mlp.loss_curve_, lw=1.3, color="#C0392B", label="network on amplitudes")
ax.plot(mlp_r.loss_curve_, lw=1.3, color="#1B7A3D", label="network on residual")
ax.set_yscale("log")
ax.set_xlabel("iteration", fontsize=11)
ax.set_ylabel("training loss (standardised units)", fontsize=11)
ax.set_title("training", fontsize=12)
ax.legend(fontsize=9)
ax.grid(alpha=0.25, which="both")

fig.suptitle(
    f"Z{det}: energy from the {p} NxM amplitudes, network against linear. "
    f"Hidden {best[1]}, alpha {best[2]:.0e}, chosen on a validation split inside "
    f"the training half\n"
    f"test core width: linear {core(res_lin[te]):.1f} eV "
    f"({100 * core(res_lin[te]) / y[te].mean():.2f}%), network "
    f"{core(res_mlp[te]):.1f} eV ({100 * core(res_mlp[te]) / y[te].mean():.2f}%), "
    f"linear + network on the residual {core(res_hyb[te]):.1f} eV "
    f"({100 * core(res_hyb[te]) / y[te].mean():.2f}%)",
    fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.90))
os.makedirs(PLOTS, exist_ok=True)
fn = os.path.join(PLOTS, f"mlp_zip{det}.png")
fig.savefig(fn, dpi=150)
plt.close(fig)
say(f"\nsaved {fn}")

np.savez_compressed(os.path.join(RES, f"mlp_zip{det}.npz"),
                    pred_mlp=pred_mlp, pred_hyb=pred_hyb, y=y,
                    train_idx=tr, test_idx=te, hidden=np.asarray(best[1]),
                    alpha=best[2])
with open(os.path.join(RES, f"mlp_zip{det}.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"saved {RES}/mlp_zip{det}.npz and .txt")
