#!/usr/bin/env python3
# coding: utf-8
# Collect raw traces for ONE series and ONE zip detector.
# Saves a partial pkl that template_merge_traces_v10.py will combine.
#
# Logic is identical to template_single_zip_v10.py:
#   - same channel detection (from first available processed file for this det)
#   - same event selection filter (PTOFamps, TriggerType==1)
#   - same trace preprocessing (100 kHz LP, PTOFdelay alignment)
#   - same pf_traces construction (requires all channels passing in same event)
#
# Usage: python template_collect_series_v10.py --det N --series 24260617_063934

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
parser.add_argument('--series', type=str, required=True)
args = parser.parse_args()

import rawio
import numpy as np
from scipy.signal import butter, sosfilt
import uproot
import os, pickle

RUN_DIR = os.environ.get("R4_RUN_DIR", "").strip()
if not RUN_DIR:
    raise RuntimeError("R4_RUN_DIR not set")
RUN_DIR   = os.path.abspath(RUN_DIR)
CACHE_DIR = os.path.join(RUN_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"
samplerate    = 625000
tracelength   = 32768

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

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
dets_all  = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

FILTER_CUTOFF_KHZ     = 100.0
ALIGN_PEAK_LO         = 15000
ALIGN_PEAK_HI         = 18000
RAW_SAMPLE_N          = 5
NEGATIVE_FRACTION     = 0.05
NEGATIVE_TAIL_SAMPLES = 12000

det_tmpl = args.det
series   = args.series

if det_tmpl not in PTOF_RANGES:
    raise ValueError(f"Zip{det_tmpl} not in PTOF_RANGES.")
if series not in ALL_SERIES:
    raise ValueError(f"Series {series} not in ALL_SERIES.")

PARTIAL_FILE = os.path.join(CACHE_DIR, f"traces_partial_zip{det_tmpl}_{series}.pkl")

# ── If this series is excluded for this det, write an empty partial and exit ──
if series in SERIES_EXCLUSIONS.get(det_tmpl, []):
    print(f"Series {series} is excluded for Zip{det_tmpl}. Writing empty partial.")
    with open(PARTIAL_FILE, 'wb') as f:
        pickle.dump({'det': det_tmpl, 'series': series,
                     'channel_traces': {c: [] for c in ALL_CHANS},
                     'pf_traces': [],
                     'raw_sample': {c: [] for c in ALL_CHANS},
                     'negative_rejected': {c: 0 for c in ALL_CHANS},
                     'excluded': True}, f)
    print(f"Saved (empty): {PARTIAL_FILE}")
    raise SystemExit(0)

if os.path.exists(PARTIAL_FILE):
    print(f"Partial already exists: {PARTIAL_FILE} — nothing to do.")
    raise SystemExit(0)

PTOF_LO, PTOF_HI = PTOF_RANGES[det_tmpl]

# ── Channel detection: use first available processed file, identical to original
_excluded = set(SERIES_EXCLUSIONS.get(det_tmpl, []))
_series_list = [s for s in ALL_SERIES if s not in _excluded]
_all_proc = [os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{s}.root") for s in _series_list]
_pairs = [(f, s) for f, s in zip(_all_proc, _series_list) if os.path.exists(f)]
if not _pairs:
    raise RuntimeError(f"No processed files on disk for Zip{det_tmpl}")
_ref_file = _pairs[0][0]   # identical to original: all_proc_files[0]

det_chan_map = {}
with uproot.open(_ref_file) as _f:
    for _det in dets_all:
        try:
            _keys = list(_f[f'rqDir/zip{_det}'].keys())
            det_chan_map[_det] = [c for c in ALL_CHANS if f'{c}OFdelay' in _keys]
        except Exception:
            det_chan_map[_det] = []
chans = det_chan_map[det_tmpl]
print(f"=== Zip{det_tmpl} / Series {series} ===")
print(f"Channels: {chans}")

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

# ── Event selection for this series ───────────────────────────────────────────
fpath = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
evnums     = np.array([], dtype=int)
ptof_delay = {}
baseline   = {c: {} for c in chans}

if not os.path.exists(fpath):
    print(f"WARNING: processed file not found: {fpath}")
else:
    try:
        with uproot.open(fpath) as f:
            trig_type = f['rqDir/eventTree/TriggerType'].array(library='np')
            event_num = f['rqDir/eventTree/EventNumber'].array(library='np').astype(int)
            ptof_amps = f[f'rqDir/zip{det_tmpl}/PTOFamps'].array(library='np')
            mask      = ((trig_type == 1) & (ptof_amps != -999999) &
                         (ptof_amps > PTOF_LO) & (ptof_amps < PTOF_HI))
            evnums    = event_num[mask]
            try:
                ptof_delay_arr = f[f'rqDir/zip{det_tmpl}/PTOFdelay'].array(library='np')[mask]
            except Exception:
                ptof_delay_arr = np.zeros(len(evnums))
            ptof_delay = dict(zip(evnums, ptof_delay_arr))
            for c in chans:
                try:
                    bs_arr = f[f'rqDir/zip{det_tmpl}/{c}bs'].array(library='np')[mask]
                except Exception:
                    bs_arr = np.zeros(len(evnums))
                baseline[c] = dict(zip(evnums, bs_arr))
        print(f'  {series}: {len(evnums)} events selected')
    except Exception as e:
        print(f'  {series}: ERROR — {e}')

# ── Raw trace reading ─────────────────────────────────────────────────────────
channel_traces    = {c: [] for c in chans}
pf_traces         = []
raw_sample        = {c: [] for c in chans}
negative_rejected = {c: 0 for c in chans}

if len(evnums) > 0:
    raw_series_dir = f'{RAW_DIR}/{series}'
    if not os.path.isdir(raw_series_dir):
        print(f'  {series}: rawio error — ERROR: No raw data files found!')
    else:
        evnum_set = set(int(n) for n in evnums)
        z_key = f'Z{det_tmpl}'
        try:
            myreader   = rawio.RawDataReader(raw_series_dir)
            nb_info    = myreader.get_nb_events()
            total_evts = nb_info.get('NbEventsNotEmpty', nb_info.get('NbEvents', 50000))
            print(f'  INFO: Found {nb_info.get("NbMidasFiles", "?")} midas raw data files')
            events_list = myreader.read_events(
                output_format=2, skip_empty=True, trigger_types=[1],
                nb_events=total_evts, detector_nums=[det_tmpl], channel_names=chans)

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
                    baseline_rq = baseline[chan].get(evn)
                    y_sub, ok = preprocess(pulse, baseline_rq)
                    if not ok:
                        continue
                    delay_s = ptof_delay.get(evn, 0.0)
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
        except Exception as e:
            print(f'  {series}: rawio error — {e}')

for c in chans:
    print(f'  {c}: {len(channel_traces[c])} traces, '
          f'{negative_rejected[c]} post-pulse >5% undershoots rejected')

# Ensure ALL_CHANS coverage for uniform merge
for c in ALL_CHANS:
    channel_traces.setdefault(c, [])
    raw_sample.setdefault(c, [])
    negative_rejected.setdefault(c, 0)

with open(PARTIAL_FILE, 'wb') as f:
    pickle.dump({'det': det_tmpl, 'series': series,
                 'channel_traces': channel_traces,
                 'pf_traces': pf_traces,
                 'raw_sample': raw_sample,
                 'negative_rejected': negative_rejected,
                 'excluded': False}, f)
print(f"Saved: {PARTIAL_FILE}")
print(f"Done. Zip{det_tmpl} Series {series} complete.")
