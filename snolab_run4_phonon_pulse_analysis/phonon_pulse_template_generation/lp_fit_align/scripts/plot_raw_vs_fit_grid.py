#!/usr/bin/env python3
"""Raw-vs-fit examples as an event grid: the SAME first 15 selected events as
plot_event_fit_grid.py (identical selection logic, so event numbers match the
fit_examples figures), one ROW per event x one COLUMN per channel.

Each panel shows three layers:
  gray = raw unfiltered trace, blue = 100 kHz LP trace, red = free-pretrigger
  2-exp fit; top-right = NRMSE.

Overwrites results/plots/raw_vs_fit_examples/zip{N}_raw_vs_fit_examples.png.

Usage:
    python3 plot_raw_vs_fit_grid.py --det 7 [--n-events 15]
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
parser.add_argument("--n-events", type=int, default=15)
parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
args = parser.parse_args()
det = args.det

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
series_list = sorted(f[:-len("_fit.pkl")] for f in os.listdir(ckpt_dir)
                     if f.endswith("_fit.pkl"))
if not series_list:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

# ── same event selection as plot_event_fit_grid.py ────────────────────────────
events = []           # (event_number, series, {chan: (raw_norm, lp_norm, fp)})
for series in series_list:
    if len(events) >= args.n_events:
        break
    raw_path = os.path.join(args.cache_dir, f"zip{det}_series", f"{series}.pkl")
    if not os.path.exists(raw_path):
        continue
    with open(raw_path, "rb") as fh:
        payload = pickle.load(fh)
    with open(os.path.join(ckpt_dir, f"{series}_fit.pkl"), "rb") as fh:
        fits = pickle.load(fh)["fits"]

    idx_by_chan = {c: {int(e): i for i, e in
                       enumerate(payload["event_numbers_ch"].get(c, []))}
                   for c in ALL_CHANS}
    for evn in payload.get("selected_event_numbers", []):
        if len(events) >= args.n_events:
            break
        evn = int(evn)
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
            fp = (fits.get(c) or [None] * (i + 1))[i] \
                if i < len(fits.get(c) or []) else None
            per_chan[c] = ((tr - baseline) / peak, (y_lp - baseline) / peak, fp)
        if per_chan:
            events.append((evn, series, per_chan))
    del payload

if not events:
    raise SystemExit(f"zip{det}: no events found")

# ── grid figure ───────────────────────────────────────────────────────────────
lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 4000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
nrows, ncols = len(events), len(ALL_CHANS)
fig, axes = plt.subplots(nrows, ncols, figsize=(2.6 * ncols, 1.9 * nrows),
                         squeeze=False)
fig.suptitle(f"Zip{det} — first {len(events)} selected events x all channels: "
             "raw (gray) vs 100kHz LP (blue) vs 2-exp fit (red)", fontsize=13)
for row, (evn, series, per_chan) in enumerate(events):
    for col, c in enumerate(ALL_CHANS):
        ax = axes[row, col]
        ax.tick_params(labelsize=5)
        ax.grid(alpha=0.2)
        if row == 0:
            ax.set_title(c, fontsize=9)
        if col == 0:
            ax.set_ylabel(f"ev {evn}\n{series[-6:]}", fontsize=7)
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
add_pipeline_note(fig, "event-organized raw-vs-fit examples: one ROW per event "
                  f"(first {len(events)} selected events, storage order — the SAME "
                  "events as the fit_examples grid), one COLUMN per channel; "
                  "gray = raw unfiltered trace, blue = 100kHz LP trace, red = "
                  "free-pretrigger 2-exp fit; top-right of each panel = NRMSE "
                  "('!ok' = failed fit_ok physicality check)")
out = plot_path("raw_vs_fit_examples", f"zip{det}_raw_vs_fit_examples.png")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(f"Saved: {out}")
