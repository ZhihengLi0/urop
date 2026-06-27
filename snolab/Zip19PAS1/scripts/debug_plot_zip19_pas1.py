#!/usr/bin/env python3
"""
Per-event debug plots: raw (LP-filtered) pulse overlaid with 2-exp analytical fit.
Reads existing fit_params.csv + fit_failures.csv, re-reads raw traces, saves one
PNG per event into run/debug_plots/.

Success events: raw (blue) + analytical fit (red dashed) + fit window shaded.
Failure events: raw (blue) only, failure reason in title.
"""

import csv
import os

import numpy as np
import uproot
from scipy.signal import butter, sosfilt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import rawio
except ImportError as exc:
    raise RuntimeError("rawio is required inside the CDMS environment") from exc

# ── constants (must match fit_plot_zip19_pas1.py) ─────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

DET               = 19
CHAN              = "PAS1"
PTOF_LO, PTOF_HI = 4.44e-7, 8.10e-7
SAMPLERATE        = 625000
TRACELENGTH       = 32768
FILTER_KHZ        = 100.0
SECTION3_RISE_INDEX = 16050
FIT_LO  = SECTION3_RISE_INDEX - 300
FIT_HI  = SECTION3_RISE_INDEX + 5000

SERIES     = "24260619_230219"
MAX_EVENTS = 200
OUT_TAG    = f"zip19_pas1_{SERIES}_first{MAX_EVENTS}"


def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)


def two_exp_fit(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = np.clip((x - pretrigger) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def main():
    run_dir   = os.environ.get("ZIP19PAS1_RUN_DIR", os.path.abspath("Zip19PAS1/run"))
    cache_dir = os.path.join(run_dir, "cache")
    debug_dir = os.path.join(run_dir, "debug_plots")
    os.makedirs(debug_dir, exist_ok=True)

    # ── load fit results ───────────────────────────────────────────────────────
    fit_params = {}
    with open(os.path.join(cache_dir, f"{OUT_TAG}_fit_params.csv")) as f:
        for row in csv.DictReader(f):
            fit_params[int(row["event"])] = {k: float(v) for k, v in row.items()
                                             if k not in ("series", "event")}

    fail_reasons = {}
    with open(os.path.join(cache_dir, f"{OUT_TAG}_fit_failures.csv")) as f:
        for row in csv.DictReader(f):
            fail_reasons[int(row["event"])] = row["reason"]

    # ── baselines + ptofamps from processed ROOT ───────────────────────────────
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{SERIES}.root")
    with uproot.open(fpath) as f:
        trig  = f["rqDir/eventTree/TriggerType"].array(library="np")
        evnum = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        ptof  = f[f"rqDir/zip{DET}/PTOFamps"].array(library="np")
        mask  = (trig == 1) & (ptof != -999999) & (ptof > PTOF_LO) & (ptof < PTOF_HI)
        evs   = evnum[mask]
        try:
            bs = f[f"rqDir/zip{DET}/{CHAN}bs"].array(library="np")[mask]
        except Exception:
            bs = np.full(len(evs), np.nan)
        ptof_sel = ptof[mask]

    baselines = {}
    ptofamps  = {}
    for evn, b, p in zip(evs[:MAX_EVENTS], bs[:MAX_EVENTS], ptof_sel[:MAX_EVENTS]):
        baselines[int(evn)] = float(b)
        ptofamps[int(evn)]  = float(p)

    target_events = set(baselines.keys())

    # ── re-read raw traces ─────────────────────────────────────────────────────
    print(f"Reading raw traces for series {SERIES} ...")
    reader  = rawio.RawDataReader(os.path.join(RAW_DIR, SERIES))
    nb      = reader.get_nb_events()
    total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
    events  = reader.read_events(
        output_format=2,
        skip_empty=True,
        trigger_types=[1],
        nb_events=total_e,
        detector_nums=[DET],
        channel_names=[CHAN],
    )

    x_full  = np.arange(TRACELENGTH, dtype=np.float64)
    t_ms    = x_full / SAMPLERATE * 1e3
    rise_ms = t_ms[SECTION3_RISE_INDEX]

    # view windows: (label, start_idx, end_idx)
    windows = [
        ("full",  SECTION3_RISE_INDEX - 600,  SECTION3_RISE_INDEX + 5500),
        ("zoom",  SECTION3_RISE_INDEX - 100,  SECTION3_RISE_INDEX + 1000),
    ]

    n_plotted = 0
    for event in events:
        evn = int(event["event"]["EventNumber"])
        if evn not in target_events:
            continue

        try:
            pulse = event[f"Z{DET}"][CHAN]
        except KeyError:
            print(f"ev{evn}: channel missing in raw data, skipping")
            continue

        # ── reproduce the same preprocessing as fit_pulse ─────────────────────
        y_raw = pulse.astype(np.float64)
        b0    = baselines[evn]
        if np.isfinite(b0) and b0 != -999999:
            baseline0 = b0
        else:
            baseline0 = float(np.mean(y_raw[:5000]))
        y_lp = butter_lp(y_raw - baseline0)

        # pre-trigger baseline (same window used during fitting)
        pre_lo   = max(0, SECTION3_RISE_INDEX - 700)
        pre_base = float(np.median(y_lp[pre_lo:SECTION3_RISE_INDEX]))

        is_success = evn in fit_params
        reason     = fail_reasons.get(evn, "")

        # ── reconstruct analytical fit at y_lp scale ──────────────────────────
        if is_success:
            p     = fit_params[evn]
            # two_exp_fit was fit on (y_lp - pre_base); add pre_base back for overlay
            y_ana = two_exp_fit(
                x_full,
                p["amp"], p["t_rise"], p["t_fall"],
                p["baseline_fit"], p["pretrigger_fit"],
            ) + pre_base

        # ── plot ──────────────────────────────────────────────────────────────
        fig, axes = plt.subplots(1, 2, figsize=(15, 4), sharey=False)

        for ax, (tag, lo, hi) in zip(axes, windows):
            sl = slice(lo, hi)

            ax.plot(t_ms[sl], y_lp[sl], lw=0.9, color="steelblue",
                    alpha=0.85, label="raw (LP-filtered)")

            if is_success:
                ax.plot(t_ms[sl], y_ana[sl], lw=1.3, color="crimson",
                        ls="--", alpha=0.9, label="2-exp fit")
                if tag == "full":
                    ax.axvspan(t_ms[FIT_LO], t_ms[FIT_HI - 1],
                               alpha=0.08, color="orange", label="fit window")

            ax.axvline(rise_ms, color="gray", lw=0.8, ls=":", alpha=0.7,
                       label=f"rise idx={SECTION3_RISE_INDEX}")
            ax.axhline(pre_base, color="purple", lw=0.6, ls=":", alpha=0.5,
                       label=f"pre_base={pre_base:.2f}")

            ax.set_title(tag)
            ax.set_xlabel("Time (ms)")
            ax.grid(alpha=0.18, ls=":")
            ax.legend(fontsize=7, loc="upper right")

        axes[0].set_ylabel("Amplitude (ADU, baseline-sub)")

        if is_success:
            p = fit_params[evn]
            info = (
                f"t_rise={p['t_rise']*1e3:.3f} ms  t_fall={p['t_fall']*1e3:.3f} ms  "
                f"pretrig={p['pretrigger_fit']:.0f}  nrmse={p['nrmse']:.3f}"
            )
            status_str = f"FIT OK  |  {info}"
            fig.patch.set_facecolor("#f0fff0")
        else:
            status_str = f"FIT FAIL  |  reason: {reason}"
            fig.patch.set_facecolor("#fff0f0")

        fig.suptitle(
            f"Zip19 PAS1  |  {SERIES}  ev{evn}  |  PTOFamps={ptofamps[evn]:.3e}\n{status_str}",
            fontsize=9,
        )
        fig.tight_layout()

        status_tag = "ok" if is_success else "fail"
        png = os.path.join(debug_dir, f"ev{evn:06d}_{status_tag}.png")
        fig.savefig(png, dpi=130, bbox_inches="tight")
        plt.close(fig)
        n_plotted += 1
        if n_plotted % 20 == 0:
            print(f"  plotted {n_plotted} events ...")

    print(f"Done. Saved {n_plotted} debug plots to {debug_dir}")


if __name__ == "__main__":
    main()
