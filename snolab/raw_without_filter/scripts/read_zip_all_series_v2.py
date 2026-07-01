#!/usr/bin/env python3
"""
Fill gaps in the 126GB per-series pkl cache AND fix the fit methodology —
in one script, writing directly back into the same shared cache directory.

Two problems being fixed at once (2026-06-30, per user/teacher instruction):

1. GAPS: the original read_zip_all_series.py run (on user's personal MSI
   storage) got OOM-killed partway through and was later moved to the
   shared cache path below. Many zips are missing a large fraction of their
   30 series (see CONTEXT_FOR_NEXT_AI.md section 7.3 for the exact gap
   table). This script only does the expensive rawio/uproot read for
   SERIES THAT ARE ACTUALLY MISSING — every series that already has a
   checkpoint pkl is loaded, not re-read from raw MIDAS.

2. WRONG FIT MODEL: the original script's `two_exp_fixed_pt` pinned
   `pretrigger` to SECTION3_RISE_IDX=16050 inside the fit itself, so
   curve_fit never got to find the real trigger time — it could only
   distort amp/t_rise/t_fall to compensate for a misaligned window. Per
   teacher's correction (relayed by user 2026-06-30): "现在就是我们做的时候
   需要先fit,fit在哪就在哪,只有在align的时候才改成一个定数,钉死rise的点。"
   This matches the teacher's own notebook (first/notebooks/NxM_cedar.ipynb,
   `two_exp_fit`, pretrigger free with p0=15600, unbounded) and the PDF
   finding "risetime has significant correlation with pretrigger" — treating
   pretrigger as a constant throws away real physics.

   Fix: fit with `two_exp_free_pt` (pretrigger is a free curve_fit
   parameter, bounded to SECTION3_RISE_IDX +/- PRETRIGGER_FREEDOM for
   optimizer stability — same bounds already validated in
   ai_v2/scripts/template_from_pkl_v3.py's `refit_one`). ALIGNMENT (pinning
   to a common reference so events can be stacked for PCA) is done
   afterwards as a separate step: re-evaluate the same closed-form curve
   with the fitted (amp, t_rise, t_fall) but pretrigger overridden to
   SECTION3_RISE_IDX. This is exact (analytic function), no interpolation.

   IMPORTANT — explicit user instruction (2026-06-30): "那个数据统计的部分,
   新的部分就不要按错误的思路fit,写入数据" — newly-filled (gap) series must
   NEVER be written with the old fixed-pretrigger fit, not even
   transiently. They go straight to free-pretrigger fit on first write.

Behavior per series (single pass, see main loop):
  - checkpoint pkl exists AND already tagged fit_method="free_pretrigger":
      load only, no rawio, no re-fit. (idempotent re-runs are cheap)
  - checkpoint pkl exists but is OLD (fixed-pretrigger, no fit_method tag):
      raw_traces are reused as-is (verified fit-independent, see
      CONTEXT_FOR_NEXT_AI.md section 6.5) — re-fit ONLY (no rawio) with
      the free-pretrigger model, overwrite ana_traces/fit_ok_mask/
      fit_params_ch/fail_reasons in place, tag fit_method="free_pretrigger".
  - checkpoint pkl missing (a real gap): full pipeline — uproot event
      selection + rawio raw trace read + free-pretrigger fit from the
      start — then save, tagged fit_method="free_pretrigger" immediately.

Every series is saved via tmp-file + os.replace as soon as it's done, so a
kill/OOM at any point loses at most the one series in flight — nothing
already-written is ever redone needlessly, and nothing is left half-written.

Usage:
    python read_zip_all_series_v2.py --det 1                  # fill gaps + refit stale, whole zip
    python read_zip_all_series_v2.py --det 1 --dry-run         # report only, no writes
    python read_zip_all_series_v2.py --det 1 --skip-refit      # only fill gaps, leave old-fit series alone
    python read_zip_all_series_v2.py --det 1 --series 24260620_032928 24260621_021444
"""

import argparse, os, pickle, datetime
import numpy as np
import uproot
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt

try:
    import rawio
except ImportError as exc:
    rawio = None  # allow --dry-run without rawio present

# ── paths ─────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"

# same shared 126GB cache location documented in CONTEXT_FOR_NEXT_AI.md section 1/7.3
CACHE_DIR_DEFAULT = "/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache"

# ── constants ─────────────────────────────────────────────────────────────────
SAMPLERATE          = 625000
TRACELENGTH         = 32768
FILTER_KHZ          = 100.0
SECTION3_RISE_IDX   = 16050             # ALIGNMENT reference only — not a fit constraint anymore
PRETRIGGER_FREEDOM  = 3000              # samples of freedom for the fit around the reference
                                          # (matches ai_v2/scripts/template_from_pkl_v3.py)
FIT_LO              = max(0, SECTION3_RISE_IDX - PRETRIGGER_FREEDOM - 500)
FIT_HI              = min(TRACELENGTH, SECTION3_RISE_IDX + PRETRIGGER_FREEDOM + 5000)
FIT_STRIDE          = 4

FIT_METHOD_TAG = "free_pretrigger"  # written into payload so re-runs can skip already-fixed series

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

# ── helpers ───────────────────────────────────────────────────────────────────
def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype="low", fs=fs, output="sos")
    return sosfilt(sos, data)

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
X_FIT  = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]

def two_exp_free_pt(x, amp, t_rise, t_fall, baseline, pretrigger):
    """Notebook-style 2-exp pulse — pretrigger is a FREE fit parameter."""
    dt = (x - pretrigger) / SAMPLERATE
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def extract_raw_norm(pulse_raw, baseline_rq):
    """
    Baseline-subtract + 100kHz LP filter + peak-normalize.
    UNCHANGED from the original script — this part is fit-independent and
    already verified reusable (CONTEXT_FOR_NEXT_AI.md section 6.5).
    Returns (raw_lp_norm[float32] or None, reason_str_or_None).
    """
    y = pulse_raw.astype(np.float64)
    if len(y) < TRACELENGTH:
        return None, f"short_trace_{len(y)}"

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
        return None, "bad_peak"

    return (y_lp / peak).astype(np.float32), None


def fit_and_align(raw_norm):
    """
    raw_norm: already baseline~0, 100kHz LP-filtered, peak-normalized to 1.
    FIT step: pretrigger free (bounded +/- PRETRIGGER_FREEDOM for stability).
    ALIGN step: re-evaluate the fitted curve with pretrigger pinned to
    SECTION3_RISE_IDX — this is where "钉死" happens now, AFTER the fit,
    not inside it.
    Returns (ana_aligned[float32] or None, fit_ok, reason, fit_params dict
    with amp/t_rise/t_fall/baseline/pretrigger/nrmse, or None).
    """
    y = np.asarray(raw_norm, dtype=np.float64)
    y_fit = y[FIT_LO:FIT_HI:FIT_STRIDE]
    try:
        popt, _ = curve_fit(
            two_exp_free_pt, X_FIT, y_fit,
            p0=[1.0, 6e-5, 2.8e-4, 0.0, float(SECTION3_RISE_IDX)],
            bounds=([0.0,     1e-6,  1e-5, -0.5, SECTION3_RISE_IDX - PRETRIGGER_FREEDOM],
                    [np.inf,  8e-4,  8e-3,  0.5, SECTION3_RISE_IDX + PRETRIGGER_FREEDOM]),
            maxfev=50000,
        )
        amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall):
            raise ValueError("unphysical")
        residuals = y_fit - two_exp_free_pt(X_FIT, amp, t_rise, t_fall, bl, pt)
        nrmse = float(np.sqrt(np.mean(residuals**2)))

        # ALIGN: same closed-form curve, pretrigger overridden to the reference
        y_ana = two_exp_free_pt(X_FULL, amp, t_rise, t_fall, 0.0, float(SECTION3_RISE_IDX))
        ana_peak = float(np.max(y_ana))
        if ana_peak <= 0:
            raise ValueError("zero_ana_peak")
        ana_aligned = (y_ana / ana_peak).astype(np.float32)

        fit_params = {"amp": amp, "t_rise": t_rise, "t_fall": t_fall,
                      "baseline": bl, "pretrigger": pt, "nrmse": nrmse}
        return ana_aligned, True, None, fit_params
    except Exception as exc:
        return None, False, str(exc), None


def refit_series_payload(payload):
    """Re-fit every trace already sitting in `payload['raw_traces']` with the
    free-pretrigger model; raw_traces themselves are left untouched."""
    new_ana    = {c: [] for c in ALL_CHANS}
    new_ok     = {c: [] for c in ALL_CHANS}
    new_params = {c: [] for c in ALL_CHANS}
    new_fail   = {c: {} for c in ALL_CHANS}

    for c in ALL_CHANS:
        for raw_tr in payload.get("raw_traces", {}).get(c, []):
            ana, ok, reason, fp = fit_and_align(raw_tr)
            new_ana[c].append(ana if ana is not None else np.zeros(TRACELENGTH, dtype=np.float32))
            new_ok[c].append(ok)
            new_params[c].append(fp)
            if not ok and reason:
                new_fail[c][reason] = new_fail[c].get(reason, 0) + 1

    payload = dict(payload)  # shallow copy, don't mutate caller's dict in place
    payload["ana_traces"]    = new_ana
    payload["fit_ok_mask"]   = new_ok
    payload["fit_params_ch"] = new_params
    payload["fail_reasons"]  = new_fail
    payload["fit_method"]    = FIT_METHOD_TAG
    payload["refit_at"]      = datetime.datetime.now().isoformat()
    return payload


def select_events_for_series(det, series, ptof_lo, ptof_hi):
    """uproot step: which events in this series fall in the PTOFamps window,
    plus per-channel RQ baselines for those events. Returns None if the
    processed ROOT file is missing or unreadable."""
    fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(fpath):
        print(f"  {series}: processed file missing, skipping")
        return None
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
        print(f"  {series}: {len(evs)} events in PTOFamps window")
        return {"evnums": set(int(e) for e in evs), "baselines": baselines}
    except Exception as exc:
        print(f"  {series}: ERROR reading processed ROOT — {exc}")
        return None


def build_payload_from_raw(det, series, sel_info):
    """Full pipeline for a genuinely missing series: rawio read + free-pretrigger
    fit from the start. Never touches the old fixed-pretrigger fit function."""
    evnum_set = sel_info["evnums"]
    if not evnum_set:
        return None
    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        print(f"  {series}: raw directory missing, skipping")
        return None
    if rawio is None:
        raise RuntimeError("rawio is required to read missing series (not available in this environment)")

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
        return None

    n_found = 0
    z_key = f"Z{det}"
    raw_traces    = {c: [] for c in ALL_CHANS}
    ana_traces    = {c: [] for c in ALL_CHANS}
    fit_ok_mask   = {c: [] for c in ALL_CHANS}
    fit_params_ch = {c: [] for c in ALL_CHANS}
    fail_reasons  = {c: {} for c in ALL_CHANS}

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
            baseline_rq = sel_info["baselines"].get(chan, {}).get(evn, np.nan)
            raw_norm, reason = extract_raw_norm(pulse, baseline_rq)
            if raw_norm is None:
                fail_reasons[chan][reason] = fail_reasons[chan].get(reason, 0) + 1
                continue

            ana, ok, reason, fp = fit_and_align(raw_norm)
            raw_traces[chan].append(raw_norm)
            ana_traces[chan].append(ana if ana is not None else np.zeros(TRACELENGTH, dtype=np.float32))
            fit_ok_mask[chan].append(ok)
            fit_params_ch[chan].append(fp)
            if not ok and reason:
                fail_reasons[chan][reason] = fail_reasons[chan].get(reason, 0) + 1

    print(f"  {series}: found {n_found}/{len(evnum_set)} events in raw files")
    return {
        "series":        series,
        "det":           det,
        "n_found":       n_found,
        "n_selected":    len(evnum_set),
        "raw_traces":    raw_traces,
        "ana_traces":    ana_traces,
        "fit_ok_mask":   fit_ok_mask,
        "fit_params_ch": fit_params_ch,
        "fail_reasons":  fail_reasons,
        "fit_method":    FIT_METHOD_TAG,
        "created_at":    datetime.datetime.now().isoformat(),
    }


def atomic_save(payload, path):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--det", type=int, required=True)
    parser.add_argument("--series", nargs="*", default=None,
                        help="Optional explicit series list to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be done (gap-fill vs refit vs already-up-to-date) without writing anything")
    parser.add_argument("--skip-refit", action="store_true",
                        help="Only fill missing series; leave existing old-fit checkpoints untouched")
    parser.add_argument("--cache-dir", default=None,
                        help=f"Override cache dir (default: {CACHE_DIR_DEFAULT})")
    args = parser.parse_args()
    det = args.det

    if det not in PTOF_RANGES:
        raise ValueError(f"zip{det} not in PTOF_RANGES")

    CACHE_DIR = args.cache_dir or CACHE_DIR_DEFAULT
    SERIES_CACHE_DIR = os.path.join(CACHE_DIR, f"zip{det}_series")
    os.makedirs(SERIES_CACHE_DIR, exist_ok=True)

    ptof_lo, ptof_hi = PTOF_RANGES[det]
    excluded = set(SERIES_EXCLUSIONS.get(det, []))
    series_list = [s for s in ALL_SERIES if s not in excluded]
    if args.series:
        wanted = set(args.series)
        unknown = sorted(wanted - set(ALL_SERIES))
        if unknown:
            raise ValueError(f"unknown series: {unknown}")
        series_list = [s for s in series_list if s in wanted]

    print(f"=== Zip{det} v2 (fill gaps + free-pretrigger fit)  PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}] ===")
    print(f"Series to check ({len(series_list)}): {series_list}")
    if args.dry_run:
        print("*** DRY RUN — no files will be written ***")

    n_uptodate = n_refit = n_filled = n_skipped = 0

    for series in series_list:
        ckpt_path = os.path.join(SERIES_CACHE_DIR, f"{series}.pkl")

        if os.path.exists(ckpt_path):
            try:
                with open(ckpt_path, "rb") as f:
                    payload = pickle.load(f)
            except Exception as exc:
                print(f"  {series}: checkpoint unreadable ({exc}); treating as missing")
                payload = None

            if payload is not None:
                if payload.get("fit_method") == FIT_METHOD_TAG:
                    print(f"  {series}: already free-pretrigger fit, skip")
                    n_uptodate += 1
                    continue
                if args.skip_refit:
                    print(f"  {series}: old fixed-pretrigger fit present, --skip-refit set, leaving as-is")
                    n_skipped += 1
                    continue
                print(f"  {series}: old fixed-pretrigger checkpoint found — re-fitting from cached raw_traces (no rawio)")
                if not args.dry_run:
                    new_payload = refit_series_payload(payload)
                    atomic_save(new_payload, ckpt_path)
                    print(f"  {series}: refit done, checkpoint updated in place")
                n_refit += 1
                continue

        # missing series: genuine gap, needs rawio
        print(f"  {series}: MISSING — needs raw MIDAS read")
        if args.dry_run:
            n_filled += 1
            continue

        sel_info = select_events_for_series(det, series, ptof_lo, ptof_hi)
        if sel_info is None:
            continue
        payload = build_payload_from_raw(det, series, sel_info)
        if payload is None:
            continue
        atomic_save(payload, ckpt_path)
        print(f"  {series}: gap filled, checkpoint saved (fit_method={FIT_METHOD_TAG})")
        n_filled += 1

    print(f"\n=== Zip{det} summary ===")
    print(f"  already up to date (free_pretrigger) : {n_uptodate}")
    print(f"  refit in place (old->free_pretrigger) : {n_refit}")
    print(f"  gap filled (rawio + free_pretrigger)  : {n_filled}")
    if args.skip_refit:
        print(f"  left untouched (--skip-refit)         : {n_skipped}")
    print("Done." + ("  (dry run, nothing written)" if args.dry_run else ""))
