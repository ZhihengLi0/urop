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
from scipy.optimize import curve_fit
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
SECTION3_RISE_INDEX = 16050
SECTION3_TARGET_AMP = 1300.0
FIT_LO       = 15000
FIT_HI       = 18000
FIT_MAXFEV   = 20000
MIN_FIT_SNR  = 4.0
MAX_FIT_RMSE_FRAC = 0.50
NEGATIVE_FRACTION     = 0.05
NEGATIVE_TAIL_SAMPLES = 12000
CACHE_VERSION         = 4

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

def two_exp_fit(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = (x - pretrigger) / SAMPLERATE
    # Clip to zero before pretrigger: np.where evaluates both branches, so
    # negative dt with small t_rise causes exp overflow → inf → curve_fit fails.
    dt_pos = np.clip(dt, 0.0, None)
    pulse = -(amp * np.exp(-dt_pos / t_rise) - amp * np.exp(-dt_pos / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

def preprocess(y_raw, baseline_rq=None, n=5000):
    y = y_raw.astype(np.float64)
    if baseline_rq is None or not np.isfinite(baseline_rq) or baseline_rq == -999999:
        bs = np.mean(y[:n])
    else:
        bs = float(baseline_rq)
    y = y - bs
    return y if np.max(y) > 0 else None

def shift_trace(y, shift):
    out = np.zeros(TRACELENGTH, dtype=np.float64)
    if shift > 0:
        if shift < TRACELENGTH:
            out[shift:] = y[:-shift]
    elif shift < 0:
        if -shift < TRACELENGTH:
            out[:shift] = y[-shift:]
    else:
        out[:] = y
    return out

def first_rise_index(y, peak_idx, peak, frac=0.05):
    lo = max(0, peak_idx - 2500)
    segment = y[lo:peak_idx + 1]
    hits = np.flatnonzero(segment >= frac * peak)
    return int(lo + hits[0]) if len(hits) else int(peak_idx)

def fit_section3_pulse(y_raw, baseline_rq=None):
    y_raw = y_raw.astype(np.float64)
    baseline0 = float(baseline_rq) if (
        baseline_rq is not None and np.isfinite(baseline_rq) and baseline_rq != -999999
    ) else float(np.mean(y_raw[:5000]))

    # Use LP-filtered trace for peak detection and rise-index estimation.
    # The raw trace contains noise spikes that move the apparent peak outside
    # the expected window and cause rise0 < FIT_LO → ValueError in curve_fit.
    y_lp = butter_lp(y_raw - baseline0)
    peak_idx = int(np.argmax(y_lp))
    peak = float(np.max(y_lp))
    if peak <= 0 or peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
        return None, 'peak_window'
    noise = float(np.std(y_lp[:5000]))
    if noise <= 0 or peak / noise < MIN_FIT_SNR:
        return None, 'low_snr'

    # Estimate pretrigger from peak position using initial time-constant guesses.
    # first_rise_index is unreliable on noisy traces — noise spikes bias it far
    # before the true pulse start, causing the optimizer to find a wrong local
    # minimum with t_rise > t_fall (rejected as unphysical).
    T_RISE_INIT = 6.0e-5
    T_FALL_INIT = 2.8e-4
    dt_to_peak = (np.log(T_FALL_INIT / T_RISE_INIT) /
                  (1.0 / T_RISE_INIT - 1.0 / T_FALL_INIT))  # seconds
    pretrig_init = float(np.clip(
        peak_idx - dt_to_peak * SAMPLERATE, FIT_LO, FIT_HI - 1))
    x = np.arange(FIT_LO, min(FIT_HI, TRACELENGTH), dtype=np.float64)
    y_fit = y_lp[FIT_LO:min(FIT_HI, TRACELENGTH)]
    p0 = [peak, T_RISE_INIT, T_FALL_INIT, 0.0, pretrig_init]
    bounds = ([0.0, 1.0e-6, 1.0e-6, -5.0 * max(peak, 1.0), FIT_LO],
              [np.inf, 2.0e-3, 5.0e-3,  5.0 * max(peak, 1.0), FIT_HI])

    try:
        popt, _ = curve_fit(two_exp_fit, x, y_fit, p0=p0, bounds=bounds,
                            maxfev=FIT_MAXFEV)
        amp, t_rise, t_fall, baseline, pretrigger = popt
        if not np.all(np.isfinite(popt)) or amp <= 0:
            raise RuntimeError("invalid_fit")
        align_idx = int(round(pretrigger))
        scale_amp = float(amp)
        t_rise = float(t_rise)
        t_fall = float(t_fall)
        if not (1.0e-6 <= t_rise < t_fall <= 5.0e-3):
            raise RuntimeError("unphysical_time_constants")
        fit_resid = y_fit - two_exp_fit(x, *popt)
        fit_rmse = float(np.sqrt(np.mean(fit_resid * fit_resid)))
        if fit_rmse / scale_amp > MAX_FIT_RMSE_FRAC:
            raise RuntimeError("poor_fit_quality")
        fit_ok = True
    except RuntimeError as e:
        return None, str(e)
    except Exception:
        return None, 'fit_failed'

    # y_lp is butter_lp(y_raw - baseline0), already baseline-subtracted.
    # `baseline` is the residual baseline term from the LP-trace fit (~0).
    y_base = y_lp - baseline
    shift = SECTION3_RISE_INDEX - align_idx
    y_aligned = shift_trace(y_base, shift)
    y_scaled = y_aligned * (SECTION3_TARGET_AMP / scale_amp)

    # Reject if the scaled peak is far below the target — indicates the fit found
    # a spurious amplitude (dead channel noise) or the shift pushed the pulse
    # entirely out of the trace window.
    if np.max(y_scaled) < SECTION3_TARGET_AMP * 0.5:
        return None, 'low_scaled_amplitude'

    return y_scaled, {
        'fit_ok': fit_ok,
        'amp': float(scale_amp),
        'baseline': float(baseline),
        'align_idx': int(align_idx),
        'shift': int(shift),
        't_rise': float(t_rise),
        't_fall': float(t_fall),
        'snr': float(peak / noise),
        'fit_rmse_frac': float(fit_rmse / scale_amp),
    }

# ── Event selection from processed files ──────────────────────────────────────
PTOF_LO, PTOF_HI = PTOF_RANGES[det]

sel_events     = {}
sel_ptof_delay = {}
sel_baseline   = {}

for series in day_series:
    fpath = proc_files[series]
    try:
        with uproot.open(fpath) as f:
            trig     = f['rqDir/eventTree/TriggerType'].array(library='np')
            trig_det = f['rqDir/eventTree/TriggerDetectorNum'].array(library='np')
            evnum    = f['rqDir/eventTree/EventNumber'].array(library='np').astype(int)
            ptof     = f[f'rqDir/zip{det}/PTOFamps'].array(library='np')
            mask  = (trig == 1) & (trig_det == det) & (ptof != -999999) & \
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
selected_event_counts = {s: int(len(v)) for s, v in sel_events.items()}
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
trace_meta    = {c: [] for c in chans}
reject_stats  = {}
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
            baseline_rq = sel_baseline[series][chan].get(evn)
            y = preprocess(pulse, baseline_rq)
            if y is None:
                reject_stats['preprocess'] = reject_stats.get('preprocess', 0) + 1
                continue

            fitted = fit_section3_pulse(pulse, baseline_rq)
            if fitted[0] is None:
                reject_stats[fitted[1]] = reject_stats.get(fitted[1], 0) + 1
                continue
            y_corr, meta = fitted
            peak_idx = int(np.argmax(y_corr))
            peak = np.max(y_corr)
            if peak <= 0:
                continue
            # undershoot cut
            tail = y_corr[peak_idx:min(TRACELENGTH, peak_idx + NEGATIVE_TAIL_SAMPLES)]
            if len(tail) and np.min(tail) < -NEGATIVE_FRACTION * peak:
                reject_stats['undershoot'] = reject_stats.get('undershoot', 0) + 1
                continue

            traces_corr[chan].append(y_corr)
            trace_meta[chan].append(meta)
            n_good += 1

            # uncorrected: LP filter only, no PTOFdelay shift
            y_uncorr = butter_lp(y)
            peak_u   = np.max(y_uncorr)
            if peak_u > 0:
                traces_uncorr[chan].append(y_uncorr / peak_u)

    print(f"  {series}: {n_good} good channel-trace pairs")

for c in chans:
    print(f"  {c}: {len(traces_corr[c])} traces saved")
print(f"Reject stats: {reject_stats}")

# ── Save pkl ──────────────────────────────────────────────────────────────────
with open(cache_file, 'wb') as f:
    pickle.dump({
        'cache_version': CACHE_VERSION,
        'det':           det,
        'day':           day,
        'chans':         chans,
        'section3_alignment': {
            'method': 'two_exp_fit_pretrigger_to_fixed_rise',
            'rise_index': SECTION3_RISE_INDEX,
            'target_amplitude': SECTION3_TARGET_AMP,
            'fit_window': [FIT_LO, FIT_HI],
            'min_snr': MIN_FIT_SNR,
            'max_fit_rmse_frac': MAX_FIT_RMSE_FRAC,
            'fallback': None,
        },
        'selected_event_counts': selected_event_counts,
        'total_selected_events': int(total),
        'traces_corr':   traces_corr,
        'traces_uncorr': traces_uncorr,
        'trace_meta':    trace_meta,
        'reject_stats':  reject_stats,
    }, f)
print(f"Saved: {cache_file}")
print(f"Done. Zip{det} Day{day} complete.")
