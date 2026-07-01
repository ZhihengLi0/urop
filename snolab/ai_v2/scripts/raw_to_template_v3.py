#!/usr/bin/env python3
"""
Template generation v3 — reads raw MIDAS directly, no dependency on the
126GB pkl cache under raw_without_filter/ (that cache was built with
pretrigger pinned inside the fit itself, which is methodologically wrong).

Teacher's correction (2026-06-30, relayed by user):
  "现在就是我们做的时候需要先fit,fit在哪就在哪,只有在align的时候才改成一个
   定数,钉死rise的点。"
  -> Fit and align are two separate steps:
     1. FIT: pretrigger is a free curve_fit parameter (matches teacher's
        notebook first/notebooks/NxM_cedar.ipynb two_exp_fit). Wherever the
        optimizer puts it is the real fitted trigger time for that event.
     2. ALIGN: only AFTER fitting, build an aligned analytical trace by
        evaluating the same closed-form 2-exp curve with the fitted
        (amp, t_rise, t_fall) but with pretrigger overridden to a fixed
        reference sample (SECTION3_RISE_IDX). Because the model is a
        closed-form analytic function, this substitution is exact — no
        interpolation needed for the analytical trace. Raw traces are
        aligned separately via sub-sample interpolation using the fitted
        pretrigger.

This script does raw I/O + fit + align + NRMSE quality cut + PCA template
construction in one pass per zip, with per-series checkpointing (raw I/O
on this cluster is slow and SLURM/background jobs have been killed
mid-run before — see CONTEXT_FOR_NEXT_AI.md section 4.4).

Usage:
    python raw_to_template_v3.py --det 7
    python raw_to_template_v3.py --det 7 --nrmse-max 0.15
    python raw_to_template_v3.py --det 7 --series-after 24260618_013000
"""

import argparse, os, pickle, json, warnings, datetime
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

try:
    import rawio
except ImportError as exc:
    raise RuntimeError("rawio is required inside the CDMS singularity environment") from exc

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

try:
    import ROOT
    from ROOT import TFile, TH1D
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    print("WARNING: ROOT not available — skipping ROOT output")

# ── paths ────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

RUN_DIR   = os.environ.get(
    "AI_V3_RUN_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'run')))
CACHE_DIR = os.path.join(RUN_DIR, 'cache_v3')      # per-series checkpoints owned by THIS script
PLOT_DIR  = os.path.join(RUN_DIR, 'plots')
ROOT_DIR  = os.path.join(RUN_DIR, 'root_files')
STATS_DIR = os.path.join(RUN_DIR, 'stats')
for d in [CACHE_DIR, PLOT_DIR, ROOT_DIR, STATS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── constants ────────────────────────────────────────────────────────────────
SAMPLERATE        = 625000
TRACELENGTH       = 32768
FILTER_KHZ        = 100.0
SECTION3_RISE_IDX = 16050          # ALIGNMENT reference only — not a fit constraint
PRETRIGGER_FREEDOM = 3000          # samples; fit may place pretrigger anywhere in
                                    # [SECTION3_RISE_IDX-freedom, SECTION3_RISE_IDX+freedom]
FIT_LO            = SECTION3_RISE_IDX - 300
FIT_HI            = SECTION3_RISE_IDX + 5000
FIT_STRIDE        = 4

N_COMPONENTS      = 5              # nxm0 (mean) + nxm1-4 (PC1-4)
PCA_COMPONENTS    = N_COMPONENTS - 1
MAX_NXM           = 500
MIN_EVENTS        = 5
MIN_CLUSTER_EVENTS = 20
N_EXAMPLES        = 20

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

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

SERIES_EXCLUSIONS = {
     1: ["24260621_075659"],
    13: ["24260617_063934"],
    15: ["24260619_093653", "24260619_144815", "24260619_230219"],
    18: ["24260617_063934", "24260617_175849", "24260617_190838",
         "24260617_234805", "24260618_013000", "24260618_062713",
         "24260618_073543"],
    22: ["24260620_032928", "24260621_021444", "24260621_041432",
         "24260621_075659", "24260621_111527", "24260621_145024"],
}

PTOF_RANGES = {
     1: (2.96e-7, 5.40e-7),
     4: (4.44e-7, 8.10e-7),
     6: (3.33e-7, 6.08e-7),
     7: (1.48e-6, 2.70e-6),
     9: (5.93e-7, 1.08e-6),
    10: (5.93e-7, 1.08e-6),
    13: (1.19e-6, 2.16e-6),
    15: (7.41e-6, 1.35e-5),
    16: (1.33e-6, 2.43e-6),
    18: (1.04e-6, 1.89e-6),
    19: (4.44e-7, 8.10e-7),
    22: (3.70e-7, 6.75e-7),
    24: (4.44e-7, 8.10e-7),
}

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
X_FIT  = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]

# ── fit model: FREE pretrigger (matches teacher's NxM_cedar.ipynb two_exp_fit) ─
def two_exp_free_pt(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = (x - pretrigger) / SAMPLERATE
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)


def shift_interp(y, shift):
    """Sub-sample shift: output[i] = y[i - shift], via linear interpolation."""
    idx = np.arange(len(y))
    return np.interp(idx - shift, idx, y, left=y[0], right=y[-1])


def process_pulse(pulse_raw, baseline_rq):
    """
    Returns dict with:
      raw_norm       : raw LP-filtered trace, peak-normalised, NATIVE trigger time
      raw_aligned     : same, sub-sample shifted so fitted pretrigger -> SECTION3_RISE_IDX
      ana_aligned     : closed-form 2-exp curve evaluated with fitted (amp,t_rise,t_fall)
                        but pretrigger PINNED to SECTION3_RISE_IDX (the align step)
      fit_ok, reason, fit_params (t_rise, t_fall, nrmse, pretrigger — all from the
        FREE-pretrigger fit; nrmse is computed against the free fit, i.e. genuine
        goodness of fit, not inflated/deflated by a wrong pinned pretrigger)
    or None fields on failure.
    """
    y = pulse_raw.astype(np.float64)
    if len(y) < TRACELENGTH:
        return None, None, None, False, f"short_trace_{len(y)}", None

    if np.isfinite(baseline_rq) and baseline_rq != -999999:
        bs = float(baseline_rq)
    else:
        bs = float(np.mean(y[:5000]))
    y -= bs

    y_lp = butter_lp(y)

    pre_base = float(np.median(y_lp[SECTION3_RISE_IDX - 700:SECTION3_RISE_IDX]))
    y_lp -= pre_base

    peak = float(np.max(y_lp[SECTION3_RISE_IDX:SECTION3_RISE_IDX + 5000]))
    if not np.isfinite(peak) or peak <= 0:
        return None, None, None, False, "bad_peak", None

    raw_norm = (y_lp / peak).astype(np.float32)

    y_fit = y_lp[FIT_LO:FIT_HI:FIT_STRIDE]
    try:
        popt, _ = curve_fit(
            two_exp_free_pt, X_FIT, y_fit,
            p0=[peak, 6e-5, 2.8e-4, 0.0, float(SECTION3_RISE_IDX)],
            bounds=([0.0,     1e-6,  1e-5, -0.5 * peak, SECTION3_RISE_IDX - PRETRIGGER_FREEDOM],
                    [np.inf,  8e-4,  8e-3,  0.5 * peak, SECTION3_RISE_IDX + PRETRIGGER_FREEDOM]),
            maxfev=50000,
        )
        amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall):
            raise ValueError("unphysical")

        # NRMSE against the genuine free-pretrigger fit (real goodness of fit)
        residuals = y_fit / peak - two_exp_free_pt(X_FIT, amp/peak, t_rise, t_fall, bl/peak, pt)
        nrmse = float(np.sqrt(np.mean(residuals**2)))

        # ── ALIGN step: pin pretrigger to the reference, keep fitted shape params ──
        y_ana = two_exp_free_pt(X_FULL, amp, t_rise, t_fall, 0.0, float(SECTION3_RISE_IDX))
        ana_peak = float(np.max(y_ana))
        if ana_peak <= 0:
            raise ValueError("zero_ana_peak")
        ana_aligned = (y_ana / ana_peak).astype(np.float32)

        raw_aligned = (shift_interp(y_lp, SECTION3_RISE_IDX - pt) / peak).astype(np.float32)

        fit_params = {"t_rise": t_rise, "t_fall": t_fall, "nrmse": nrmse, "pretrigger": pt}
        return raw_norm, raw_aligned, ana_aligned, True, None, fit_params
    except Exception as exc:
        return raw_norm, None, None, False, str(exc), None


# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--det", type=int, required=True)
parser.add_argument("--nrmse-max", type=float, default=0.15)
parser.add_argument("--series", nargs="*", default=None)
parser.add_argument("--series-from", dest="series_from", default=None)
parser.add_argument("--series-after", dest="series_after", default=None)
args = parser.parse_args()
det       = args.det
NRMSE_MAX = args.nrmse_max

if det not in PTOF_RANGES:
    raise ValueError(f"zip{det} not in PTOF_RANGES")

ptof_lo, ptof_hi = PTOF_RANGES[det]
excluded = set(SERIES_EXCLUSIONS.get(det, []))
series_list = [s for s in ALL_SERIES if s not in excluded]
if args.series:
    wanted = set(args.series)
    unknown = sorted(wanted - set(ALL_SERIES))
    if unknown:
        raise ValueError(f"unknown series: {unknown}")
    series_list = [s for s in series_list if s in wanted]
if args.series_from:
    first_idx = ALL_SERIES.index(args.series_from)
    series_list = [s for s in series_list if ALL_SERIES.index(s) >= first_idx]
if args.series_after:
    first_idx = ALL_SERIES.index(args.series_after) + 1
    series_list = [s for s in series_list if ALL_SERIES.index(s) >= first_idx]

print(f"=== Zip{det} v3 (free-pretrigger fit + align)  PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}] ===")
print(f"Series to process ({len(series_list)}): {series_list}")

SERIES_CACHE_DIR = os.path.join(CACHE_DIR, f"zip{det}_series")
os.makedirs(SERIES_CACHE_DIR, exist_ok=True)

# ── step 1: select events from processed ROOT files (same as old pipeline) ─────
sel = {}
for series in series_list:
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(fpath):
        print(f"  {series}: processed file missing, skipping")
        continue
    try:
        with uproot.open(fpath) as f:
            trig  = f["rqDir/eventTree/TriggerType"].array(library="np")
            evnum = f["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
            ptof  = f[f"rqDir/zip{det}/PTOFamps"].array(library="np")
            mask  = (trig == 1) & (ptof != -999999) & (ptof > ptof_lo) & (ptof < ptof_hi)
            evs   = evnum[mask]

            baselines = {}
            for c in ALL_CHANS:
                try:
                    bs_arr = f[f"rqDir/zip{det}/{c}bs"].array(library="np")[mask]
                    baselines[c] = dict(zip(evs.tolist(), bs_arr.tolist()))
                except Exception:
                    baselines[c] = {}

        sel[series] = {"evnums": set(int(e) for e in evs), "baselines": baselines}
        print(f"  {series}: {len(evs)} events in PTOFamps window")
    except Exception as exc:
        print(f"  {series}: ERROR — {exc}")

# ── step 2: read raw traces, fit + align, with per-series checkpointing ────────
raw_traces     = {c: [] for c in ALL_CHANS}
raw_aligned_tr = {c: [] for c in ALL_CHANS}
ana_traces     = {c: [] for c in ALL_CHANS}
fit_ok_mask    = {c: [] for c in ALL_CHANS}
fit_params_ch  = {c: [] for c in ALL_CHANS}
fail_reasons   = {c: {} for c in ALL_CHANS}

def merge_series_payload(payload):
    for chan in ALL_CHANS:
        raw_traces[chan].extend(payload.get("raw_traces", {}).get(chan, []))
        raw_aligned_tr[chan].extend(payload.get("raw_aligned", {}).get(chan, []))
        ana_traces[chan].extend(payload.get("ana_traces", {}).get(chan, []))
        fit_ok_mask[chan].extend(payload.get("fit_ok_mask", {}).get(chan, []))
        fit_params_ch[chan].extend(payload.get("fit_params_ch", {}).get(chan, []))
        for reason, count in payload.get("fail_reasons", {}).get(chan, {}).items():
            fail_reasons[chan][reason] = fail_reasons[chan].get(reason, 0) + int(count)

for series, info in sel.items():
    series_cache = os.path.join(SERIES_CACHE_DIR, f"{series}.pkl")
    if os.path.exists(series_cache):
        try:
            with open(series_cache, "rb") as f:
                payload = pickle.load(f)
            merge_series_payload(payload)
            print(f"  {series}: loaded checkpoint {series_cache}")
            continue
        except Exception as exc:
            print(f"  {series}: checkpoint unreadable ({exc}); recomputing")

    evnum_set = info["evnums"]
    if not evnum_set:
        continue
    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        print(f"  {series}: raw directory missing, skipping")
        continue

    try:
        reader  = rawio.RawDataReader(raw_dir)
        nb      = reader.get_nb_events()
        total_e = nb.get("NbEventsNotEmpty", nb.get("NbEvents", 50000))
        events  = reader.read_events(
            output_format=2, skip_empty=True, trigger_types=[1],
            nb_events=total_e, detector_nums=[det], channel_names=ALL_CHANS,
        )
    except Exception as exc:
        print(f"  {series}: rawio error — {exc}")
        continue

    n_found = 0
    z_key = f"Z{det}"
    s_raw     = {c: [] for c in ALL_CHANS}
    s_raw_al  = {c: [] for c in ALL_CHANS}
    s_ana     = {c: [] for c in ALL_CHANS}
    s_ok      = {c: [] for c in ALL_CHANS}
    s_params  = {c: [] for c in ALL_CHANS}
    s_fail    = {c: {} for c in ALL_CHANS}

    for event in events:
        evn = int(event["event"]["EventNumber"])
        if evn not in evnum_set:
            continue
        n_found += 1

        for chan in ALL_CHANS:
            try:
                pulse = event[z_key][chan]
            except KeyError:
                continue
            baseline_rq = info["baselines"].get(chan, {}).get(evn, np.nan)
            raw_n, raw_al, ana_al, ok, reason, fpar = process_pulse(pulse, baseline_rq)
            if raw_n is None:
                s_fail[chan][reason] = s_fail[chan].get(reason, 0) + 1
                continue
            s_raw[chan].append(raw_n)
            s_raw_al[chan].append(raw_al if raw_al is not None else raw_n)
            s_ana[chan].append(ana_al)
            s_ok[chan].append(ok)
            s_params[chan].append(fpar)
            if not ok and reason:
                s_fail[chan][reason] = s_fail[chan].get(reason, 0) + 1

    print(f"  {series}: found {n_found}/{len(evnum_set)} events in raw files")
    payload = {
        "series": series, "det": det,
        "n_found": n_found, "n_selected": len(evnum_set),
        "raw_traces": s_raw, "raw_aligned": s_raw_al, "ana_traces": s_ana,
        "fit_ok_mask": s_ok, "fit_params_ch": s_params, "fail_reasons": s_fail,
    }
    tmp_cache = series_cache + ".tmp"
    with open(tmp_cache, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_cache, series_cache)
    print(f"  {series}: checkpoint saved {series_cache}")
    merge_series_payload(payload)

for c in ALL_CHANS:
    n_total  = len(raw_traces[c])
    n_fit_ok = sum(fit_ok_mask[c])
    if n_total:
        print(f"  {c}: {n_total} raw traces, {n_fit_ok} fit OK ({n_fit_ok/n_total*100:.0f}%)")

# ── step 3: quality cut (fit_ok AND nrmse<=NRMSE_MAX), same as v2 ──────────────
channel_traces = {c: [] for c in ALL_CHANS}   # ana_aligned, selected
channel_raws   = {c: [] for c in ALL_CHANS}   # raw_traces (native time), selected
channel_trises = {c: [] for c in ALL_CHANS}
channel_tfalls = {c: [] for c in ALL_CHANS}
channel_nrmses = {c: [] for c in ALL_CHANS}
channel_pretrg = {c: [] for c in ALL_CHANS}

n_total_c = {c: 0 for c in ALL_CHANS}
n_fitok_c = {c: 0 for c in ALL_CHANS}
n_nrmse_c = {c: 0 for c in ALL_CHANS}

for c in ALL_CHANS:
    n_total_c[c] = len(raw_traces[c])
    for i in range(len(raw_traces[c])):
        ok = fit_ok_mask[c][i]
        fp = fit_params_ch[c][i]
        ana = ana_traces[c][i]
        if not ok or fp is None or ana is None:
            continue
        n_fitok_c[c] += 1
        if float(fp['nrmse']) > NRMSE_MAX:
            continue
        n_nrmse_c[c] += 1
        channel_traces[c].append(np.asarray(ana, dtype=np.float32))
        channel_raws[c].append(np.asarray(raw_traces[c][i], dtype=np.float32))
        channel_trises[c].append(float(fp['t_rise']))
        channel_tfalls[c].append(float(fp['t_fall']))
        channel_nrmses[c].append(float(fp['nrmse']))
        channel_pretrg[c].append(float(fp['pretrigger']))

print(f"\nEvent counts per channel:")
print(f"{'Chan':6} {'total':>7} {'fit_ok':>7} {'nrmse_ok':>9}")
for c in ALL_CHANS:
    print(f"  {c:6} {n_total_c[c]:>7} {n_fitok_c[c]:>7} {n_nrmse_c[c]:>9}")

# ── PCA template builder (identical algorithm to v2's build_nxm) ───────────────
def build_nxm(traces, n_comp=PCA_COMPONENTS, max_ev=MAX_NXM):
    arr = np.array(traces, dtype=np.float64)
    if len(arr) > max_ev:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr), max_ev, replace=False)
        arr = arr[idx]

    mean_tr = arr.mean(axis=0)
    mean_tr[:SECTION3_RISE_IDX + 1] = 0.0
    pk = float(np.max(mean_tr))
    if pk > 0:
        mean_tr /= pk

    if len(arr) < n_comp + 1:
        return [mean_tr] + [np.zeros_like(mean_tr) for _ in range(n_comp)], [0.0] * n_comp

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca = PCA(n_components=n_comp, svd_solver='full')
        pca.fit(arr)

    var_exp = pca.explained_variance_ratio_.tolist()
    templates = [mean_tr] + [pca.components_[i].copy() for i in range(n_comp)]
    return templates, var_exp

specific_templates = {}
specific_var       = {}
print(f"\nBuilding specific templates:")
for c in ALL_CHANS:
    trs = channel_traces[c]
    if len(trs) < MIN_EVENTS:
        print(f"  {c}: only {len(trs)} events — skipping")
        specific_templates[c] = None
        continue
    tmpl, var = build_nxm(trs)
    specific_templates[c] = tmpl
    specific_var[c] = var
    print(f"  {c}: {len(trs)} events -> PCA var: {[f'{v:.3f}' for v in var]}")

all_traces_concat = []
for c in ALL_CHANS:
    if len(channel_traces[c]) >= MIN_EVENTS:
        all_traces_concat.extend(channel_traces[c])

agnostic_templates = {}
if len(all_traces_concat) >= PCA_COMPONENTS + 1:
    arr_all = np.array(all_traces_concat, dtype=np.float64)
    n_active = len([c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS])
    if len(arr_all) > MAX_NXM * n_active:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr_all), min(len(arr_all), MAX_NXM * n_active), replace=False)
        arr_all = arr_all[idx]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca_all = PCA(n_components=PCA_COMPONENTS, svd_solver='full')
        pca_all.fit(arr_all)
    for c in ALL_CHANS:
        trs = channel_traces[c]
        if len(trs) < MIN_EVENTS:
            agnostic_templates[c] = None
            continue
        arr_c  = np.array(trs, dtype=np.float64)
        mean_c = arr_c.mean(axis=0)
        mean_c[:SECTION3_RISE_IDX + 1] = 0.0
        pk = float(np.max(mean_c))
        if pk > 0:
            mean_c /= pk
        agnostic_templates[c] = [mean_c] + [pca_all.components_[i].copy() for i in range(PCA_COMPONENTS)]

# ── ROOT output ──────────────────────────────────────────────────────────────
def write_root(out_path, templates_dict):
    if not HAS_ROOT:
        return
    tf = TFile(out_path, "RECREATE")
    for c, tmpl in templates_dict.items():
        if tmpl is None:
            continue
        for k, tr in enumerate(tmpl):
            name  = f"nxm{k}_zip{det}_{c}"
            title = f"Zip{det} {c} NxM{k} (v3, free-pretrigger fit + align)"
            h = TH1D(name, title, TRACELENGTH, -0.5, TRACELENGTH - 0.5)
            for j, v in enumerate(tr):
                h.SetBinContent(j + 1, float(v))
            h.Write()
    tf.Close()
    print(f"Saved ROOT: {out_path}")

write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_v3_agnostic.root"), agnostic_templates)
write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_v3_specific.root"), specific_templates)

# ── JSON stats (now includes pretrigger — the new free fit parameter) ─────────
time_consts = {}
for c in ALL_CHANS:
    trs = channel_trises[c]
    tfs = channel_tfalls[c]
    ns  = channel_nrmses[c]
    pts = channel_pretrg[c]
    if not trs:
        time_consts[c] = None
        continue
    time_consts[c] = {
        "n_events":  len(trs),
        "t_rise_ms": {"median": float(np.median(trs)*1e3), "std": float(np.std(trs)*1e3),
                      "p16": float(np.percentile(trs,16)*1e3), "p84": float(np.percentile(trs,84)*1e3)},
        "t_fall_ms": {"median": float(np.median(tfs)*1e3), "std": float(np.std(tfs)*1e3),
                      "p16": float(np.percentile(tfs,16)*1e3), "p84": float(np.percentile(tfs,84)*1e3)},
        "nrmse":     {"median": float(np.median(ns)), "p95": float(np.percentile(ns,95))},
        "pretrigger": {"median": float(np.median(pts)), "std": float(np.std(pts)),
                       "p16": float(np.percentile(pts,16)), "p84": float(np.percentile(pts,84)),
                       "reference": SECTION3_RISE_IDX},
    }

json_path = os.path.join(STATS_DIR, f"time_constants_zip{det}_v3.json")
with open(json_path, 'w') as fh:
    json.dump(time_consts, fh, indent=2)
print(f"Saved stats: {json_path}")

# ── plots ────────────────────────────────────────────────────────────────────
t_ms    = X_FULL / SAMPLERATE * 1e3
PLOT_LO = SECTION3_RISE_IDX - 500
PLOT_HI = min(TRACELENGTH, SECTION3_RISE_IDX + 8000)
ZOOM_LO = SECTION3_RISE_IDX - 50
ZOOM_HI = SECTION3_RISE_IDX + 2000

active = [c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS]

# 1. Aligned overlay
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — aligned ana_traces (free-pretrigger fit, fit_ok + NRMSE<={NRMSE_MAX})", fontsize=10)
    for row, c in enumerate(active):
        arr = np.array(channel_traces[c], dtype=np.float64)
        ax  = axes[row, 0]
        for tr in arr[:200]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI], lw=0.4, alpha=0.15, color='steelblue')
        if specific_templates[c]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], specific_templates[c][0][PLOT_LO:PLOT_HI], lw=1.5, color='crimson', label='mean')
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.set_title(f"{c}  n={len(arr)}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7); ax.set_ylabel("Norm. amp.", fontsize=7)
        ax.legend(fontsize=7); ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
        ax2 = axes[row, 1]
        for tr in arr[:200]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], tr[ZOOM_LO:ZOOM_HI], lw=0.5, alpha=0.2, color='steelblue')
        if specific_templates[c]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], specific_templates[c][0][ZOOM_LO:ZOOM_HI], lw=1.5, color='crimson')
        ax2.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax2.set_title(f"{c} zoom", fontsize=8)
        ax2.set_xlabel("Time (ms)", fontsize=7)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_aligned_overlay.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_aligned_overlay.png")

# 2. NxM templates (specific)
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(10, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — NxM specific (PCA components, free-pretrigger fit + align)", fontsize=10)
    colors = ['black', 'crimson', 'royalblue', 'darkorange', 'forestgreen']
    labels = ['mean (nxm0)', 'PC1 (nxm1)', 'PC2 (nxm2)', 'PC3 (nxm3)', 'PC4 (nxm4)']
    for row, c in enumerate(active):
        ax   = axes[row, 0]
        tmpl = specific_templates[c]
        if tmpl is None:
            continue
        for k, (tr, col, lbl) in enumerate(zip(tmpl, colors, labels)):
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI], lw=1.2, color=col, label=lbl, alpha=0.85)
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.axhline(0, color='gray', lw=0.5, ls='--')
        n   = len(channel_traces[c])
        var = specific_var.get(c, [])
        var_str = '  '.join([f"PC{i+1}:{v:.2f}" for i, v in enumerate(var)])
        ax.set_title(f"{c}  n={n}   {var_str}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7); ax.set_ylabel("Amp.", fontsize=7)
        ax.legend(fontsize=7, ncol=N_COMPONENTS)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_nxm_specific.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_nxm_specific.png")

# 3. t_rise / t_fall distributions
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 2.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — t_rise / t_fall distributions (free-pretrigger fit)", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax1, ax2 = axes[row, 0], axes[row, 1]
        ax1.hist(trs, bins=40, color='steelblue', edgecolor='white', lw=0.3)
        ax1.set_title(f"{c} t_rise  median={np.median(trs):.3f}ms", fontsize=8)
        ax1.set_xlabel("t_rise (ms)", fontsize=7)
        ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
        ax2.hist(tfs, bins=40, color='darkorange', edgecolor='white', lw=0.3)
        ax2.set_title(f"{c} t_fall  median={np.median(tfs):.3f}ms", fontsize=8)
        ax2.set_xlabel("t_fall (ms)", fontsize=7)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_time_constants.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_time_constants.png")

# 4. t_rise vs t_fall scatter
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(8, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — t_rise vs t_fall scatter", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax  = axes[row, 0]
        ax.scatter(trs, tfs, s=2, alpha=0.3, color='steelblue')
        ax.set_xlabel("t_rise (ms)", fontsize=7); ax.set_ylabel("t_fall (ms)", fontsize=7)
        ax.set_title(f"{c}  n={len(trs)}", fontsize=8)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_trise_vs_tfall.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_trise_vs_tfall.png")

# 5. NEW: pretrigger vs t_rise scatter — directly tests the teacher's PDF claim
#    ("significant correlation for risetime and pretrigger") which was impossible
#    to check in v1/v2 because pretrigger was pinned constant in the fit.
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 3.0 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — fitted pretrigger diagnostics (new: pretrigger was NOT free in v1/v2)", fontsize=10)
    for row, c in enumerate(active):
        pts = np.array(channel_pretrg[c])
        trs = np.array(channel_trises[c]) * 1e3
        ax1, ax2 = axes[row, 0], axes[row, 1]
        ax1.hist(pts, bins=40, color='slategray', edgecolor='white', lw=0.3)
        ax1.axvline(SECTION3_RISE_IDX, color='crimson', lw=1, ls='--', label='align reference')
        ax1.set_title(f"{c} fitted pretrigger  median={np.median(pts):.1f}  std={np.std(pts):.1f}", fontsize=8)
        ax1.set_xlabel("pretrigger (sample)", fontsize=7)
        ax1.legend(fontsize=6); ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
        ax2.scatter(pts, trs, s=2, alpha=0.3, color='darkorange')
        corr = float(np.corrcoef(pts, trs)[0, 1]) if len(pts) > 2 else float('nan')
        ax2.set_xlabel("pretrigger (sample)", fontsize=7); ax2.set_ylabel("t_rise (ms)", fontsize=7)
        ax2.set_title(f"{c}  pretrigger vs t_rise  corr={corr:.2f}", fontsize=8)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_pretrigger_diagnostics.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_pretrigger_diagnostics.png")

# 6. Rise/fall cluster correspondence
rise_fall_concordance = {}
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(8, 3.8 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — rise/fall cluster correspondence (KMeans k=2)", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax  = axes[row, 0]
        n   = len(trs)
        if n < MIN_CLUSTER_EVENTS:
            ax.text(0.5, 0.5, f"{c}: only {n} events, skip clustering", transform=ax.transAxes, ha='center', fontsize=8)
            ax.set_title(c, fontsize=8)
            continue
        km_r = KMeans(n_clusters=2, n_init=10, random_state=0).fit(trs.reshape(-1, 1))
        km_f = KMeans(n_clusters=2, n_init=10, random_state=0).fit(tfs.reshape(-1, 1))
        r_order = np.argsort(km_r.cluster_centers_.ravel())
        f_order = np.argsort(km_f.cluster_centers_.ravel())
        rise_slow = (km_r.labels_ == r_order[1])
        fall_slow = (km_f.labels_ == f_order[1])
        both_fast = (~rise_slow) & (~fall_slow)
        both_slow = ( rise_slow) & ( fall_slow)
        rise_only = ( rise_slow) & (~fall_slow)
        fall_only = (~rise_slow) & ( fall_slow)
        concord = (both_fast.sum() + both_slow.sum()) / n
        rise_fall_concordance[c] = concord
        ax.scatter(trs[both_fast], tfs[both_fast], s=3, alpha=0.4, color='steelblue', label=f'rise-fast&fall-fast (n={int(both_fast.sum())})')
        ax.scatter(trs[both_slow], tfs[both_slow], s=3, alpha=0.4, color='crimson', label=f'rise-slow&fall-slow (n={int(both_slow.sum())})')
        ax.scatter(trs[rise_only], tfs[rise_only], s=3, alpha=0.4, color='darkorange', label=f'rise-slow,fall-fast (n={int(rise_only.sum())})')
        ax.scatter(trs[fall_only], tfs[fall_only], s=3, alpha=0.4, color='forestgreen', label=f'rise-fast,fall-slow (n={int(fall_only.sum())})')
        rs_bound = km_r.cluster_centers_.ravel()[r_order[1]]
        fs_bound = km_f.cluster_centers_.ravel()[f_order[1]]
        ax.set_xlabel("t_rise (ms)", fontsize=7); ax.set_ylabel("t_fall (ms)", fontsize=7)
        ax.set_title(f"{c}  n={n}  concordance={concord*100:.0f}%  (rise-slow~{rs_bound:.3f}ms, fall-slow~{fs_bound:.3f}ms)", fontsize=7)
        ax.legend(fontsize=6, loc='upper left')
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_rise_fall_correspondence.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_rise_fall_correspondence.png")

# 7. Raw trace examples (native trigger time, NOT aligned) by rise-fast vs rise-slow
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — raw trace examples (native time): rise-fast (blue) vs rise-slow (red)", fontsize=10)
    for row, c in enumerate(active):
        trs  = np.array(channel_trises[c]) * 1e3
        raws = channel_raws[c]
        n    = len(trs)
        ax_full, ax_zoom = axes[row, 0], axes[row, 1]
        if n < MIN_CLUSTER_EVENTS or len(raws) != n:
            ax_full.text(0.5, 0.5, f"{c}: only {n} events, skip", transform=ax_full.transAxes, ha='center', fontsize=8)
            ax_full.set_title(c, fontsize=8); ax_zoom.set_title(c, fontsize=8)
            continue
        km_r = KMeans(n_clusters=2, n_init=10, random_state=0).fit(trs.reshape(-1, 1))
        r_order  = np.argsort(km_r.cluster_centers_.ravel())
        fast_idx = np.where(km_r.labels_ == r_order[0])[0]
        slow_idx = np.where(km_r.labels_ == r_order[1])[0]
        rng = np.random.default_rng(0)
        fast_sample = rng.choice(fast_idx, min(N_EXAMPLES, len(fast_idx)), replace=False)
        slow_sample = rng.choice(slow_idx, min(N_EXAMPLES, len(slow_idx)), replace=False)
        for ax, lo, hi in [(ax_full, PLOT_LO, PLOT_HI), (ax_zoom, ZOOM_LO, ZOOM_HI)]:
            for i in fast_sample:
                ax.plot(t_ms[lo:hi], raws[i][lo:hi], lw=0.6, alpha=0.4, color='steelblue')
            for i in slow_sample:
                ax.plot(t_ms[lo:hi], raws[i][lo:hi], lw=0.6, alpha=0.4, color='crimson')
            ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
            ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
        rise_fast_c = km_r.cluster_centers_.ravel()[r_order[0]]
        rise_slow_c = km_r.cluster_centers_.ravel()[r_order[1]]
        ax_full.set_title(f"{c} full  fast~{rise_fast_c:.3f}ms (n={len(fast_idx)})  slow~{rise_slow_c:.3f}ms (n={len(slow_idx)})", fontsize=7)
        ax_zoom.set_title(f"{c} zoom (rise region)", fontsize=7)
        ax_full.set_xlabel("Time (ms)", fontsize=7); ax_full.set_ylabel("Norm. raw amp.", fontsize=7)
        ax_zoom.set_xlabel("Time (ms)", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_raw_examples_by_rise_peak.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_raw_examples_by_rise_peak.png")

# ── text summary ────────────────────────────────────────────────────────────
txt_path = os.path.join(PLOT_DIR, f"zip{det}_v3_summary.txt")
lines = []
lines.append("=" * 70)
lines.append(f"SUMMARY: Zip{det} v3  (generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})")
lines.append("=" * 70)
lines.append("Fit: 2-exp, pretrigger FREE (curve_fit), bounded to "
              f"[{SECTION3_RISE_IDX-PRETRIGGER_FREEDOM}, {SECTION3_RISE_IDX+PRETRIGGER_FREEDOM}]")
lines.append(f"Align: ana_traces built by re-evaluating fitted (amp,t_rise,t_fall) "
              f"with pretrigger pinned to {SECTION3_RISE_IDX} (align step only, not in fit)")
lines.append(f"Quality cut: fit_ok AND nrmse<={NRMSE_MAX}")
lines.append("")
for c in ALL_CHANS:
    n_t, n_f, n_n = n_total_c[c], n_fitok_c[c], n_nrmse_c[c]
    if n_t == 0:
        continue
    lines.append(f"{c}: total={n_t}  fit_ok={n_f} ({n_f/n_t*100:.1f}%)  "
                 f"nrmse_ok={n_n} ({n_n/n_t*100:.1f}%)")
    if c in rise_fall_concordance:
        lines.append(f"  rise/fall concordance={rise_fall_concordance[c]*100:.1f}%")
with open(txt_path, 'w') as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved summary: {txt_path}")

print(f"\nDone. Zip{det} v3 complete.")
