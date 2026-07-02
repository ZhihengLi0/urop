#!/usr/bin/env python3
# coding: utf-8
"""
Per-day, per-detector section-3 trace reader.

Reads raw traces for one calendar day's series that pass PTOFamps + undershoot
cuts, LP-filters, and saves both aligned and unaligned normalised traces to pkl.

Output: $R4_RUN_DIR/cache/sec3_day{day}_zip{det}.pkl

Usage:
  python process_day_section3.py --det N --day 260617
"""

import argparse, os, pickle
import numpy as np
import uproot
from scipy.signal import butter, sosfilt  # used directly in butter_lp

try:
    import rawio
    HAS_RAWIO = True
except ImportError:
    HAS_RAWIO = False
    print("WARNING: rawio not available — no traces will be read")

# ── Config ─────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"
SAMPLERATE    = 625000
TRACELENGTH   = 32768
FILTER_KHZ    = 100.0
ALIGN_PEAK_LO = 15000
ALIGN_PEAK_HI = 18000
NEGATIVE_FRACTION     = 0.05
NEGATIVE_TAIL_SAMPLES = 12000
CACHE_VERSION         = 1

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

# ── CLI ────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
parser.add_argument('--day', type=str, required=True,
                    help='Date string embedded in series name, e.g. 260617')
args = parser.parse_args()

det = args.det
day = args.day

RUN_DIR   = os.environ.get('R4_RUN_DIR', '.').strip()
CACHE_DIR = os.path.join(RUN_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

cache_file = os.path.join(CACHE_DIR, f'sec3_day{day}_zip{det}.pkl')

print(f"=== Zip{det}  Day{day} ===")

if det not in PTOF_RANGES:
    raise ValueError(f"Zip{det} not in PTOF_RANGES")

# ── Select series for this day and detector ────────────────────────────────────
_excluded   = set(SERIES_EXCLUSIONS.get(det, []))
day_series  = [s for s in ALL_SERIES
               if s[2:8] == day and s not in _excluded]

if not day_series:
    print(f"No series for Zip{det} Day{day} after exclusions — writing empty pkl.")
    with open(cache_file, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION, 'det': det, 'day': day,
                     'traces_corr': {}, 'traces_uncorr': {}}, f)
    raise SystemExit(0)

print(f"Series ({len(day_series)}): {day_series}")

# ── Build channel map from first available processed file ─────────────────────
proc_files = {s: os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{s}.root")
              for s in day_series}
missing = [s for s, f in proc_files.items() if not os.path.exists(f)]
if missing:
    print(f"WARNING: processed file not found for: {missing}")
    for s in missing:
        del proc_files[s]
        day_series.remove(s)

if not proc_files:
    print("No processed files available — writing empty pkl.")
    with open(cache_file, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION, 'det': det, 'day': day,
                     'traces_corr': {}, 'traces_uncorr': {}}, f)
    raise SystemExit(0)

_ref = list(proc_files.values())[0]
det_chan_map = {}
with uproot.open(_ref) as _f:
    for _d in dets_all:
        try:
            _keys = list(_f[f'rqDir/zip{_d}'].keys())
            det_chan_map[_d] = [c for c in ALL_CHANS if f'{c}OFdelay' in _keys]
        except Exception:
            det_chan_map[_d] = []

chans = det_chan_map.get(det, [])
if not chans:
    print(f"No channels found for Zip{det}")
    with open(cache_file, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION, 'det': det, 'day': day,
                     'traces_corr': {c: [] for c in ALL_CHANS},
                     'traces_uncorr': {c: [] for c in ALL_CHANS}}, f)
    raise SystemExit(0)

print(f"Channels ({len(chans)}): {chans}")

# ── Helpers ────────────────────────────────────────────────────────────────────
def butter_lp(data, cutoff_khz=FILTER_KHZ, fs=SAMPLERATE, order=4):
    sos = butter(order, cutoff_khz * 1000, btype='low', fs=fs, output='sos')
    return sosfilt(sos, data)

def preprocess(y_raw, baseline_rq=None, n=5000):
    y = y_raw.astype(np.float64)
    if baseline_rq is None or not np.isfinite(baseline_rq) or baseline_rq == -999999:
        bs = np.mean(y[:n])
    else:
        bs = float(baseline_rq)
    y = y - bs
    return y if np.max(y) > 0 else None

# ── Event selection from processed files ──────────────────────────────────────
PTOF_LO, PTOF_HI = PTOF_RANGES[det]

sel_events     = {}
sel_ptof_delay = {}
sel_baseline   = {}

for series in day_series:
    fpath = proc_files[series]
    try:
        with uproot.open(fpath) as f:
            trig  = f['rqDir/eventTree/TriggerType'].array(library='np')
            evnum = f['rqDir/eventTree/EventNumber'].array(library='np').astype(int)
            ptof  = f[f'rqDir/zip{det}/PTOFamps'].array(library='np')
            mask  = (trig == 1) & (ptof != -999999) & \
                    (ptof > PTOF_LO) & (ptof < PTOF_HI)
            evs   = evnum[mask]
            sel_events[series]     = evs
            sel_baseline[series]   = {}
            try:
                delay_arr = f[f'rqDir/zip{det}/PTOFdelay'].array(library='np')[mask]
            except Exception:
                delay_arr = np.zeros(len(evs))
            sel_ptof_delay[series] = dict(zip(evs, delay_arr))
            for c in chans:
                try:
                    bs_arr = f[f'rqDir/zip{det}/{c}bs'].array(library='np')[mask]
                except Exception:
                    bs_arr = np.zeros(len(evs))
                sel_baseline[series][c] = dict(zip(evs, bs_arr))
        print(f"  {series}: {len(evs)} events pass PTOFamps cut")
    except Exception as e:
        print(f"  {series}: ERROR reading processed file — {e}")
        sel_events[series]     = np.array([], dtype=int)
        sel_ptof_delay[series] = {}
        sel_baseline[series]   = {c: {} for c in chans}

total = sum(len(v) for v in sel_events.values())
print(f"Total: {total} events pass PTOFamps cut")

# ── Read raw traces ────────────────────────────────────────────────────────────
if not HAS_RAWIO:
    print("rawio not available — cannot read raw traces. Writing empty pkl.")
    with open(cache_file, 'wb') as f:
        pickle.dump({'cache_version': CACHE_VERSION, 'det': det, 'day': day,
                     'chans': chans,
                     'traces_corr':   {c: [] for c in chans},
                     'traces_uncorr': {c: [] for c in chans}}, f)
    raise SystemExit(1)

traces_corr   = {c: [] for c in chans}
traces_uncorr = {c: [] for c in chans}
z_key = f'Z{det}'

for series, evnums in sel_events.items():
    if len(evnums) == 0:
        continue
    raw_dir = f'{RAW_DIR}/{series}'
    if not os.path.isdir(raw_dir):
        print(f"  {series}: raw directory not found, skipping")
        continue
    evnum_set = set(int(n) for n in evnums)
    try:
        reader  = rawio.RawDataReader(raw_dir)
        nb      = reader.get_nb_events()
        total_e = nb.get('NbEventsNotEmpty', nb.get('NbEvents', 50000))
        events  = reader.read_events(output_format=2, skip_empty=True,
                                     trigger_types=[1], nb_events=total_e,
                                     detector_nums=[det], channel_names=chans)
    except Exception as e:
        print(f"  {series}: rawio error — {e}"); continue

    n_good = 0
    for event in events:
        evn = int(event['event']['EventNumber'])
        if evn not in evnum_set:
            continue
        delay_s = sel_ptof_delay[series].get(evn, 0.0)
        if not np.isfinite(delay_s):
            continue
        shift = -round(delay_s * SAMPLERATE)

        for chan in chans:
            try:
                pulse = event[z_key][chan]
            except KeyError:
                continue
            y = preprocess(pulse, sel_baseline[series][chan].get(evn))
            if y is None:
                continue

            # corrected: apply PTOFdelay shift then LP filter
            y_al = np.zeros(TRACELENGTH)
            if shift > 0:
                y_al[shift:] = y[:-shift] if shift < TRACELENGTH else 0
            elif shift < 0:
                y_al[:shift] = y[-shift:] if -shift < TRACELENGTH else 0
            else:
                y_al[:] = y
            y_corr   = butter_lp(y_al)
            peak_idx = int(np.argmax(y_corr))
            if peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
                continue
            peak = np.max(y_corr)
            if peak <= 0:
                continue
            # undershoot cut
            tail = y_corr[peak_idx:min(TRACELENGTH, peak_idx + NEGATIVE_TAIL_SAMPLES)]
            if len(tail) and np.min(tail) < -NEGATIVE_FRACTION * peak:
                continue

            traces_corr[chan].append(y_corr / peak)
            n_good += 1

            # uncorrected: LP filter only, no PTOFdelay shift
            y_uncorr = butter_lp(y)
            peak_u   = np.max(y_uncorr)
            if peak_u > 0:
                traces_uncorr[chan].append(y_uncorr / peak_u)

    print(f"  {series}: {n_good} good channel-trace pairs")

for c in chans:
    print(f"  {c}: {len(traces_corr[c])} traces saved")

# ── Save pkl ──────────────────────────────────────────────────────────────────
with open(cache_file, 'wb') as f:
    pickle.dump({
        'cache_version': CACHE_VERSION,
        'det':           det,
        'day':           day,
        'chans':         chans,
        'traces_corr':   traces_corr,
        'traces_uncorr': traces_uncorr,
    }, f)
print(f"Saved: {cache_file}")
print(f"Done. Zip{det} Day{day} complete.")
