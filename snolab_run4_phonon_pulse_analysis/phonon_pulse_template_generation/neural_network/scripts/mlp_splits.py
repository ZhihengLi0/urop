#!/usr/bin/env python3
"""Does the network really beat the linear model? A paired test over many splits.

A single train/test split cannot answer this. On the split of stage 1 the hybrid
is 2.8 eV narrower than linear, but a paired bootstrap of that one test half puts
the difference below zero 28% of the time. What moves between splits is mostly
which events land in the test half, and that moves every model together, so the
models must be compared on the same test half, split after split.

For each of N random halvings of the events this script fits, on the training
half only,
    linear      E = c . S, least squares
    network     the 55 amplitudes -> E directly
    hybrid      linear, plus a network fitted to the linear model's residual
and records the 2-sigma-clipped core width of each on the test half.

The architecture is the one mlp_fit.py chose on the stage-1 split, hidden (256,)
and alpha 1. It is not re-chosen per split: those two numbers were picked on a
validation set inside the stage-1 training half, which overlaps the other splits'
test halves, so the comparison carries that small leak.

Output: results/mlp_splits_zip{det}.txt

Usage (inside the CDMS singularity image; about a minute on an 8-core node,
far longer on a login node):
    python3 scripts/mlp_splits.py --det 7 --splits 20
"""
import argparse
import os
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=ConvergenceWarning)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--splits", type=int, default=20)
ap.add_argument("--max-t0-ms", type=float, default=0.5)
args = ap.parse_args()
det = args.det

d = np.load(os.path.join(RES, f"dataset_zip{det}.npz"), allow_pickle=True)
X, y, t0 = d["X"], d["y"], d["t0_ms"]
late = np.abs(t0 - np.median(t0)) > args.max_t0_ms
X, y = X[~late], y[~late]
n = len(y)
lines = []


def say(s=""):
    print(s, flush=True)
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


def mlp(seed):
    return MLPRegressor(hidden_layer_sizes=(256,), alpha=1.0, activation="relu",
                        solver="adam", learning_rate_init=1e-3, batch_size=64,
                        max_iter=4000, n_iter_no_change=25, early_stopping=True,
                        validation_fraction=0.15, random_state=seed)


say(f"Z{det}: {n} events, {args.splits} random halvings; every model is fitted "
    f"on the training half and scored on the same test half")
say(f"{'split':>5} {'linear':>8} {'network':>8} {'hybrid':>8} "
    f"{'hybrid-linear':>14}   (test core width, % of the mean energy)")
rows, split0 = [], None
for seed in range(args.splits):
    perm = np.random.default_rng(seed).permutation(n)      # as linear_fit.py
    tr, te = perm[: n // 2], perm[n // 2:]
    c, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
    res_lin = X @ c - y
    Xs = StandardScaler().fit(X[tr]).transform(X)
    mu, sd = float(y[tr].mean()), float(y[tr].std())
    res_net = mlp(seed).fit(Xs[tr], (y[tr] - mu) / sd).predict(Xs) * sd + mu - y
    res_hyb = res_lin - mlp(seed).fit(Xs[tr], res_lin[tr] / sd).predict(Xs) * sd
    ym = y[te].mean()
    r = [100 * core(v[te]) / ym for v in (res_lin, res_net, res_hyb)]
    rows.append(r)
    say(f"{seed:>5} {r[0]:>7.3f}% {r[1]:>7.3f}% {r[2]:>7.3f}% {r[2] - r[0]:>+13.3f}")
    if seed == 0:
        split0 = (te, res_lin, res_hyb)

a = np.array(rows)
k = len(a)
say()
for j, name in enumerate(("linear", "network", "hybrid")):
    say(f"{name:>8}: mean {a[:, j].mean():.3f}%, spread between splits "
        f"{a[:, j].std():.3f}%")
for j, name in ((1, "network"), (2, "hybrid")):
    dd = a[:, j] - a[:, 0]
    say(f"{name} - linear: mean {dd.mean():+.3f}% ({100 * (dd / a[:, 0]).mean():+.1f}% "
        f"of the width), spread {dd.std():.3f}%, narrower than linear in "
        f"{int((dd < 0).sum())}/{k} splits")
say("the splits share events, so they are not independent and the spread of the "
    "mean is not quoted as an error; the count of splits won is the robust number")

te, rl, rh = split0
rng = np.random.default_rng(123)
bd = np.array([core(rl[i]) - core(rh[i])
               for i in (rng.choice(te, te.size, replace=True) for _ in range(2000))])
say()
say(f"for contrast, split 0 alone (the stage-1 split): linear - hybrid = "
    f"{core(rl[te]) - core(rh[te]):.2f} eV, paired bootstrap 68% interval "
    f"[{np.percentile(bd, 16):.2f}, {np.percentile(bd, 84):.2f}] eV, at or below "
    f"zero in {100 * (bd <= 0).mean():.0f}% of resamples: one split cannot decide")

with open(os.path.join(RES, f"mlp_splits_zip{det}.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"saved {RES}/mlp_splits_zip{det}.txt")
