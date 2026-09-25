#!/usr/bin/env python3
"""Raw trace vs NxM reconstruction overlay, using the NxM amplitudes from the
UMN processing (Addison, 2026-07-08) of our delivered templates.

For each example event (K-line cache events that appear in the Addison
processed subfiles of --series): reconstruction = sum_k amp_k * nxm_k per
channel, with amp_k = PTOFnxm{CHAN}tem{k}amps and the templates read back
from the delivered NxM ROOT; shifted by PTOFnxmdelay. Overlaid on the raw
trace (gray) and its 100 kHz LP (blue), baseline-subtracted, in ADC units.

Output: results/plots/nxm_reco_overlay/zip{N}_nxm_reco_overlay.png

Usage:
    python3 plot_nxm_reco_overlay.py --det 7 --series 24260623_064608 [--n-events 3]
"""

import argparse
import glob
import os
import pickle
import sys

import numpy as np
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path,
                          ALL_CHANS, BASELINE_HI, BASELINE_LO,
                          CACHE_DIR_DEFAULT, RISE_REF_IDX, SAMPLERATE,
                          TRACELENGTH, X_FULL, lowpass)

ADDISON_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
               "/Processed/Default/Default_tag/Unmerged")

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--series", nargs="+", required=True)
parser.add_argument("--n-events", type=int, default=3)
parser.add_argument("--events", type=int, nargs="+", default=None,
                    help="only these event numbers (overrides --n-events)")
parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
args = parser.parse_args()
det = args.det

# delivered NxM templates (peak-normalized), read back with uproot
DELIV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "deliverables"))
tf = uproot.open(os.path.join(DELIV, "nxm", "root_files",
                              f"Templates_SNOLAB_R4_zip{det}_nxm_pca.root"))
templates = {}
for c in ALL_CHANS:
    try:
        templates[c] = [tf[f"nxm{k}_zip{det}_{c}"].values() for k in range(5)]
    except uproot.KeyInFileError:
        pass
print(f"templates: {len(templates)} channels")

# delivered 1x1 templates (NRMSE-weighted 2-exp mean, peak-normalized)
tf1 = uproot.open(os.path.join(DELIV, "1x1", "root_files",
                               f"Templates_SNOLAB_R4_zip{det}_2expfit_weighted.root"))
onexone = {}
for c in ALL_CHANS:
    try:
        onexone[c] = tf1[f"t2exp_zip{det}_{c}"].values()
    except uproot.KeyInFileError:
        pass

examples = []          # (series, evn, {chan: amps[5]}, delay_s)
caches = {}
idx_by_series = {}

def _load_series(series):
    cache = pickle.load(open(os.path.join(args.cache_dir, f"zip{det}_series",
                                          f"{series}.pkl"), "rb"))
    caches[series] = cache
    idx_by_series[series] = {c: {int(e): i for i, e in
                                 enumerate(cache["event_numbers_ch"].get(c, []))}
                             for c in ALL_CHANS}
    return cache

for series in args.series:
  if args.events is None and len(examples) >= args.n_events:
      break
  cache = _load_series(series)
  sel = set(int(e) for e in cache["selected_event_numbers"])
  idx_by_chan = idx_by_series[series]
  paths = (sorted(glob.glob(os.path.join(ADDISON_DIR, f"{series}_Addison.root")))
           + sorted(glob.glob(os.path.join(ADDISON_DIR,
                                           f"UMN.Addison.*_{series}_F*.root"))))
  for path in paths:
      if args.events is None and len(examples) >= args.n_events:
          break
      h = uproot.open(path)
      if "rqDir" not in h:
          continue
      evs = h["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
      hits = [(j, int(e)) for j, e in enumerate(evs) if int(e) in sel]
      if not hits:
          continue
      z = h[f"rqDir/zip{det}"]
      amps = {c: np.stack([z[f"PTOFnxm{c}tem{k}amps"].array(library="np")
                           for k in range(5)], axis=1)
              for c in templates}
      delay = z["PTOFnxmdelay"].array(library="np")
      taken = 0
      for j, evn in hits:
          if args.events is not None and evn not in args.events:
              continue
          if args.events is None and len(examples) >= args.n_events:
              break
          if any(evn == e[1] for e in examples):
              continue                        # already taken from another file
          ev_amps = {c: amps[c][j] for c in templates}
          if all(a[0] == -999999 for a in ev_amps.values()):
              continue                        # NxM not computed for this event
          d = float(delay[j])
          if d < -1000:                       # -999999 sentinel: delay not filled
              d = 0.0
          i = idx_by_chan.get("PBS1", {}).get(evn)
          if i is not None:
              tr = np.asarray(cache["raw_traces"]["PBS1"][i], dtype=np.float64)
              if tr.size == TRACELENGTH:
                  y = lowpass(tr)
                  pk = int(np.argmax(y - np.median(y[BASELINE_LO:BASELINE_HI])))
                  if abs(pk - RISE_REF_IDX) > 3000:
                      continue                # late/odd pulse, skip as example
          examples.append((series, evn, ev_amps, d))
          taken += 1
      print(f"  {os.path.basename(path)}: took {taken} event(s)")
if not examples:
    raise SystemExit("no overlapping events found")

lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 4000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
nrows, ncols = len(examples), len(ALL_CHANS)
fig, axes = plt.subplots(nrows, ncols, figsize=(2.6 * ncols, 1.9 * nrows),
                         squeeze=False)
fig.suptitle(f"Zip{det} — raw (gray) / LP (blue) vs NxM reconstruction "
             "Σ ampₖ·nxmₖ (red) and the delivered 1x1 template (green "
             "dashed); amplitudes from the UMN (Addison) processing",
             fontsize=13)
for row, (series, evn, amps, delay_s) in enumerate(examples):
    idx_by_chan = idx_by_series[series]
    cache = caches[series]
    shift = delay_s * SAMPLERATE
    for col, c in enumerate(ALL_CHANS):
        ax = axes[row, col]
        ax.tick_params(labelsize=5)
        ax.grid(alpha=0.2)
        if row == 0:
            ax.set_title(c, fontsize=9)
        if col == 0:
            ax.set_ylabel(f"ev {evn}\n{series}", fontsize=6)
        i = idx_by_chan.get(c, {}).get(evn)
        if i is None or c not in templates:
            ax.text(0.5, 0.5, "missing", transform=ax.transAxes,
                    ha="center", va="center", fontsize=7, color="gray")
            continue
        tr = np.asarray(cache["raw_traces"][c][i], dtype=np.float64)
        if tr.size != TRACELENGTH:
            ax.text(0.5, 0.5, "missing", transform=ax.transAxes,
                    ha="center", va="center", fontsize=7, color="gray")
            continue
        y_lp = lowpass(tr)
        base = float(np.median(y_lp[BASELINE_LO:BASELINE_HI]))
        reco = np.zeros(TRACELENGTH)
        for k in range(5):
            reco += amps[c][k] * templates[c][k]
        # PTOFnxmdelay is not filled by this processing (sentinel), so align
        # the reconstruction at the pulse peak for the shape comparison
        dpk = int(np.argmax((y_lp - base)[lo:hi])) - int(np.argmax(reco[lo:hi]))
        reco_sh = np.interp(X_FULL - shift - dpk, X_FULL, reco,
                            left=0.0, right=0.0)
        pk_lp = float(np.max((y_lp - base)[lo:hi]))
        pk_rc = float(np.max(reco_sh[lo:hi]))
        if pk_lp <= 0 or pk_rc <= 0:
            ax.text(0.5, 0.5, "no pulse", transform=ax.transAxes,
                    ha="center", va="center", fontsize=7, color="gray")
            continue
        # amps are physical units (A), trace is ADC: compare SHAPES, each
        # normalized to its own peak
        ax.plot(t_ms, (tr - base)[lo:hi] / pk_lp, lw=0.3, alpha=0.45, color="gray")
        ax.plot(t_ms, (y_lp - base)[lo:hi] / pk_lp, lw=0.4, color="steelblue")
        ax.plot(t_ms, reco_sh[lo:hi] / pk_rc, lw=0.9, color="crimson")
        if c in onexone:
            t1 = onexone[c]
            d1 = int(np.argmax((y_lp - base)[lo:hi])) - int(np.argmax(t1[lo:hi]))
            t1s = np.interp(X_FULL - d1, X_FULL, t1, left=0.0, right=0.0)
            pk1 = float(np.max(t1s[lo:hi]))
            if pk1 > 0:
                ax.plot(t_ms, t1s[lo:hi] / pk1, lw=0.8, ls=(0, (4, 2)),
                        color="darkgreen", alpha=0.9)
        atxt = "\n".join(f"a{k}={amps[c][k]:.1e}" for k in range(5))
        ax.text(0.98, 0.95, atxt, transform=ax.transAxes,
                ha="right", va="top", fontsize=4.6, family="monospace",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
fig.tight_layout()
add_pipeline_note(fig, "NxM reconstruction check on real events: raw MIDAS trace "
                  "(gray), 100kHz LP (blue), and sum_k PTOFnxm{chan}tem{k}amps x "
                  "nxm_k (red, delivered peak-normalized templates) and the delivered 1x1 "
                  "template (green dashed, peak-aligned); amplitudes from the "
                  "UMN (Addison) Default_tag processing are in physical units, "
                  "so each side is normalized to its own peak and the reconstruction is "
                  "aligned at the pulse peak (PTOFnxmdelay not filled, sentinel); "
                  "baseline = median LP samples 2000-12000")
suffix = ("_ev" + "_".join(str(e) for e in args.events)) if args.events else ""
out = plot_path("nxm_reco_overlay", f"zip{det}_nxm_reco_overlay{suffix}.png")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(f"Saved: {out}  ({len(examples)} events)")
