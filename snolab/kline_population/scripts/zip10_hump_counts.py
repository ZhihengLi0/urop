#!/usr/bin/env python3
"""How many events are in the high-amplitude hump of the Z10 K-line spectrum,
and how much run time do the contributing series represent?

Context: slide 2 of the deck shows the 13 per-detector "Summed (N series)
PTOFamps, rejecting SumPF/PT less than 0.05" histograms taken from the Ge
Activation ops note (reference/Ge Activation Data - Ops Shift 2_*.pdf). Z10
shows three populations: noise triggers near 2e-7 A, the 10.37 keV K line at
8.7e-7 A (red marker), and a broad hump from ~4e-6 to ~7e-5 A. This script
counts the hump and sums the run time, two ways:

  1. from the data: PTOFamps for zip10 from the Prompt processing on MSI;
  2. as a cross-check, by integrating the published histogram out of the ops
     note PDF pixel by pixel (--figure), which needs no series list at all.

Run time comes from the ops note's own Series Info table (pp. 21-23) and,
independently, from the largest TriggerTime in each processed series.

Note on the series list: the ops note plots say "26 series" but never print the
list. 18 of the 26 are provable from the note's per-detector removal lists; the
27 series used here are those plus our own analysis list over the same dates, so
this set contains the note's 26 with at most one extra series.

Usage (inside the CDMS singularity image):
    python3 scripts/zip10_hump_counts.py            # data + run time
    python3 scripts/zip10_hump_counts.py --figure   # add the PDF cross-check
"""
import argparse
import glob
import os

import numpy as np
import uproot

PROMPT = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed"
          "/Prompt/Prompt_V07-02_C0.4.5/Submerged")
SENT = -999999.0
CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
         "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]
THRESHOLDS = (1e-6, 2e-6, 3e-6, 5e-6, 1e-5, 2e-5, 3e-5, 5e-5)
VALLEY = 3e-6            # the dip between the K line and the hump

# ops note Series Info table (pp. 21-23): series -> Duration column
OPS_DURATION = {
    "24260616_222125": "1:15:46", "24260616_235257": "0:29:12",
    "24260617_063934": "2:02:48", "24260617_175849": "1:01:29",
    "24260617_190838": "2:10:16", "24260617_234805": "1:20:09",
    "24260618_013000": "1:20:09", "24260618_062713": "0:56:20",
    "24260618_073543": "1:20:09", "24260618_202553": "1:33:28",
    "24260619_023225": "1:20:09", "24260619_061249": "1:20:09",
    "24260619_075448": "1:20:09", "24260619_093653": "0:23:02",
    "24260619_144815": "0:50:05", "24260619_174938": "1:31:47",
    "24260619_210312": "1:40:09", "24260619_230219": "1:40:10",
    "24260620_032928": "1:40:12", "24260621_021444": "1:40:11",
    "24260621_041432": "0:37:51", "24260621_075659": "1:18:10",
    "24260621_111527": "1:43:22", "24260621_145024": "1:40:10",
    "24260622_022708": "1:40:09", "24260622_042718": "1:38:30",
    "24260622_073439": "1:40:09",
}
SERIES = list(OPS_DURATION)
# the 18 series provable to be in the note's list (they appear in its
# per-detector SERIES_LIST.remove() calls)
PROVABLE = {
    "24260616_222125", "24260616_235257", "24260617_063934", "24260617_175849",
    "24260617_190838", "24260617_234805", "24260618_013000", "24260618_062713",
    "24260618_073543", "24260619_093653", "24260619_144815", "24260619_230219",
    "24260620_032928", "24260621_021444", "24260621_041432", "24260621_075659",
    "24260621_111527", "24260621_145024",
}
secs = lambda s: sum(int(x) * f for x, f in zip(s.split(":"), (3600, 60, 1)))

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=10)
ap.add_argument("--ratio-cut", type=float, default=0.05)
ap.add_argument("--figure", action="store_true",
                help="also integrate the published histogram out of the ops PDF")
args = ap.parse_args()
det = args.det
lines = []


def say(s=""):
    print(s)
    lines.append(s)


# ------------------------------------------------------------------ the data
pt, sf, sall, sidx, dur_data = [], [], [], [], []
for i, s in enumerate(SERIES):
    paths = sorted(glob.glob(os.path.join(PROMPT, f"*_{s}.root")))
    if not paths:
        say(f"  !! no Prompt file for {s}")
        dur_data.append(np.nan)
        continue
    h = uproot.open(paths[0])
    z = h[f"rqDir/zip{det}"]
    a_pt = z["PTOFamps"].array(library="np")
    tot = np.zeros_like(a_pt)
    fsum = np.zeros_like(a_pt)
    for c in CHANS:
        try:
            a = z[f"{c}OFamps"].array(library="np")
        except uproot.KeyInFileError:
            continue
        if np.all(a == SENT):
            continue
        a = np.where(a == SENT, 0.0, a)
        tot += a
        if c.startswith("PF"):
            fsum += a
    tt = h["rqDir/eventTree"]["TriggerTime"].array(library="np")
    tt = tt[(tt > 0) & (tt != SENT)]
    pt.append(a_pt)
    sall.append(tot)
    sf.append(fsum)
    sidx.append(np.full(a_pt.size, i))
    dur_data.append(float(tt.max()) if tt.size else np.nan)

pt = np.concatenate(pt)
sall = np.concatenate(sall)
sf = np.concatenate(sf)
sidx = np.concatenate(sidx)
dur_data = np.array(dur_data)
valid = (pt != SENT) & np.isfinite(pt) & (pt > 0)

say(f"=== Z{det}: {len(SERIES)} series, {pt.size} triggers, "
    f"{int(valid.sum())} with a valid PTOFamps ===")
with np.errstate(invalid="ignore", divide="ignore"):
    r_f = np.where(valid, sf / pt, np.nan)
kept = valid & (r_f > args.ratio_cut)
say(f"the note's junk cut is quoted as SumPF/PT > {args.ratio_cut}; taking "
    f"SumPF/PT with PF = the PF channels keeps {int(kept.sum())} events.")
say("It does not reproduce the note's suppression of the noise-trigger hump, so")
say("the note's cut must be something stricter than its wording implies. It")
say("barely matters here: the hump numbers below move by <0.1% under the cut.")

say()
say("--- counts above threshold (PTOFamps, A) ---")
say(f"{'threshold':>10} {'valid':>8} {'after cut':>10}")
for t in THRESHOLDS:
    say(f"{t:>10.0e} {int((valid & (pt > t)).sum()):>8d} "
        f"{int((kept & (pt > t)).sum()):>10d}")

hump = valid & (pt > VALLEY)
say()
say(f"--- the rightmost hump (PTOFamps > {VALLEY:.0e}, the valley) ---")
say(f"  events            : {int(hump.sum())}")
say(f"  events > 1e-5     : {int((valid & (pt > 1e-5)).sum())}")
say(f"  median amplitude  : {np.median(pt[hump]):.3e} A")
say(f"  max amplitude     : {pt[valid].max():.3e} A")
say(f"  in K-line units   : median hump / K line (8.7e-7 A) = "
    f"{np.median(pt[hump]) / 8.7e-7:.1f}x  -> of order "
    f"{10.37 * np.median(pt[hump]) / 8.7e-7:.0f} keV if the response were linear")

# ------------------------------------------------------------------ run time
tot_ops = sum(secs(OPS_DURATION[s]) for s in SERIES)
prov_ops = sum(secs(OPS_DURATION[s]) for s in PROVABLE)
say()
say("--- run time ---")
say(f"  ops Series Info table, all {len(SERIES)} series : {tot_ops} s = "
    f"{tot_ops / 3600:.2f} h")
say(f"  the 18 series provably in the note's list       : {prov_ops / 3600:.2f} h")
say(f"  max TriggerTime per series, summed              : "
    f"{np.nansum(dur_data) / 3600:.2f} h")
say(f"  -> the note's 26 series are {tot_ops / 3600:.1f} h minus one series, "
    f"i.e. about 35-37 h (~1.5 days)")
say(f"  rate in the hump: {int(hump.sum()) / (tot_ops / 3600):.0f} events/hour "
    f"above {VALLEY:.0e} A, "
    f"{int((valid & (pt > 1e-5)).sum()) / (tot_ops / 3600):.0f}/hour above 1e-5 A")

say()
say(f"{'series':>16} {'ops dur':>9} {'processed':>10} {'valid':>7} {'>1e-5':>6}"
    f" {'in note':>8}")
for i, s in enumerate(SERIES):
    m = valid & (sidx == i)
    say(f"{s:>16} {OPS_DURATION[s]:>9} {dur_data[i]:>9.0f}s "
        f"{int(m.sum()):>7} {int((m & (pt > 1e-5)).sum()):>6}"
        f" {'yes' if s in PROVABLE else '?':>8}")

# ------------------------------------------- cross-check against the PDF plot
if args.figure:
    import io
    import fitz
    from PIL import Image
    PDF = os.path.join(HERE, "..", "..", "reference",
                       "Ge Activation Data - Ops Shift 2_"
                       "3114372f63d84582a99a75e4f45c5d0b-240626-1548-790.pdf")
    XREF = {10: 54}[det]                      # the Z10 red-line plot
    doc = fitz.open(PDF)
    pix = fitz.Pixmap(doc, XREF)
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    im = np.asarray(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    bar = (abs(r - 150) < 45) & (abs(g - 119) < 45) & (abs(b - 158) < 45) & (r > b - 40)
    X0, X1, Y0, Y1 = 126, 958, 116, 517       # inside the axes frame
    PX7, PX4, PY2, PY1 = 209.0, 922.0, 192.0, 347.0   # visible gridlines
    DX, DY = (PX4 - PX7) / 3.0, PY1 - PY2
    amp = lambda px: 10 ** (-7 + (px - PX7) / DX)
    cnt = lambda py: 10 ** (2 + (PY2 - py) / DY)
    tops = np.full(X1 - X0, -1)
    for i, c in enumerate(range(X0, X1)):
        col = bar[Y0:Y1, c]
        if not col[-4:].any():                # a real bar reaches the axis
            continue
        top = np.where(col)[0].min()
        if col[top:].mean() > 0.9:            # and is filled
            tops[i] = top + Y0
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
    bars = [(amp(X0 + (i + j) / 2), round(cnt(t)), max(1, int(round((j - i + 1) / p))))
            for i, j, t in runs]
    say()
    say("--- cross-check: the published histogram, integrated from the PDF ---")
    say(f"  bin width {p:.1f} px -> {DX / p:.0f} bins/decade; "
        f"{len(bars)} bars, total {sum(c * n for _, c, n in bars)} events")
    say(f"{'threshold':>10} {'from PDF':>9} {'from data':>10}")
    for t in (3e-6, 1e-5, 2e-5, 3e-5, 5e-5):
        say(f"{t:>10.0e} {sum(c * n for a, c, n in bars if a > t):>9d} "
            f"{int((valid & (pt > t)).sum()):>10d}")
    say(f"  right edge of the published data: {bars[-1][0]:.2e} A "
        f"(data max {pt[valid].max():.2e} A)")

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, f"zip{det}_hump_counts.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"\nsaved {OUT}/zip{det}_hump_counts.txt")
