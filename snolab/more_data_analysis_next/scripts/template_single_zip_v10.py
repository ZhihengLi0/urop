#!/usr/bin/env python3
# coding: utf-8
# Tenth-iteration template generation for SNOLAB Run 4.
# Outputs two ROOT files per zip:
#   Templates_SNOLAB_R4_zip{det}_agnostic.root  — shared PCA basis across channels
#   Templates_SNOLAB_R4_zip{det}_specific.root  — independent PCA basis per channel
#
# Changes from ninth (v9) → tenth (v10):
#   100 kHz LP filter (was 4 kHz in v8/v9)
#   NxM synthetic traces normalized by peak before PCA (captures shape variation, not amplitude)
#   NxM PCA plot: single overlaid axes with tab10 colors + legend (was N stacked subplots)
#   New all_analytic_*_channels.png: cross-zip overlay for each channel
#
# nxm0 is the positive mean pulse; nxm1..4 are non-negative physical pulses
# displaced from that mean along the first four centered-PCA directions.
#
# Usage: python template_single_zip_v10.py --det <zip_number>

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
args = parser.parse_args()

import rawio
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import cdms
import ROOT
from ROOT import TFile, TH1D
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt
from sklearn.decomposition import PCA
import uproot
import os, warnings, pickle, json

print("CDMS Software Version:", cdms.get_global_version())

RUN_DIR = os.environ.get("R4_RUN_DIR", "").strip()
if RUN_DIR:
    RUN_DIR    = os.path.abspath(RUN_DIR)
    CACHE_DIR  = os.path.join(RUN_DIR, "cache")
    ROOT_AGNOSTIC = os.path.join(RUN_DIR, "agnostic", "root_files")
    ROOT_SPECIFIC = os.path.join(RUN_DIR, "specific", "root_files")
    PLOT_AGNOSTIC = os.path.join(RUN_DIR, "agnostic", "template_plots")
    PLOT_SPECIFIC = os.path.join(RUN_DIR, "specific", "template_plots")
else:
    CACHE_DIR     = "."
    ROOT_AGNOSTIC = "agnostic/root_files"
    ROOT_SPECIFIC = "specific/root_files"
    PLOT_AGNOSTIC = "agnostic/template_plots"
    PLOT_SPECIFIC = "specific/template_plots"

for d in [CACHE_DIR, ROOT_AGNOSTIC, ROOT_SPECIFIC, PLOT_AGNOSTIC, PLOT_SPECIFIC]:
    os.makedirs(d, exist_ok=True)

# ── Paths and global config ────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"
samplerate    = 625000
tracelength   = 32768

ALL_SERIES = [
    "24260617_063934", "24260617_175849", "24260617_190838", "24260617_234805",
    "24260618_013000", "24260618_025048", "24260618_031157", "24260618_062713",
    "24260618_073543", "24260618_202553",
    "24260619_023225", "24260619_061249", "24260619_075448", "24260619_093653",
    "24260619_144815", "24260619_174938", "24260619_210312", "24260619_230219",
    "24260620_032928", "24260621_021444", "24260621_041432", "24260621_075659",
    "24260621_111527", "24260621_145024", "24260622_022708", "24260622_042718",
    "24260622_073439",
]

# Per-detector series to exclude (from ops shift report)
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

# PTOFamps selection window around the Ge K-shell peak for each detector
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

det_tmpl = args.det
if det_tmpl not in PTOF_RANGES:
    raise ValueError(f"Zip{det_tmpl} not in PTOF_RANGES.")

print(f"\n=== Processing Zip{det_tmpl} ===")

# Build per-detector series list after applying exclusions
_excluded = set(SERIES_EXCLUSIONS.get(det_tmpl, []))
series_list = [s for s in ALL_SERIES if s not in _excluded]
all_proc_files = [os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{s}.root")
                  for s in series_list]
# Drop any file that doesn't exist on disk
_pairs = [(f, s) for f, s in zip(all_proc_files, series_list) if os.path.exists(f)]
if len(_pairs) < len(all_proc_files):
    _missing = [s for f, s in zip(all_proc_files, series_list)
                if not os.path.exists(f)]
    print(f"WARNING: {len(_missing)} series file(s) not found on disk: {_missing}")
all_proc_files, series_list = ([p[0] for p in _pairs], [p[1] for p in _pairs])
print(f"Using {len(series_list)} series for Zip{det_tmpl} "
      f"({len(SERIES_EXCLUSIONS.get(det_tmpl, []))} excluded)")

if not all_proc_files:
    raise RuntimeError(f"No processed files found on disk for Zip{det_tmpl}. "
                       f"Check PROCESSED_DIR and series list.")

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
dets_all  = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

_ref_file = all_proc_files[0]
det_chan_map = {}
with uproot.open(_ref_file) as _f:
    for _det in dets_all:
        try:
            _keys = list(_f[f'rqDir/zip{_det}'].keys())
            det_chan_map[_det] = [c for c in ALL_CHANS if f'{c}OFdelay' in _keys]
        except Exception:
            det_chan_map[_det] = []

chan_names = det_chan_map[det_tmpl]
print(f"Zip{det_tmpl} channels ({len(chan_names)}): {chan_names}")

# ── Event selection ────────────────────────────────────────────────────────────
PTOF_LO, PTOF_HI = PTOF_RANGES[det_tmpl]
chans = det_chan_map[det_tmpl]
print(f"\nZip{det_tmpl} — cut: {PTOF_LO:.2e} < PTOFamps < {PTOF_HI:.2e}")

sel_events      = {}
sel_ptof_delay  = {}
sel_baseline    = {}

for fpath, series in zip(all_proc_files, series_list):
    try:
        with uproot.open(fpath) as f:
            trig_type = f['rqDir/eventTree/TriggerType'].array(library='np')
            trig_det  = f['rqDir/eventTree/TriggerDetectorNum'].array(library='np')
            event_num = f['rqDir/eventTree/EventNumber'].array(library='np').astype(int)
            ptof_amps = f[f'rqDir/zip{det_tmpl}/PTOFamps'].array(library='np')
            mask   = (trig_type == 1) & (trig_det == det_tmpl) & (ptof_amps != -999999) & \
                     (ptof_amps > PTOF_LO) & (ptof_amps < PTOF_HI)
            evnums = event_num[mask]
            sel_events[series]     = evnums
            sel_baseline[series]   = {}
            try:
                ptof_delay_arr = f[f'rqDir/zip{det_tmpl}/PTOFdelay'].array(library='np')[mask]
            except Exception:
                ptof_delay_arr = np.zeros(len(evnums))
            sel_ptof_delay[series] = dict(zip(evnums, ptof_delay_arr))
            for c in chans:
                try:
                    bs_arr = f[f'rqDir/zip{det_tmpl}/{c}bs'].array(library='np')[mask]
                except Exception:
                    bs_arr = np.zeros(len(evnums))
                sel_baseline[series][c] = dict(zip(evnums, bs_arr))
        print(f'  {series}: {len(evnums)} events selected')
    except Exception as e:
        print(f'  {series}: ERROR — {e}')
        sel_events[series]     = np.array([], dtype=int)
        sel_ptof_delay[series] = {}
        sel_baseline[series]   = {c: {} for c in chans}

total = sum(len(v) for v in sel_events.values())
print(f'  → Zip{det_tmpl} total: {total} events')

# ── Read raw traces, filter and align ─────────────────────────────────────────
FILTER_CUTOFF_KHZ = 100.0

def butter_lowpass(data, cutoff_khz=FILTER_CUTOFF_KHZ, fs=625000, order=4):
    sos = butter(order, cutoff_khz * 1000, btype='low', fs=fs, output='sos')
    return sosfilt(sos, data)

def preprocess(y_raw, baseline_rq=None, baseline_n=5000):
    y = y_raw.astype(np.float64)
    if baseline_rq is None or not np.isfinite(baseline_rq) or baseline_rq == -999999:
        baseline = np.mean(y[:baseline_n])
    else:
        baseline = float(baseline_rq)
    y = y - baseline
    peak = np.max(y)
    if peak <= 0:
        return None, False
    return y, True

FORCE_RERUN   = False
CACHE_FILE    = os.path.join(CACHE_DIR, f"traces_cache_zip{det_tmpl}.pkl")
CACHE_VERSION = 11
ALIGN_PEAK_LO = 15000
ALIGN_PEAK_HI = 18000
RAW_SAMPLE_N  = 5
NEGATIVE_FRACTION = 0.05
NEGATIVE_TAIL_SAMPLES = 12000

if not FORCE_RERUN and os.path.exists(CACHE_FILE):
    print(f"Loading cache: {CACHE_FILE}")
    with open(CACHE_FILE, 'rb') as f:
        cache = pickle.load(f)
    if cache.get('cache_version') == CACHE_VERSION:
        channel_traces = cache['channel_traces']
        pf_traces      = cache['pf_traces']
        raw_sample     = cache['raw_sample']
        print("Loaded from cache.")
        for c in chans:
            print(f"  {c}: {len(channel_traces[c])} traces")
    else:
        print("Cache version mismatch; rebuilding.")
        FORCE_RERUN = True

if FORCE_RERUN or not os.path.exists(CACHE_FILE):
    channel_traces = {c: [] for c in chans}
    pf_traces      = []
    raw_sample     = {c: [] for c in chans}
    negative_rejected = {c: 0 for c in chans}

    z_key = f'Z{det_tmpl}'
    print(f"\nReading raw traces for Zip{det_tmpl}...")

    for series, evnums in sel_events.items():
        if len(evnums) == 0:
            continue
        raw_series_dir = f'{RAW_DIR}/{series}'
        if not os.path.isdir(raw_series_dir):
            print(f'  {series}: raw directory not found, skipping')
            continue
        evnum_set = set(int(n) for n in evnums)
        try:
            myreader   = rawio.RawDataReader(raw_series_dir)
            nb_info    = myreader.get_nb_events()
            total_evts = nb_info.get('NbEventsNotEmpty', nb_info.get('NbEvents', 50000))
            events_list = myreader.read_events(
                output_format=2, skip_empty=True, trigger_types=[1],
                nb_events=total_evts, detector_nums=[det_tmpl], channel_names=chans)
        except Exception as e:
            print(f'  {series}: rawio failed — {e}')
            continue

        n_good = 0
        for event in events_list:
            evn = int(event['event']['EventNumber'])
            if evn not in evnum_set:
                continue
            chan_aligned = {}
            for chan in chans:
                try:
                    pulse = event[z_key][chan]
                except KeyError:
                    continue
                baseline_rq = sel_baseline[series][chan].get(evn)
                y_sub, ok = preprocess(pulse, baseline_rq)
                if not ok:
                    continue
                delay_s = sel_ptof_delay[series].get(evn, 0.0)
                if not np.isfinite(delay_s):
                    continue
                shift    = -round(delay_s * samplerate)
                y_raw_al = np.zeros_like(y_sub)
                if shift > 0:
                    y_raw_al[shift:] = y_sub[:-shift]
                elif shift < 0:
                    y_raw_al[:shift] = y_sub[-shift:]
                else:
                    y_raw_al[:] = y_sub
                y_align  = butter_lowpass(y_raw_al)
                peak_idx = int(np.argmax(y_align))
                if peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
                    continue
                peak = np.max(y_align)
                if peak <= 0:
                    continue
                tail = y_align[peak_idx:min(tracelength,
                                           peak_idx + NEGATIVE_TAIL_SAMPLES)]
                if len(tail) and np.min(tail) < -NEGATIVE_FRACTION * peak:
                    negative_rejected[chan] += 1
                    continue
                channel_traces[chan].append(y_align)
                chan_aligned[chan] = y_align
                if len(raw_sample[chan]) < RAW_SAMPLE_N:
                    raw_sample[chan].append(y_raw_al)
                n_good += 1

            if len(chan_aligned) == len(chans):
                pf_sum  = sum(chan_aligned.values())
                pf_peak = np.max(pf_sum)
                if pf_peak > 0:
                    pf_traces.append(pf_sum)

        print(f'  {series}: {n_good} good channel-trace pairs')

    for c in chans:
        print(f'  {c}: {len(channel_traces[c])} traces, '
              f'{negative_rejected[c]} post-pulse >5% undershoots rejected')

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION,
                     'channel_traces': channel_traces,
                     'pf_traces': pf_traces,
                     'raw_sample': raw_sample,
                     'negative_rejected': negative_rejected,
                     'alignment': 'PTOFdelay'}, f)
    print(f"Cache saved: {CACHE_FILE}")

# ── Average template ───────────────────────────────────────────────────────────
average_trace = {}
for chan in chan_names:
    traces = channel_traces[chan]
    if len(traces) == 0:
        average_trace[chan] = None
    else:
        avg = np.mean(traces, axis=0)
        avg /= np.max(avg)
        average_trace[chan] = avg
        print(f"  {chan}: template from {len(traces)} traces")

# ── Exponential fitting ────────────────────────────────────────────────────────
def two_exp_fit(x, amp1, t1, t2, baseline, pretrigger):
    x = np.asarray(x, dtype=float)
    dt = np.maximum(x - pretrigger, 0.0) / samplerate
    pulse = -(amp1 * np.exp(-dt/t1) - amp1 * np.exp(-dt/t2))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

def three_exp_fit(x, amp1, amp2, t1, t2, t3, baseline, pretrigger):
    x = np.asarray(x, dtype=float)
    dt = np.maximum(x - pretrigger, 0.0) / samplerate
    pulse = -((amp1+amp2)*np.exp(-dt/t1)
              - amp1*np.exp(-dt/t2) - amp2*np.exp(-dt/t3))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

def four_exp_fit(x, amp1, amp2, amp3, t1, t2, t3, t4, baseline, pretrigger):
    x = np.asarray(x, dtype=float)
    dt = np.maximum(x - pretrigger, 0.0) / samplerate
    pulse = -((amp1+amp2+amp3)*np.exp(-dt/t1)
              - amp1*np.exp(-dt/t2) - amp2*np.exp(-dt/t3) - amp3*np.exp(-dt/t4))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

def auto_guess(tmpl, win_start):
    peak_idx = int(np.argmax(tmpl))
    smooth   = np.convolve(tmpl, np.ones(21)/21.0, mode='same')
    baseline = float(np.median(smooth[win_start:min(win_start+1000, peak_idx)]))
    derivative = np.convolve(np.diff(smooth), np.ones(21)/21.0, mode='same')
    edge_lo = max(win_start, peak_idx - 1500)
    edge    = edge_lo + int(np.argmax(derivative[edge_lo:peak_idx]))
    pt_guess = max(float(win_start), float(edge) - 50)
    post = tmpl[peak_idx:]
    fall_threshold = baseline + (float(tmpl[peak_idx]) - baseline) / np.e
    inv_e  = np.where(post <= fall_threshold)[0]
    t_fall = inv_e[0] / samplerate if len(inv_e) > 0 else 5e-3
    return pt_guess, t_fall*0.05, t_fall*0.3, t_fall, t_fall*5.0

WIN_START       = tracelength // 2 - 3000
FIT_STRIDE      = 4
T1_MIN          = 1e-6
T1_MAX          = 5e-4
T_DECAY_MIN     = 5e-5
T_DECAY_MAX     = 2e-2
T3_DECAY_MAX    = 1e-1
T4_DECAY_MAX    = 5e-1   # t4 is the slowest component; allow up to 500 ms
BASELINE_LIMIT  = 0.2
PRETRIGGER_TOL  = 300
CANONICAL_PT    = 16250                    # shared pretrigger for 1x1 and NxM

fit_params    = {}
fit_avg_trace = {}
fit_metrics   = {}

def measure_shape_times(trace):
    """Return waveform-defined 10-90 rise and peak-to-1/e fall times."""
    peak_idx = int(np.argmax(trace))
    peak = float(trace[peak_idx])
    if not np.isfinite(peak) or peak <= 0:
        return {'rise_10_90': np.nan, 'fall_1e': np.nan}
    pre = trace[:peak_idx + 1]
    i10s = np.where(pre >= 0.1 * peak)[0]
    i90s = np.where(pre >= 0.9 * peak)[0]
    post = trace[peak_idx:]
    ies = np.where(post <= peak / np.e)[0]
    rise = ((i90s[0] - i10s[0]) / samplerate
            if len(i10s) and len(i90s) else np.nan)
    fall = (ies[0] / samplerate if len(ies) else np.nan)
    return {'rise_10_90': float(rise), 'fall_1e': float(fall)}

def fit_average_template(tmpl):
    """Fit 2/3/4-exp models, reject boundary solutions, and select by BIC.

    4-exp is attempted sequentially: t1/t2/t3 are fixed from the best 3-exp
    result, then only t4 and the amplitude redistribution are free.
    """
    tmpl = tmpl / np.max(tmpl)
    x = np.arange(WIN_START, len(tmpl), FIT_STRIDE, dtype=float)
    y = tmpl[WIN_START::FIT_STRIDE]
    pt_g, t1_g, t2_g, t3_g, t4_g = auto_guess(tmpl, WIN_START)
    peak_idx = int(np.argmax(tmpl))
    pt_lo = max(float(WIN_START), pt_g - PRETRIGGER_TOL)
    pt_hi = min(float(peak_idx - 1), pt_g + PRETRIGGER_TOL)
    t1_p0 = np.clip(t1_g, 1e-6, T1_MAX * 0.8)
    t2_p0 = np.clip(t2_g, max(T_DECAY_MIN * 1.1, t1_p0 * 1.2),
                    T_DECAY_MAX * 0.8)
    t3_p0 = np.clip(max(t3_g, t2_p0 * 2), T_DECAY_MIN * 1.1,
                    T_DECAY_MAX * 0.8)
    candidates = []

    for mode in ['3-exp', '2-exp']:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '3-exp':
                    popt, _ = curve_fit(
                        three_exp_fit, x, y,
                        p0=[0.6, 0.4, t1_p0, t2_p0, t3_p0, 0.0, pt_g],
                        bounds=([0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,
                                 -BASELINE_LIMIT,pt_lo],
                                [np.inf,np.inf,T1_MAX,T_DECAY_MAX,T_DECAY_MAX,
                                 BASELINE_LIMIT,pt_hi]), maxfev=int(1e5))
                    a1,a2,t1,t2,t3,bl,pt = popt
                    if t2 > t3:
                        a1,a2,t2,t3 = a2,a1,t3,t2
                        popt = np.array([a1,a2,t1,t2,t3,bl,pt])
                    decay = [t2, t3]
                    full = three_exp_fit(np.arange(len(tmpl), dtype=float), *popt)
                    y_fit = three_exp_fit(x, *popt)
                else:
                    popt, _ = curve_fit(
                        two_exp_fit, x, y,
                        p0=[1.0,t1_p0,t2_p0,0.0,pt_g],
                        bounds=([0,1e-6,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,T1_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    a1,t1,t2,bl,pt = popt
                    decay = [t2]
                    full = two_exp_fit(np.arange(len(tmpl), dtype=float), *popt)
                    y_fit = two_exp_fit(x, *popt)

            full = full - bl
            peak_f = float(np.max(full))
            rmse = float(np.sqrt(np.mean((y - y_fit) ** 2)))
            if (not np.all(np.isfinite(full)) or peak_f <= 0 or
                    abs(int(np.argmax(full)) - peak_idx) > 750 or rmse > 0.25 or
                    t1 >= T1_MAX * 0.98 or any(t >= T_DECAY_MAX * 0.98 for t in decay) or
                    any(t <= t1 * 1.05 for t in decay)):
                raise RuntimeError('nonphysical or boundary fit')
            rss = max(float(np.sum((y - y_fit) ** 2)), np.finfo(float).tiny)
            bic = len(y) * np.log(rss / len(y)) + len(popt) * np.log(len(y))
            candidates.append((bic, mode, popt, full / peak_f, rmse))
        except (RuntimeError, ValueError):
            continue

    # 4-exp: fix t1/t2/t3 from the best 3-exp result, fit only t4 and
    # the amplitude redistribution.
    best_3exp = next((c for c in candidates if c[1] == '3-exp'), None)
    if best_3exp is not None:
        _, _, popt_3, _, _ = best_3exp
        a1_3, a2_3, t1_3, t2_3, t3_3, bl_3, pt_3 = popt_3
        t4_lower = t3_3 * 1.5
        t4_init  = np.clip(max(t4_g, t3_3 * 3.0), t4_lower * 1.01,
                           T4_DECAY_MAX * 0.8)

        def _4exp_1x1(x, amp1, amp2, amp3, t4, bl, pt):
            return four_exp_fit(x, amp1, amp2, amp3, t1_3, t2_3, t3_3, t4, bl, pt)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt4_free, _ = curve_fit(
                    _4exp_1x1, x, y,
                    p0=[a1_3 * 0.6, a2_3, a1_3 * 0.3, t4_init, bl_3, pt_3],
                    bounds=([0, 0, 0, t4_lower, -BASELINE_LIMIT, pt_lo],
                            [np.inf, np.inf, np.inf, T4_DECAY_MAX,
                             BASELINE_LIMIT, pt_hi]),
                    maxfev=int(1e5))
            amp1_4, amp2_4, amp3_4, t4, bl_4, pt_4 = popt4_free
            # Store the full 9-parameter vector so popt is self-contained.
            popt_full4 = np.array([amp1_4, amp2_4, amp3_4,
                                   t1_3, t2_3, t3_3, t4, bl_4, pt_4])
            full4 = (four_exp_fit(np.arange(len(tmpl), dtype=float), *popt_full4)
                     - bl_4)
            peak_f4 = float(np.max(full4))
            y_fit4  = _4exp_1x1(x, *popt4_free)
            rmse4   = float(np.sqrt(np.mean((y - y_fit4) ** 2)))
            if (not np.all(np.isfinite(full4)) or peak_f4 <= 0 or
                    abs(int(np.argmax(full4)) - peak_idx) > 750 or rmse4 > 0.25 or
                    t4 >= T4_DECAY_MAX * 0.98):
                raise RuntimeError('nonphysical or boundary 4-exp fit')
            rss4 = max(float(np.sum((y - y_fit4) ** 2)), np.finfo(float).tiny)
            bic4 = (len(y) * np.log(rss4 / len(y))
                    + len(popt_full4) * np.log(len(y)))
            candidates.append((bic4, '4-exp', popt_full4, full4 / peak_f4, rmse4))
        except (RuntimeError, ValueError):
            pass

    if not candidates:
        raise RuntimeError('all constrained 2/3/4-exp fits failed')
    _, mode, popt, full_norm, rmse = min(candidates, key=lambda item: item[0])
    return mode, popt, full_norm, rmse, measure_shape_times(full_norm)

for chan in chan_names:
    raw_tmpl = average_trace[chan]
    if raw_tmpl is None:
        fit_params[chan] = None; fit_avg_trace[chan] = None; continue

    try:
        mode, popt, full, rmse, metrics = fit_average_template(raw_tmpl)
        fit_params[chan] = (mode, popt)
        fit_avg_trace[chan] = full
        fit_metrics[chan] = metrics
        if mode == '4-exp':
            a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
            print(f"  {chan}: [4-exp] RMSE={rmse:.4f}, "
                  f"rise10-90={metrics['rise_10_90']*1e3:.3f} ms, "
                  f"fall1/e={metrics['fall_1e']*1e3:.3f} ms, "
                  f"t4={t4*1e3:.2f} ms")
        elif mode == '3-exp':
            print(f"  {chan}: [3-exp] RMSE={rmse:.4f}, "
                  f"rise10-90={metrics['rise_10_90']*1e3:.3f} ms, "
                  f"fall1/e={metrics['fall_1e']*1e3:.3f} ms")
        else:
            print(f"  {chan}: [2-exp] RMSE={rmse:.4f}, "
                  f"rise10-90={metrics['rise_10_90']*1e3:.3f} ms, "
                  f"fall1/e={metrics['fall_1e']*1e3:.3f} ms")
    except RuntimeError as e:
        print(f'  {chan}: fit failed ({e})')
        fit_params[chan] = None; fit_avg_trace[chan] = None

# Re-pin all 1x1 analytical traces to CANONICAL_PT so channel-to-channel
# pretrigger variation in the LP-averaged data does not propagate into the
# templates written to ROOT or into the PT/PS1/PS2 sums below.
_x_all = np.arange(tracelength, dtype=float)
for chan in chan_names:
    entry = fit_params.get(chan)
    if entry is None:
        continue
    mode, popt = entry
    if mode == '4-exp':
        a1, a2, a3, t1, t2, t3, t4, bl, pt = popt
        tr = four_exp_fit(_x_all, a1, a2, a3, t1, t2, t3, t4, 0.0,
                          float(CANONICAL_PT))
    elif mode == '3-exp':
        a1, a2, t1, t2, t3, bl, pt = popt
        tr = three_exp_fit(_x_all, a1, a2, t1, t2, t3, 0.0, float(CANONICAL_PT))
    else:
        a1, t1, t2, bl, pt = popt
        tr = two_exp_fit(_x_all, a1, t1, t2, 0.0, float(CANONICAL_PT))
    peak = float(np.max(tr))
    if peak > 0:
        fit_avg_trace[chan] = tr / peak

# ── Build PT / PS1 / PS2 ──────────────────────────────────────────────────────
ALL_12 = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
          'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

trace_s1 = np.zeros(tracelength)
for c in ALL_12[:6]:
    if fit_avg_trace.get(c) is not None:
        trace_s1 += fit_avg_trace[c]
if np.max(trace_s1) > 0:
    fit_avg_trace['PS1'] = trace_s1 / np.max(trace_s1)

trace_s2 = np.zeros(tracelength)
for c in ALL_12[6:]:
    if fit_avg_trace.get(c) is not None:
        trace_s2 += fit_avg_trace[c]
if np.max(trace_s2) > 0:
    fit_avg_trace['PS2'] = trace_s2 / np.max(trace_s2)

_pt_mode = None
_pt_popt = None
if pf_traces:
    pf_avg = np.mean(pf_traces, axis=0)
    pf_avg = pf_avg / np.max(pf_avg)
    average_trace['PT'] = pf_avg
    try:
        _pt_mode, _pt_popt, pt_full, rmse, metrics = fit_average_template(pf_avg)
        fit_avg_trace['PT'] = pt_full
        print(f"PT [{_pt_mode}]: RMSE={rmse:.4f}, "
              f"rise10-90={metrics['rise_10_90']*1e3:.3f} ms, "
              f"fall1/e={metrics['fall_1e']*1e3:.3f} ms")
    except RuntimeError:
        print("PT: constrained fit failed — using sum of positive channel fits")
        trace_pt = np.zeros(tracelength)
        for c in ALL_12:
            if fit_avg_trace.get(c) is not None:
                trace_pt += fit_avg_trace[c]
        if np.max(trace_pt) > 0:
            fit_avg_trace['PT'] = trace_pt / np.max(trace_pt)
else:
    trace_pt = np.zeros(tracelength)
    for c in ALL_12:
        if fit_avg_trace.get(c) is not None:
            trace_pt += fit_avg_trace[c]
    if np.max(trace_pt) > 0:
        fit_avg_trace['PT'] = trace_pt / np.max(trace_pt)

# Re-pin PT to CANONICAL_PT using the fitted time constants.
if _pt_mode is not None and _pt_popt is not None:
    if _pt_mode == '4-exp':
        a1, a2, a3, t1, t2, t3, t4, bl, pt = _pt_popt
        _tr_pt = four_exp_fit(_x_all, a1, a2, a3, t1, t2, t3, t4, 0.0,
                              float(CANONICAL_PT))
    elif _pt_mode == '3-exp':
        a1, a2, t1, t2, t3, bl, pt = _pt_popt
        _tr_pt = three_exp_fit(_x_all, a1, a2, t1, t2, t3, 0.0, float(CANONICAL_PT))
    else:
        a1, t1, t2, bl, pt = _pt_popt
        _tr_pt = two_exp_fit(_x_all, a1, t1, t2, 0.0, float(CANONICAL_PT))
    _pk_pt = float(np.max(_tr_pt))
    if _pk_pt > 0:
        fit_avg_trace['PT'] = _tr_pt / _pk_pt

# ── Write 1x1 templates to both ROOT files (shared) ───────────────────────────
write_chans = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
               'PAS2','PBS2','PCS2','PDS2','PES2','PFS2','PT','PS1','PS2']

out_agnostic = os.path.join(ROOT_AGNOSTIC, f"Templates_SNOLAB_R4_zip{det_tmpl}_agnostic.root")
out_specific = os.path.join(ROOT_SPECIFIC, f"Templates_SNOLAB_R4_zip{det_tmpl}_specific.root")

rf_agnostic = TFile(out_agnostic, "RECREATE")
rf_agnostic.mkdir(f"zip{det_tmpl}").cd()
for channel in write_chans:
    tr = fit_avg_trace.get(channel)
    if tr is None:
        continue
    tr_norm = tr / np.max(tr)
    h = TH1D(channel, channel, tracelength, 0, tracelength)
    for i, v in enumerate(tr_norm):
        h.SetBinContent(i+1, v)
    h.Write()

rf_specific = TFile(out_specific, "RECREATE")
rf_specific.mkdir(f"zip{det_tmpl}").cd()
for channel in write_chans:
    tr = fit_avg_trace.get(channel)
    if tr is None:
        continue
    tr_norm = tr / np.max(tr)
    h = TH1D(channel, channel, tracelength, 0, tracelength)
    for i, v in enumerate(tr_norm):
        h.SetBinContent(i+1, v)
    h.Write()

# ── Save time constants ────────────────────────────────────────────────────────
tc_out = {}
for chan, entry in fit_params.items():
    if entry is None:
        continue
    mode, popt = entry
    if mode == '4-exp':
        a1, a2, a3, t1, t2, t3, t4, bl, pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3, 't4': t4}
    elif mode == '3-exp':
        a1, a2, t1, t2, t3, bl, pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3}
    else:
        a1, t1, t2, bl, pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2}
    tc_out[chan].update(fit_metrics.get(chan, {}))

tc_path_agnostic = os.path.join(ROOT_AGNOSTIC, f'time_constants_zip{det_tmpl}.json')
tc_path_specific = os.path.join(ROOT_SPECIFIC, f'time_constants_zip{det_tmpl}.json')
for tc_path in [tc_path_agnostic, tc_path_specific]:
    with open(tc_path, 'w') as fj:
        json.dump(tc_out, fj, indent=2)
print(f"Time constants saved.")

# ── NxM: per-event 3-step fit → fixed-pretrigger traces → mean + PCA ──────────
# Step 1: 2-exp → fixes t1 (rise) and t2 (primary fall)
# Step 2: 3-exp (t1/t2 fixed) → fixes t3 (secondary fall)
# Step 3: 4-exp (t1/t2/t3 fixed) → adds t4 (slow fall)
# Canonical 4-exp synthetic trace with pretrigger pinned to CANONICAL_PT.

N_COMPONENTS  = 5
PCA_COMPONENTS = N_COMPONENTS - 1
MAX_NXM       = 300
NXM_RMSE_MAX  = 0.15
DIAG_PER_CHAN = 3

x_full_nxm = np.arange(tracelength, dtype=float)
x_nxm_fit  = np.arange(WIN_START, tracelength, FIT_STRIDE, dtype=float)

def nxm_p0(chan):
    entry = fit_params.get(chan)
    if entry is None:
        return None
    tag, popt = entry
    if tag == '4-exp':
        a1, a2, a3, t1, t2, t3, t4, bl, pt = popt
        amp = a1 + a2 + a3
        decay = ((a1*t2 + a2*t3 + a3*t4) / amp
                 if amp > 0 else max(t2, t3, t4))
        return [amp, t1, decay, 0.0, float(CANONICAL_PT)]
    elif tag == '3-exp':
        a1, a2, t1, t2, t3, bl, pt = popt
        amp = a1 + a2
        decay = (a1*t2 + a2*t3) / amp if amp > 0 else max(t2, t3)
        return [amp, t1, decay, 0.0, float(CANONICAL_PT)]
    else:
        a1, t1, t2, bl, pt = popt
        return [a1, t1, t2, 0.0, float(CANONICAL_PT)]

def make_fixed_pretrigger_synth_4exp(amp1, amp2, amp3, t1, t2, t3, t4):
    """Generate a 4-exp synthetic trace whose pretrigger is exactly CANONICAL_PT."""
    synth = four_exp_fit(
        x_full_nxm, amp1, amp2, amp3, t1, t2, t3, t4, 0.0, float(CANONICAL_PT))
    if np.any(synth[:CANONICAL_PT + 1] != 0.0):
        raise RuntimeError('fixed-pretrigger invariant failed (4-exp)')
    return synth

nxm_synth_all    = []
nxm_synth_bychan = {c: [] for c in chan_names}

print(f"\n── NxM per-event fitting (PTOFdelay aligned, CANONICAL_PT={CANONICAL_PT}) ──")
print(f"   100 kHz filtered → 2-exp fixes t1/t2 → 3-exp fixes t3 → 4-exp adds t4 → mean + PCA")

for chan in chan_names:
    traces    = channel_traces[chan]
    raw_samps = raw_sample.get(chan, [])
    if not traces:
        print(f"  {chan}: no traces"); continue
    p0 = nxm_p0(chan)
    if p0 is None:
        print(f"  {chan}: no 1x1 params for initial guess"); continue

    n_accept = 0
    n_reject = 0
    n_raw_negative = 0
    diag_done = 0

    n_take = min(len(traces), MAX_NXM)
    selected_indices = np.linspace(0, len(traces) - 1, n_take, dtype=int)
    for i in selected_indices:
        tr = traces[i]
        if not np.all(np.isfinite(tr)):
            n_reject += 1
            continue
        trace_peak = float(np.max(tr))
        if trace_peak <= 0:
            n_reject += 1
            continue
        peak_idx = int(np.argmax(tr))
        tail = tr[peak_idx:min(tracelength, peak_idx + NEGATIVE_TAIL_SAMPLES)]
        if len(tail) and np.min(tail) < -NEGATIVE_FRACTION * trace_peak:
            n_raw_negative += 1
            continue
        y_region = tr[WIN_START::FIT_STRIDE]
        p0_ev = list(p0)
        p0_ev[0] = trace_peak
        p0_ev[3] = float(np.median(tr[WIN_START:WIN_START + 500]))

        # ── Step 1: 2-exp → fix t1 and t2 ────────────────────────────────────
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt_2exp, _ = curve_fit(two_exp_fit, x_nxm_fit, y_region,
                    p0=p0_ev,
                    bounds=([0,1e-6,T_DECAY_MIN,-np.inf,float(WIN_START)],
                            [np.inf,T1_MAX,T_DECAY_MAX,np.inf,
                             float(tracelength-500)]),
                    maxfev=int(5e4))
        except (RuntimeError, ValueError):
            n_reject += 1; continue

        amp_2, t1_fix, t2_fix, bl_2, pt_2 = popt_2exp

        if amp_2 <= 0 or t2_fix <= t1_fix * 1.05:
            n_reject += 1; continue
        if t1_fix <= T1_MIN * 1.1 or t1_fix >= T1_MAX * 0.98:
            n_reject += 1; continue
        if t2_fix >= T_DECAY_MAX * 0.98:
            n_reject += 1; continue
        if not (WIN_START < pt_2 < tracelength - 500):
            n_reject += 1; continue

        # ── Step 2: 3-exp; t1 and t2 fixed → fix t3 ──────────────────────────
        def _3exp_t3_free(x, amp1, amp2, t3, bl, pt):
            return three_exp_fit(x, amp1, amp2, t1_fix, t2_fix, t3, bl, pt)

        t3_lower = t2_fix * 1.5
        t3_init  = np.clip(t2_fix * 3.0, t3_lower * 1.01, T3_DECAY_MAX * 0.8)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt_3exp, _ = curve_fit(
                    _3exp_t3_free, x_nxm_fit, y_region,
                    p0=[amp_2 * 0.8, amp_2 * 0.2, t3_init, bl_2, pt_2],
                    bounds=([0, 0, t3_lower, -np.inf, float(WIN_START)],
                            [np.inf, np.inf, T3_DECAY_MAX, np.inf,
                             float(tracelength - 500)]),
                    maxfev=int(5e4))
        except (RuntimeError, ValueError):
            n_reject += 1; continue

        amp1_3, amp2_3, t3_fix, bl_3, pt_3ev = popt_3exp

        if amp1_3 <= 0 or amp2_3 < 0:
            n_reject += 1; continue
        if t3_fix >= T3_DECAY_MAX * 0.98:
            n_reject += 1; continue
        if not (WIN_START < pt_3ev < tracelength - 500):
            n_reject += 1; continue

        # ── Step 3: 4-exp; t1, t2, t3 all fixed → free only t4 ───────────────
        def _4exp_t4_free(x, amp1, amp2, amp3, t4, bl, pt):
            return four_exp_fit(x, amp1, amp2, amp3,
                                t1_fix, t2_fix, t3_fix, t4, bl, pt)

        t4_lower = t3_fix * 1.5
        t4_init  = np.clip(t3_fix * 3.0, t4_lower * 1.01, T4_DECAY_MAX * 0.8)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt_4exp, _ = curve_fit(
                    _4exp_t4_free, x_nxm_fit, y_region,
                    p0=[amp1_3 * 0.6, amp2_3, amp1_3 * 0.3,
                        t4_init, bl_3, pt_3ev],
                    bounds=([0, 0, 0, t4_lower, -np.inf, float(WIN_START)],
                            [np.inf, np.inf, np.inf, T4_DECAY_MAX, np.inf,
                             float(tracelength - 500)]),
                    maxfev=int(5e4))
        except (RuntimeError, ValueError):
            n_reject += 1; continue

        amp1_4, amp2_4, amp3_4, t4, bl_4, pt_4ev = popt_4exp
        y_fit_win = _4exp_t4_free(x_nxm_fit, *popt_4exp)
        rmse  = float(np.sqrt(np.mean((y_region - y_fit_win)**2)))
        nrmse = rmse / trace_peak

        if amp1_4 <= 0 or amp2_4 < 0 or amp3_4 < 0:
            n_reject += 1; continue
        if t4 >= T4_DECAY_MAX * 0.98:
            n_reject += 1; continue
        if not (WIN_START < pt_4ev < tracelength - 500):
            n_reject += 1; continue
        if nrmse > NXM_RMSE_MAX:
            n_reject += 1; continue

        # Diagnostic plot: show 3-exp and 4-exp fits on top of the data trace.
        if diag_done < DIAG_PER_CHAN:
            y_3exp_disp = _3exp_t3_free(x_full_nxm, *popt_3exp) - bl_3
            y_4exp_disp = _4exp_t4_free(x_full_nxm, *popt_4exp) - bl_4
            for plot_dir in [PLOT_AGNOSTIC, PLOT_SPECIFIC]:
                fig_d, ax_d = plt.subplots(figsize=(13, 4))
                t_ms = x_full_nxm / samplerate * 1e3
                lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
                hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3
                if i < len(raw_samps):
                    ax_d.plot(t_ms, raw_samps[i], color='gray', lw=0.7,
                              alpha=0.9, label='Raw (unfiltered)')
                ax_d.plot(t_ms, tr, color='steelblue', lw=1.0, label='LP filtered')
                ax_d.plot(t_ms, y_3exp_disp, color='orange', lw=1.2, ls=':',
                          label=f'3-exp (t1={t1_fix*1e3:.3f} ms, '
                                f't2={t2_fix*1e3:.2f} ms, '
                                f't3={t3_fix*1e3:.2f} ms)')
                ax_d.plot(t_ms, y_4exp_disp, color='red', lw=1.5, ls='--',
                          label=f'4-exp NRMSE={nrmse:.4f}  '
                                f't4={t4*1e3:.2f} ms')
                ax_d.set_xlim(lo_ms, hi_ms)
                ax_d.set_xlabel('Time (ms)'); ax_d.set_ylabel('Amplitude')
                ax_d.set_title(f'Zip{det_tmpl}/{chan} event {i}\n'
                               f'rise tau={t1_fix*1e3:.3f} ms, '
                               f't2={t2_fix*1e3:.2f} ms, '
                               f't3={t3_fix*1e3:.2f} ms, '
                               f't4={t4*1e3:.2f} ms')
                ax_d.legend(fontsize=8); ax_d.grid(alpha=0.3)
                fig_d.tight_layout()
                fig_d.savefig(os.path.join(plot_dir,
                    f'nxm_diag_zip{det_tmpl}_{chan}_ev{i}.png'), dpi=120)
                plt.close(fig_d)
            diag_done += 1

        # 4-exp canonical synthetic trace pinned to CANONICAL_PT.
        try:
            synth = make_fixed_pretrigger_synth_4exp(
                amp1_4, amp2_4, amp3_4, t1_fix, t2_fix, t3_fix, t4)
        except RuntimeError:
            n_reject += 1; continue
        peak_s = np.max(synth)
        if (not np.all(np.isfinite(synth)) or peak_s <= 0 or
                np.min(synth) < -1e-12):
            n_reject += 1; continue

        nxm_synth_all.append(synth / peak_s)
        nxm_synth_bychan[chan].append(synth / peak_s)
        n_accept += 1

    print(f"  {chan}: {n_accept} accepted, {n_reject} rejected, "
          f"{n_raw_negative} >5% undershoot rejected")

# ── Alignment diagnostic plot ─────────────────────────────────────────────────
demo_chan = next((c for c in chan_names if nxm_synth_bychan.get(c)), None)
if demo_chan:
    raw_lp   = channel_traces[demo_chan][:30]
    synth_30 = nxm_synth_bychan[demo_chan][:30]
    t_ms_al  = x_full_nxm / samplerate * 1e3
    lo_ms = (CANONICAL_PT - 1500) / samplerate * 1e3
    hi_ms = (CANONICAL_PT + 4000) / samplerate * 1e3

    for plot_dir in [PLOT_AGNOSTIC, PLOT_SPECIFIC]:
        fig_al, axes_al = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
        for tr in raw_lp:
            axes_al[0].plot(t_ms_al, tr, alpha=0.3, lw=0.6, color='steelblue')
        axes_al[0].set_xlim(lo_ms, hi_ms)
        axes_al[0].set_title(f'Zip{det_tmpl}/{demo_chan} — LP aligned traces')
        axes_al[0].set_xlabel('Time (ms)'); axes_al[0].set_ylabel('Amplitude')
        axes_al[0].grid(alpha=0.3)
        for tr in synth_30:
            axes_al[1].plot(t_ms_al, tr, alpha=0.3, lw=0.6, color='darkorange')
        axes_al[1].set_xlim(lo_ms, hi_ms)
        axes_al[1].set_title(f'Canonical traces (pretrigger fixed at {CANONICAL_PT})')
        axes_al[1].set_xlabel('Time (ms)'); axes_al[1].grid(alpha=0.3)
        fig_al.suptitle(f'Zip{det_tmpl} NxM — Fixed-pretrigger alignment', fontsize=12)
        fig_al.tight_layout()
        fig_al.savefig(os.path.join(plot_dir, f'nxm_alignment_zip{det_tmpl}.png'), dpi=150)
        plt.close(fig_al)

# ── Mean + PCA helper ─────────────────────────────────────────────────────────
def mean_plus_pca(arr):
    arr = np.asarray(arr, dtype=float)
    if (arr.ndim != 2 or len(arr) <= PCA_COMPONENTS or
            not np.all(np.isfinite(arr)) or np.min(arr) < -1e-12 or
            np.any(arr[:, :CANONICAL_PT + 1] != 0.0)):
        raise RuntimeError('PCA input failed fixed-pretrigger/positivity checks')
    mean_raw = np.mean(arr, axis=0)
    mean_raw[:CANONICAL_PT + 1] = 0.0
    mean_raw = np.maximum(mean_raw, 0.0)
    mean_peak = float(np.max(mean_raw))
    if not np.isfinite(mean_peak) or mean_peak <= 0:
        raise RuntimeError('PCA mean pulse is invalid')
    pca = PCA(PCA_COMPONENTS, svd_solver='full').fit(arr)
    residuals = pca.components_.copy()
    residuals[:, :CANONICAL_PT + 1] = 0.0
    physical = [mean_raw / mean_peak]
    for i in range(PCA_COMPONENTS):
        direction = residuals[i]
        sigma = float(np.sqrt(pca.explained_variance_[i]))
        options = []
        for sign in (1.0, -1.0):
            signed = sign * direction
            negative = signed < 0
            alpha_max = (np.min(mean_raw[negative] / -signed[negative])
                         if np.any(negative) else np.inf)
            options.append((min(sigma, 0.98 * alpha_max), signed))
        alpha, direction = max(options, key=lambda item: item[0])
        candidate = mean_raw + alpha * direction
        candidate[:CANONICAL_PT + 1] = 0.0
        candidate = np.maximum(candidate, 0.0)
        peak = float(np.max(candidate))
        if not np.isfinite(peak) or peak <= 0:
            raise RuntimeError(f'PCA-derived physical template {i+1} is invalid')
        physical.append(candidate / peak)
    return np.asarray(physical), pca.explained_variance_ratio_

# ── AGNOSTIC PCA: pool all channels → one set of components per zip ───────────
print(f"\n── Agnostic mean + PCA: {len(nxm_synth_all)} traces from all channels ──")
rf_agnostic.cd(f"zip{det_tmpl}")

if len(nxm_synth_all) <= PCA_COMPONENTS:
    print(f"WARNING: not enough traces for agnostic PCA "
          f"({len(nxm_synth_all)}, need >{PCA_COMPONENTS})")
else:
    nxm_arr = np.array(nxm_synth_all)
    components_ag, var_ag = mean_plus_pca(nxm_arr)
    print("  nxm0: positive mean pulse")
    for i, v in enumerate(var_ag):
        print(f"  nxm{i+1}: physical pulse along PC{i} "
              f"({v*100:.2f}% residual variance)")

    t_ms_pca = x_full_nxm / samplerate * 1e3
    lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
    hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3

    _comp_colors = plt.cm.tab10(np.linspace(0, 0.9, N_COMPONENTS))
    fig_pca, ax_pca = plt.subplots(figsize=(14, 5))
    for i in range(N_COMPONENTS):
        lbl = ('nxm0 — mean pulse' if i == 0 else
               f'nxm{i} — PC{i-1} ({var_ag[i-1]*100:.2f}%)')
        ax_pca.plot(t_ms_pca, components_ag[i], lw=1.0,
                    color=_comp_colors[i], label=lbl)
    ax_pca.set_xlim(lo_ms, hi_ms)
    ax_pca.set_xlabel('Time (ms)'); ax_pca.set_ylabel('Amplitude (norm.)')
    ax_pca.legend(fontsize=9); ax_pca.grid(alpha=0.3)
    fig_pca.suptitle(f'Zip{det_tmpl} — Agnostic NxM mean + PCA '
                     '(100 kHz LP, PTOFdelay aligned, 4-exp, all channels pooled)',
                     fontsize=12)
    fig_pca.tight_layout()
    fig_pca.savefig(os.path.join(PLOT_AGNOSTIC,
        f'nxm_pca_components_zip{det_tmpl}.png'), dpi=150)
    plt.close(fig_pca)

    fig_var, ax_var = plt.subplots(figsize=(6, 4))
    ax_var.plot(range(1, N_COMPONENTS), var_ag*100, 'o-', color='steelblue')
    ax_var.set_xlabel('PCA direction used by NxM'); ax_var.set_ylabel('Explained variance (%)')
    ax_var.set_title(f'Zip{det_tmpl} Agnostic NxM — PCA residual variance')
    ax_var.set_yscale('log'); ax_var.grid(alpha=0.4)
    fig_var.tight_layout()
    fig_var.savefig(os.path.join(PLOT_AGNOSTIC,
        f'nxm_variance_zip{det_tmpl}.png'), dpi=120)
    plt.close(fig_var)

    for chan in chan_names:
        for i in range(N_COMPONENTS):
            hname  = f"{chan}nxm{i}"
            h      = ROOT.TH1D(hname, hname, tracelength, 0, tracelength)
            y = components_ag[i]
            for j, val in enumerate(y):
                h.SetBinContent(j+1, val)
            h.Write(); h.Delete()

    print(f"Agnostic NxM written: {N_COMPONENTS} components × {len(chan_names)} channels")

rf_agnostic.Close()
print(f"Saved: {out_agnostic}")

# ── SPECIFIC PCA: independent mean+PCA basis per channel ─────────────────────
print(f"\n── Specific mean + PCA: per-channel independent basis ──")
rf_specific.cd(f"zip{det_tmpl}")

t_ms_pca = x_full_nxm / samplerate * 1e3
lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3
n_chan_written = 0

for chan in chan_names:
    synth_list = nxm_synth_bychan[chan]
    if len(synth_list) <= PCA_COMPONENTS:
        print(f"  {chan}: {len(synth_list)} traces — need >{PCA_COMPONENTS}, skipping")
        continue

    nxm_chan_arr = np.array(synth_list)
    components_ch, var_ch = mean_plus_pca(nxm_chan_arr)
    print(f"  {chan}: {len(synth_list)} traces, "
          f"nxm0=mean, PC0={var_ch[0]*100:.1f}% PC1={var_ch[1]*100:.1f}%")

    _comp_colors = plt.cm.tab10(np.linspace(0, 0.9, N_COMPONENTS))
    fig_pca, ax_pca = plt.subplots(figsize=(14, 5))
    for i in range(N_COMPONENTS):
        lbl = ('nxm0 — mean pulse' if i == 0 else
               f'nxm{i} — PC{i-1} ({var_ch[i-1]*100:.2f}%)')
        ax_pca.plot(t_ms_pca, components_ch[i], lw=1.0,
                    color=_comp_colors[i], label=lbl)
    ax_pca.set_xlim(lo_ms, hi_ms)
    ax_pca.set_xlabel('Time (ms)'); ax_pca.set_ylabel('Amplitude (norm.)')
    ax_pca.legend(fontsize=9); ax_pca.grid(alpha=0.3)
    fig_pca.suptitle(f'Zip{det_tmpl}/{chan} — Specific NxM mean + PCA '
                     '(100 kHz LP, PTOFdelay aligned, 4-exp)',
                     fontsize=12)
    fig_pca.tight_layout()
    fig_pca.savefig(os.path.join(PLOT_SPECIFIC,
        f'nxm_pca_components_zip{det_tmpl}_{chan}.png'), dpi=150)
    plt.close(fig_pca)

    fig_var, ax_var = plt.subplots(figsize=(6, 4))
    ax_var.plot(range(1, N_COMPONENTS), var_ch*100, 'o-', color='steelblue')
    ax_var.set_xlabel('PCA direction used by NxM'); ax_var.set_ylabel('Explained variance (%)')
    ax_var.set_title(f'Zip{det_tmpl}/{chan} Specific PCA residuals')
    ax_var.set_yscale('log'); ax_var.grid(alpha=0.4)
    fig_var.tight_layout()
    fig_var.savefig(os.path.join(PLOT_SPECIFIC,
        f'nxm_variance_zip{det_tmpl}_{chan}.png'), dpi=120)
    plt.close(fig_var)

    for i in range(N_COMPONENTS):
        hname  = f"{chan}nxm{i}"
        h      = ROOT.TH1D(hname, hname, tracelength, 0, tracelength)
        y = components_ch[i]
        for j, val in enumerate(y):
            h.SetBinContent(j+1, val)
        h.Write(); h.Delete()
    n_chan_written += 1

rf_specific.Close()
print(f"Specific NxM written for {n_chan_written}/{len(chan_names)} channels")
print(f"Saved: {out_specific}")
print(f"\nDone. Zip{det_tmpl} complete.")
