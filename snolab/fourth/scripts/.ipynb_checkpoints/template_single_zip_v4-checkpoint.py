#!/usr/bin/env python3
# coding: utf-8
# Fourth-run template generation.
# Outputs two ROOT files per zip:
#   Templates_SNOLAB_R4_zip{det}_agnostic.root  — shared PCA across all channels
#   Templates_SNOLAB_R4_zip{det}_specific.root  — independent PCA per channel
#
# Key fix vs. third run: canonical synthetic traces are peak-aligned so that
# the pulse peak always falls at CANONICAL_PT, eliminating the pre-pulse dip
# that arose from mixing traces with different rise times (different peak offsets).
#
# Usage: python template_single_zip_v4.py --det <zip_number>

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
import glob, os, warnings, pickle, json

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
    raise ValueError(f"Zip{det_tmpl} not in PTOF_RANGES.")

print(f"\n=== Processing Zip{det_tmpl} ===")

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
dets_all  = [1, 4, 6, 7, 9, 10, 15, 16, 18, 24]

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

# ── Read raw traces, filter and align ─────────────────────────────────────────
def butter_lowpass(data, cutoff_khz=10.0, fs=625000, order=4):
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
CACHE_VERSION = 3
ALIGN_PEAK_LO = 15000
ALIGN_PEAK_HI = 18000
RAW_SAMPLE_N  = 5

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
                y_filt  = butter_lowpass(y_sub)
                delay_s = sel_delay[series][chan].get(evn, 0.0)
                if not np.isfinite(delay_s):
                    continue
                shift    = -round(delay_s * samplerate)
                y_align  = np.roll(y_filt, shift)
                y_raw_al = np.roll(y_sub,  shift)
                peak_idx = int(np.argmax(y_align))
                if peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
                    continue
                peak = np.max(y_align)
                if peak <= 0:
                    continue
                channel_traces[chan].append(y_align / peak)
                chan_aligned[chan] = y_align
                if len(raw_sample[chan]) < RAW_SAMPLE_N:
                    raw_sample[chan].append(y_raw_al / peak)
                n_good += 1

            if len(chan_aligned) == len(chans):
                pf_sum  = sum(chan_aligned.values())
                pf_peak = np.max(pf_sum)
                if pf_peak > 0:
                    pf_traces.append(pf_sum / pf_peak)

        print(f'  {series}: {n_good} good channel-trace pairs')

    for c in chans:
        print(f'  {c}: {len(channel_traces[c])} traces')

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION,
                     'channel_traces': channel_traces,
                     'pf_traces': pf_traces,
                     'raw_sample': raw_sample}, f)
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
    return np.where(x <= pretrigger, baseline,
        -(amp1 * np.exp(-(x-pretrigger)/t1/samplerate)
          - amp1 * np.exp(-(x-pretrigger)/t2/samplerate)) + baseline)

def three_exp_fit(x, amp1, amp2, t1, t2, t3, baseline, pretrigger):
    return np.where(x <= pretrigger, baseline,
        -((amp1+amp2)*np.exp(-(x-pretrigger)/t1/samplerate)
          - amp1*np.exp(-(x-pretrigger)/t2/samplerate)
          - amp2*np.exp(-(x-pretrigger)/t3/samplerate)) + baseline)

def four_exp_fit(x, amp1, amp2, amp3, t1, t2, t3, t4, baseline, pretrigger):
    return np.where(x <= pretrigger, baseline,
        -((amp1+amp2+amp3)*np.exp(-(x-pretrigger)/t1/samplerate)
          - amp1*np.exp(-(x-pretrigger)/t2/samplerate)
          - amp2*np.exp(-(x-pretrigger)/t3/samplerate)
          - amp3*np.exp(-(x-pretrigger)/t4/samplerate)) + baseline)

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
T1_MAX          = 8e-5
T_DECAY_MIN     = T1_MAX * 1.05
T_DECAY_MAX     = 5e-2
BASELINE_LIMIT  = 0.2
PRETRIGGER_TOL  = 300

fit_params    = {}
fit_avg_trace = {}

for chan in chan_names:
    raw_tmpl = average_trace[chan]
    if raw_tmpl is None:
        fit_params[chan] = None; fit_avg_trace[chan] = None; continue

    tmpl = raw_tmpl / np.max(raw_tmpl)
    x    = np.arange(WIN_START, len(tmpl), dtype=float)
    y    = tmpl[WIN_START:]
    pt_g, t1_g, t2_g, t3_g, t4_g = auto_guess(tmpl, WIN_START)
    t1_p0 = np.clip(t1_g, 1e-6, T1_MAX*0.99)
    t2_p0 = np.clip(t2_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    t3_p0 = np.clip(t3_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    t4_p0 = np.clip(t4_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    peak_idx = int(np.argmax(tmpl))
    pt_lo = max(float(WIN_START), pt_g - PRETRIGGER_TOL)
    pt_hi = min(float(peak_idx - 1), pt_g + PRETRIGGER_TOL)

    for mode in ['4-exp', '3-exp', '2-exp']:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '4-exp':
                    popt, _ = curve_fit(four_exp_fit, x, y,
                        p0=[0.4, 0.3, 0.3, t1_p0, t2_p0, t3_p0, t4_p0, 0.0, pt_g],
                        bounds=([0,0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,T_DECAY_MIN,
                                 -BASELINE_LIMIT, pt_lo],
                                [np.inf,np.inf,np.inf,T1_MAX,T_DECAY_MAX,
                                 T_DECAY_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    y_fit = four_exp_fit(x, *popt)
                    a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
                    label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  t3={t3*1e3:.2f}  t4={t4*1e3:.2f} ms'
                elif mode == '3-exp':
                    popt, _ = curve_fit(three_exp_fit, x, y,
                        p0=[0.5, 0.5, t1_p0, t2_p0, t3_p0, 0.0, pt_g],
                        bounds=([0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,np.inf,T1_MAX,T_DECAY_MAX,T_DECAY_MAX,
                                 BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    y_fit = three_exp_fit(x, *popt)
                    a1,a2,t1,t2,t3,bl,pt = popt
                    label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f}  t3={t3*1e3:.2f} ms'
                else:
                    popt, _ = curve_fit(two_exp_fit, x, y,
                        p0=[1.0, t1_p0, t2_p0, 0.0, pt_g],
                        bounds=([0,1e-6,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,T1_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    y_fit = two_exp_fit(x, *popt)
                    a1,t1,t2,bl,pt = popt
                    label = f't1={t1*1e3:.3f}  t2={t2*1e3:.2f} ms'

            fit_params[chan] = (mode, popt)
            x_full = np.arange(len(tmpl), dtype=float)
            if mode == '4-exp':
                full = four_exp_fit(x_full, *popt)
            elif mode == '3-exp':
                full = three_exp_fit(x_full, *popt)
            else:
                full = two_exp_fit(x_full, *popt)
            full = full - bl
            peak_f = np.max(full)
            fit_peak_idx = int(np.argmax(full))
            rmse = float(np.sqrt(np.mean((y - y_fit)**2)))
            if (not np.all(np.isfinite(full)) or peak_f <= 0 or
                    abs(fit_peak_idx - peak_idx) > 750 or rmse > 0.25):
                raise RuntimeError(f'nonphysical fit')
            fit_avg_trace[chan] = full / peak_f
            print(f'  {chan}: [{mode}] {label}')
            break
        except (RuntimeError, ValueError) as e:
            if mode != '2-exp':
                print(f'  {chan}: {mode} failed ({e}), trying next')
            else:
                print(f'  {chan}: all fits failed')
                fit_params[chan] = None; fit_avg_trace[chan] = None

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

if pf_traces:
    pf_avg = np.mean(pf_traces, axis=0)
    pf_avg = pf_avg / np.max(pf_avg)
    average_trace['PT'] = pf_avg
    pt_g, t1_g, t2_g, t3_g, t4_g = auto_guess(pf_avg, WIN_START)
    t1_p0 = np.clip(t1_g, 1e-6, T1_MAX*0.99)
    t2_p0 = np.clip(t2_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    t3_p0 = np.clip(t3_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    t4_p0 = np.clip(t4_g, T_DECAY_MIN*1.01, T_DECAY_MAX*0.99)
    pt_peak_idx = int(np.argmax(pf_avg))
    pt_lo = max(float(WIN_START), pt_g - PRETRIGGER_TOL)
    pt_hi = min(float(pt_peak_idx - 1), pt_g + PRETRIGGER_TOL)
    x_pf  = np.arange(WIN_START, len(pf_avg), dtype=float)
    y_pf  = pf_avg[WIN_START:]
    x_full_pt = np.arange(tracelength, dtype=float)
    for mode in ['4-exp', '3-exp', '2-exp']:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if mode == '4-exp':
                    popt_pt,_ = curve_fit(four_exp_fit, x_pf, y_pf,
                        p0=[0.4,0.3,0.3,t1_p0,t2_p0,t3_p0,t4_p0,0.0,pt_g],
                        bounds=([0,0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,T_DECAY_MIN,
                                 -BASELINE_LIMIT,pt_lo],
                                [np.inf,np.inf,np.inf,T1_MAX,T_DECAY_MAX,
                                 T_DECAY_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    pt_full = four_exp_fit(x_full_pt, *popt_pt)
                    a1,a2,a3,t1,t2,t3,t4,bl,ptrg = popt_pt
                elif mode == '3-exp':
                    popt_pt,_ = curve_fit(three_exp_fit, x_pf, y_pf,
                        p0=[0.5,0.5,t1_p0,t2_p0,t3_p0,0.0,pt_g],
                        bounds=([0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,np.inf,T1_MAX,T_DECAY_MAX,T_DECAY_MAX,
                                 BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    pt_full = three_exp_fit(x_full_pt, *popt_pt)
                    a1,a2,t1,t2,t3,bl,ptrg = popt_pt
                else:
                    popt_pt,_ = curve_fit(two_exp_fit, x_pf, y_pf,
                        p0=[1.0,t1_p0,t2_p0,0.0,pt_g],
                        bounds=([0,1e-6,T_DECAY_MIN,-BASELINE_LIMIT,pt_lo],
                                [np.inf,T1_MAX,T_DECAY_MAX,BASELINE_LIMIT,pt_hi]),
                        maxfev=int(1e5))
                    pt_full = two_exp_fit(x_full_pt, *popt_pt)
                    a1,t1,t2,bl,ptrg = popt_pt

            rmse = float(np.sqrt(np.mean((y_pf - pt_full[WIN_START:])**2)))
            pt_full = pt_full - bl
            peak_pt = np.max(pt_full)
            fit_peak_idx = int(np.argmax(pt_full))
            if (not np.all(np.isfinite(pt_full)) or peak_pt <= 0 or
                    abs(fit_peak_idx - pt_peak_idx) > 750 or rmse > 0.25):
                raise RuntimeError('nonphysical fit')
            fit_avg_trace['PT'] = pt_full / peak_pt
            print(f"PT [{mode}]: t1={t1*1e3:.3f} ms")
            break
        except (RuntimeError, ValueError) as e:
            if mode != '2-exp':
                print(f"PT: {mode} failed, trying next")
            else:
                print("PT: all fits failed — storing raw PF average")
                fit_avg_trace['PT'] = pf_avg
else:
    trace_pt = np.zeros(tracelength)
    for c in ALL_12:
        if fit_avg_trace.get(c) is not None:
            trace_pt += fit_avg_trace[c]
    if np.max(trace_pt) > 0:
        fit_avg_trace['PT'] = trace_pt / np.max(trace_pt)

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
        a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3, 't4': t4}
    elif mode == '3-exp':
        a1,a2,t1,t2,t3,bl,pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2, 't3': t3}
    else:
        a1,t1,t2,bl,pt = popt
        tc_out[chan] = {'mode': mode, 't1': t1, 't2': t2}

tc_path_agnostic = os.path.join(ROOT_AGNOSTIC, f'time_constants_zip{det_tmpl}.json')
tc_path_specific = os.path.join(ROOT_SPECIFIC, f'time_constants_zip{det_tmpl}.json')
for tc_path in [tc_path_agnostic, tc_path_specific]:
    with open(tc_path, 'w') as fj:
        json.dump(tc_out, fj, indent=2)
print(f"Time constants saved.")

# ── NxM: per-event 4-exp fit → peak-aligned canonical traces → PCA ────────────
#
# KEY FIX: canonical synthetic traces are peak-aligned.
# Each event's fitted time constants give a different peak offset from pretrigger.
# We adjust the pretrigger so that every synthetic trace has its peak at exactly
# CANONICAL_PT — eliminating the pre-pulse dip caused by peak-position variance
# in PCA.

N_COMPONENTS  = 5
MAX_NXM       = 300
CANONICAL_PT  = float(tracelength // 2)   # 16384 — peak will land here
NXM_RMSE_MAX  = 0.15
DIAG_PER_CHAN = 3

x_full_nxm = np.arange(tracelength, dtype=float)
x_nxm_fit  = np.arange(WIN_START, tracelength, dtype=float)

def nxm_p0(chan):
    entry = fit_params.get(chan)
    if entry is None:
        return None
    tag, popt = entry
    if tag == '4-exp':
        a1,a2,a3,t1,t2,t3,t4,bl,pt = popt
        return [a1, a2, a3, t1, t2, t3, t4, 0.0, CANONICAL_PT]
    elif tag == '3-exp':
        a1,a2,t1,t2,t3,bl,pt = popt
        return [a1/2, a2/2, a2/2, t1, t2, t3, t3*3, 0.0, CANONICAL_PT]
    else:
        a1,t1,t2,bl,pt = popt
        return [a1/3, a1/3, a1/3, t1, t2, t2*5, t2*20, 0.0, CANONICAL_PT]

def make_peak_aligned_synth(a1, a2, a3, t1, t2, t3, t4):
    """Generate canonical synthetic trace with peak at exactly CANONICAL_PT.

    Adjust pretrigger so the four_exp_fit peak lands at CANONICAL_PT,
    eliminating peak-position variance across events (which is what caused
    the pre-pulse dip in the agnostic third-run PCA).
    """
    # Test trace with pretrigger at CANONICAL_PT to measure peak offset
    test = four_exp_fit(x_full_nxm, a1, a2, a3, t1, t2, t3, t4, 0.0, CANONICAL_PT)
    peak_offset = int(np.argmax(test)) - int(CANONICAL_PT)   # samples after pretrigger
    # Shift pretrigger so peak lands at CANONICAL_PT
    adj_pt = CANONICAL_PT - peak_offset
    synth  = four_exp_fit(x_full_nxm, a1, a2, a3, t1, t2, t3, t4, 0.0, adj_pt)
    return synth

nxm_synth_all    = []
nxm_synth_bychan = {c: [] for c in chan_names}

print(f"\n── NxM per-event fitting (peak-aligned canonical traces) ──")

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
    diag_done = 0

    for i, tr in enumerate(traces[:MAX_NXM]):
        y_region = tr[WIN_START:]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                popt_ev, _ = curve_fit(four_exp_fit, x_nxm_fit, y_region,
                    p0=p0,
                    bounds=([0,0,0,1e-6,T_DECAY_MIN,T_DECAY_MIN,T_DECAY_MIN,
                             -BASELINE_LIMIT, float(WIN_START)],
                            [np.inf,np.inf,np.inf,T1_MAX,T_DECAY_MAX,
                             T_DECAY_MAX,T_DECAY_MAX,BASELINE_LIMIT,
                             float(tracelength-500)]),
                    maxfev=int(5e4))
        except (RuntimeError, ValueError):
            n_reject += 1; continue

        a1,a2,a3,t1,t2,t3,t4,bl,pt_ev = popt_ev
        y_fit_win = four_exp_fit(x_nxm_fit, *popt_ev)
        rmse      = float(np.sqrt(np.mean((y_region - y_fit_win)**2)))

        if a1 <= 0 or a2 <= 0 or a3 <= 0:
            n_reject += 1; continue
        if t1 >= T1_MAX * 0.99:
            n_reject += 1; continue
        if not (WIN_START < pt_ev < tracelength - 500):
            n_reject += 1; continue
        if rmse > NXM_RMSE_MAX:
            n_reject += 1; continue

        # Diagnostic plot
        if diag_done < DIAG_PER_CHAN:
            y_fit_disp = four_exp_fit(x_full_nxm, *popt_ev) - bl
            for plot_dir in [PLOT_AGNOSTIC, PLOT_SPECIFIC]:
                fig_d, ax_d = plt.subplots(figsize=(13, 4))
                t_ms = x_full_nxm / samplerate * 1e3
                lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
                hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3
                if i < len(raw_samps):
                    ax_d.plot(t_ms, raw_samps[i], color='gray', lw=0.7,
                              alpha=0.9, label='Raw (unfiltered)')
                ax_d.plot(t_ms, tr, color='steelblue', lw=1.0, label='LP filtered')
                ax_d.plot(t_ms, y_fit_disp, color='red', lw=1.5, ls='--',
                          label=f'4-exp fit  RMSE={rmse:.4f}')
                ax_d.set_xlim(lo_ms, hi_ms)
                ax_d.set_xlabel('Time (ms)'); ax_d.set_ylabel('Amplitude (norm.)')
                ax_d.set_title(f'Zip{det_tmpl}/{chan} event {i}\n'
                               f't1={t1*1e3:.3f} t2={t2*1e3:.2f} '
                               f't3={t3*1e3:.2f} t4={t4*1e3:.2f} ms')
                ax_d.legend(fontsize=8); ax_d.grid(alpha=0.3)
                fig_d.tight_layout()
                fig_d.savefig(os.path.join(plot_dir,
                    f'nxm_diag_zip{det_tmpl}_{chan}_ev{i}.png'), dpi=120)
                plt.close(fig_d)
            diag_done += 1

        # Peak-aligned canonical synthetic trace
        synth = make_peak_aligned_synth(a1, a2, a3, t1, t2, t3, t4)
        peak_s = np.max(synth)
        if peak_s <= 0:
            n_reject += 1; continue

        synth_norm = synth / peak_s
        nxm_synth_all.append(synth_norm)
        nxm_synth_bychan[chan].append(synth_norm)
        n_accept += 1

    print(f"  {chan}: {n_accept} accepted, {n_reject} rejected")

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
        axes_al[0].set_xlabel('Time (ms)'); axes_al[0].set_ylabel('Amplitude (norm.)')
        axes_al[0].grid(alpha=0.3)
        for tr in synth_30:
            axes_al[1].plot(t_ms_al, tr, alpha=0.3, lw=0.6, color='darkorange')
        axes_al[1].set_xlim(lo_ms, hi_ms)
        axes_al[1].set_title(f'Peak-aligned canonical traces (peak at {int(CANONICAL_PT)})')
        axes_al[1].set_xlabel('Time (ms)'); axes_al[1].grid(alpha=0.3)
        fig_al.suptitle(f'Zip{det_tmpl} NxM — Peak alignment', fontsize=12)
        fig_al.tight_layout()
        fig_al.savefig(os.path.join(plot_dir, f'nxm_alignment_zip{det_tmpl}.png'), dpi=150)
        plt.close(fig_al)

# ── AGNOSTIC PCA: pool all channels → one set of components per zip ───────────
print(f"\n── Agnostic PCA: {len(nxm_synth_all)} traces from all channels ──")
rf_agnostic.cd(f"zip{det_tmpl}")

if len(nxm_synth_all) <= N_COMPONENTS:
    print(f"WARNING: not enough traces for agnostic PCA ({len(nxm_synth_all)}, need >{N_COMPONENTS})")
else:
    nxm_arr = np.array(nxm_synth_all)
    pca_ag  = PCA(N_COMPONENTS, svd_solver='randomized', random_state=42).fit(nxm_arr)
    PC_ag   = pca_ag.components_
    var_ag  = pca_ag.explained_variance_ratio_
    for i, v in enumerate(var_ag):
        print(f"  PC{i}: {v*100:.2f}%")

    t_ms_pca = x_full_nxm / samplerate * 1e3
    lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
    hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3

    fig_pca, axes_pca = plt.subplots(N_COMPONENTS, 1,
                                      figsize=(14, 3*N_COMPONENTS), sharex=True)
    for i in range(N_COMPONENTS):
        axes_pca[i].plot(t_ms_pca, PC_ag[i], lw=0.9)
        axes_pca[i].set_title(f'PC{i}  ({var_ag[i]*100:.2f}%)', fontsize=10)
        axes_pca[i].set_ylabel('Amplitude'); axes_pca[i].grid(alpha=0.3)
    axes_pca[-1].set_xlabel('Time (ms)')
    axes_pca[0].set_xlim(lo_ms, hi_ms)
    fig_pca.suptitle(f'Zip{det_tmpl} — Agnostic NxM PCA (peak-aligned, all channels pooled)',
                     fontsize=12)
    fig_pca.tight_layout()
    fig_pca.savefig(os.path.join(PLOT_AGNOSTIC,
        f'nxm_pca_components_zip{det_tmpl}.png'), dpi=150)
    plt.close(fig_pca)

    fig_var, ax_var = plt.subplots(figsize=(6, 4))
    ax_var.plot(range(N_COMPONENTS), var_ag*100, 'o-', color='steelblue')
    ax_var.set_xlabel('Component'); ax_var.set_ylabel('Explained variance (%)')
    ax_var.set_title(f'Zip{det_tmpl} Agnostic NxM — Explained variance')
    ax_var.set_yscale('log'); ax_var.grid(alpha=0.4)
    fig_var.tight_layout()
    fig_var.savefig(os.path.join(PLOT_AGNOSTIC,
        f'nxm_variance_zip{det_tmpl}.png'), dpi=120)
    plt.close(fig_var)

    # Write agnostic NxM: same PC[i] for every channel
    for chan in chan_names:
        for i in range(N_COMPONENTS):
            hname  = f"{chan}nxm{i}"
            h      = ROOT.TH1D(hname, hname, tracelength, 0, tracelength)
            comp   = PC_ag[i]
            peak_p = np.max(np.abs(comp))
            y = comp / peak_p if peak_p > 0 else comp
            for j, val in enumerate(y):
                h.SetBinContent(j+1, val)
            h.Write(); h.Delete()

    print(f"Agnostic NxM written: {N_COMPONENTS} components × {len(chan_names)} channels")

rf_agnostic.Close()
print(f"Saved: {out_agnostic}")

# ── SPECIFIC PCA: independent PCA per channel ─────────────────────────────────
print(f"\n── Specific PCA: per-channel independent PCA ──")
rf_specific.cd(f"zip{det_tmpl}")

t_ms_pca = x_full_nxm / samplerate * 1e3
lo_ms = (CANONICAL_PT - 2000) / samplerate * 1e3
hi_ms = (CANONICAL_PT + 8000) / samplerate * 1e3
n_chan_written = 0

for chan in chan_names:
    synth_list = nxm_synth_bychan[chan]
    if len(synth_list) <= N_COMPONENTS:
        print(f"  {chan}: {len(synth_list)} traces — need >{N_COMPONENTS}, skipping")
        continue

    pca_ch  = PCA(N_COMPONENTS, svd_solver='randomized', random_state=42).fit(np.array(synth_list))
    PC_ch   = pca_ch.components_
    var_ch  = pca_ch.explained_variance_ratio_
    print(f"  {chan}: {len(synth_list)} traces, "
          f"PC0={var_ch[0]*100:.1f}% PC1={var_ch[1]*100:.1f}%")

    fig_pca, axes_pca = plt.subplots(N_COMPONENTS, 1,
                                      figsize=(14, 3*N_COMPONENTS), sharex=True)
    for i in range(N_COMPONENTS):
        axes_pca[i].plot(t_ms_pca, PC_ch[i], lw=0.9)
        axes_pca[i].set_title(f'PC{i}  ({var_ch[i]*100:.2f}%)', fontsize=10)
        axes_pca[i].set_ylabel('Amplitude'); axes_pca[i].grid(alpha=0.3)
    axes_pca[-1].set_xlabel('Time (ms)')
    axes_pca[0].set_xlim(lo_ms, hi_ms)
    fig_pca.suptitle(f'Zip{det_tmpl}/{chan} — Specific NxM PCA (peak-aligned)',
                     fontsize=12)
    fig_pca.tight_layout()
    fig_pca.savefig(os.path.join(PLOT_SPECIFIC,
        f'nxm_pca_components_zip{det_tmpl}_{chan}.png'), dpi=150)
    plt.close(fig_pca)

    fig_var, ax_var = plt.subplots(figsize=(6, 4))
    ax_var.plot(range(N_COMPONENTS), var_ch*100, 'o-', color='steelblue')
    ax_var.set_xlabel('Component'); ax_var.set_ylabel('Explained variance (%)')
    ax_var.set_title(f'Zip{det_tmpl}/{chan} Specific NxM')
    ax_var.set_yscale('log'); ax_var.grid(alpha=0.4)
    fig_var.tight_layout()
    fig_var.savefig(os.path.join(PLOT_SPECIFIC,
        f'nxm_variance_zip{det_tmpl}_{chan}.png'), dpi=120)
    plt.close(fig_var)

    for i in range(N_COMPONENTS):
        hname  = f"{chan}nxm{i}"
        h      = ROOT.TH1D(hname, hname, tracelength, 0, tracelength)
        comp   = PC_ch[i]
        peak_p = np.max(np.abs(comp))
        y = comp / peak_p if peak_p > 0 else comp
        for j, val in enumerate(y):
            h.SetBinContent(j+1, val)
        h.Write(); h.Delete()
    n_chan_written += 1

rf_specific.Close()
print(f"Specific NxM written for {n_chan_written}/{len(chan_names)} channels")
print(f"Saved: {out_specific}")
print(f"\nDone. Zip{det_tmpl} complete.")
