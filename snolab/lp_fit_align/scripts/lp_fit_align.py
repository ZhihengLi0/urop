#!/usr/bin/env python3
"""Low-pass + free-pretrigger fit + shift-align pipeline on the raw PTOF cache.

Input : raw_ptof_selected_event_v1 pkl cache written by
        raw_without_filter/scripts/read_ptof_selected_events.py
        (raw MIDAS traces, PTOFamps selection only, no processing).

Per trace:
  1. 100 kHz order-4 Butterworth low-pass (teacher's butter_lowpass_filter,
     NxM_cedar.ipynb cell 3, cutoff moved from 20 kHz to 100 kHz per teacher).
  2. Baseline = median of the early pretrigger region, subtracted.
  3. Normalize by the GLOBAL peak of the trace (no peak-window restriction).
  4. Free-pretrigger 2-exp fit (5 free params, teacher's two_exp_fit).
     fit_ok = converged AND amp > 0 AND 0 < t_rise < t_fall.
     NRMSE  = rms(fit residual over fit window) / fitted pulse peak.
     NRMSE is RECORDED ONLY — no cut at this stage (teacher 2026-07-02).
  5. Align = shift the measured low-passed trace itself by
     (fitted_pretrigger - 16050) so the rise lands on the fixed reference.
     No analytic regeneration (teacher's correction 2026-07-01).

Outputs (local repo):
  lp_fit_align/results/plots/zip{N}_*.png
  lp_fit_align/results/stats/zip{N}_lp_fit_summary.json
  lp_fit_align/run/checkpoints/zip{N}/{series}_fit.pkl  (fit params only, small)

Usage:
  python3 lp_fit_align.py --det 1
  python3 lp_fit_align.py --det 1 --series 24260617_063934 --max-per-channel 5
"""

import argparse
import datetime
import json
import multiprocessing as mp
import os
import pickle
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt, sosfilt_zi

SAMPLERATE = 625000.0
TRACELENGTH = 32768
RISE_REF_IDX = 16050            # fixed alignment reference (teacher: 16050)
PRETRIGGER_FREEDOM = 3000       # fit bounds: RISE_REF_IDX +/- this
BASELINE_LO, BASELINE_HI = 2000, 12000   # early region, clear of pulse and filter warm-up
FIT_LO = RISE_REF_IDX - PRETRIGGER_FREEDOM - 500
FIT_HI = RISE_REF_IDX + 8000
FIT_STRIDE = 4
LP_CUTOFF_KHZ = 100.0
MAX_OVERLAY = 200               # traces kept per channel for the overlay plot
N_FIT_EXAMPLES = 3

CACHE_DIR_DEFAULT = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
                     "/raw_without_filter/run/cache")

ALL_CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
             "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLOT_DIR = os.path.join(BASE_DIR, "results", "plots")
STATS_DIR = os.path.join(BASE_DIR, "results", "stats")
CKPT_DIR = os.path.join(BASE_DIR, "run", "checkpoints")


PIPELINE_NOTE = (
    "processing: raw MIDAS trace -> 100 kHz 4th-order Butterworth low-pass (scipy sosfilt, steady-state init)\n"
    "  -> baseline subtract (median of samples 2000-12000) -> normalize by GLOBAL trace peak (no peak window)\n"
    "  -> 2-exp fit y = A(exp(-t/t_fall) - exp(-t/t_rise)), ALL 5 params free incl. pretrigger"
    " (curve_fit, pretrigger in 16050+-3000, maxfev=10000)\n"
    "  -> fit_ok := amp>0 and 0<t_rise<t_fall -> NRMSE := RMS(fit residual)/fitted pulse peak,"
    " RECORDED ONLY (no cut)\n"
    "  -> align := shift the MEASURED LP trace by (fitted pretrigger - 16050), sub-sample np.interp"
)


def add_pipeline_note(fig, what):
    """Reserve a band at the top of the figure and stamp the full processing
    chain + a description of what this figure shows. Must be called AFTER the
    plotting code's own tight_layout(); it re-runs tight_layout with a rect
    that keeps the band clear (text above y=1 would be clipped by Agg)."""
    import textwrap
    h = float(fig.get_size_inches()[1])
    pad_in = 1.1
    top = max(0.5, 1.0 - pad_in / h)
    fig.tight_layout(rect=[0, 0, 1, top])
    what_wrapped = "\n".join(textwrap.wrap("this figure: " + what, width=130,
                                           subsequent_indent="  "))
    fig.text(0.01, 0.9992, PIPELINE_NOTE + "\n" + what_wrapped,
             ha="left", va="top", fontsize=6.5, color="dimgray",
             family="monospace")
    if fig._suptitle is not None:
        fig._suptitle.set_y(top + 0.35 * (1.0 - top))


X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
X_FIT = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]

_SOS = butter(4, (LP_CUTOFF_KHZ * 1000.0) / (0.5 * SAMPLERATE),
              btype="low", output="sos")
_SOS_ZI = sosfilt_zi(_SOS)


def lowpass(trace):
    # steady-state initial conditions: without this the filter rings for the
    # first ~10 samples (trace starts at ~24000 ADC, filter state at 0) and
    # that transient would be picked up as the global peak
    y = np.asarray(trace, dtype=np.float64)
    out, _ = sosfilt(_SOS, y, zi=_SOS_ZI * y[0])
    return out


def two_exp_free_pt(x, amp, t_rise, t_fall, baseline, pretrigger):
    """Teacher's two_exp_fit (NxM_cedar.ipynb cell 5): all 5 params free."""
    dt = (x - pretrigger) / SAMPLERATE
    with np.errstate(over="ignore", invalid="ignore"):
        pulse = -(amp * np.exp(-np.clip(dt, 0.0, None) / t_rise)
                  - amp * np.exp(-np.clip(dt, 0.0, None) / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def normalize_trace(trace):
    """LP filter, subtract early-region median baseline, divide by global peak."""
    trace = np.asarray(trace)
    if trace.size != TRACELENGTH:
        return None
    y_lp = lowpass(trace)
    baseline = float(np.median(y_lp[BASELINE_LO:BASELINE_HI]))
    y = y_lp - baseline
    peak = float(np.max(y))          # global max, no window restriction
    if not np.isfinite(peak) or peak <= 0:
        return None
    return (y / peak).astype(np.float64)


def fit_trace(y_norm):
    """Free-pretrigger 2-exp fit on the normalized LP trace."""
    y_fit = y_norm[FIT_LO:FIT_HI:FIT_STRIDE]
    p0 = [1.0, 2e-4, 1e-3, 0.0, float(RISE_REF_IDX)]
    bounds = ([0.0, 1e-6, 1e-5, -0.5, RISE_REF_IDX - PRETRIGGER_FREEDOM],
              [10.0, 5e-3, 2e-2, 0.5, RISE_REF_IDX + PRETRIGGER_FREEDOM])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(two_exp_free_pt, X_FIT, y_fit,
                                p0=p0, bounds=bounds, maxfev=10000)
    except Exception:
        return None
    amp, t_rise, t_fall, baseline, pretrigger = (float(v) for v in popt)
    model = two_exp_free_pt(X_FIT, *popt)
    resid = y_fit - model
    pulse_peak = float(np.max(model) - baseline)
    if pulse_peak <= 0:
        pulse_peak = 1.0
    nrmse = float(np.sqrt(np.mean(resid ** 2)) / pulse_peak)
    fit_ok = bool(amp > 0 and 0 < t_rise < t_fall and np.isfinite(nrmse))
    return {"amp": amp, "t_rise": t_rise, "t_fall": t_fall,
            "baseline": baseline, "pretrigger": pretrigger,
            "nrmse": nrmse, "fit_ok": fit_ok}


def shift_align(y_norm, fitted_pretrigger):
    """Shift the measured LP trace so its fitted rise lands on RISE_REF_IDX."""
    shift = fitted_pretrigger - RISE_REF_IDX
    return np.interp(X_FULL + shift, X_FULL, y_norm, left=0.0, right=0.0)


def process_channel(task):
    """Worker: LP + fit + shift every trace of one channel of one series.

    Returns a partial per-channel collector; merged by the parent. Fitting is
    the bottleneck (noise-dominated traces often run to maxfev), so series are
    parallelized channel-wise across a process pool.
    """
    series, chan, traces, events, prior_fits, n_overlay_slots, n_example_slots = task
    out = {"chan": chan, "fits_raw": [], "fits": [], "overlay": [],
           "examples": [], "mean_sum": np.zeros(TRACELENGTH), "mean_n": 0}
    for i, trace in enumerate(traces):
        y_norm = normalize_trace(trace)
        if y_norm is None:
            out["fits_raw"].append(None)
            continue

        if prior_fits is not None and i < len(prior_fits):
            fp = prior_fits[i]
        else:
            fp = fit_trace(y_norm)
        out["fits_raw"].append(fp)
        if fp is None:
            continue

        fp = dict(fp)
        fp["event_number"] = int(events[i]) if i < len(events) else -1
        fp["series"] = series
        out["fits"].append(fp)
        if fp["fit_ok"]:
            shifted = shift_align(y_norm, fp["pretrigger"])
            out["mean_sum"] += shifted
            out["mean_n"] += 1
            if len(out["overlay"]) < n_overlay_slots:
                out["overlay"].append(shifted.astype(np.float32))
            if len(out["examples"]) < n_example_slots:
                out["examples"].append(
                    (y_norm[FIT_LO:FIT_HI].astype(np.float32), dict(fp)))
    return out


def process_series(det, series, pkl_path, ckpt_path, collector,
                   max_per_channel, pool):
    """Fit every trace of one series (or reuse checkpointed fits) and feed the
    per-channel collector with fit params and shifted traces."""
    fits = None
    if os.path.exists(ckpt_path):
        try:
            with open(ckpt_path, "rb") as fh:
                fits = pickle.load(fh)["fits"]
            print(f"  {series}: checkpoint found, reusing fits", flush=True)
        except Exception:
            fits = None

    with open(pkl_path, "rb") as fh:
        payload = pickle.load(fh)
    raw_traces = payload.get("raw_traces", {})
    event_numbers_ch = payload.get("event_numbers_ch", {})

    tasks = []
    for c in ALL_CHANS:
        traces = raw_traces.get(c, [])
        events = event_numbers_ch.get(c, [])
        if max_per_channel is not None:
            traces = traces[:max_per_channel]
        col = collector[c]
        tasks.append((series, c, traces, events,
                      None if fits is None else fits.get(c),
                      max(0, MAX_OVERLAY - len(col["overlay"])),
                      max(0, N_FIT_EXAMPLES - len(col["examples"]))))

    results = pool.map(process_channel, tasks) if pool else \
        [process_channel(t) for t in tasks]

    new_fits = {}
    for res in results:
        c = res["chan"]
        new_fits[c] = res["fits_raw"]
        col = collector[c]
        col["fits"].extend(res["fits"])
        col["mean_sum"] += res["mean_sum"]
        col["mean_n"] += res["mean_n"]
        col["overlay"].extend(res["overlay"])
        col["examples"].extend(res["examples"])
    n_ok = sum(1 for res in results for f in res["fits"] if f["fit_ok"])
    n_all = sum(len(res["fits_raw"]) for res in results)
    print(f"  {series}: {n_all} traces, {n_ok} fit_ok", flush=True)

    if fits is None and max_per_channel is None:
        tmp = ckpt_path + ".tmp"
        with open(tmp, "wb") as fh:
            pickle.dump({"det": det, "series": series, "fits": new_fits,
                         "created_at": datetime.datetime.now().isoformat()}, fh,
                        protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, ckpt_path)


# ── Plotting ──────────────────────────────────────────────────────────────────

def active_channels(collector):
    return [c for c in ALL_CHANS if collector[c]["mean_n"] > 0]


def plot_aligned_overlay(det, collector):
    chans = active_channels(collector)
    if not chans:
        return
    t_ms = X_FULL / SAMPLERATE * 1e3
    lo, hi = RISE_REF_IDX - 500, RISE_REF_IDX + 8000
    zlo, zhi = RISE_REF_IDX - 100, RISE_REF_IDX + 2000
    fig, axes = plt.subplots(len(chans), 2, figsize=(14, 3.5 * len(chans)),
                             squeeze=False)
    fig.suptitle(f"Zip{det} — 100kHz LP, shift-aligned measured traces "
                 f"(fit_ok only, no NRMSE cut)", fontsize=10)
    for row, c in enumerate(chans):
        col = collector[c]
        mean_tr = col["mean_sum"] / col["mean_n"]
        for ax, a, b in [(axes[row, 0], lo, hi), (axes[row, 1], zlo, zhi)]:
            for tr in col["overlay"]:
                ax.plot(t_ms[a:b], tr[a:b], lw=0.4, alpha=0.15, color="steelblue")
            ax.plot(t_ms[a:b], mean_tr[a:b], lw=1.5, color="crimson",
                    label=f"mean (n={col['mean_n']})")
            ax.axvline(t_ms[RISE_REF_IDX], color="k", lw=0.8, ls=":")
            ax.legend(fontsize=7)
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.2)
            ax.set_xlabel("Time (ms)", fontsize=7)
        axes[row, 0].set_title(f"{c}  (showing {len(col['overlay'])} of "
                               f"{col['mean_n']} fit_ok)", fontsize=8)
        axes[row, 1].set_title(f"{c} zoom", fontsize=8)
        axes[row, 0].set_ylabel("Norm. amp.", fontsize=7)
    fig.tight_layout()
    add_pipeline_note(fig, "shift-aligned MEASURED low-pass traces (blue, up to "
                      f"{MAX_OVERLAY}/channel) + mean of ALL fit_ok events (red); "
                      "dotted line = alignment reference 16050; fit_ok only, no NRMSE cut")
    out = os.path.join(PLOT_DIR, f"zip{det}_lp_aligned_overlay.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def plot_fit_examples(det, collector):
    chans = [c for c in ALL_CHANS if collector[c]["examples"]]
    if not chans:
        return
    t_ms = X_FULL[FIT_LO:FIT_HI] / SAMPLERATE * 1e3
    fig, axes = plt.subplots(len(chans), N_FIT_EXAMPLES,
                             figsize=(5 * N_FIT_EXAMPLES, 2.8 * len(chans)),
                             squeeze=False)
    fig.suptitle(f"Zip{det} — LP trace (blue) vs free-pretrigger 2-exp fit (red)",
                 fontsize=10)
    for row, c in enumerate(chans):
        for k in range(N_FIT_EXAMPLES):
            ax = axes[row, k]
            if k >= len(collector[c]["examples"]):
                ax.axis("off")
                continue
            seg, fp = collector[c]["examples"][k]
            model = two_exp_free_pt(
                X_FULL[FIT_LO:FIT_HI], fp["amp"], fp["t_rise"], fp["t_fall"],
                fp["baseline"], fp["pretrigger"])
            ax.plot(t_ms, seg, lw=0.7, color="steelblue", label="LP trace")
            ax.plot(t_ms, model, lw=1.0, color="crimson", label="fit")
            ax.set_title(f"{c} ev{fp['event_number']}  nrmse={fp['nrmse']:.3f}  "
                         f"pt={fp['pretrigger']:.0f}", fontsize=7)
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.2)
            if row == 0 and k == 0:
                ax.legend(fontsize=7)
    fig.tight_layout()
    add_pipeline_note(fig, "LP trace (blue) vs fitted 2-exp curve (red), first "
                      f"{N_FIT_EXAMPLES} fit_ok events per channel; examples NOT "
                      "quality-selected - shows honestly what fit_ok alone lets through")
    out = os.path.join(PLOT_DIR, f"zip{det}_fit_examples.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def plot_histograms(det, collector):
    chans = [c for c in ALL_CHANS if collector[c]["fits"]]
    if not chans:
        return

    specs = [
        ("pretrigger", lambda f: f["pretrigger"], "fitted pretrigger (samples)",
         f"zip{det}_pretrigger.png"),
        ("nrmse", lambda f: f["nrmse"], "NRMSE",
         f"zip{det}_nrmse.png"),
    ]
    for name, getter, xlabel, fname in specs:
        fig, axes = plt.subplots(len(chans), 1, figsize=(8, 2.2 * len(chans)),
                                 squeeze=False)
        fig.suptitle(f"Zip{det} — {name} distribution (fit_ok events)", fontsize=10)
        for row, c in enumerate(chans):
            vals = np.array([getter(f) for f in collector[c]["fits"] if f["fit_ok"]])
            ax = axes[row, 0]
            if len(vals):
                if name == "nrmse":
                    # log-spaced bins: outliers reach O(100) and would squash
                    # a linear histogram into a single bin at zero
                    vals = vals[np.isfinite(vals) & (vals > 0)]
                    bins = np.logspace(np.log10(max(vals.min(), 1e-3)),
                                       np.log10(vals.max()), 60)
                    ax.hist(vals, bins=bins, color="steelblue",
                            edgecolor="white", lw=0.3)
                    ax.set_xscale("log")
                else:
                    ax.hist(vals, bins=60, color="steelblue",
                            edgecolor="white", lw=0.3)
                ax.set_title(f"{c}  n={len(vals)}  median={np.median(vals):.4g}",
                             fontsize=8)
            ax.set_xlabel(xlabel, fontsize=7)
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.2)
        fig.tight_layout()
        if name == "nrmse":
            add_pipeline_note(fig, "NRMSE distribution of fit_ok events, LOG-spaced "
                              "bins/axis; bimodal = good-fit population vs noise "
                              "triggers; valley = natural cut candidate; NO cut applied")
        else:
            add_pipeline_note(fig, "distribution of the FITTED free pretrigger "
                              "(samples) for fit_ok events; reference 16050")
        out = os.path.join(PLOT_DIR, fname)
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {out}")

    # t_rise / t_fall histograms side by side
    fig, axes = plt.subplots(len(chans), 2, figsize=(12, 2.5 * len(chans)),
                             squeeze=False)
    fig.suptitle(f"Zip{det} — t_rise / t_fall (fit_ok events, free-pretrigger fit)",
                 fontsize=10)
    for row, c in enumerate(chans):
        oks = [f for f in collector[c]["fits"] if f["fit_ok"]]
        trs = np.array([f["t_rise"] for f in oks]) * 1e3
        tfs = np.array([f["t_fall"] for f in oks]) * 1e3
        for ax, vals, label, color in [(axes[row, 0], trs, "t_rise (ms)", "steelblue"),
                                       (axes[row, 1], tfs, "t_fall (ms)", "darkorange")]:
            if len(vals):
                ax.hist(vals, bins=60, color=color, edgecolor="white", lw=0.3)
                ax.set_title(f"{c} {label} median={np.median(vals):.3f}ms", fontsize=8)
            ax.set_xlabel(label, fontsize=7)
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.2)
    fig.tight_layout()
    add_pipeline_note(fig, "fitted t_rise / t_fall distributions (ms) of fit_ok "
                      "events; free-pretrigger fit, loose bounds t_rise<5ms t_fall<20ms")
    out = os.path.join(PLOT_DIR, f"zip{det}_time_constants.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def write_summary(det, collector):
    summary = {"det": det, "created_at": datetime.datetime.now().isoformat(),
               "lp_cutoff_khz": LP_CUTOFF_KHZ, "rise_ref_idx": RISE_REF_IDX,
               "nrmse_cut": None, "channels": {}}
    for c in ALL_CHANS:
        fits = collector[c]["fits"]
        if not fits:
            continue
        oks = [f for f in fits if f["fit_ok"]]
        entry = {"n_traces": len(fits), "n_fit_ok": len(oks),
                 "fit_ok_frac": len(oks) / len(fits)}
        if oks:
            for key in ["pretrigger", "t_rise", "t_fall", "nrmse"]:
                vals = np.array([f[key] for f in oks])
                entry[key] = {"median": float(np.median(vals)),
                              "std": float(np.std(vals)),
                              "p16": float(np.percentile(vals, 16)),
                              "p84": float(np.percentile(vals, 84))}
        summary["channels"][c] = entry
    out = os.path.join(STATS_DIR, f"zip{det}_lp_fit_summary.json")
    with open(out, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"Saved: {out}")
    print(f"\n{'Chan':6} {'traces':>7} {'fit_ok':>7} {'ok%':>6} "
          f"{'pt_med':>8} {'nrmse_med':>9}")
    for c, e in summary["channels"].items():
        pt = e.get("pretrigger", {}).get("median", float("nan"))
        nr = e.get("nrmse", {}).get("median", float("nan"))
        print(f"  {c:6} {e['n_traces']:>7} {e['n_fit_ok']:>7} "
              f"{100*e['fit_ok_frac']:>5.1f}% {pt:>8.1f} {nr:>9.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--det", type=int, required=True)
    parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
    parser.add_argument("--series", nargs="*", default=None,
                        help="restrict to these series (smoke tests)")
    parser.add_argument("--max-per-channel", type=int, default=None,
                        help="fit at most N traces per channel (smoke tests; "
                             "disables checkpointing)")
    args = parser.parse_args()
    det = args.det

    for d in [PLOT_DIR, STATS_DIR, os.path.join(CKPT_DIR, f"zip{det}")]:
        os.makedirs(d, exist_ok=True)

    series_dir = os.path.join(args.cache_dir, f"zip{det}_series")
    if not os.path.isdir(series_dir):
        raise FileNotFoundError(series_dir)
    pkl_files = sorted(f for f in os.listdir(series_dir) if f.endswith(".pkl"))
    if args.series:
        pkl_files = [f for f in pkl_files if f[:-4] in set(args.series)]
    print(f"=== zip{det}: LP + free-pretrigger fit + shift align ===")
    print(f"Series: {len(pkl_files)}   cutoff={LP_CUTOFF_KHZ}kHz   "
          f"ref={RISE_REF_IDX}   nrmse cut: none")

    collector = {c: {"fits": [], "overlay": [], "examples": [],
                     "mean_sum": np.zeros(TRACELENGTH), "mean_n": 0}
                 for c in ALL_CHANS}

    n_workers = min(len(ALL_CHANS), os.cpu_count() or 1)
    with mp.Pool(n_workers) as pool:
        for fname in pkl_files:
            series = fname[:-4]
            process_series(det, series,
                           os.path.join(series_dir, fname),
                           os.path.join(CKPT_DIR, f"zip{det}", f"{series}_fit.pkl"),
                           collector, args.max_per_channel, pool)

    plot_aligned_overlay(det, collector)
    plot_fit_examples(det, collector)
    plot_histograms(det, collector)
    write_summary(det, collector)
    print(f"\nDone. zip{det} complete.")


if __name__ == "__main__":
    main()
