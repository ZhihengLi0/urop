#!/usr/bin/env python3
import argparse, os, pickle, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lp_fit_align import (add_pipeline_note, plot_path, ALL_CHANS,
    BASELINE_HI, BASELINE_LO, CACHE_DIR_DEFAULT, CKPT_DIR, RISE_REF_IDX,
    SAMPLERATE, TRACELENGTH, X_FULL, lowpass, two_exp_free_pt)
P = argparse.ArgumentParser()
P.add_argument("--det", type=int, required=True)
P.add_argument("--ref-chan", default="PDS2")
P.add_argument("--tfall-min", type=float, default=1.5e-3)
P.add_argument("--nrmse-max", type=float, default=0.4)
P.add_argument("--n-events", type=int, default=10)
P.add_argument("--seed", type=int, default=0)
P.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
A = P.parse_args()
det, REF, TF, NR = A.det, A.ref_chan, A.tfall_min, A.nrmse_max
sd = os.path.join(A.cache_dir, f"zip{det}_series")
pkls = sorted(f for f in os.listdir(sd) if f.endswith(".pkl"))
cand = []
for fn in pkls:
    ck = os.path.join(CKPT_DIR, f"zip{det}", fn[:-4] + "_fit.pkl")
    if not os.path.exists(ck): continue
    fits = pickle.load(open(ck, "rb"))["fits"]
    enum = pickle.load(open(os.path.join(sd, fn), "rb"))["event_numbers_ch"].get(REF, [])
    for i, fp in enumerate(fits.get(REF) or []):
        if fp and fp["fit_ok"] and fp["nrmse"] <= NR and fp["t_fall"] > TF and i < len(enum):
            cand.append((fn, int(enum[i]), fp["t_fall"]))
if not cand: raise SystemExit(f"zip{det} {REF}: none t_fall>{TF}")
print(f"{len(cand)} events t_fall>{TF*1e3:.1f}ms, sampling {A.n_events}", flush=True)
rng = np.random.default_rng(A.seed)
picked = [cand[i] for i in rng.choice(len(cand), min(A.n_events, len(cand)), replace=False)]
bs = {}
for fn, evn, tf in picked: bs.setdefault(fn, []).append((evn, tf))
events = []
for fn, evl in bs.items():
    pl = pickle.load(open(os.path.join(sd, fn), "rb"))
    fits = pickle.load(open(os.path.join(CKPT_DIR, f"zip{det}", fn[:-4] + "_fit.pkl"), "rb"))["fits"]
    im = {c: {int(e): i for i, e in enumerate(pl["event_numbers_ch"].get(c, []))} for c in ALL_CHANS}
    for evn, tf in evl:
        rows = {}
        for c in ALL_CHANS:
            i = im[c].get(evn)
            if i is None: continue
            lst = fits.get(c) or []
            rows[c] = (pl["raw_traces"][c][i], lst[i] if i < len(lst) else None)
        events.append((evn, fn[:-4], tf, rows))
events.sort(key=lambda e: -e[2])
lo, hi = RISE_REF_IDX - 500, min(TRACELENGTH, RISE_REF_IDX + 15000)
xw = X_FULL[lo:hi]; t_ms = xw / SAMPLERATE * 1e3
fig, axes = plt.subplots(len(events), len(ALL_CHANS), figsize=(2.6*len(ALL_CHANS), 1.9*len(events)), squeeze=False)
fig.suptitle(f"Zip{det} {len(events)} random events {REF} t_fall>{TF*1e3:.1f}ms: raw(gray) LP(blue) fit(red)", fontsize=13)
for r, (evn, series, tf, rows) in enumerate(events):
    for ci, c in enumerate(ALL_CHANS):
        ax = axes[r, ci]; ax.tick_params(labelsize=5); ax.grid(alpha=0.2)
        if r == 0: ax.set_title(c, fontsize=9)
        if ci == 0: ax.set_ylabel(f"ev {evn}\n{REF} tf={tf*1e3:.1f}ms", fontsize=7)
        if c not in rows:
            ax.text(0.5,0.5,"missing",transform=ax.transAxes,ha="center",va="center",fontsize=7,color="gray"); continue
        raw = np.asarray(rows[c][0], dtype=np.float64); fp = rows[c][1]
        if raw.size != TRACELENGTH: ax.axis("off"); continue
        ylp = lowpass(raw); base = float(np.median(ylp[BASELINE_LO:BASELINE_HI])); pk = float(np.max(ylp-base)) or 1.0
        ax.plot(t_ms, (raw-base)[lo:hi]/pk, lw=0.3, alpha=0.45, color="gray")
        ax.plot(t_ms, (ylp-base)[lo:hi]/pk, lw=0.4, color="steelblue")
        if fp is not None:
            m = two_exp_free_pt(xw, fp["amp"], fp["t_rise"], fp["t_fall"], fp["baseline"], fp["pretrigger"])
            ax.plot(t_ms, m, lw=0.9, color="crimson")
            tag = f"tf={fp['t_fall']*1e3:.1f}\nnr={fp['nrmse']:.2f}"
        else: tag = "no fit"
        ax.text(0.98,0.95,tag,transform=ax.transAxes,ha="right",va="top",fontsize=5.5,family="monospace",bbox=dict(facecolor="white",alpha=0.7,edgecolor="none"))
fig.tight_layout()
add_pipeline_note(fig, f"random {len(events)} events {REF} t_fall>{TF*1e3:.1f}ms (fit_ok NRMSE<={NR}); row=event col=channel; gray=raw blue=LP red=fit")
out = plot_path("slow_fall_events", f"zip{det}_{REF}_slow_fall.png")
fig.savefig(out, dpi=110, bbox_inches="tight")
print(f"Saved: {out}", flush=True)
