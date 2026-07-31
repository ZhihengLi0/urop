#!/usr/bin/env python3
"""Stage 1: the linear combination of the 55 NxM amplitudes that predicts the
energy of an event.

    E_pred = c . S,   S = the 55 amplitudes,   c fitted once for the detector

The coefficients come from least squares over the training half,

    minimise  sum_events [ c . S - E_true ]^2

whose stationary point is the global minimum because the loss is a sum of
squares: setting the 55 partial derivatives to zero gives the normal equations
(S^T S) c = S^T E, solved in closed form. The other half of the events is never
seen by the fit and carries the quoted numbers.

Two one-parameter baselines are fitted the same way, to show what the 55
coefficients actually buy: the summed amplitude of the first template of each
channel, and the total-phonon optimal-filter amplitude.

Outputs (results/):
    linear_zip{det}.npz            coefficients and the split
    linear_zip{det}.txt            the numbers
    plots/linear_zip{det}.png      predicted against true, residuals, coefficients

Usage (inside the CDMS singularity image):
    python3 scripts/linear_fit.py --det 7
"""
import argparse
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")
PLOTS = os.path.join(RES, "plots")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--intercept", action="store_true",
                help="also fit a constant term (the specification has none)")
ap.add_argument("--max-t0-ms", type=float, default=0.5,
                help="drop events whose fitted pulse start is this far from the "
                     "trigger: their NxM amplitudes are measured in the standard "
                     "window and miss the pulse, so input and target disagree")
args = ap.parse_args()
det = args.det

d = np.load(os.path.join(RES, f"dataset_zip{det}.npz"), allow_pickle=True)
X, y = d["X"], d["y"]
chans, core = list(d["chans"]), list(d["core"])
t0 = d["t0_ms"]
late = np.abs(t0 - np.median(t0)) > args.max_t0_ms
if late.any():
    print(f"dropping {int(late.sum())} late-pulse events "
          f"(|t0 - median| > {args.max_t0_ms} ms): their amplitudes are measured "
          f"in a window the pulse has left")
    X, y = X[~late], y[~late]
    for k in ("events", "series"):
        d = dict(d)
        d[k] = np.asarray(d[k])[~late]
n, p = X.shape
lines = []


def say(s=""):
    print(s)
    lines.append(s)


say(f"Z{det}: {n} events, {p} amplitudes ({len(chans)} channels x 5 templates)")
say(f"target = summed absorbed energy over {len(core)} channels "
    f"({d['formula']}), mean {y.mean():.1f} eV, std {y.std():.1f} eV "
    f"({100 * y.std() / y.mean():.2f}%)")

rng = np.random.default_rng(args.seed)
perm = rng.permutation(n)
half = n // 2
tr, te = perm[:half], perm[half:]
say(f"split: {len(tr)} train, {len(te)} test (seed {args.seed}); the test half "
    f"never enters the fit")


def fit(A_tr, y_tr):
    c, *_ = np.linalg.lstsq(A_tr, y_tr, rcond=None)
    return c


def gauss_core(v):
    """Iterative 2-sigma-clipped width: the resolution of the bulk, insensitive
    to a handful of pathological events."""
    mu, s = float(np.median(v)), float(v.std())
    for _ in range(8):
        m = np.abs(v - mu) < 2 * s
        if m.sum() < 10:
            break
        mu, s = float(v[m].mean()), float(v[m].std())
    return mu, s


def report(name, A, c):
    pred = A @ c
    res = pred - y
    out = {}
    for lab, idx in (("train", tr), ("test", te)):
        r = res[idx]
        _, cs = gauss_core(r)
        out[lab] = dict(bias=float(r.mean()), rms=float(r.std()),
                        rel=float(100 * r.std() / y[idx].mean()),
                        core=cs, core_rel=float(100 * cs / y[idx].mean()))
    say(f"{name:<32} train {out['train']['rms']:6.1f} / "
        f"{out['train']['core']:5.1f} eV ({out['train']['core_rel']:4.2f}%)"
        f"   test {out['test']['rms']:6.1f} / {out['test']['core']:5.1f} eV "
        f"({out['test']['core_rel']:4.2f}%)")
    return pred, res, out


say()
say(f"{'model':<32} {'train RMS / core sigma':>28}   {'test RMS / core sigma':>28}")
# the 55-parameter linear model of the specification
A55 = np.hstack([X, np.ones((n, 1))]) if args.intercept else X
c55 = fit(A55[tr], y[tr])
pred55, res55, m55 = report(f"55 amplitudes"
                            + (" + intercept" if args.intercept else ""),
                            A55, c55)

# baselines, one parameter each, fitted the same way
sum0 = X.reshape(n, len(chans), 5)[:, :, 0].sum(axis=1, keepdims=True)
c_sum0 = fit(sum0[tr], y[tr])
_, _, m_sum0 = report("baseline: sum of template-0 amps", sum0, c_sum0)
sumall = X.sum(axis=1, keepdims=True)
c_all = fit(sumall[tr], y[tr])
_, _, m_all = report("baseline: sum of all 55 amps", sumall, c_all)

say()
say(f"the 55 coefficients cut the test core width by "
    f"{100 * (1 - m55['test']['core'] / m_sum0['test']['core']):.0f}% against the "
    f"best single scaling of the template-0 sum")
say(f"train / test core width {m55['train']['core'] / m55['test']['core']:.3f} "
    f"(1.00 would mean no overfitting at all; {p} parameters on {len(tr)} events "
    f"predict {np.sqrt((1 - p / len(tr)) / (1 + p / len(tr))):.3f})")
_, cy = gauss_core(y[te])
say(f"the target itself has a core width of {cy:.1f} eV "
    f"({100 * cy / y[te].mean():.2f}%), so the {p} amplitudes explain "
    f"{100 * (1 - (m55['test']['core'] / cy) ** 2):.0f}% of its variance")
cond = np.linalg.cond(A55[tr])
say(f"condition number of the training matrix: {cond:.3g}")

say()
say("coefficients, by channel (template 0..4), in eV per unit amplitude:")
cc = c55[:p].reshape(len(chans), 5)
for i, ch in enumerate(chans):
    say(f"  {ch:>5}: " + " ".join(f"{v:12.4e}" for v in cc[i]))
if args.intercept:
    say(f"  intercept: {c55[-1]:.2f} eV")

# ------------------------------------------------------------------ figures
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
ax = axes[0]
ax.plot(y[tr], pred55[tr], ls="none", marker="o", ms=2.2, alpha=0.35,
        color="#8899AA", label=f"train ({len(tr)})")
ax.plot(y[te], pred55[te], ls="none", marker="o", ms=2.2, alpha=0.55,
        color="#C0392B", label=f"test ({len(te)})")
lim = [0.95 * y.min(), 1.05 * y.max()]
ax.plot(lim, lim, lw=1.2, color="black", ls=(0, (5, 4)), label="perfect")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_xlabel("true absorbed energy (eV)", fontsize=11)
ax.set_ylabel("predicted from the 55 amplitudes (eV)", fontsize=11)
ax.set_title("predicted against true", fontsize=12)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)

ax = axes[1]
bins = np.linspace(-4 * res55.std(), 4 * res55.std(), 61)
ax.hist(res55[tr], bins=bins, histtype="step", lw=1.3, color="#8899AA",
        label=f"train: {m55['train']['rms']:.1f} eV ({m55['train']['rel']:.2f}%)")
ax.hist(res55[te], bins=bins, histtype="stepfilled", color="#C0392B", alpha=0.35,
        edgecolor="#C0392B", lw=1.3,
        label=f"test: {m55['test']['rms']:.1f} eV ({m55['test']['rel']:.2f}%)")
ax.axvline(0, color="black", lw=1.0, ls=":")
ax.set_xlabel("predicted - true (eV)", fontsize=11)
ax.set_ylabel("events", fontsize=11)
ax.set_title("residual", fontsize=12)
ax.legend(fontsize=9)
ax.grid(alpha=0.25)

ax = axes[2]
w = 0.15
for k in range(5):
    ax.bar(np.arange(len(chans)) + (k - 2) * w, cc[:, k], width=w,
           label=f"template {k}")
ax.set_xticks(np.arange(len(chans)))
ax.set_xticklabels(chans, rotation=45, fontsize=9)
ax.axhline(0, color="black", lw=0.8)
ax.set_ylabel("coefficient (eV per unit amplitude)", fontsize=11)
ax.set_title("the 55 coefficients", fontsize=12)
ax.legend(fontsize=8, ncol=5)
ax.grid(alpha=0.25, axis="y")

fig.suptitle(
    f"Z{det}: energy from the {p} NxM amplitudes, linear least squares. "
    f"Test residual {m55['test']['rms']:.1f} eV = {m55['test']['rel']:.2f}%, "
    f"against {m_sum0['test']['rel']:.2f}% for the best single scaling of the "
    f"template-0 sum\n"
    f"target = summed absorbed energy of the event over {len(core)} channels "
    f"(two-exponential fit, closed-form power integral, {d['formula']}), "
    f"each event with its own energy rather than the nominal line value",
    fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.90))
os.makedirs(PLOTS, exist_ok=True)
fn = os.path.join(PLOTS, f"linear_zip{det}.png")
fig.savefig(fn, dpi=150)
plt.close(fig)
say(f"\nsaved {fn}")

np.savez_compressed(os.path.join(RES, f"linear_zip{det}.npz"), c=c55,
                    train_idx=tr, test_idx=te, chans=np.asarray(chans),
                    intercept=args.intercept, seed=args.seed)
with open(os.path.join(RES, f"linear_zip{det}.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"saved {RES}/linear_zip{det}.npz and .txt")
