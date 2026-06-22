#!/usr/bin/env python
# coding: utf-8
# Template generation for a single zip (detector).
# Usage: python template_single_zip.py --det <zip_number>

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True, help='Zip/detector number')
args = parser.parse_args()

import rawio
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import cdms
import ROOT
from ROOT import TFile, TH1D
from cats.cdataframe import CDataFrame
from scipy.optimize import curve_fit
from scipy.signal import butter, sosfilt
from scipy import signal
from sklearn.decomposition import PCA
import uproot
import glob, os, warnings, pickle

print("CDMS Software Version:", cdms.get_global_version())

# Optional isolated run directory.  If unset, retain the historical paths.
RUN_DIR = os.environ.get("R4_RUN_DIR", "").strip()
if RUN_DIR:
    RUN_DIR = os.path.abspath(RUN_DIR)
    CACHE_DIR = os.path.join(RUN_DIR, "cache")
    ROOT_DIR = os.path.join(RUN_DIR, "root_files")
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(ROOT_DIR, exist_ok=True)
else:
    CACHE_DIR = "."
    ROOT_DIR = "root_files"

# ── Paths and global config ────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"
samplerate    = 625000
tracelength   = 32768

all_proc_files = sorted(glob.glob(f"{PROCESSED_DIR}/{PROD_TAG}_*.root"))
series_list    = [os.path.basename(f).replace(f"{PROD_TAG}_", "").replace(".root", "") for f in all_proc_files]
print(f"Found {len(series_list)} series")

PTOF_RANGES = {
     1: (7.5e-7, 1.05e-6),
     4: (1.1e-6,  1.6e-6),
     6: (1.1e-6,  2.0e-6),
     7: (7.0e-7,  1.2e-6),
    10: (1.1e-6,  1.7e-6),
    15: (2.0e-6,  3.0e-6),
    16: (2.4e-6,  3.5e-6),
    18: (2.3e-6,  3.6e-6),
}

det_tmpl = args.det
if det_tmpl not in PTOF_RANGES:
    raise ValueError(f"Zip{det_tmpl} not in PTOF_RANGES. Valid: {list(PTOF_RANGES.keys())}")

print(f"\n=== Processing Zip{det_tmpl} ===")

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

dets_all = [1, 4, 6, 7, 9, 10, 15, 16, 18, 24]

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

sel_events   = {}
sel_delay    = {}
sel_baseline = {}

for fpath, series in zip(all_proc_files, series_list):
    try:
        with uproot.open(fpath) as f:
            trig_type = f['rqDir/eventTree/TriggerType'].array(library='np')
            event_num = f['rqDir/eventTree/EventNumber'].array(library='np').astype(int)
            ptof_amps = f[f'rqDir/zip{det_tmpl}/PTOFamps'].array(library='np')

            mask   = (trig_type == 1) & (ptof_amps != -999999) & \
                     (ptof_amps > PTOF_LO) & (ptof_amps < PTOF_HI)
            evnums = event_num[mask]

            sel_events[series]   = evnums
            sel_delay[series]    = {}
            sel_baseline[series] = {}
            for c in chans:
                try:
                    delay_arr = f[f'rqDir/zip{det_tmpl}/{c}OFdelay'].array(library='np')[mask]
                    bs_arr    = f[f'rqDir/zip{det_tmpl}/{c}bs'].array(library='np')[mask]
                except Exception:
                    delay_arr = np.zeros(len(evnums))
                    bs_arr    = np.zeros(len(evnums))
                sel_delay[series][c]    = dict(zip(evnums, delay_arr))
                sel_baseline[series][c] = dict(zip(evnums, bs_arr))

        print(f'  {series}: {len(evnums)} events selected')
    except Exception as e:
        print(f'  {series}: ERROR — {e}')
        sel_events[series]   = np.array([], dtype=int)
        sel_delay[series]    = {c: {} for c in chans}
        sel_baseline[series] = {c: {} for c in chans}

total = sum(len(v) for v in sel_events.values())
print(f'  → Zip{det_tmpl} total: {total} events')
if total < 100:
    print(f"  WARNING: only {total} events — consider widening PTOF_RANGES[{det_tmpl}]")

# ── Read raw traces, filter and align ─────────────────────────────────────────
def butter_lowpass(data, cutoff_khz=10.0, fs=625000, order=4):
    sos = butter(order, cutoff_khz * 1000, btype='low', fs=fs, output='sos')
    return sosfilt(sos, data)

def preprocess(y_raw, baseline_rq=None, baseline_n=5000):
    y = y_raw.astype(np.float64)
    # Use the processed RQ baseline, as in the reference template notebook.
    # Fall back to the raw pre-trigger mean only when the RQ is unavailable.
    if baseline_rq is None or not np.isfinite(baseline_rq) or baseline_rq == -999999:
        baseline = np.mean(y[:baseline_n])
    else:
        baseline = float(baseline_rq)
    y = y - baseline
    peak = np.max(y)
    if peak <= 0:
        return None, False
    return y, True

FORCE_RERUN = False
CACHE_FILE  = os.path.join(CACHE_DIR, f"traces_cache_zip{det_tmpl}.pkl")
CACHE_VERSION = 2
ALIGN_PEAK_LO = 15000
ALIGN_PEAK_HI = 18000

if not FORCE_RERUN and os.path.exists(CACHE_FILE):
    print(f"Loading cache: {CACHE_FILE}")
    with open(CACHE_FILE, 'rb') as f:
        cache = pickle.load(f)
    if cache.get('cache_version') == CACHE_VERSION:
        channel_traces = cache['channel_traces']
        pf_traces      = cache['pf_traces']
        print("Loaded:")
        for c in chans:
            print(f"  {c}: {len(channel_traces[c])} traces")
        print(f"  PF: {len(pf_traces)} traces")
    else:
        print("Cache was made with the old preprocessing; rebuilding it.")
        FORCE_RERUN = True

if FORCE_RERUN or not os.path.exists(CACHE_FILE):
    channel_traces = {c: [] for c in chans}
    pf_traces      = []

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
            myreader    = rawio.RawDataReader(raw_series_dir)
            nb_info     = myreader.get_nb_events()
            total_evts  = nb_info.get('NbEventsNotEmpty', nb_info.get('NbEvents', 50000))
            events_list = myreader.read_events(
                output_format = 2,
                skip_empty    = True,
                trigger_types = [1],
                nb_events     = total_evts,
                detector_nums = [det_tmpl],
                channel_names = chans
            )
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

                y_filt  = butter_lowpass(y_sub)
                delay_s = sel_delay[series][chan].get(evn, 0.0)
                if not np.isfinite(delay_s):
                    continue
                y_align = np.roll(y_filt, -round(delay_s * samplerate))
                peak_idx = int(np.argmax(y_align))
                if peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
                    continue
                peak = np.max(y_align)
                if peak <= 0:
                    continue

                channel_traces[chan].append(y_align / peak)
                chan_aligned[chan] = y_align
                n_good += 1

            # Type 3 is the full phonon sum: require every available channel.
            if len(chan_aligned) == len(chans):
                pf_sum  = sum(chan_aligned.values())
                pf_peak = np.max(pf_sum)
                if pf_peak > 0:
                    pf_traces.append(pf_sum / pf_peak)

        print(f'  {series}: {n_good} good channel-trace pairs')

    for c in chans:
        print(f'  {c}: {len(channel_traces[c])} traces')
    print(f'  PF (Type 3): {len(pf_traces)} per-event traces')

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION,
                     'channel_traces': channel_traces,
                     'pf_traces': pf_traces}, f)
    print(f"Cache saved: {os.path.abspath(CACHE_FILE)}")

# ── Average template ───────────────────────────────────────────────────────────
average_trace = {}
for chan in chan_names:
    traces = channel_traces[chan]
    if len(traces) == 0:
        average_trace[chan] = None
        print(f"  {chan}: no good traces")
    else:
        avg = np.mean(traces, axis=0)
        avg /= np.max(avg)
        average_trace[chan] = avg
        print(f"  {chan}: template from {len(traces)} traces")

# ── Exponential fitting ────────────────────────────────────────────────────────
def two_exp_fit(x, amp1, t1, t2, baseline, pretrigger):
    return np.where(
        x <= pretrigger, baseline,
        -(amp1 * np.exp(-(x - pretrigger) / t1 / samplerate)
          - amp1 * np.exp(-(x - pretrigger) / t2 / samplerate)) + baseline
    )

def three_exp_fit(x, amp1, amp2, t1, t2, t3, baseline, pretrigger):
    return np.where(
        x <= pretrigger, baseline,
        -((amp1 + amp2) * np.exp(-(x - pretrigger) / t1 / samplerate)
          - amp1         * np.exp(-(x - pretrigger) / t2 / samplerate)
          - amp2         * np.exp(-(x - pretrigger) / t3 / samplerate)) + baseline
    )

def four_exp_fit(x, amp1, amp2, amp3, t1, t2, t3, t4, baseline, pretrigger):
    return np.where(
        x <= pretrigger, baseline,
        -((amp1 + amp2 + amp3) * np.exp(-(x - pretrigger) / t1 / samplerate)
          - amp1                * np.exp(-(x - pretrigger) / t2 / samplerate)
          - amp2                * np.exp(-(x - pretrigger) / t3 / samplerate)
          - amp3                * np.exp(-(x - pretrigger) / t4 / samplerate)) + baseline
    )

def auto_guess(tmpl, win_start):
    peak_idx = int(np.argmax(tmpl))
    smooth = np.convolve(tmpl, np.ones(21) / 21.0, mode='same')
    baseline = float(np.median(smooth[win_start:min(win_start + 1000, peak_idx)]))
    # The average can contain a broad low-level pedestal that crosses an amplitude
    # threshold long before the physical pulse.  The steepest smoothed leading
    # edge is stable across channels and follows the white gap in the trace plot.
    derivative = np.convolve(np.diff(smooth), np.ones(21) / 21.0, mode='same')
    edge_lo = max(win_start, peak_idx - 1500)
    edge = edge_lo + int(np.argmax(derivative[edge_lo:peak_idx]))
    pt_guess = float(edge) - 50
    pt_guess = max(float(win_start), pt_guess)
    post     = tmpl[peak_idx:]
    fall_threshold = baseline + (float(tmpl[peak_idx]) - baseline) / np.e
    inv_e    = np.where(post <= fall_threshold)[0]
    t_fall   = inv_e[0] / samplerate if len(inv_e) > 0 else 5e-3
    return pt_guess, t_fall * 0.05, t_fall * 0.3, t_fall, t_fall * 5.0

WIN_START = tracelength // 2 - 3000
T1_MAX    = 8e-5
T_DECAY_MIN = T1_MAX * 1.05
T_DECAY_MAX = 5e-2
BASELINE_LIMIT = 0.2
PRETRIGGER_TOL = 300

fit_params    = {}
fit_avg_trace = {}

for chan in chan_names:
    raw_tmpl = average_trace[chan]
    if raw_tmpl is None:
        fit_params[chan]    = None
        fit_avg_trace[chan] = None
        continue

    tmpl  = raw_tmpl / np.max(raw_tmpl)
    x     = np.arange(WIN_START, len(tmpl), dtype=float)
    y     = tmpl[WIN_START:]
    pt_g, t1_g, t2_g, t3_g, t4_g = auto_guess(tmpl, WIN_START)
    t1_p0 = np.clip(t1_g, 1e-6, T1_MAX * 0.99)
    t2_p0 = np.clip(t2_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    t3_p0 = np.clip(t3_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    t4_p0 = np.clip(t4_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    peak_idx = int(np.argmax(tmpl))
    pt_lo = max(float(WIN_START), pt_g - PRETRIGGER_TOL)
    pt_hi = min(float(peak_idx - 1), pt_g + PRETRIGGER_TOL)

    fit_ok = False
    for mode in ['4-exp', '3-exp', '2-exp']:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '4-exp':
                    popt, _ = curve_fit(
                        four_exp_fit, x, y,
                        p0=[0.4, 0.3, 0.3, t1_p0, t2_p0, t3_p0, t4_p0, 0.0, pt_g],
                        bounds=([0, 0, 0, 1e-6, T_DECAY_MIN, T_DECAY_MIN,
                                 T_DECAY_MIN, -BASELINE_LIMIT, pt_lo],
                                [np.inf, np.inf, np.inf, T1_MAX, T_DECAY_MAX,
                                 T_DECAY_MAX, T_DECAY_MAX, BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5)
                    )
                    y_fit = four_exp_fit(x, *popt)
                    a1, a2, a3, t1, t2, t3, t4, bl, pt = popt
                    label = (f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  '
                             f't3={t3*1e3:.2f}  t4={t4*1e3:.2f} ms')
                elif mode == '3-exp':
                    popt, _ = curve_fit(
                        three_exp_fit, x, y,
                        p0=[0.5, 0.5, t1_p0, t2_p0, t3_p0, 0.0, pt_g],
                        bounds=([0, 0, 1e-6, T_DECAY_MIN, T_DECAY_MIN,
                                 -BASELINE_LIMIT, pt_lo],
                                [np.inf, np.inf, T1_MAX, T_DECAY_MAX, T_DECAY_MAX,
                                 BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5)
                    )
                    y_fit = three_exp_fit(x, *popt)
                    a1, a2, t1, t2, t3, bl, pt = popt
                    label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  t3={t3*1e3:.2f} ms'
                else:
                    popt, _ = curve_fit(
                        two_exp_fit, x, y,
                        p0=[1.0, t1_p0, t2_p0, 0.0, pt_g],
                        bounds=([0, 1e-6, T_DECAY_MIN, -BASELINE_LIMIT, pt_lo],
                                [np.inf, T1_MAX, T_DECAY_MAX, BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5)
                    )
                    y_fit = two_exp_fit(x, *popt)
                    a1, t1, t2, bl, pt = popt
                    label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f} ms'

            fit_params[chan] = (mode, popt)

            x_full = np.arange(len(tmpl), dtype=float)
            if mode == '4-exp':
                full = four_exp_fit(x_full, *popt)
            elif mode == '3-exp':
                full = three_exp_fit(x_full, *popt)
            else:
                full = two_exp_fit(x_full, *popt)
            # The fitted baseline absorbs residual preprocessing offset; it is not
            # part of the physical pulse template stored in ROOT.
            full = full - bl
            peak_f = np.max(full)
            fit_peak_idx = int(np.argmax(full))
            rmse = float(np.sqrt(np.mean((y - y_fit) ** 2)))
            if (not np.all(np.isfinite(full)) or peak_f <= 0 or
                    abs(fit_peak_idx - peak_idx) > 750 or rmse > 0.25):
                raise RuntimeError(
                    f'nonphysical fit: peak={fit_peak_idx}, data_peak={peak_idx}, rmse={rmse:.3f}')
            fit_avg_trace[chan] = full / peak_f if peak_f > 0 else full

            print(f'  {chan}: [{mode}] {label}')
            fit_ok = True
            break
        except (RuntimeError, ValueError) as e:
            if mode != '2-exp':
                print(f'  {chan}: {mode} failed ({e}), trying next')
            else:
                print(f'  {chan}: all fits failed')
                fit_params[chan]    = None
                fit_avg_trace[chan] = None

# ── Build PT / PS1 / PS2 ──────────────────────────────────────────────────────
ALL_12 = ['PAS1', 'PBS1', 'PCS1', 'PDS1', 'PES1', 'PFS1',
          'PAS2', 'PBS2', 'PCS2', 'PDS2', 'PES2', 'PFS2']

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

if pf_traces:
    pf_avg = np.mean(pf_traces, axis=0)
    pf_avg = pf_avg / np.max(pf_avg)
    average_trace['PT'] = pf_avg

    pt_g, t1_g, t2_g, t3_g, t4_g = auto_guess(pf_avg, WIN_START)
    t1_p0 = np.clip(t1_g, 1e-6, T1_MAX * 0.99)
    t2_p0 = np.clip(t2_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    t3_p0 = np.clip(t3_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    t4_p0 = np.clip(t4_g, T_DECAY_MIN * 1.01, T_DECAY_MAX * 0.99)
    pt_peak_idx = int(np.argmax(pf_avg))
    pt_lo = max(float(WIN_START), pt_g - PRETRIGGER_TOL)
    pt_hi = min(float(pt_peak_idx - 1), pt_g + PRETRIGGER_TOL)
    x_pf  = np.arange(WIN_START, len(pf_avg), dtype=float)
    y_pf  = pf_avg[WIN_START:]
    x_full = np.arange(tracelength, dtype=float)

    for mode in ['4-exp', '3-exp', '2-exp']:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '4-exp':
                    popt_pt, _ = curve_fit(
                        four_exp_fit, x_pf, y_pf,
                        p0=[0.4, 0.3, 0.3, t1_p0, t2_p0, t3_p0, t4_p0, 0.0, pt_g],
                        bounds=([0, 0, 0, 1e-6, T_DECAY_MIN, T_DECAY_MIN,
                                 T_DECAY_MIN, -BASELINE_LIMIT, pt_lo],
                                [np.inf, np.inf, np.inf, T1_MAX, T_DECAY_MAX,
                                 T_DECAY_MAX, T_DECAY_MAX, BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5))
                    pt_full = four_exp_fit(x_full, *popt_pt)
                    a1, a2, a3, t1, t2, t3, t4, bl, ptrg = popt_pt
                    pt_label = (f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  '
                                f't3={t3*1e3:.2f}  t4={t4*1e3:.2f} ms')
                elif mode == '3-exp':
                    popt_pt, _ = curve_fit(
                        three_exp_fit, x_pf, y_pf,
                        p0=[0.5, 0.5, t1_p0, t2_p0, t3_p0, 0.0, pt_g],
                        bounds=([0, 0, 1e-6, T_DECAY_MIN, T_DECAY_MIN,
                                 -BASELINE_LIMIT, pt_lo],
                                [np.inf, np.inf, T1_MAX, T_DECAY_MAX, T_DECAY_MAX,
                                 BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5))
                    pt_full = three_exp_fit(x_full, *popt_pt)
                    a1, a2, t1, t2, t3, bl, ptrg = popt_pt
                    pt_label = (f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  '
                                f't3={t3*1e3:.2f} ms')
                else:
                    popt_pt, _ = curve_fit(
                        two_exp_fit, x_pf, y_pf,
                        p0=[1.0, t1_p0, t2_p0, 0.0, pt_g],
                        bounds=([0, 1e-6, T_DECAY_MIN, -BASELINE_LIMIT, pt_lo],
                                [np.inf, T1_MAX, T_DECAY_MAX, BASELINE_LIMIT, pt_hi]),
                        maxfev=int(1e5))
                    pt_full = two_exp_fit(x_full, *popt_pt)
                    a1, t1, t2, bl, ptrg = popt_pt
                    pt_label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f} ms'

            rmse = float(np.sqrt(np.mean((y_pf - pt_full[WIN_START:]) ** 2)))
            pt_full = pt_full - bl
            peak_pt = np.max(pt_full)
            fit_peak_idx = int(np.argmax(pt_full))
            if (not np.all(np.isfinite(pt_full)) or peak_pt <= 0 or
                    abs(fit_peak_idx - pt_peak_idx) > 750 or rmse > 0.25):
                raise RuntimeError(
                    f'nonphysical fit: peak={fit_peak_idx}, data_peak={pt_peak_idx}, rmse={rmse:.3f}')
            fit_avg_trace['PT'] = pt_full / peak_pt if peak_pt > 0 else pt_full
            print(f"PT [PF method, {len(pf_traces)} events, {mode}]: {pt_label}")
            break
        except (RuntimeError, ValueError) as e:
            if mode != '2-exp':
                print(f"PT: {mode} failed ({e}), trying next")
            else:
                print("PT: all fits failed — storing raw PF average")
                fit_avg_trace['PT'] = pf_avg
else:
    print("WARNING: no PF traces — falling back to sum of individual fitted channels")
    trace_pt = np.zeros(tracelength)
    for c in ALL_12:
        if fit_avg_trace.get(c) is not None:
            trace_pt += fit_avg_trace[c]
    if np.max(trace_pt) > 0:
        fit_avg_trace['PT'] = trace_pt / np.max(trace_pt)

# ── Write 1x1 templates to ROOT ───────────────────────────────────────────────
os.makedirs(ROOT_DIR, exist_ok=True)
output_file = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det_tmpl}_1x1.root")
root_file   = TFile(output_file, "RECREATE")
root_file.mkdir(f"zip{det_tmpl}").cd()

write_chans = ['PAS1', 'PBS1', 'PCS1', 'PDS1', 'PES1', 'PFS1',
               'PAS2', 'PBS2', 'PCS2', 'PDS2', 'PES2', 'PFS2',
               'PT', 'PS1', 'PS2']

for channel in write_chans:
    tr = fit_avg_trace.get(channel)
    if tr is None:
        print(f"  {channel}: skipped (no template)")
        continue
    tr_norm = tr / np.max(tr)
    h = TH1D(channel, channel, tracelength, 0, tracelength)
    for i, v in enumerate(tr_norm):
        h.SetBinContent(i + 1, v)
    h.Write()
    print(f"  {channel}: written")

# ── NxM (PCA) templates ───────────────────────────────────────────────────────
WIN_NXM_LO   = 14000
WIN_NXM_HI   = 20000
WIN_NXM      = WIN_NXM_HI - WIN_NXM_LO
N_COMPONENTS = 4
MAX_EVENTS   = 200
x_win        = np.arange(WIN_NXM, dtype=float)
SYNTH_PT     = float(16384 - WIN_NXM_LO - 200)

def chan_p0_nxm(chan):
    entry = fit_params.get(chan)
    if entry is None:
        return None
    tag, popt = entry
    if tag == '4-exp':
        a1, a2, a3, t1, t2, t3, t4, bl, pt = popt
        return [a1, a2, a3, t1, t2, t3, t4, 0.0, SYNTH_PT]
    elif tag == '3-exp':
        a1, a2, t1, t2, t3, bl, pt = popt
        return [a1/2, a2/2, a2/2, t1, t2, t3, t3 * 3, 0.0, SYNTH_PT]
    else:
        a1, t1, t2, bl, pt = popt
        return [a1/3, a1/3, a1/3, t1, t2, t2 * 5, t2 * 20, 0.0, SYNTH_PT]

training_set = {c: [] for c in chan_names}

for chan in chan_names:
    traces = channel_traces[chan]
    if not traces:
        print(f"  {chan}: no traces for NxM")
        continue
    p0 = chan_p0_nxm(chan)
    if p0 is None:
        print(f"  {chan}: no avg fit params for NxM")
        continue

    n_fit = 0
    n_raw = 0
    for tr in traces[:MAX_EVENTS]:
        cut = tr[WIN_NXM_LO:WIN_NXM_HI]
        if len(cut) < WIN_NXM:
            continue
        peak_pos = int(np.argmax(cut))
        if peak_pos < 1500 or peak_pos > 3500:
            continue

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt_ev, _ = curve_fit(
                    four_exp_fit, x_win, cut,
                    p0=p0, maxfev=int(3e4)
                )
            a1, a2, a3, t1, t2, t3, t4, bl, pt_ev = popt_ev
            synth = four_exp_fit(x_win, a1, a2, a3, t1, t2, t3, t4, 0.0, SYNTH_PT)
            peak_s = np.max(synth)
            if peak_s <= 0:
                continue
            training_set[chan].append(synth / peak_s)
            n_fit += 1
        except RuntimeError:
            training_set[chan].append(cut)
            n_raw += 1

    print(f"  {chan}: {n_fit} fitted + {n_raw} raw = {n_fit+n_raw} training events")

combined = []
for chan in chan_names:
    if training_set.get(chan):
        combined.extend(training_set[chan])

if len(combined) == 0:
    print("WARNING: No training events for PCA — NxM templates skipped")
else:
    pca = PCA(N_COMPONENTS, svd_solver='full').fit(combined)
    PC  = pca.components_
    var = pca.explained_variance_ratio_
    print(f"PCA on {len(combined)} synthetic traces ({N_COMPONENTS} components)")
    for i, v in enumerate(var):
        print(f"  PC{i}: {v*100:.2f}% variance")

    root_file.cd(f"zip{det_tmpl}")
    n_post = tracelength - WIN_NXM_HI

    for chan in chan_names:
        for i in range(N_COMPONENTS):
            hname  = f"{chan}nxm{i}"
            h      = ROOT.TH1D(hname, hname, tracelength, 0, tracelength)
            padded = np.pad(PC[i], pad_width=(WIN_NXM_LO, 0), mode='constant')
            padded = np.pad(padded, pad_width=(0, n_post),     mode='constant')
            padded = padded[:tracelength]
            peak_p = np.max(np.abs(padded))
            y = padded / peak_p if peak_p > 0 else padded
            for j, v in enumerate(y):
                h.SetBinContent(j + 1, v)
            h.Write()
            h.Delete()

    print(f"NxM templates ({N_COMPONENTS} components × {len(chan_names)} channels) written.")

root_file.Close()
print(f"\nDone. Saved: {os.path.abspath(output_file)}")
