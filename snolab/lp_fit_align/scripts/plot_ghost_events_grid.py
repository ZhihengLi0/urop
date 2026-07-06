#!/usr/bin/env python3
"""Event grid for the GHOST population of aligned_overlay — genuinely slow,
well-fit events.

Selection: an event qualifies when the MEDIAN NRMSE across its fit_ok
channels is BELOW --nrmse-max (good fits) AND the MEDIAN t_rise exceeds
--trise-min (slow rise). These are the events that form the faint displaced
"ghost" bundle in the aligned_overlay figures: onset aligned at 16050 but
peaking later because of the slow rise. The first --n-events such events
(storage order) are shown, one ROW per event x one COLUMN per channel, each
panel raw (gray) + 100 kHz LP (blue) + 2-exp fit (red) with its NRMSE.

Output: results/plots/ghost_events/zip{N}_ghost_events.png

Usage:
    python3 plot_ghost_events_grid.py --det 7 [--nrmse-max 0.4] [--trise-min 2e-4]
"""

import argparse
import os
import pickle
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path,
                          ALL_CHANS, BASELINE_HI, BASELINE_LO,
                          CACHE_DIR_DEFAULT, CKPT_DIR, RISE_REF_IDX,
                          SAMPLERATE, TRACELENGTH, X_FULL, lowpass,
                          two_exp_free_pt)

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--nrmse-max", type=float, default=0.4,
                    help="event qualifies if median NRMSE over its fit_ok "
                         "channels is below this (good fits)")
parser.add_argument("--trise-min", type=float, default=2e-4,
                    help="event qualifies if median t_rise (s) over its "
                         "fit_ok channels exceeds this (slow rise)")
parser.add_argument("--n-events", type=int, default=15)
parser.add_argument("--min-channels", type=int, default=4,
                    help="require at least this many fit_ok channels")
parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
args = parser.parse_args()
det, CUT, TRISE = args.det, args.nrmse_max, args.trise_min

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
series_list = sorted(f[:-len("_fit.pkl")] for f in os.listdir(ckpt_dir)
                     if f.endswith("_fit.pkl"))
if not series_list:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

events = []           # (event_number, series, med_nrmse, {chan: (raw,lp,fp)})
for series in series_list:
    if len(events) >= args.n_events:
        break
    raw_path = os.path.join(args.cache_dir, f"zip{det}_series", f"{series}.pkl")
    if not os.path.exists(raw_path):
        continue
    with open(os.path.join(ckpt_dir, f"{series}_fit.pkl"), "rb") as fh:
        fits = pickle.load(fh)["fits"]
    with open(raw_path, "rb") as fh:
        payload = pickle.load(fh)

    idx_by_chan = {c: {int(e): i for i, e in
                       enumerate(payload["event_numbers_ch"].get(c, []))}
                   for c in ALL_CHANS}
    for evn in payload.get("selected_event_numbers", []):
        if len(events) >= args.n_events:
            break
        evn = int(evn)
        # event-level criterion first (cheap, fits only)
        nrmses, trises = [], []
        for c in ALL_CHANS:
            i = idx_by_chan[c].get(evn)
            if i is None or i >= len(fits.get(c) or []):
                continue
            fp = fits[c][i]
            if fp is not None and fp["fit_ok"]:
                nrmses.append(fp["nrmse"])
                trises.append(fp["t_rise"])
        if (len(nrmses) < args.min_channels
                or np.median(nrmses) > CUT
                or np.median(trises) <= TRISE):
            continue
        # qualified: collect traces for all channels
        per_chan = {}
        for c in ALL_CHANS:
            i = idx_by_chan[c].get(evn)
            if i is None:
                continue
            tr = np.asarray(payload["raw_traces"][c][i], dtype=np.float64)
            if tr.size != TRACELENGTH:
                continue
            y_lp = lowpass(tr)
            baseline = float(np.median(y_lp[BASELINE_LO:BASELINE_HI]))
            peak = float(np.max(y_lp - baseline))
            if not np.isfinite(peak) or peak <= 0:
                continue
            fp = fits[c][i] if i < len(fits.get(c) or []) else None
            per_chan[c] = ((tr - baseline) / peak, (y_lp - baseline) / peak, fp)
        if per_chan:
            events.append((evn, series, float(np.median(nrmses)), per_chan))
    del payload

if not events:
    raise SystemExit(f"zip{det}: no events with median NRMSE <= {CUT} "
                     f"and median t_rise > {TRISE}")

lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 4000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
nrows, ncols = len(events), len(ALL_CHANS)
fig, axes = plt.subplots(nrows, ncols, figsize=(2.6 * ncols, 1.9 * nrows),
                         squeeze=False)
fig.suptitle(f"Zip{det} — ghost population (well-fit slow-rise events), first "
             f"{len(events)} events with median NRMSE <= {CUT} and median "
             f"t_rise > {TRISE*1e3:.2f} ms: raw (gray) vs LP (blue) vs "
             "2-exp fit (red)", fontsize=13)
for row, (evn, series, med, per_chan) in enumerate(events):
    for col, c in enumerate(ALL_CHANS):
        ax = axes[row, col]
        ax.tick_params(labelsize=5)
        ax.grid(alpha=0.2)
        if row == 0:
            ax.set_title(c, fontsize=9)
        if col == 0:
            ax.set_ylabel(f"ev {evn}\nmed={med:.2f}", fontsize=7)
        if c not in per_chan:
            ax.text(0.5, 0.5, "missing", transform=ax.transAxes,
                    ha="center", va="center", fontsize=7, color="gray")
            continue
        raw_norm, lp_norm, fp = per_chan[c]
        ax.plot(t_ms, raw_norm[lo:hi], lw=0.3, alpha=0.45, color="gray")
        ax.plot(t_ms, lp_norm[lo:hi], lw=0.4, color="steelblue")
        if fp is not None:
            model = two_exp_free_pt(x, fp["amp"], fp["t_rise"], fp["t_fall"],
                                    fp["baseline"], fp["pretrigger"])
            ax.plot(t_ms, model, lw=0.9, color="crimson")
            tag = f"nrmse={fp['nrmse']:.2f}" + ("" if fp["fit_ok"] else " (!ok)")
        else:
            tag = "fit failed"
        ax.text(0.98, 0.95, tag, transform=ax.transAxes, ha="right", va="top",
                fontsize=5.5, family="monospace",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
fig.tight_layout()
add_pipeline_note(fig, "GHOST population of aligned_overlay = genuinely slow, WELL-FIT "
                  f"events: median NRMSE across fit_ok channels <= {CUT} AND median "
                  f"t_rise > {TRISE*1e3:.2f} ms (first {len(events)} in storage order); "
                  "onset aligns at 16050 but the peak comes later, producing the faint "
                  "displaced bundle in aligned_overlay; one ROW per event, one COLUMN "
                  "per channel, gray = raw, blue = 100kHz LP, red = 2-exp fit")
out = plot_path("ghost_events", f"zip{det}_ghost_events.png")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(f"Saved: {out}  ({len(events)} events)")
