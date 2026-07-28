#!/usr/bin/env python3
"""Event grid for the fit_ok-rejected population.

Selection: an event qualifies when its fit on --chan (default PBS1)
converged but FAILED fit_ok (amp > 0 and t_rise < t_fall) — the events whose
fitted curves come out negative / with swapped time constants. The first
--n-events such events (storage order) are shown, one ROW per event x one
COLUMN per channel, each panel raw (gray) + 100 kHz LP (blue) + 2-exp fit
(red) with its NRMSE, so one can judge from the RAW traces what these events
actually are (expected: pulse-free traces with a downward baseline drift).

Each row is labeled with the event's PTOFamps (from the cache); the PBS1 and
PDS2 panels additionally show that channel's OFamps, read back from the
official Prompt processed file of the series.

Output: results/plots/fitok_rejected_events/zip{N}_fitok_rejected_events.png

Usage:
    python3 plot_fitok_rejected_grid.py --det 7 [--chan PBS1] [--n-events 15]
"""

import argparse
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
                          CACHE_DIR_DEFAULT, CKPT_DIR, RISE_REF_IDX,
                          SAMPLERATE, TRACELENGTH, X_FULL, lowpass,
                          two_exp_free_pt)

PROCESSED_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
                 "/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged")
AMP_CHANS = ("PBS1", "PDS2")

parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--chan", default="PBS1",
                    help="event qualifies if THIS channel's fit failed fit_ok")
parser.add_argument("--n-events", type=int, default=15)
parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
args = parser.parse_args()
det, SEL = args.det, args.chan

ckpt_dir = os.path.join(CKPT_DIR, f"zip{det}")
series_list = sorted(f[:-len("_fit.pkl")] for f in os.listdir(ckpt_dir)
                     if f.endswith("_fit.pkl"))
if not series_list:
    raise SystemExit(f"no fit checkpoints in {ckpt_dir}")

events = []           # (event_number, series, {chan: (raw,lp,fp)})
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

    # per-channel OF amplitudes from the official Prompt processed file
    proc = os.path.join(PROCESSED_DIR,
                        f"Prompt_V07-02_C0.4.5_{series}.root")
    ofamp_by_event = {c: {} for c in AMP_CHANS}
    if os.path.exists(proc):
        with uproot.open(proc) as h:
            evs = h["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
            for c in AMP_CHANS:
                vals = h[f"rqDir/zip{det}/{c}OFamps"].array(library="np")
                ofamp_by_event[c] = dict(zip(evs.tolist(), vals.tolist()))

    idx_by_chan = {c: {int(e): i for i, e in
                       enumerate(payload["event_numbers_ch"].get(c, []))}
                   for c in ALL_CHANS}
    for evn in payload.get("selected_event_numbers", []):
        if len(events) >= args.n_events:
            break
        evn = int(evn)
        i = idx_by_chan.get(SEL, {}).get(evn)
        if i is None or i >= len(fits.get(SEL) or []):
            continue
        fp_sel = fits[SEL][i]
        if fp_sel is None or fp_sel["fit_ok"]:
            continue
        # qualified: collect traces + per-channel OF amplitudes
        ptof = payload.get("selected_ptofamps", {}).get(evn)
        ofamp = {c: ofamp_by_event[c].get(evn) for c in AMP_CHANS}
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
            events.append((evn, series, ptof, ofamp, per_chan))
    del payload

if not events:
    raise SystemExit(f"zip{det}: no events failing fit_ok on {SEL}")

lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 4000
x = X_FULL[lo:hi]
t_ms = x / SAMPLERATE * 1e3
nrows, ncols = len(events), len(ALL_CHANS)
fig, axes = plt.subplots(nrows, ncols, figsize=(2.6 * ncols, 1.9 * nrows),
                         squeeze=False)
fig.suptitle(f"Zip{det} — fit_ok-rejected population ({SEL} fit failed "
             f"fit_ok), first {len(events)} events: "
             "raw (gray) vs LP (blue) vs 2-exp fit (red)", fontsize=13)
print(f"{'event':>8} {'PTOFamps':>12} {'PBS1OFamps':>12} {'PDS2OFamps':>12}")
for evn, series, ptof, ofamp, _ in events:
    def _f(v):
        return f"{v:.3e}" if v is not None else "n/a"
    print(f"{evn:>8} {_f(ptof):>12} {_f(ofamp.get('PBS1')):>12} "
          f"{_f(ofamp.get('PDS2')):>12}")

for row, (evn, series, ptof, ofamp, per_chan) in enumerate(events):
    for col, c in enumerate(ALL_CHANS):
        ax = axes[row, col]
        ax.tick_params(labelsize=5)
        ax.grid(alpha=0.2)
        if row == 0:
            ax.set_title(c, fontsize=9)
        if col == 0:
            ptxt = f"{ptof:.1e}" if ptof is not None else "n/a"
            ax.set_ylabel(f"ev {evn}\nPTOF={ptxt}", fontsize=6.5)
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
        if c in AMP_CHANS and ofamp.get(c) is not None:
            tag += f"\nOFamps={ofamp[c]:.2e}"
        ax.text(0.98, 0.95, tag, transform=ax.transAxes, ha="right", va="top",
                fontsize=5.5, family="monospace",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
fig.tight_layout()
add_pipeline_note(fig, f"fit_ok-rejected events: {SEL} fit converged but failed "
                  "fit_ok (amp>0 and t_rise<t_fall), i.e. the negative / "
                  f"swapped-tau fitted curves (first {len(events)} in storage "
                  "order); one ROW per event, one COLUMN per channel, gray = raw, "
                  "blue = 100kHz LP, red = free-pretrigger 2-exp fit; judge from "
                  "the raw traces what these events are")
out = plot_path("fitok_rejected_events", f"zip{det}_fitok_rejected_events.png")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(f"Saved: {out}  ({len(events)} events)")
