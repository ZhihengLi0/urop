#!/usr/bin/env python3
"""
Two-stage per-event template analysis.

Stage 1 — PKL scan (fast):
  Load per-series pkl cache from raw_without_filter.
  For every event compute pretrigger noise, onset shift, check fit_ok + nrmse.
  Build per-channel data-driven thresholds (noise percentile, nrmse cutoff).
  Output: selected event numbers per series, per-channel thresholds.

Stage 2 — rawio re-read (only selected events):
  For each series that has a pkl, re-read ONLY the selected event numbers via rawio.
  Apply per-event:
    - pretrigger baseline subtraction (from the actual trace)
    - 100 kHz LP filter
    - data-driven onset detection → alignment to CANONICAL_PT
    - noise gate using the threshold from Stage 1
  Accumulate accepted traces → mean template + NxM 4-exp PCA (like v10).

Series not in the pkl → entirely skipped.

Usage:
    python per_event_analysis.py --det 16
    python per_event_analysis.py --det 16 --nrmse-max 0.12 --noise-pctile 80
"""

import argparse, os, pickle, json, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt
from sklearn.decomposition import PCA
import uproot

try:
    import rawio
except ImportError as exc:
    raise RuntimeError(
        "rawio is required — run inside the CDMS singularity environment") from exc

try:
    import ROOT
    from ROOT import TFile, TH1D
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    print("WARNING: ROOT not available — skipping ROOT file output")

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det',          type=int,   required=True)
parser.add_argument('--nrmse-max',    type=float, default=0.15)
parser.add_argument('--noise-pctile', type=int,   default=75)
parser.add_argument('--onset-frac',   type=float, default=0.02)
args = parser.parse_args()
det          = args.det
NRMSE_MAX    = args.nrmse_max
NOISE_PCTILE = args.noise_pctile
ONSET_FRAC   = args.onset_frac

# ── Paths ─────────────────────────────────────────────────────────────────────
PKL_CACHE    = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
                "/raw_without_filter/run/cache")
RAW_DIR      = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
RUN_DIR      = os.environ.get(
    "AI_RUN_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'run')))
PLOT_DIR     = os.path.join(RUN_DIR, 'plots')
STATS_DIR    = os.path.join(RUN_DIR, 'stats')
ROOT_DIR     = os.path.join(RUN_DIR, 'root_files')
for d in [PLOT_DIR, STATS_DIR, ROOT_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLERATE   = 625000
TRACELENGTH  = 32768
CANONICAL_PT = 16050          # all traces aligned here after Stage 2

NOISE_LO     = 12000          # pretrigger noise window in pkl traces
NOISE_HI     = 15500          # (already LP-filtered, normalized)
ONSET_LO     = 14000          # onset search window
ONSET_HI     = 16800

# Stage 2 filter / fit
FILTER_KHZ   = 100.0
WIN_START     = 13750          # fit/plot window start
T1_MIN, T1_MAX           = 1e-6, 5e-4
T_DECAY_MIN, T_DECAY_MAX = 5e-5, 2e-2
T3_DECAY_MAX             = 1e-1
T4_DECAY_MAX             = 5e-1
BASELINE_LIMIT           = 0.2
FIT_STRIDE               = 4
NEGATIVE_FRAC            = 0.05
NEGATIVE_TAIL            = 12000

# NxM
NXM_RMSE_MAX  = 0.15
MAX_NXM       = 300
N_COMPONENTS  = 5
PCA_COMPONENTS = N_COMPONENTS - 1

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

print(f"=== Zip{det} — NRMSE_MAX={NRMSE_MAX}  "
      f"NOISE_PCTILE={NOISE_PCTILE}  ONSET_FRAC={ONSET_FRAC} ===")

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  STAGE 1: PKL SCAN — thresholds + event selection
# ╚══════════════════════════════════════════════════════════════════════════════
series_dir = os.path.join(PKL_CACHE, f"zip{det}_series")
if not os.path.isdir(series_dir):
    raise FileNotFoundError(f"No pkl cache directory: {series_dir}")

pkl_files = sorted([
    os.path.join(series_dir, f)
    for f in os.listdir(series_dir) if f.endswith('.pkl')
])
print(f"\nStage 1: scanning {len(pkl_files)} series pkl files...")

# Per-channel accumulators for threshold computation
noise_all  = {c: [] for c in ALL_CHANS}   # pretrigger noise per event
nrmse_all  = {c: [] for c in ALL_CHANS}   # nrmse per event (fit_ok only)
onset_all  = {c: [] for c in ALL_CHANS}   # onset - CANONICAL_PT shift

# Per-series selected event numbers (events that pass Stage 1 cuts)
# selected[series][chan] = set of indices into the pkl trace list
# We also need to map pkl index → event number so Stage 2 can look them up.
# The pkl does not store event numbers, but the series pkl stores n_found events
# in the same order they were read; we store the pkl index positions.
# Stage 2 will re-select by scanning raw events and checking event number
# membership — so we need the actual event numbers from processed ROOT.
# Instead: we store which pkl indices pass Stage 1 so we can cross-reference
# after rawio reads.  We save (series → chan → set-of-good-pk-indices).

stage1_good = {}   # series -> {chan: set(indices)}

for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    try:
        with open(pkl_path, 'rb') as fh:
            data = pickle.load(fh)
    except Exception as exc:
        print(f"  {series}: load error — {exc}")
        continue

    stage1_good[series] = {}

    for c in ALL_CHANS:
        rts  = data.get('raw_traces',    {}).get(c, [])
        oks  = data.get('fit_ok_mask',   {}).get(c, [])
        fps  = data.get('fit_params_ch', {}).get(c, [])
        if not rts:
            continue

        good_idx = set()
        for i, tr in enumerate(rts):
            tr  = np.asarray(tr, dtype=np.float64)
            ok  = bool(oks[i]) if i < len(oks) else False
            fp  = fps[i]       if i < len(fps) else None
            if not ok or fp is None:
                continue
            nrmse = float(fp['nrmse'])
            if nrmse > NRMSE_MAX:
                continue

            # pretrigger noise on the LP-normalised pkl trace
            noise = float(np.std(tr[NOISE_LO:NOISE_HI]))

            # onset detection on the pkl trace (already normalised to ~1 at peak)
            seg   = tr[ONSET_LO:ONSET_HI]
            hits  = np.where(seg >= ONSET_FRAC)[0]
            if len(hits) == 0:
                continue
            onset = ONSET_LO + int(hits[0])
            onset_shift = onset - CANONICAL_PT

            noise_all[c].append(noise)
            nrmse_all[c].append(nrmse)
            onset_all[c].append(onset_shift)
            good_idx.add(i)

        stage1_good[series][c] = good_idx

    print(f"  {series}: ok")

# Compute per-channel noise threshold from the full distribution
noise_thr = {}
for c in ALL_CHANS:
    if noise_all[c]:
        noise_thr[c] = float(np.percentile(noise_all[c], NOISE_PCTILE))
    else:
        noise_thr[c] = np.inf

print(f"\nStage 1 thresholds (noise p{NOISE_PCTILE}):")
for c in ALL_CHANS:
    n = len(noise_all[c])
    thr = noise_thr[c]
    if n:
        n_pass = sum(1 for v in noise_all[c] if v <= thr)
        print(f"  {c}: thr={thr:.4f}  events_before_noise_cut={n}  "
              f"would_pass={n_pass}")

# Second pass: apply noise threshold to refine good indices per series
print("\nApplying noise threshold to Stage 1 selection...")
selected_evnums = {}  # series -> {chan: set of pkl indices after noise cut}

for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    if series not in stage1_good:
        continue
    try:
        with open(pkl_path, 'rb') as fh:
            data = pickle.load(fh)
    except Exception:
        continue

    selected_evnums[series] = {}
    for c in ALL_CHANS:
        rts  = data.get('raw_traces',    {}).get(c, [])
        oks  = data.get('fit_ok_mask',   {}).get(c, [])
        fps  = data.get('fit_params_ch', {}).get(c, [])
        good_pre = stage1_good[series].get(c, set())
        if not rts or not good_pre:
            selected_evnums[series][c] = set()
            continue

        final = set()
        for i in good_pre:
            tr    = np.asarray(rts[i], dtype=np.float64)
            noise = float(np.std(tr[NOISE_LO:NOISE_HI]))
            if noise <= noise_thr[c]:
                final.add(i)
        selected_evnums[series][c] = final

# Summarise Stage 1
print("\nStage 1 selection summary:")
stage1_counts = {c: 0 for c in ALL_CHANS}
for series, chd in selected_evnums.items():
    for c, idx in chd.items():
        stage1_counts[c] += len(idx)
for c in ALL_CHANS:
    print(f"  {c}: {stage1_counts[c]} good events across "
          f"{len(selected_evnums)} series")

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  STAGE 2: rawio RE-READ of selected events only
# ╚══════════════════════════════════════════════════════════════════════════════
print(f"\nStage 2: rawio re-read for selected events...")

# Replicate the exact PTOFamps filter used when generating the pkl so that the
# per-channel counters match the pkl's trace ordering exactly.
PROCESSED_DIR = ("/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4"
                 "/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged")
PROD_TAG = "Prompt_V07-02_C0.4.5"

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

if det not in PTOF_RANGES:
    raise ValueError(f"zip{det} not in PTOF_RANGES")
ptof_lo, ptof_hi = PTOF_RANGES[det]

def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype='low', fs=fs, output='sos')
    return sosfilt(sos, data)

def find_onset_from_raw(trace_lp, peak):
    threshold = ONSET_FRAC * peak
    seg = trace_lp[ONSET_LO:ONSET_HI]
    hits = np.where(seg >= threshold)[0]
    return None if len(hits) == 0 else ONSET_LO + int(hits[0])

def align_trace(trace, onset):
    shift   = CANONICAL_PT - onset
    aligned = np.zeros(TRACELENGTH, dtype=np.float64)
    if shift > 0:
        aligned[shift:] = trace[:TRACELENGTH - shift]
    elif shift < 0:
        aligned[:TRACELENGTH + shift] = trace[-shift:]
    else:
        aligned[:] = trace
    return aligned

# ── Stage-2 per-series checkpoint (survives job interruption) ─────────────────
S2_CACHE_DIR = os.path.join(RUN_DIR, 'stage2_cache', f'zip{det}')
os.makedirs(S2_CACHE_DIR, exist_ok=True)

channel_traces = {c: [] for c in ALL_CHANS}
series_done    = set()

print("\nChecking Stage-2 checkpoints...")
for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    ckpt = os.path.join(S2_CACHE_DIR, f'{series}.pkl')
    if not os.path.exists(ckpt):
        continue
    try:
        with open(ckpt, 'rb') as fh:
            ckpt_data = pickle.load(fh)
        n_loaded = 0
        for c in ALL_CHANS:
            trs = ckpt_data.get(c, [])
            channel_traces[c].extend(trs)
            n_loaded += len(trs)
        series_done.add(series)
        print(f"  {series}: checkpoint loaded ({n_loaded} traces)")
    except Exception as exc:
        print(f"  {series}: checkpoint broken ({exc}), will reprocess")

# ── Main Stage-2 loop ─────────────────────────────────────────────────────────
for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    if series not in selected_evnums:
        continue
    if series in series_done:
        continue   # already loaded from checkpoint

    any_selected = any(len(idx) > 0 for idx in selected_evnums[series].values())
    if not any_selected:
        continue

    # ── Load evnum_set + baselines from processed ROOT ────────────────────────
    proc_root = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(proc_root):
        print(f"  {series}: processed ROOT missing — skipping (cannot replicate event order)")
        continue
    try:
        with uproot.open(proc_root) as rf:
            trig_arr  = rf["rqDir/eventTree/TriggerType"].array(library="np")
            evnum_arr = rf["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
            ptof_arr  = rf[f"rqDir/zip{det}/PTOFamps"].array(library="np")
            sel_mask  = ((trig_arr == 1) &
                         (ptof_arr != -999999) &
                         (ptof_arr > ptof_lo) &
                         (ptof_arr < ptof_hi))
            evnum_set = set(int(e) for e in evnum_arr[sel_mask])
    except Exception as exc:
        print(f"  {series}: processed ROOT error — {exc}")
        continue

    raw_series_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_series_dir):
        print(f"  {series}: raw directory missing, skipping")
        continue

    needed_positions  = {c: selected_evnums[series].get(c, set()) for c in ALL_CHANS}
    series_ch_traces  = {c: [] for c in ALL_CHANS}   # per-series accumulator

    try:
        reader     = rawio.RawDataReader(raw_series_dir)
        nb_info    = reader.get_nb_events()
        total_evts = nb_info.get('NbEventsNotEmpty', nb_info.get('NbEvents', 50000))
        events_it  = reader.read_events(
            output_format=2, skip_empty=True, trigger_types=[1],
            nb_events=total_evts, detector_nums=[det], channel_names=ALL_CHANS)
    except Exception as exc:
        print(f"  {series}: rawio failed — {exc}")
        continue

    z_key = f'Z{det}'
    chan_counter = {c: 0 for c in ALL_CHANS}
    n_accepted_series = 0
    n_read = 0

    for event in events_it:
        evn = int(event['event']['EventNumber'])
        if evn not in evnum_set:
            continue  # PTOFamps filter — must stay before counter to match pkl ordering
        n_read += 1

        for c in ALL_CHANS:
            try:
                pulse = event[z_key][c]
            except KeyError:
                continue

            y = pulse.astype(np.float64)
            if len(y) < TRACELENGTH:
                continue

            idx_in_pkl = chan_counter[c]
            chan_counter[c] += 1

            if idx_in_pkl not in needed_positions[c]:
                continue

            y_s2 = y - float(np.mean(y[:5000]))
            y_lp = butter_lp(y_s2)

            peak = float(np.max(y_lp[CANONICAL_PT:CANONICAL_PT + 5000]))
            if not np.isfinite(peak) or peak <= 0:
                continue

            # noise normalized by peak to match Stage-1 units (pkl traces are peak-normalised)
            noise_s2 = float(np.std(y_lp[NOISE_LO:NOISE_HI])) / peak
            if noise_s2 > noise_thr[c]:
                continue

            tail = y_lp[CANONICAL_PT:min(TRACELENGTH, CANONICAL_PT + NEGATIVE_TAIL)]
            if len(tail) and np.min(tail) < -NEGATIVE_FRAC * peak:
                continue

            onset = find_onset_from_raw(y_lp, peak)
            if onset is None:
                continue

            aligned = align_trace(y_lp, onset)
            aligned_peak = float(np.max(aligned[CANONICAL_PT:CANONICAL_PT + 5000]))
            if aligned_peak <= 0:
                continue
            aligned /= aligned_peak

            series_ch_traces[c].append(aligned.astype(np.float32))
            n_accepted_series += 1

    # Merge into global accumulator and save checkpoint atomically
    for c in ALL_CHANS:
        channel_traces[c].extend(series_ch_traces[c])

    ckpt_path = os.path.join(S2_CACHE_DIR, f'{series}.pkl')
    ckpt_tmp  = ckpt_path + '.tmp'
    with open(ckpt_tmp, 'wb') as fh:
        pickle.dump(series_ch_traces, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(ckpt_tmp, ckpt_path)

    total_needed = sum(len(v) for v in needed_positions.values())
    print(f"  {series}: rawio scanned {n_read} PTOFamps events, "
          f"accepted {n_accepted_series}/{total_needed} — checkpoint saved")

print(f"\nStage 2 complete:")
for c in ALL_CHANS:
    print(f"  {c}: {len(channel_traces[c])} accepted traces")

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  TEMPLATE FITTING (on Stage-2 mean trace)
# ╚══════════════════════════════════════════════════════════════════════════════
x_full = np.arange(TRACELENGTH, dtype=float)
x_fit  = np.arange(WIN_START, TRACELENGTH, FIT_STRIDE, dtype=float)

def two_exp(x, amp, t1, t2, bl, pt):
    dt = np.maximum(x - pt, 0.0) / SAMPLERATE
    return np.where(x <= pt, bl, -(amp*np.exp(-dt/t1) - amp*np.exp(-dt/t2)) + bl)

def three_exp(x, a1, a2, t1, t2, t3, bl, pt):
    dt = np.maximum(x - pt, 0.0) / SAMPLERATE
    return np.where(x <= pt, bl,
                    -((a1+a2)*np.exp(-dt/t1) - a1*np.exp(-dt/t2)
                      - a2*np.exp(-dt/t3)) + bl)

def four_exp(x, a1, a2, a3, t1, t2, t3, t4, bl, pt):
    dt = np.maximum(x - pt, 0.0) / SAMPLERATE
    return np.where(x <= pt, bl,
                    -((a1+a2+a3)*np.exp(-dt/t1) - a1*np.exp(-dt/t2)
                      - a2*np.exp(-dt/t3) - a3*np.exp(-dt/t4)) + bl)

def fit_mean(tmpl):
    """Try 2/3/4-exp on the mean template; select by BIC."""
    tmpl   = tmpl / np.max(tmpl)
    y      = tmpl[WIN_START::FIT_STRIDE]
    pk_idx = int(np.argmax(tmpl))
    pt_g   = float(max(WIN_START, pk_idx - 300))
    pt_lo  = float(max(WIN_START, pt_g - 400))
    pt_hi  = float(min(pk_idx - 1, pt_g + 400))

    # rough guesses from waveform
    post    = tmpl[pk_idx:]
    inv_e   = np.where(post <= 1.0 / np.e)[0]
    t_fall  = inv_e[0] / SAMPLERATE if len(inv_e) else 3e-3
    t1_g    = np.clip(t_fall * 0.05, T1_MIN * 2, T1_MAX * 0.5)
    t2_g    = np.clip(t_fall * 0.3,  T_DECAY_MIN * 2, T_DECAY_MAX * 0.5)
    t3_g    = np.clip(t_fall,        T_DECAY_MIN * 2, T_DECAY_MAX * 0.5)

    candidates = []
    for mode in ('3-exp', '2-exp'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '3-exp':
                    popt, _ = curve_fit(
                        three_exp, x_fit, y,
                        p0=[0.6, 0.4, t1_g, t2_g, t3_g, 0.0, pt_g],
                        bounds=([0,0,T1_MIN,T_DECAY_MIN,T_DECAY_MIN,
                                 -BASELINE_LIMIT, pt_lo],
                                [np.inf,np.inf,T1_MAX,T_DECAY_MAX,T3_DECAY_MAX,
                                 BASELINE_LIMIT, pt_hi]),
                        maxfev=100000)
                    a1,a2,t1,t2,t3,bl,pt = popt
                    if t2 > t3: a1,a2,t2,t3 = a2,a1,t3,t2
                    full = three_exp(x_full, a1,a2,t1,t2,t3,0.0,float(CANONICAL_PT))
                    y_fit = three_exp(x_fit, a1,a2,t1,t2,t3,bl,pt)
                else:
                    popt, _ = curve_fit(
                        two_exp, x_fit, y,
                        p0=[1.0, t1_g, t2_g, 0.0, pt_g],
                        bounds=([0,T1_MIN,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,T1_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=100000)
                    a1,t1,t2,bl,pt = popt
                    full = two_exp(x_full, a1,t1,t2,0.0,float(CANONICAL_PT))
                    y_fit = two_exp(x_fit, a1,t1,t2,bl,pt)

            pk_f = float(np.max(full))
            if pk_f <= 0 or not np.all(np.isfinite(full)):
                raise ValueError('bad full trace')
            rmse = float(np.sqrt(np.mean((y - y_fit)**2)))
            if rmse > 0.25:
                raise ValueError(f'rmse={rmse:.3f} too high')
            rss  = max(float(np.sum((y - y_fit)**2)), 1e-300)
            bic  = len(y)*np.log(rss/len(y)) + len(popt)*np.log(len(y))
            candidates.append((bic, mode, popt, full/pk_f, rmse))
        except Exception:
            continue

    # 4-exp: build on best 3-exp
    best3 = next((c for c in candidates if c[1]=='3-exp'), None)
    if best3:
        _,_,p3,_,_ = best3
        a1_3,a2_3,t1_3,t2_3,t3_3,bl_3,pt_3 = p3
        t4_lo  = t3_3 * 1.5
        t4_ini = np.clip(t3_3*3, t4_lo*1.01, T4_DECAY_MAX*0.8)
        def _4f(x, a1,a2,a3,t4,bl,pt):
            return four_exp(x, a1,a2,a3, t1_3,t2_3,t3_3, t4, bl, pt)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                p4f,_ = curve_fit(
                    _4f, x_fit, y,
                    p0=[a1_3*0.6, a2_3, a1_3*0.3, t4_ini, bl_3, pt_3],
                    bounds=([0,0,0,t4_lo,-BASELINE_LIMIT,pt_lo],
                            [np.inf,np.inf,np.inf,T4_DECAY_MAX,
                             BASELINE_LIMIT,pt_hi]),
                    maxfev=100000)
            a1_4,a2_4,a3_4,t4,bl_4,pt_4 = p4f
            popt_4 = np.array([a1_4,a2_4,a3_4, t1_3,t2_3,t3_3,t4, bl_4, pt_4])
            full4  = four_exp(x_full, *popt_4) - bl_4
            pk_f4  = float(np.max(full4))
            yf4    = _4f(x_fit, *p4f)
            rmse4  = float(np.sqrt(np.mean((y - yf4)**2)))
            if pk_f4>0 and rmse4<0.25 and np.all(np.isfinite(full4)):
                rss4 = max(float(np.sum((y-yf4)**2)), 1e-300)
                bic4 = len(y)*np.log(rss4/len(y)) + len(popt_4)*np.log(len(y))
                candidates.append((bic4,'4-exp',popt_4, full4/pk_f4, rmse4))
        except Exception:
            pass

    if not candidates:
        raise RuntimeError('all fits failed')
    return min(candidates, key=lambda r: r[0])   # (bic, mode, popt, trace, rmse)

# ── Per-channel mean template ─────────────────────────────────────────────────
fit_results  = {}
mean_traces  = {}
t_ms         = x_full / SAMPLERATE * 1e3
lo_ms = (CANONICAL_PT - 600)  / SAMPLERATE * 1e3
hi_ms = (CANONICAL_PT + 5500) / SAMPLERATE * 1e3

for c in ALL_CHANS:
    traces = channel_traces[c]
    if not traces:
        print(f"\n{c}: no accepted traces")
        continue
    arr    = np.array(traces, dtype=np.float64)
    mean_t = np.mean(arr, axis=0)
    pk     = float(np.max(mean_t))
    if pk <= 0:
        continue
    mean_t /= pk
    mean_traces[c] = mean_t

    try:
        _, mode, popt, fit_t, rmse = fit_mean(mean_t)
        fit_results[c] = (mode, popt, fit_t, rmse)
        print(f"  {c}: [{mode}] RMSE={rmse:.4f}  n={len(traces)}")
    except RuntimeError as exc:
        print(f"  {c}: fit failed ({exc})")
        fit_results[c] = None

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  NxM: per-event 4-exp → canonical synthetic traces → mean + PCA
# ╚══════════════════════════════════════════════════════════════════════════════
print(f"\n── NxM per-event 4-exp fitting ──")
x_nxm = np.arange(WIN_START, TRACELENGTH, FIT_STRIDE, dtype=float)
nxm_bychan = {c: [] for c in ALL_CHANS}

for c in ALL_CHANS:
    traces = channel_traces[c]
    if not traces or fit_results.get(c) is None:
        print(f"  {c}: skipped (no data or no 1×1 params)")
        continue
    mode, popt, _, _ = fit_results[c]

    # Seed values from 1×1 fit
    if mode == '4-exp':
        a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
        seed = [a1+a2+a3, t1, (a1*t2+a2*t3+a3*t4)/(a1+a2+a3), 0.0,
                float(CANONICAL_PT)]
    elif mode == '3-exp':
        a1,a2,t1,t2,t3,bl,pt = popt
        seed = [a1+a2, t1, (a1*t2+a2*t3)/(a1+a2), 0.0, float(CANONICAL_PT)]
    else:
        a1,t1,t2,bl,pt = popt
        seed = [a1, t1, t2, 0.0, float(CANONICAL_PT)]

    n_acc = n_rej = 0
    n_take = min(len(traces), MAX_NXM)
    indices = np.linspace(0, len(traces)-1, n_take, dtype=int)

    for i in indices:
        tr = np.asarray(traces[i], dtype=np.float64)
        tr_pk = float(np.max(tr[CANONICAL_PT:CANONICAL_PT+5000]))
        if tr_pk <= 0 or not np.all(np.isfinite(tr)):
            n_rej += 1; continue

        y_r = tr[WIN_START::FIT_STRIDE]
        p0  = [seed[0]*tr_pk, seed[1], seed[2],
               float(np.median(tr[WIN_START:WIN_START+500])),
               float(CANONICAL_PT)]

        # Step 1: 2-exp
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                p2,_ = curve_fit(
                    two_exp, x_nxm, y_r, p0=p0,
                    bounds=([0,T1_MIN,T_DECAY_MIN,-np.inf,float(WIN_START)],
                            [np.inf,T1_MAX,T_DECAY_MAX,np.inf,
                             float(TRACELENGTH-500)]),
                    maxfev=50000)
        except Exception:
            n_rej += 1; continue
        amp2,t1f,t2f,bl2,pt2 = p2
        if (amp2 <= 0 or t2f <= t1f*1.05 or
                t1f <= T1_MIN*1.1 or t1f >= T1_MAX*0.98 or
                t2f >= T_DECAY_MAX*0.98):
            n_rej += 1; continue

        # Step 2: 3-exp (t1,t2 fixed)
        t3_lo  = t2f*1.5
        t3_ini = np.clip(t2f*3, t3_lo*1.01, T3_DECAY_MAX*0.8)
        def _3f(x, a1,a2,t3,bl,pt):
            return three_exp(x, a1,a2, t1f,t2f,t3, bl,pt)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                p3,_ = curve_fit(
                    _3f, x_nxm, y_r,
                    p0=[amp2*0.8, amp2*0.2, t3_ini, bl2, pt2],
                    bounds=([0,0,t3_lo,-np.inf,float(WIN_START)],
                            [np.inf,np.inf,T3_DECAY_MAX,np.inf,
                             float(TRACELENGTH-500)]),
                    maxfev=50000)
        except Exception:
            n_rej += 1; continue
        a1_3,a2_3,t3f,bl3,pt3 = p3
        if a1_3<=0 or t3f>=T3_DECAY_MAX*0.98:
            n_rej += 1; continue

        # Step 3: 4-exp (t1,t2,t3 fixed)
        t4_lo  = t3f*1.5
        t4_ini = np.clip(t3f*3, t4_lo*1.01, T4_DECAY_MAX*0.8)
        def _4f(x, a1,a2,a3,t4,bl,pt):
            return four_exp(x, a1,a2,a3, t1f,t2f,t3f,t4, bl,pt)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                p4,_ = curve_fit(
                    _4f, x_nxm, y_r,
                    p0=[a1_3*0.6, a2_3, a1_3*0.3, t4_ini, bl3, pt3],
                    bounds=([0,0,0,t4_lo,-np.inf,float(WIN_START)],
                            [np.inf,np.inf,np.inf,T4_DECAY_MAX,np.inf,
                             float(TRACELENGTH-500)]),
                    maxfev=50000)
        except Exception:
            n_rej += 1; continue
        a1_4,a2_4,a3_4,t4,bl4,pt4 = p4
        yf4   = _4f(x_nxm, *p4)
        nrmse = float(np.sqrt(np.mean((y_r - yf4)**2))) / tr_pk
        if (a1_4<=0 or t4>=T4_DECAY_MAX*0.98 or nrmse>NXM_RMSE_MAX):
            n_rej += 1; continue

        # Canonical synthetic trace (pretrigger pinned to CANONICAL_PT)
        synth = four_exp(x_full, a1_4,a2_4,a3_4, t1f,t2f,t3f,t4, 0.0,
                         float(CANONICAL_PT))
        pk_s  = float(np.max(synth))
        if (not np.all(np.isfinite(synth)) or pk_s<=0 or
                np.min(synth) < -1e-10):
            n_rej += 1; continue

        nxm_bychan[c].append((synth / pk_s).astype(np.float32))
        n_acc += 1

    print(f"  {c}: {n_acc} NxM accepted, {n_rej} rejected")

# ── Mean + PCA ────────────────────────────────────────────────────────────────
def mean_plus_pca(arr):
    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2 or len(arr) <= PCA_COMPONENTS:
        raise RuntimeError(f'need >{PCA_COMPONENTS} traces, got {len(arr)}')
    if not np.all(np.isfinite(arr)) or np.any(arr[:, :CANONICAL_PT+1] != 0.0):
        raise RuntimeError('fixed-pretrigger check failed')
    mean_r = np.mean(arr, axis=0)
    mean_r[:CANONICAL_PT+1] = 0.0
    mean_r = np.maximum(mean_r, 0.0)
    pk = float(np.max(mean_r))
    if pk <= 0:
        raise RuntimeError('zero mean peak')
    pca = PCA(PCA_COMPONENTS, svd_solver='full').fit(arr)
    res = pca.components_.copy()
    res[:, :CANONICAL_PT+1] = 0.0
    physical = [mean_r / pk]
    for i in range(PCA_COMPONENTS):
        d = res[i]
        sigma = float(np.sqrt(pca.explained_variance_[i]))
        opts  = []
        for sgn in (1.0, -1.0):
            sd = sgn * d
            neg = sd < 0
            a_max = np.min(mean_r[neg] / -sd[neg]) if np.any(neg) else np.inf
            opts.append((min(sigma, 0.98*a_max), sd))
        alpha, direction = max(opts, key=lambda r: r[0])
        cand = np.maximum(mean_r + alpha*direction, 0.0)
        cand[:CANONICAL_PT+1] = 0.0
        pk2 = float(np.max(cand))
        if pk2 <= 0:
            raise RuntimeError(f'PCA component {i} invalid')
        physical.append(cand / pk2)
    return np.asarray(physical), pca.explained_variance_ratio_

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  PLOTS
# ╚══════════════════════════════════════════════════════════════════════════════
stats_out = {}

for c in ALL_CHANS:
    traces = channel_traces[c]
    n = len(traces)
    stats_out[c] = {
        'n_accepted_stage2': n,
        'noise_threshold': noise_thr.get(c),
        'nrmse_max': NRMSE_MAX,
        'noise_pctile': NOISE_PCTILE,
        'onset_frac': ONSET_FRAC,
    }
    if n == 0:
        continue
    if n > 0 and noise_all[c]:
        stats_out[c]['nrmse_stage1_median'] = float(np.median(nrmse_all[c]))
        stats_out[c]['onset_shift_median']  = float(np.median(onset_all[c]))
        stats_out[c]['onset_shift_std']     = float(np.std(onset_all[c]))

    arr    = np.array(traces, dtype=np.float32)
    mean_t = mean_traces.get(c)
    if mean_t is None:
        continue
    fit_r  = fit_results.get(c)
    alpha  = max(0.04, min(0.35, 12.0 / n))

    # ── Overlay plot ─────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(17, 5), sharey=True)
    fig.suptitle(
        f'Zip{det} / {c}  —  onset-aligned, noise-gated, nrmse≤{NRMSE_MAX}\n'
        f'accepted {n} events  |  noise≤p{NOISE_PCTILE}={noise_thr.get(c,0):.4f}  '
        f'|  onset_frac={ONSET_FRAC}',
        fontsize=10)

    ax = axes[0]
    for tr in arr:
        ax.plot(t_ms, tr, lw=0.35, alpha=alpha, color='steelblue')
    ax.axvline(CANONICAL_PT/SAMPLERATE*1e3, color='k', lw=0.8,
               ls=':', alpha=0.6, label='Canonical pretrigger')
    ax.set_xlim(lo_ms, hi_ms); ax.set_ylim(-0.08, 1.18)
    ax.set_xlabel('Time (ms)'); ax.set_ylabel('Norm. amplitude')
    ax.set_title(f'Stage-2 re-processed traces  n={n}')
    ax.legend(fontsize=8); ax.grid(alpha=0.2, ls=':')

    ax2 = axes[1]
    for tr in arr:
        ax2.plot(t_ms, tr, lw=0.35, alpha=alpha, color='steelblue')
    ax2.plot(t_ms, mean_t, color='crimson', lw=2.2,
             label=f'Mean (n={n})', zorder=5)
    if fit_r is not None:
        mode, popt, fit_t, rmse = fit_r
        ax2.plot(t_ms, fit_t, color='darkorange', lw=1.6, ls='--',
                 label=f'{mode} fit  RMSE={rmse:.4f}', zorder=6)
    ax2.axvline(CANONICAL_PT/SAMPLERATE*1e3, color='k', lw=0.8,
                ls=':', alpha=0.6)
    ax2.set_xlim(lo_ms, hi_ms)
    ax2.set_xlabel('Time (ms)')
    ax2.set_title('+ Mean + analytical fit')
    ax2.legend(fontsize=9); ax2.grid(alpha=0.2, ls=':')

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out = os.path.join(PLOT_DIR, f'zip{det}_{c}_aligned.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {out}")

    # ── Diagnostics: Stage-1 distributions ───────────────────────────────────
    fig2, axes2 = plt.subplots(1, 3, figsize=(15, 4))
    fig2.suptitle(f'Zip{det} / {c} — Stage-1 per-event distributions', fontsize=10)

    def _hist(ax, vals, label, cut=None, color='steelblue'):
        vals = [v for v in vals if v is not None and np.isfinite(v)]
        if not vals:
            ax.set_title(f'{label}: no data'); return
        ax.hist(vals, bins=60, color=color, alpha=0.75, edgecolor='none')
        if cut is not None:
            ax.axvline(cut, color='crimson', lw=1.5, ls='--',
                       label=f'cut={cut:.4g}')
            ax.legend(fontsize=8)
        ax.set_xlabel(label); ax.set_ylabel('Count')
        ax.set_title(f'median={np.median(vals):.4g}')
        ax.grid(alpha=0.2)

    _hist(axes2[0], noise_all[c], 'Pretrigger noise (std)',
          cut=noise_thr.get(c), color='steelblue')
    _hist(axes2[1], nrmse_all[c], 'NRMSE (fit_ok events)',
          cut=NRMSE_MAX, color='darkorange')
    _hist(axes2[2], onset_all[c], 'Onset shift vs CANONICAL_PT (samples)',
          color='seagreen')

    fig2.tight_layout(rect=[0, 0, 1, 0.93])
    out2 = os.path.join(PLOT_DIR, f'zip{det}_{c}_diagnostics.png')
    fig2.savefig(out2, dpi=130, bbox_inches='tight')
    plt.close(fig2)

    # ── NxM PCA plot ─────────────────────────────────────────────────────────
    synths = nxm_bychan[c]
    if len(synths) > PCA_COMPONENTS:
        try:
            components, var = mean_plus_pca(np.array(synths))
            colors = plt.cm.tab10(np.linspace(0, 0.9, N_COMPONENTS))
            fig3, ax3 = plt.subplots(figsize=(14, 5))
            for i in range(N_COMPONENTS):
                lbl = ('nxm0 — mean' if i==0 else
                       f'nxm{i} — PC{i-1} ({var[i-1]*100:.2f}%)')
                ax3.plot(t_ms, components[i], lw=1.0,
                         color=colors[i], label=lbl)
            ax3.set_xlim(lo_ms, hi_ms)
            ax3.set_xlabel('Time (ms)'); ax3.set_ylabel('Norm. amplitude')
            ax3.legend(fontsize=9); ax3.grid(alpha=0.3)
            fig3.suptitle(
                f'Zip{det}/{c} — NxM mean + PCA  ({len(synths)} accepted)',
                fontsize=11)
            fig3.tight_layout()
            out3 = os.path.join(PLOT_DIR, f'zip{det}_{c}_nxm_pca.png')
            fig3.savefig(out3, dpi=150, bbox_inches='tight')
            plt.close(fig3)
            print(f"  Saved NxM PCA: {out3}")
        except RuntimeError as exc:
            print(f"  {c}: NxM PCA failed — {exc}")

# ── Summary table ─────────────────────────────────────────────────────────────
chans_with = [c for c in ALL_CHANS if stats_out.get(c, {}).get('n_accepted_stage2', 0) > 0]
fig_s, ax_s = plt.subplots(figsize=(14, 5))
ax_s.axis('off')
cols = ['Channel','Stage1\ngood','Stage2\naccepted','NxM\nsynth',
        'Noise thr','Onset shift\nmedian (smp)','NRMSE\nmedian']
rows = []
for c in chans_with:
    s   = stats_out[c]
    na2 = s.get('n_accepted_stage2', 0)
    rows.append([
        c,
        str(stage1_counts.get(c, 0)),
        str(na2),
        str(len(nxm_bychan.get(c, []))),
        f"{s.get('noise_threshold', 0):.4f}",
        f"{s.get('onset_shift_median', 0):.1f}" if s.get('onset_shift_median') is not None else '–',
        f"{s.get('nrmse_stage1_median', 0):.4f}" if s.get('nrmse_stage1_median') is not None else '–',
    ])
if rows:
    tbl = ax_s.table(cellText=rows, colLabels=cols, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1.0, 1.6)
    for j in range(len(cols)):
        tbl[(0,j)].set_facecolor('#2c3e50')
        tbl[(0,j)].set_text_props(color='white', fontweight='bold')
ax_s.set_title(
    f'Zip{det} — two-stage per-event summary\n'
    f'NRMSE≤{NRMSE_MAX}  |  noise≤p{NOISE_PCTILE}  |  onset_frac={ONSET_FRAC}',
    fontsize=11, pad=18)
fig_s.tight_layout()
out_s = os.path.join(PLOT_DIR, f'zip{det}_summary.png')
fig_s.savefig(out_s, dpi=130, bbox_inches='tight')
plt.close(fig_s)
print(f"\nSaved summary: {out_s}")

# ╔══════════════════════════════════════════════════════════════════════════════
# ║  ROOT FILES + TIME CONSTANTS (same format as v10)
# ╚══════════════════════════════════════════════════════════════════════════════

# Build PT / PS1 / PS2 sum traces (re-pin all to CANONICAL_PT via fit params)
fit_avg_trace = {}
fit_params_out = {}

for c in ALL_CHANS:
    fr = fit_results.get(c)
    if fr is None:
        continue
    mode, popt, fit_t, rmse = fr
    # Re-pin to CANONICAL_PT using the analytical fit
    if mode == '4-exp':
        a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
        tr = four_exp(x_full, a1,a2,a3,t1,t2,t3,t4, 0.0, float(CANONICAL_PT))
        fit_params_out[c] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3, 't4': t4}
    elif mode == '3-exp':
        a1,a2,t1,t2,t3,bl,pt = popt
        tr = three_exp(x_full, a1,a2,t1,t2,t3, 0.0, float(CANONICAL_PT))
        fit_params_out[c] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3}
    else:
        a1,t1,t2,bl,pt = popt
        tr = two_exp(x_full, a1,t1,t2, 0.0, float(CANONICAL_PT))
        fit_params_out[c] = {'mode': mode, 't1': t1, 't2': t2}
    pk = float(np.max(tr))
    if pk > 0:
        fit_avg_trace[c] = tr / pk
        fit_params_out[c]['rmse'] = rmse

# PS1 / PS2 / PT sums
for side, chans_s in [('PS1', ALL_CHANS[:6]), ('PS2', ALL_CHANS[6:])]:
    s = np.zeros(TRACELENGTH)
    for c in chans_s:
        if fit_avg_trace.get(c) is not None:
            s += fit_avg_trace[c]
    pk = float(np.max(s))
    if pk > 0:
        fit_avg_trace[side] = s / pk

pt = np.zeros(TRACELENGTH)
for c in ALL_CHANS:
    if fit_avg_trace.get(c) is not None:
        pt += fit_avg_trace[c]
pk = float(np.max(pt))
if pk > 0:
    fit_avg_trace['PT'] = pt / pk

write_chans = ALL_CHANS + ['PT', 'PS1', 'PS2']

# NxM agnostic (all-channel pool)
nxm_all_synth = []
for c in ALL_CHANS:
    nxm_all_synth.extend(nxm_bychan.get(c, []))

def _write_root(rf, chans_to_write, nxm_components=None):
    rf.mkdir(f"zip{det}").cd()
    for ch in chans_to_write:
        tr = fit_avg_trace.get(ch)
        if tr is None:
            continue
        tr_norm = tr / np.max(tr)
        h = TH1D(ch, ch, TRACELENGTH, 0, TRACELENGTH)
        for i, v in enumerate(tr_norm):
            h.SetBinContent(i+1, float(v))
        h.Write()
    if nxm_components is not None:
        for ch in ALL_CHANS:
            comps = nxm_components.get(ch)
            if comps is None:
                continue
            for i, comp in enumerate(comps):
                hname = f"{ch}nxm{i}"
                h = TH1D(hname, hname, TRACELENGTH, 0, TRACELENGTH)
                for j, v in enumerate(comp):
                    h.SetBinContent(j+1, float(v))
                h.Write()

if HAS_ROOT:
    # Agnostic NxM: pool all channels
    nxm_agnostic = {}
    if len(nxm_all_synth) > PCA_COMPONENTS:
        try:
            comp_ag, var_ag = mean_plus_pca(np.array(nxm_all_synth, dtype=float))
            for c in ALL_CHANS:
                nxm_agnostic[c] = comp_ag   # same basis for all channels
            print(f"\nAgnostic NxM PCA: {len(nxm_all_synth)} traces, "
                  f"{N_COMPONENTS} components")
        except RuntimeError as exc:
            print(f"Agnostic NxM PCA failed: {exc}")

    # Specific NxM: per channel
    nxm_specific = {}
    for c in ALL_CHANS:
        synths = nxm_bychan.get(c, [])
        if len(synths) > PCA_COMPONENTS:
            try:
                comp_ch, _ = mean_plus_pca(np.array(synths, dtype=float))
                nxm_specific[c] = comp_ch
            except RuntimeError:
                pass

    out_ag = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_agnostic.root")
    rf_ag  = TFile(out_ag, "RECREATE")
    _write_root(rf_ag, write_chans, nxm_components=nxm_agnostic)
    rf_ag.Close()
    print(f"Saved: {out_ag}")

    out_sp = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_specific.root")
    rf_sp  = TFile(out_sp, "RECREATE")
    _write_root(rf_sp, write_chans, nxm_components=nxm_specific)
    rf_sp.Close()
    print(f"Saved: {out_sp}")
else:
    print("ROOT not available — skipped ROOT file writing")

# Time constants JSON (same keys as v10)
tc_path = os.path.join(ROOT_DIR, f'time_constants_zip{det}.json')
with open(tc_path, 'w') as fh:
    json.dump(fit_params_out, fh, indent=2)
print(f"Saved: {tc_path}")

# ── JSON stats ────────────────────────────────────────────────────────────────
stats_path = os.path.join(STATS_DIR, f'zip{det}_per_event_stats.json')
with open(stats_path, 'w') as fh:
    json.dump(stats_out, fh, indent=2)
print(f"Saved stats:   {stats_path}")
print(f"\nDone. Zip{det} complete.")
