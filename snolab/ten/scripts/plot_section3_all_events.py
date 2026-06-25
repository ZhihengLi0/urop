#!/usr/bin/env python3
# coding: utf-8
"""
Section 3 style plot — ALL events (no undershoot cut).

Reads raw traces for every event that passes the PTOFamps cut,
applies LP filter + PTOFdelay alignment, then plots corrected overlays
(baseline=0, peak-normalised, pretrigger pinned to CANONICAL_PT).

Generates per-zip:
  zip{N}_section3_all_corrected.png   — all events, amplitude normalised
  zip{N}_section3_all_uncorrected.png — all events, raw amplitude (baseline removed)

Does NOT modify any existing cache or ROOT output.

Usage:
  python plot_section3_all_events.py [--det N]
  (omit --det to process all zips)
"""

import argparse, glob, os, pickle, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import uproot
from scipy.signal import butter, sosfilt

try:
    import rawio
    HAS_RAWIO = True
except ImportError:
    HAS_RAWIO = False

# ── Config ─────────────────────────────────────────────────────────────────────
PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR       = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG      = "Prompt_V07-02_C0.4.5"
SAMPLERATE    = 625000
TRACELENGTH   = 32768
CANONICAL_PT  = 16250
FILTER_KHZ    = 100.0
ALIGN_PEAK_LO = 15000
ALIGN_PEAK_HI = 18000

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

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
dets_all  = [1, 4, 6, 7, 9, 10, 15, 16, 18, 24]

RUN_DIR  = os.environ.get('R4_RUN_DIR', '.').strip()
OUT_DIR  = os.path.join(RUN_DIR, 'agnostic', 'template_plots')
os.makedirs(OUT_DIR, exist_ok=True)

# ── CLI ────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, default=None,
                    help='Zip number (default: all)')
args = parser.parse_args()
ZIPS = [args.det] if args.det else list(PTOF_RANGES.keys())

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

# ── Discover processed files ───────────────────────────────────────────────────
all_proc_files = sorted(glob.glob(f"{PROCESSED_DIR}/{PROD_TAG}_*.root"))
series_list    = [os.path.basename(f).replace(f"{PROD_TAG}_","").replace(".root","")
                  for f in all_proc_files]
print(f"Found {len(series_list)} series")

# ── Build det→channel map from first file ─────────────────────────────────────
det_chan_map = {}
with uproot.open(all_proc_files[0]) as _f:
    for _d in dets_all:
        try:
            _keys = list(_f[f'rqDir/zip{_d}'].keys())
            det_chan_map[_d] = [c for c in ALL_CHANS if f'{c}OFdelay' in _keys]
        except Exception:
            det_chan_map[_d] = []

t_axis = np.arange(TRACELENGTH) / SAMPLERATE * 1e3  # ms

# ── Per-zip processing ─────────────────────────────────────────────────────────
for det in ZIPS:
    print(f"\n=== Zip{det} ===")
    if not HAS_RAWIO:
        print("  rawio not available, skipping"); continue

    chans = det_chan_map.get(det, [])
    if not chans:
        print("  No channels found"); continue

    PTOF_LO, PTOF_HI = PTOF_RANGES[det]

    # -- event selection (same PTOFamps cut as main script) --------------------
    sel_events     = {}
    sel_ptof_delay = {}
    sel_baseline   = {}

    for fpath, series in zip(all_proc_files, series_list):
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
        except Exception as e:
            sel_events[series]     = np.array([], dtype=int)
            sel_ptof_delay[series] = {}
            sel_baseline[series]   = {c: {} for c in chans}

    total = sum(len(v) for v in sel_events.values())
    print(f"  {total} events pass PTOFamps cut")

    # -- read raw traces WITHOUT undershoot cut --------------------------------
    channel_traces_all = {c: [] for c in chans}  # no quality cut
    z_key = f'Z{det}'

    for series, evnums in sel_events.items():
        if len(evnums) == 0:
            continue
        raw_dir = f'{RAW_DIR}/{series}'
        if not os.path.isdir(raw_dir):
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
                y_al = np.zeros(TRACELENGTH)
                if shift > 0:
                    y_al[shift:] = y[:-shift] if shift < TRACELENGTH else 0
                elif shift < 0:
                    y_al[:shift] = y[-shift:] if -shift < TRACELENGTH else 0
                else:
                    y_al[:] = y
                y_filt   = butter_lp(y_al)
                peak_idx = int(np.argmax(y_filt))
                if peak_idx < ALIGN_PEAK_LO or peak_idx > ALIGN_PEAK_HI:
                    continue
                if np.max(y_filt) <= 0:
                    continue
                channel_traces_all[chan].append(y_filt)

    for c in chans:
        print(f"  {c}: {len(channel_traces_all[c])} traces (no undershoot cut)")

    # -- plot ------------------------------------------------------------------
    chans_have = [c for c in chans if channel_traces_all[c]]
    if not chans_have:
        print("  No traces to plot"); continue

    LO_FULL = CANONICAL_PT - 500
    HI_FULL = CANONICAL_PT + 3000
    LO_ZOOM = CANONICAL_PT - 50
    HI_ZOOM = CANONICAL_PT + 600

    n_ev_max = max(len(channel_traces_all[c]) for c in chans_have)
    ev_colors = [plt.cm.tab20(i % 20) for i in range(n_ev_max)]

    ncols = min(4, len(chans_have))
    nrows = (len(chans_have) + ncols - 1) // ncols

    for label, normalise, fname_tag, suptitle in [
        (True,  True,  'section3_all_corrected',
         'All events (no undershoot cut) — corrected\nbaseline=0, peak-normalised, PTOFdelay aligned'),
        (False, False, 'section3_all_uncorrected',
         'All events (no undershoot cut) — uncorrected\nbaseline removed, amplitude NOT normalised'),
    ]:
        fig, axes = plt.subplots(nrows, ncols * 2,
                                 figsize=(5 * ncols * 2, 3.5 * nrows),
                                 sharex='col', sharey=True)
        axes = np.array(axes).reshape(nrows, ncols * 2)
        fig.suptitle(f'Zip{det} [{os.path.basename(RUN_DIR)}] — {suptitle}', fontsize=10)

        for idx, ch in enumerate(chans_have):
            row      = idx // ncols
            col_base = (idx % ncols) * 2
            ax_full  = axes[row, col_base]
            ax_zoom  = axes[row, col_base + 1]

            traces = channel_traces_all[ch]
            for ei, tr in enumerate(traces):
                tr   = np.asarray(tr, dtype=float)
                peak = np.max(tr)
                if peak <= 0:
                    continue
                y = tr / peak if normalise else tr
                col = ev_colors[ei % len(ev_colors)]
                ax_full.plot(t_axis[LO_FULL:HI_FULL], y[LO_FULL:HI_FULL],
                             color=col, lw=0.7, alpha=0.75)
                ax_zoom.plot(t_axis[LO_ZOOM:HI_ZOOM], y[LO_ZOOM:HI_ZOOM],
                             color=col, lw=0.8, alpha=0.75)

            for ax, tag in [(ax_full, 'full'), (ax_zoom, 'zoom')]:
                ax.axvline(x=t_axis[CANONICAL_PT], color='gray',
                           lw=0.8, ls='--', alpha=0.5)
                ax.set_title(f'{ch} (n={len(traces)}) [{tag}]', fontsize=8)
                ax.grid(alpha=0.2, ls=':')
                ax.set_ylabel('Amplitude (norm.)' if normalise else 'ADC (baseline sub.)')
            ax_full.set_xlabel('Time (ms)')
            ax_zoom.set_xlabel('Time (ms)')

        for idx in range(len(chans_have), nrows * ncols):
            row = idx // ncols; col_base = (idx % ncols) * 2
            for ax in [axes[row, col_base], axes[row, col_base+1]]:
                ax.set_visible(False)

        plt.tight_layout()
        out = os.path.join(OUT_DIR, f'zip{det}_{fname_tag}.png')
        plt.savefig(out, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {out}")

print("\nDone.")
