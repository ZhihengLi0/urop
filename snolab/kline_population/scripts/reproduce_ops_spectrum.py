#!/usr/bin/env python3
"""Reproduce the ops-note summed-PTOFamps spectrum from our own data, with no cut.

The ops note (reference/Ge Activation Data - Ops Shift 2_*.pdf) shows, per
detector, a histogram of the summed-channel optimal-filter amplitude with the
title "Summed (26 series) PTOFamps, rejecting SumPF/PT less than X" (X = 0.1 on
Z7, 0.05 on Z10). This script rebuilds the same histogram from the Prompt
processing on MSI and **applies no such cut**, so that what the cut removes
becomes visible.

For comparison the published histogram is read back out of the PDF by measuring
its bars pixel by pixel: the axes are calibrated on the gridlines that the bars
do not cover, and the bin width is recovered from the runs of equal bar height.
That gives a curve on the same axes with no assumption about the series list.

Outputs (results/plots/):
    ops_spectrum_zip{det}.png

Usage (inside the CDMS singularity image):
    python3 scripts/reproduce_ops_spectrum.py --det 7
"""
import argparse
import glob
import io
import os

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SENTINEL = -999999.0
PROMPT = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed"
          "/Prompt/Prompt_V07-02_C0.4.5/Submerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLOTS = os.path.join(HERE, "results", "plots")
PDF = os.path.join(HERE, "..", "reference", "Ge Activation Data - Ops Shift 2_"
                   "3114372f63d84582a99a75e4f45c5d0b-240626-1548-790.pdf")

# the ops note's own series list is never printed; these 27 contain its 26 (see
# the README) and are the ones used everywhere else in this directory
SERIES = [
    "24260616_222125", "24260616_235257", "24260617_063934", "24260617_175849",
    "24260617_190838", "24260617_234805", "24260618_013000", "24260618_062713",
    "24260618_073543", "24260618_202553", "24260619_023225", "24260619_061249",
    "24260619_075448", "24260619_093653", "24260619_144815", "24260619_174938",
    "24260619_210312", "24260619_230219", "24260620_032928", "24260621_021444",
    "24260621_041432", "24260621_075659", "24260621_111527", "24260621_145024",
    "24260622_022708", "24260622_042718", "24260622_073439",
]
# the plot of each detector in the note, and the cut its title quotes
PANEL = {1: (10, 0.05), 4: (18, 0.05), 6: (26, 0.05), 7: (36, 0.1),
         9: (44, 0.05), 10: (54, 0.05), 13: (62, 0.05), 15: (73, 0.05),
         16: (84, 0.05), 18: (93, 0.05), 19: (104, 0.05), 22: (112, 0.05),
         24: (123, 0.05)}
# the reference lines the note draws, read off its own figures (A)
LINES = {7: dict(kline=2.0e-6, lline=2.8e-7)}

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
ap.add_argument("--bins-per-decade", type=float, default=34.0)
ap.add_argument("--lo", type=float, default=5e-8)
ap.add_argument("--hi", type=float, default=1.2e-4)
args = ap.parse_args()
det = args.det

# ------------------------------------------------------------------ our data
amps, n_sent, n_neg, n_tot, used = [], 0, 0, 0, 0
for s in SERIES:
    paths = sorted(glob.glob(os.path.join(PROMPT, f"*_{s}.root")))
    if not paths:
        print(f"  !! no Prompt file for {s}")
        continue
    z = uproot.open(paths[0])[f"rqDir/zip{det}"]
    a = z["PTOFamps"].array(library="np")
    n_tot += a.size
    n_sent += int((a == SENTINEL).sum())
    ok = (a != SENTINEL) & np.isfinite(a)
    n_neg += int((a[ok] <= 0).sum())
    amps.append(a[ok & (a > 0)])
    used += 1
amps = np.concatenate(amps)
print(f"Z{det}: {used} series, {n_tot} triggers, {n_sent} sentinel, "
      f"{n_neg} non-positive, {amps.size} plotted")

nb = int(round(args.bins_per_decade * np.log10(args.hi / args.lo)))
edges = np.logspace(np.log10(args.lo), np.log10(args.hi), nb + 1)
h, _ = np.histogram(amps, bins=edges)
ctr = np.sqrt(edges[1:] * edges[:-1])

# ------------------------------------- the published histogram, from the PDF
def published(det):
    """Bar centres and heights of the note's own histogram, measured on its
    pixels. Returns None if the panel is not mapped."""
    if det not in PANEL:
        return None
    import fitz
    from PIL import Image
    doc = fitz.open(PDF)
    pix = fitz.Pixmap(doc, PANEL[det][0])
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    im = np.asarray(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    bar = (abs(r - 150) < 45) & (abs(g - 119) < 45) & (abs(b - 158) < 45) & (r > b - 40)
    X0, X1, Y0, Y1 = 126, 958, 116, 517          # inside the axes frame
    PX7, PX4, PY2, PY1 = 209.0, 922.0, 192.0, 347.0    # visible gridlines
    DX, DY = (PX4 - PX7) / 3.0, PY1 - PY2
    amp = lambda px: 10 ** (-7 + (px - PX7) / DX)
    cnt = lambda py: 10 ** (2 + (PY2 - py) / DY)
    tops = np.full(X1 - X0, -1)
    for i, c in enumerate(range(X0, X1)):
        col = bar[Y0:Y1, c]
        if not col[-4:].any():                   # a real bar reaches the axis
            continue
        t = np.where(col)[0].min()
        if col[t:].mean() > 0.9:                 # and is filled
            tops[i] = t + Y0
    runs, i = [], 0
    while i < len(tops):
        if tops[i] < 0:
            i += 1
            continue
        j = i
        while j + 1 < len(tops) and tops[j + 1] == tops[i]:
            j += 1
        runs.append((i, j, tops[i]))
        i = j + 1
    w = np.array([j - i + 1 for i, j, _ in runs])
    p = np.median(w[w <= 9])
    xs, ys = [], []
    for i, j, t in runs:
        for k in range(max(1, int(round((j - i + 1) / p)))):
            xs.append(amp(X0 + i + p * (k + 0.5)))
            ys.append(round(cnt(t)))
    return np.array(xs), np.array(ys), p, DX

pub = published(det)

# ------------------------------------------------------------------- figure
fig, ax = plt.subplots(figsize=(12.5, 6.4))
ax.stairs(h, edges, fill=True, color="#8E7CC3", alpha=0.55, lw=1.0,
          edgecolor="#5B4A8A",
          label=f"our data, NO cut: {amps.size} events, {used} series")
if pub is not None:
    xs, ys, p, DX = pub
    ax.step(xs, ys, where="mid", lw=1.5, color="#111111",
            label=f"the note's histogram, after rejecting SumPF/PT < "
                  f"{PANEL[det][1]}: {int(ys.sum())} events")
for name, x, col in [("10.37 keV K line", LINES.get(det, {}).get("kline"), "#C0392B"),
                     ("1.3 keV L line", LINES.get(det, {}).get("lline"), "#B7950B")]:
    if x:
        ax.axvline(x, color=col, lw=2.0, alpha=0.9,
                   label=f"{name} (the note's marker)")
        ax.text(x, 1.5, f" {name}", rotation=90, va="bottom", ha="left",
                fontsize=9, color=col)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(args.lo, args.hi)
ax.set_ylim(0.7, max(h.max(), (pub[1].max() if pub is not None else 1)) * 2.5)
ax.set_xlabel("PTOFamps (A)", fontsize=12)
ax.set_ylabel("Counts", fontsize=12)
ax.set_title(
    f"Z{det}: summed PTOFamps over {used} series, rebuilt from the Prompt "
    f"processing with no cut applied\n"
    f"the note's version of the same plot rejects SumPF/PT below "
    f"{PANEL[det][1]}; the difference between the two curves is what that cut "
    f"removes", fontsize=12)
ax.legend(fontsize=10, loc="upper left")
ax.grid(alpha=0.25, which="both")
fig.tight_layout()
os.makedirs(PLOTS, exist_ok=True)
fn = os.path.join(PLOTS, f"ops_spectrum_zip{det}.png")
fig.savefig(fn, dpi=150)
plt.close(fig)
print("saved", fn)

if pub is not None:
    xs, ys, _, _ = pub
    for lo, hi, name in [(0, 2e-7, "noise triggers"), (2e-7, 6e-7, "L line"),
                         (1.4e-6, 3e-6, "K line"), (6e-6, 1e-4, "high hump")]:
        m_ours = (amps > lo) & (amps <= hi)
        m_pub = (xs > lo) & (xs <= hi)
        print(f"  {name:>16}: ours {int(m_ours.sum()):>7}, "
              f"note {int(ys[m_pub].sum()):>6}, "
              f"kept {100 * ys[m_pub].sum() / max(m_ours.sum(), 1):>5.1f}%")
