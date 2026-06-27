#!/usr/bin/env python3
"""
Zip19 PAS1 — one series, one channel.
2-exp fit with pretrigger PINNED to SECTION3_RISE_INDEX.
Outputs one figure: all raw (LP-filtered, norm) + analytical overlaid.
"""

import os
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import rawio
except ImportError as exc:
    raise RuntimeError("rawio is required inside the CDMS singularity environment") from exc

PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

DET               = 19
CHAN              = "PAS1"
PTOF_LO, PTOF_HI = 4.44e-7, 8.10e-7
SERIES            = "24260619_230219"

SAMPLERATE        = 625000
TRACELENGTH       = 32768
FILTER_KHZ        = 100.0
SECTION3_RISE_IDX = 16050
FIT_LO            = SECTION3_RISE_IDX - 300
FIT_HI            = SECTION3_RISE_IDX + 5000
FIT_STRIDE        = 4


def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)


def two_exp_fixed_pt(x, amp, t_rise, t_fall, baseline):
    """2-exp pulse with pretrigger pinned to SECTION3_RISE_IDX."""
    dt = np.clip((x - SECTION3_RISE_IDX) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= SECTION3_RISE_IDX, baseline, pulse + baseline)


def fit_pulse(y_raw, baseline_rq):
    if np.isfinite(baseline_rq) and baseline_rq != -999999:
        baseline0 = float(baseline_rq)
    else:
        baseline0 = float(np.mean(y_raw[:5000]))
    y_lp = butter_lp(y_raw.astype(np.float64) - baseline0)

    pre_base = float(np.median(y_lp[SECTION3_RISE_IDX - 700:SECTION3_RISE_IDX]))
    y_lp -= pre_base

    peak = float(np.max(y_lp[SECTION3_RISE_IDX:SECTION3_RISE_IDX + 3000]))
    if not np.isfinite(peak) or peak <= 0:
        return None, None, None, "bad_peak"

    x_full = np.arange(TRACELENGTH, dtype=np.float64)
    x_fit  = x_full[FIT_LO:FIT_HI:FIT_STRIDE]
    y_fit  = y_lp[FIT_LO:FIT_HI:FIT_STRIDE]

    try:
        popt, _ = curve_fit(
            two_exp_fixed_pt, x_fit, y_fit,
            p0=[peak, 6e-5, 2.8e-4, 0.0],
            bounds=([0.0,  1e-6,  1e-5, -0.5 * peak],
                    [np.inf, 8e-4, 8e-3,  0.5 * peak]),
            maxfev=50000,
        )
    except Exception as exc:
        return None, None, None, f"fit_failed:{type(exc).__name__}"

    amp, t_rise, t_fall, bl = [float(v) for v in popt]
    if not (amp > 0 and 0 < t_rise < t_fall):
        return None, None, None, "unphysical_fit"

    y_ana = two_exp_fixed_pt(x_full, amp, t_rise, t_fall, 0.0)
    return y_lp / peak, y_ana / peak, (amp, t_rise, t_fall), None


def main():
    run_dir  = os.environ.get("ZIP19PAS1_RUN_DIR", os.path.abspath("Zip19PAS1/run"))
    plot_dir = os.path.join(run_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    # --- load event list from processed ROOT ---------------------------------
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{SERIES}.root")
    with uproot.open(fpath) as f:
        trig   = f["rqDir/eventTree/TriggerType"].array(library="np")
        evnum  = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        ptof   = f[f"rqDir/zip{DET}/PTOFamps"].array(library="np")
        mask   = (trig == 1) & (ptof != -999999) & (ptof > PTOF_LO) & (ptof < PTOF_HI)
        evs    = evnum[mask]
        try:
            bs = f[f"rqDir/zip{DET}/{CHAN}bs"].array(library="np")[mask]
        except Exception:
            bs = np.full(len(evs), np.nan)

    selected = {int(e): float(b) for e, b in zip(evs, bs)}
    print(f"{SERIES}: {len(selected)} events in PTOFamps window")

    # --- read raw traces and fit ---------------------------------------------
    reader  = rawio.RawDataReader(os.path.join(RAW_DIR, SERIES))
    nb      = reader.get_nb_events()
    total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
    events  = reader.read_events(
        output_format=2, skip_empty=True, trigger_types=[1],
        nb_events=total_e, detector_nums=[DET], channel_names=[CHAN],
    )

    raw_traces, ana_traces, params = [], [], []
    n_fail = 0
    for event in events:
        evn = int(event["event"]["EventNumber"])
        if evn not in selected:
            continue
        try:
            pulse = event[f"Z{DET}"][CHAN]
        except KeyError:
            n_fail += 1
            continue
        y_raw, y_ana, p, reason = fit_pulse(pulse, selected[evn])
        if y_raw is None:
            n_fail += 1
            print(f"  ev{evn}: {reason}")
            continue
        raw_traces.append(y_raw)
        ana_traces.append(y_ana)
        params.append(p)
        if len(raw_traces) % 20 == 0:
            print(f"  fitted {len(raw_traces)} events ...")

    print(f"Done: {len(raw_traces)} fitted, {n_fail} failed")
    if not raw_traces:
        raise RuntimeError("No fitted traces")

    # --- plot ----------------------------------------------------------------
    t_ms = np.arange(TRACELENGTH) / SAMPLERATE * 1e3
    windows = [
        ("full", SECTION3_RISE_IDX - 600, SECTION3_RISE_IDX + 5000),
        ("zoom", SECTION3_RISE_IDX - 80,  SECTION3_RISE_IDX + 800),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    for ax, (tag, lo, hi) in zip(axes, windows):
        for y_raw, y_ana in zip(raw_traces, ana_traces):
            ax.plot(t_ms[lo:hi], y_raw[lo:hi], lw=0.5, alpha=0.15, color="steelblue")
            ax.plot(t_ms[lo:hi], y_ana[lo:hi], lw=0.8, alpha=0.35, color="crimson",  ls="--")
        ax.axvline(t_ms[SECTION3_RISE_IDX], color="k", lw=0.8, ls=":", alpha=0.6)
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("Amplitude (norm.)")
        ax.set_title(f"{tag}  (n={len(raw_traces)}/{len(selected)})")
        ax.grid(alpha=0.2, ls=":")

    t_rises = [p[1] * 1e3 for p in params]
    t_falls = [p[2] * 1e3 for p in params]
    fig.suptitle(
        f"Zip19 PAS1  {SERIES}  —  2-exp fit (pretrigger pinned @ {SECTION3_RISE_IDX})\n"
        f"blue=raw LP-filtered  red=analytical fit\n"
        f"t_rise median={np.median(t_rises):.3f} ms  t_fall median={np.median(t_falls):.3f} ms",
        fontsize=9,
    )
    fig.tight_layout()
    out = os.path.join(plot_dir, f"zip19_pas1_{SERIES}_raw_vs_ana_pinned.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
