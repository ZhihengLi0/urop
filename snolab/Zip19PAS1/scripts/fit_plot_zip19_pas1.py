#!/usr/bin/env python3
# coding: utf-8
"""
Zip19 PAS1 event-level analytical fits.

Selection is intentionally minimal:
  TriggerType == 1 and Zip19 PTOFamps within the configured interval.

For every selected raw PAS1 pulse, fit a two-exponential analytical pulse,
pin the rise/pretrigger point to SECTION3_RISE_INDEX, peak-normalize, and plot
all successful fitted curves. Failed fits are recorded, not silently filtered.
"""

import csv
import os
import pickle

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
    raise RuntimeError("rawio is required inside the CDMS environment") from exc


PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG = "Prompt_V07-02_C0.4.5"

DET = 19
CHAN = "PAS1"
PTOF_LO, PTOF_HI = 4.44e-7, 8.10e-7

SAMPLERATE = 625000
TRACELENGTH = 32768
FILTER_KHZ = 100.0
SECTION3_RISE_INDEX = 16050
FIT_LO = SECTION3_RISE_INDEX - 300
FIT_HI = SECTION3_RISE_INDEX + 5000
FIT_STRIDE = 4
FIT_MAXFEV = 50000

ALL_SERIES = [
    "24260617_063934", "24260617_175849", "24260617_190838", "24260617_234805",
    "24260618_013000", "24260618_062713", "24260618_073543", "24260618_202553",
    "24260619_023225", "24260619_061249", "24260619_075448", "24260619_093653",
    "24260619_144815", "24260619_174938", "24260619_210312", "24260619_230219",
    "24260620_032928", "24260621_021444", "24260621_041432", "24260621_075659",
    "24260621_111527", "24260621_145024", "24260622_022708", "24260622_042718",
    "24260622_073439", "24260622_210215", "24260622_232541", "24260623_012553",
    "24260623_035656", "24260623_064608",
]


def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)


def two_exp_fit(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = np.clip((x - pretrigger) / SAMPLERATE, 0.0, None)
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def normalize_fixed_rise(trace):
    trace = np.asarray(trace, dtype=np.float64)
    if not np.all(np.isfinite(trace)):
        return None
    trace[:SECTION3_RISE_INDEX + 1] = 0.0
    trace = np.maximum(trace, 0.0)
    peak = float(np.max(trace))
    if not np.isfinite(peak) or peak <= 0:
        return None
    return trace / peak


def select_events_and_baselines(series):
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(fpath):
        return {}, "processed_missing"
    with uproot.open(fpath) as f:
        trig = f["rqDir/eventTree/TriggerType"].array(library="np")
        evnum = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        ptof = f[f"rqDir/zip{DET}/PTOFamps"].array(library="np")
        mask = (trig == 1) & (ptof != -999999) & (ptof > PTOF_LO) & (ptof < PTOF_HI)
        evs = evnum[mask]
        try:
            bs = f[f"rqDir/zip{DET}/{CHAN}bs"].array(library="np")[mask]
        except Exception:
            bs = np.full(len(evs), np.nan)
        try:
            ptof_sel = ptof[mask]
        except Exception:
            ptof_sel = np.full(len(evs), np.nan)
    return {
        int(evn): {
            "baseline": float(baseline),
            "ptofamps": float(ptofamp),
        }
        for evn, baseline, ptofamp in zip(evs, bs, ptof_sel)
    }, None


def fit_pulse(pulse, baseline_rq):
    y_raw = pulse.astype(np.float64)
    if np.isfinite(baseline_rq) and baseline_rq != -999999:
        baseline0 = float(baseline_rq)
    else:
        baseline0 = float(np.mean(y_raw[:5000]))
    y_lp = butter_lp(y_raw - baseline0)

    x_full = np.arange(TRACELENGTH, dtype=np.float64)
    x_fit = x_full[FIT_LO:FIT_HI:FIT_STRIDE]
    y_fit = y_lp[FIT_LO:FIT_HI:FIT_STRIDE]

    pre_base = float(np.median(y_lp[max(0, SECTION3_RISE_INDEX - 700):SECTION3_RISE_INDEX]))
    y_fit = y_fit - pre_base
    peak = float(np.max(y_lp[SECTION3_RISE_INDEX:min(TRACELENGTH, SECTION3_RISE_INDEX + 3000)] - pre_base))
    if not np.isfinite(peak) or peak <= 0:
        return None, None, "bad_peak"

    peak_idx = int(np.argmax(y_lp))
    t_rise0 = 6.0e-5
    t_fall0 = 2.8e-4
    dt_to_peak = np.log(t_fall0 / t_rise0) / (1.0 / t_rise0 - 1.0 / t_fall0)
    pt0 = float(np.clip(peak_idx - dt_to_peak * SAMPLERATE, FIT_LO, FIT_HI - 1))

    try:
        popt, _ = curve_fit(
            two_exp_fit, x_fit, y_fit,
            p0=[peak, t_rise0, t_fall0, 0.0, pt0],
            bounds=([0.0, 1.0e-6, 1.0e-5, -0.5 * peak, FIT_LO],
                    [np.inf, 8.0e-4, 8.0e-3, 0.5 * peak, FIT_HI]),
            maxfev=FIT_MAXFEV,
        )
    except Exception as exc:
        return None, None, f"fit_failed:{type(exc).__name__}"

    amp, t_rise, t_fall, baseline, pretrigger = [float(v) for v in popt]
    if not (np.isfinite(amp) and np.isfinite(t_rise) and np.isfinite(t_fall) and np.isfinite(pretrigger)):
        return None, None, "nonfinite_fit"
    if not (amp > 0.0 and 0.0 < t_rise < t_fall):
        return None, None, "unphysical_fit"

    synth = two_exp_fit(x_full, amp, t_rise, t_fall, 0.0, float(SECTION3_RISE_INDEX))
    norm = normalize_fixed_rise(synth)
    if norm is None:
        return None, None, "bad_synthetic"

    model_fit = two_exp_fit(x_fit, *popt)
    rmse = float(np.sqrt(np.mean((y_fit - model_fit) ** 2)))
    meta = {
        "amp": amp,
        "t_rise": t_rise,
        "t_fall": t_fall,
        "baseline_fit": baseline,
        "pretrigger_fit": pretrigger,
        "peak_raw_lp": peak,
        "peak_idx_lp": peak_idx,
        "rmse": rmse,
        "nrmse": rmse / peak if peak > 0 else np.nan,
    }
    return norm, meta, None


def main():
    run_dir = os.environ.get("ZIP19PAS1_RUN_DIR", os.path.abspath("Zip19PAS1/run"))
    series_filter = os.environ.get("ZIP19PAS1_SERIES", "").strip()
    max_events = int(os.environ.get("ZIP19PAS1_MAX_EVENTS", "0") or "0")
    plot_dir = os.path.join(run_dir, "plots")
    cache_dir = os.path.join(run_dir, "cache")
    os.makedirs(plot_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    fitted = []
    fit_rows = []
    fail_rows = []
    selected_total = 0
    selected_interval_total = 0

    if series_filter:
        series_list = [s.strip() for s in series_filter.split(",") if s.strip()]
    else:
        series_list = ALL_SERIES
    tag_parts = ["zip19_pas1"]
    if series_filter:
        tag_parts.append(series_filter.replace(",", "_"))
    if max_events > 0:
        tag_parts.append(f"first{max_events}")
    out_tag = "_".join(tag_parts)

    for series in series_list:
        selected, error = select_events_and_baselines(series)
        if error:
            print(f"{series}: {error}")
            continue
        n_in_interval = len(selected)
        selected_interval_total += n_in_interval
        if max_events > 0 and len(selected) > max_events:
            selected = dict(list(selected.items())[:max_events])
        selected_total += len(selected)
        limit_msg = f", using first {len(selected)}" if len(selected) != n_in_interval else ""
        print(f"{series}: selected {n_in_interval} events in PTOFamps window{limit_msg}")
        if not selected:
            continue

        raw_dir = os.path.join(RAW_DIR, series)
        if not os.path.isdir(raw_dir):
            for evn in selected:
                fail_rows.append({"series": series, "event": evn, "reason": "raw_dir_missing"})
            print(f"{series}: raw directory missing")
            continue

        try:
            reader = rawio.RawDataReader(raw_dir)
            nb = reader.get_nb_events()
            total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
            events = reader.read_events(
                output_format=2,
                skip_empty=True,
                trigger_types=[1],
                nb_events=total_e,
                detector_nums=[DET],
                channel_names=[CHAN],
            )
        except Exception as exc:
            for evn in selected:
                fail_rows.append({"series": series, "event": evn, "reason": f"rawio:{type(exc).__name__}"})
            print(f"{series}: rawio error {exc}")
            continue

        selected_keys = set(selected)
        n_fit = 0
        for event in events:
            evn = int(event["event"]["EventNumber"])
            if evn not in selected_keys:
                continue
            try:
                pulse = event[f"Z{DET}"][CHAN]
            except KeyError:
                fail_rows.append({"series": series, "event": evn, "reason": "channel_missing"})
                continue

            trace, meta, reason = fit_pulse(pulse, selected[evn]["baseline"])
            if trace is None:
                fail_rows.append({"series": series, "event": evn, "reason": reason})
                continue

            fitted.append(trace.astype(np.float32))
            row = {
                "series": series,
                "event": evn,
                "ptofamps": selected[evn]["ptofamps"],
            }
            row.update(meta)
            fit_rows.append(row)
            n_fit += 1
        print(f"{series}: fitted {n_fit}/{len(selected)} selected events")

    fit_csv = os.path.join(cache_dir, f"{out_tag}_fit_params.csv")
    fail_csv = os.path.join(cache_dir, f"{out_tag}_fit_failures.csv")
    pkl_out = os.path.join(cache_dir, f"{out_tag}_fitted_traces.pkl")

    fit_fields = [
        "series", "event", "ptofamps", "amp", "t_rise", "t_fall",
        "baseline_fit", "pretrigger_fit", "peak_raw_lp", "peak_idx_lp",
        "rmse", "nrmse",
    ]
    with open(fit_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fit_fields)
        writer.writeheader()
        writer.writerows(fit_rows)

    with open(fail_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["series", "event", "reason"])
        writer.writeheader()
        writer.writerows(fail_rows)

    with open(pkl_out, "wb") as f:
        pickle.dump({
            "det": DET,
            "chan": CHAN,
            "ptof_range": [PTOF_LO, PTOF_HI],
            "series_filter": series_filter,
            "max_events": max_events,
            "selected_interval_total": selected_interval_total,
            "selected_total": selected_total,
            "fit_success": len(fitted),
            "fit_fail": len(fail_rows),
            "fit_params": fit_rows,
            "traces": fitted,
        }, f, protocol=pickle.HIGHEST_PROTOCOL)

    traces = np.asarray(fitted, dtype=np.float32)
    print(f"selected_total={selected_total} fit_success={len(fitted)} fit_fail={len(fail_rows)}")
    if traces.size == 0:
        raise RuntimeError("No fitted traces to plot")

    t_ms = np.arange(TRACELENGTH) / SAMPLERATE * 1e3
    windows = [
        ("full", SECTION3_RISE_INDEX - 500, SECTION3_RISE_INDEX + 3000),
        ("zoom", SECTION3_RISE_INDEX - 50, SECTION3_RISE_INDEX + 600),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    for ax, (tag, lo, hi) in zip(axes, windows):
        for tr in traces:
            ax.plot(t_ms[lo:hi], tr[lo:hi], lw=0.35, alpha=0.18)
        ax.axvline(t_ms[SECTION3_RISE_INDEX], color="gray", lw=0.8, ls="--", alpha=0.6)
        ax.set_title(f"{tag} (n={len(traces)}/{selected_total})")
        ax.set_xlabel("Time (ms)")
        ax.grid(alpha=0.2, ls=":")
    axes[0].set_ylabel("Amplitude (norm.)")
    fig.suptitle(
        f"Zip19 PAS1 - all selected events - 2-exp analytical fits\n"
        f"PTOFamps {PTOF_LO:.2e} to {PTOF_HI:.2e}, fixed rise @ {SECTION3_RISE_INDEX}"
        f"{', series ' + series_filter if series_filter else ''}"
    )
    fig.tight_layout()
    out_png = os.path.join(plot_dir, f"{out_tag}_all_2exp_fitted_normalized.png")
    fig.savefig(out_png, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")
    print(f"Saved: {fit_csv}")
    print(f"Saved: {fail_csv}")
    print(f"Saved: {pkl_out}")


if __name__ == "__main__":
    main()
