#!/usr/bin/env python3
"""Distribution of the TES bias current I0 behind the collection-efficiency result.

I0 is not a per-event quantity: every series has one measured bias point per
channel in its detectorConfig (i0, r0, rp, rshunt). kline_energy_hist.py reads
the detectorConfig of the FIRST cached series and applies that I0 to all 30
series. This script reads the detectorConfig of every cached series, gives each
event that enters the summed-energy distribution (all 10 core channels fitted)
the I0 of its own series, and histograms it per channel. The vertical line marks
the value actually used (first series); the spread shows how much the bias
point moved between series, i.e. the size of that approximation.

Outputs (results/plots/bias_point_check/):
    zip{det}_I0_histogram.png   one panel per channel, events per I0 bin
    zip{det}_I0_histogram.txt   per channel: value used, min / max / mean over
                                the series, and the event-weighted spread

Usage (inside the CDMS singularity image):
    python3 scripts/i0_histogram.py --det 7
"""
import argparse
import glob
import os
import re

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ALL_CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
             "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]
RAW_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
PROC_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
            "/Processed/Default/Default_tag/Unmerged")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(HERE, "results", "plots", "current_power_overlay")   # the energies
OUT_DIR = os.path.join(HERE, "results", "plots", "bias_point_check")

ap = argparse.ArgumentParser()
ap.add_argument("--det", type=int, default=7)
args = ap.parse_args()
det = args.det

series_list = sorted(os.path.basename(f)[:-4] for f in
                     glob.glob(os.path.join(RAW_CACHE, f"zip{det}_series", "*.pkl")))
print(f"{len(series_list)} cached series")


def read_cfg(series):
    fs = (sorted(glob.glob(os.path.join(PROC_DIR, f"{series}_Addison.root")))
          + sorted(glob.glob(os.path.join(PROC_DIR, f"UMN.Addison.*_{series}_F*.root"))))
    if not fs:
        return None
    cfg = uproot.open(fs[0])[f"detectorConfigDir/detectorConfigZip{det}"]
    out = {}
    for ch in ALL_CHANS:
        try:
            i0 = float(cfg[f"{ch}i0"].array(library="np")[0])
            r0 = float(cfg[f"{ch}r0"].array(library="np")[0])
            rl = (float(cfg[f"{ch}rp"].array(library="np")[0])
                  + float(cfg[f"{ch}rshunt"].array(library="np")[0]))
        except (KeyError, IndexError):
            continue
        if np.isfinite(i0) and i0 != 0 and r0 > 0:
            out[ch] = dict(i0=i0, r0=r0, rl=rl)
    return out


bias = {}
for s in series_list:
    b = read_cfg(s)
    if b:
        bias[s] = b
print(f"detectorConfig read for {len(bias)} series")
chans = [c for c in ALL_CHANS if all(c in b for b in bias.values())]
used = bias[series_list[0]]           # what kline_energy_hist.py applies everywhere

# ---- the events that enter the sum: parse the result text file
txt = os.path.join(RES_DIR, f"zip{det}_kline_energy_hist_allchan.txt")
per_event = {}
ch = None
for ln in open(txt):
    m = re.match(r"--- (\w+) ---", ln)
    if m:
        ch = m.group(1)
        continue
    if ch:
        p = ln.split()
        if len(p) >= 3 and p[1].isdigit():
            per_event.setdefault((p[0], int(p[1])), set()).add(ch)
chans = [c for c in chans if any(c in v for v in per_event.values())]   # channels with data
core = [c for c in chans if c != "PDS2"]
keys = [k for k, s in per_event.items() if all(c in s for c in core)]
n_series = {}
for s, _ in keys:
    n_series[s] = n_series.get(s, 0) + 1
print(f"{len(keys)} events enter the sum, from {len(n_series)} series")

# ---- figure: one panel per channel
ncol = 4
nrow = int(np.ceil(len(chans) / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 3.4 * nrow))
axes = axes.ravel()
lines = []
for ax, c in zip(axes, chans):
    vals = np.array([bias[s][c]["i0"] * 1e6 for s in series_list if s in bias])
    w = np.array([n_series.get(s, 0) for s in series_list if s in bias])
    v_used = used[c]["i0"] * 1e6
    lo, hi = vals.min(), vals.max()
    pad = max(0.02 * abs(v_used), 0.5 * (hi - lo) if hi > lo else 0.05)
    bins = np.linspace(lo - pad, hi + pad, 25)
    ax.hist(vals, bins=bins, weights=w, color="#1F3864", alpha=0.45,
            edgecolor="#1F3864", lw=1.2)
    ax.axvline(v_used, color="#C0392B", lw=1.8, ls=(0, (5, 3)))
    wm = np.average(vals, weights=w) if w.sum() else np.nan
    ws = np.sqrt(np.average((vals - wm) ** 2, weights=w)) if w.sum() else np.nan
    ax.set_title(f"{c}:  used {v_used:+.3f} µA;  series span {lo:+.3f} .. {hi:+.3f} µA",
                 fontsize=10.5)
    ax.set_xlabel("$I_0$ (µA)", fontsize=10)
    ax.set_ylabel("events in the sum", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.grid(alpha=0.25)
    lin = np.array([bias[s][c]["i0"] * (bias[s][c]["rl"] - bias[s][c]["r0"])
                    for s in series_list if s in bias])
    lin_used = used[c]["i0"] * (used[c]["rl"] - used[c]["r0"])
    lin_ratio = np.average(lin / lin_used, weights=w) if w.sum() else np.nan
    lines.append((c, v_used, lo, hi, vals.mean(), wm, ws,
                  100 * (hi - lo) / abs(v_used), lin_ratio,
                  100 * (lin.min() / lin_used - 1), 100 * (lin.max() / lin_used - 1)))
for ax in axes[len(chans):]:
    ax.set_axis_off()
fig.suptitle(f"Z{det}: TES bias current $I_0$ per channel, one value per series "
             f"({len(bias)} series), weighted by the {len(keys)} events in the "
             f"summed energy.\nRed dashed: the value used for every series "
             f"(detectorConfig of {series_list[0]}).", fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.95))
os.makedirs(OUT_DIR, exist_ok=True)
fn = os.path.join(OUT_DIR, f"zip{det}_I0_histogram.png")
fig.savefig(fn, dpi=150)
plt.close(fig)
print("saved", fn)

# ---- text summary
ft = fn.replace(".png", ".txt")
with open(ft, "w") as fh:
    fh.write(f"Z{det} TES bias current I0 per channel | detectorConfig of each of the "
             f"{len(bias)} cached series | histogram weighted by the {len(keys)} events "
             f"that enter the summed-energy distribution (all 10 core channels fitted)\n\n")
    fh.write("kline_energy_hist.py uses the detectorConfig of the first series "
             f"({series_list[0]}) for every series; 'used' is that value.\n\n")
    fh.write(f"{'chan':>6} {'used[uA]':>10} {'min[uA]':>10} {'max[uA]':>10} "
             f"{'mean[uA]':>10} {'ev-mean':>10} {'ev-std':>9} {'span/used':>10} "
             f"{'lin-coef ratio (ev-weighted mean, min, max vs used)':>50}\n")
    for c, vu, lo, hi, mn, wm, ws, sp, lr, lmin, lmax in lines:
        fh.write(f"{c:>6} {vu:>+10.3f} {lo:>+10.3f} {hi:>+10.3f} {mn:>+10.3f} "
                 f"{wm:>+10.3f} {ws:>9.3f} {sp:>9.2f}%   {lr:.4f}  ({lmin:+.1f}% .. {lmax:+.1f}%)\n")
    fh.write("\nlin-coef = I0(R_L-R0), the factor multiplying the energy; the ratio is series/first-series, "
             "averaged over the events in the sum. A ratio above 1 means the energies (and the "
             "efficiency) are underestimated by that factor when the first series' bias point is used everywhere.\n")
    fh.write("\nevents in the sum per series:\n")
    for s in series_list:
        fh.write(f"  {s}  {n_series.get(s, 0):>5}   "
                 + "  ".join(f"{c} {bias[s][c]['i0'] * 1e6:+.3f}" for c in chans[:3])
                 + "  ...\n" if s in bias else f"  {s}  (no detectorConfig)\n")
print("saved", ft)
