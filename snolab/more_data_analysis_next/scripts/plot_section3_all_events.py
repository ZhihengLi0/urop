#!/usr/bin/env python3
# coding: utf-8
"""
Section 3 merge + plot.

Loads all per-day pkl files produced by process_day_section3.py,
merges traces across days, and generates:
  zip{N}_section3_corrected.png   — analytical fit traces, fixed rise, peak-normalised

Usage:
  python plot_section3_all_events.py [--det N]
  (omit --det to process all detectors)
"""

import argparse, glob, os, pickle
import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CANONICAL_PT = 16250
SECTION3_RISE_INDEX = 16050
SAMPLERATE   = 625000
TRACELENGTH  = 32768
AMP_MIN      = 0.0
FIT_LO       = SECTION3_RISE_INDEX - 300
FIT_HI       = SECTION3_RISE_INDEX + 5000
FIT_STRIDE   = 8
FIT_MAXFEV   = 20000

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

def two_exp_fit(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = (x - pretrigger) / SAMPLERATE
    dt_pos = np.clip(dt, 0.0, None)
    pulse = -(amp * np.exp(-dt_pos / t_rise) - amp * np.exp(-dt_pos / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)

def normalize_fixed_rise(tr):
    tr = np.asarray(tr, dtype=float)
    if not np.all(np.isfinite(tr)):
        return None
    tr[:SECTION3_RISE_INDEX + 1] = 0.0
    tr = np.maximum(tr, 0.0)
    peak = float(np.max(tr))
    if not np.isfinite(peak) or peak <= 0:
        return None
    return tr / peak

def analytical_trace_from_meta(meta):
    amp = float(meta['amp'])
    t_rise = float(meta['t_rise'])
    t_fall = float(meta['t_fall'])
    if not (np.isfinite(amp) and np.isfinite(t_rise) and np.isfinite(t_fall)):
        return None
    if not (AMP_MIN < amp) or not (0.0 < t_rise < t_fall):
        return None
    x = np.arange(TRACELENGTH, dtype=np.float64)
    tr = two_exp_fit(x, amp, t_rise, t_fall, 0.0, float(SECTION3_RISE_INDEX))
    return normalize_fixed_rise(tr)

def analytical_trace_from_trace(trace):
    trace = np.asarray(trace, dtype=np.float64)
    if trace.shape[0] != TRACELENGTH or not np.all(np.isfinite(trace)):
        return None

    x_full = np.arange(TRACELENGTH, dtype=np.float64)
    x_fit = x_full[FIT_LO:FIT_HI:FIT_STRIDE]
    y_fit = trace[FIT_LO:FIT_HI:FIT_STRIDE]
    baseline0 = float(np.median(trace[max(0, SECTION3_RISE_INDEX - 700):SECTION3_RISE_INDEX]))
    y_fit = y_fit - baseline0
    peak = float(np.max(trace[SECTION3_RISE_INDEX:min(TRACELENGTH, SECTION3_RISE_INDEX + 3000)] - baseline0))
    if not np.isfinite(peak) or peak <= 0:
        return None

    def _fixed_pt(x, amp, t_rise, t_fall, baseline):
        return two_exp_fit(x, amp, t_rise, t_fall, baseline, float(SECTION3_RISE_INDEX))

    try:
        popt, _ = curve_fit(
            _fixed_pt, x_fit, y_fit,
            p0=[peak, 6.0e-5, 2.8e-4, 0.0],
            bounds=([0.0, 1.0e-6, 1.0e-5, -0.5 * peak],
                    [np.inf, 8.0e-4, 8.0e-3, 0.5 * peak]),
            maxfev=FIT_MAXFEV)
    except Exception:
        return None

    amp, t_rise, t_fall, _baseline = popt
    if not (np.isfinite(amp) and np.isfinite(t_rise) and np.isfinite(t_fall)):
        return None
    if not (amp > 0.0 and 0.0 < t_rise < t_fall):
        return None
    tr = two_exp_fit(x_full, amp, t_rise, t_fall, 0.0, float(SECTION3_RISE_INDEX))
    return normalize_fixed_rise(tr)

# ── CLI ────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, default=None,
                    help='Zip number (default: all)')
args = parser.parse_args()
ZIPS = [args.det] if args.det else list(PTOF_RANGES.keys())

RUN_DIR   = os.environ.get('R4_RUN_DIR', '.').strip()
CACHE_DIR = os.environ.get('R4_CACHE_DIR', os.path.join(RUN_DIR, 'cache')).strip()
OUT_DIR   = os.path.join(RUN_DIR, 'agnostic', 'template_plots')
os.makedirs(OUT_DIR, exist_ok=True)

t_axis = np.arange(TRACELENGTH) / SAMPLERATE * 1e3  # ms

# ── Per-zip merge and plot ─────────────────────────────────────────────────────
for det in ZIPS:
    print(f"\n=== Zip{det} ===")

    # Find all per-day pkl files for this detector
    pattern   = os.path.join(CACHE_DIR, f'sec3_day*_zip{det}.pkl')
    day_files = sorted(glob.glob(pattern))

    if not day_files:
        print(f"  No pkl files found matching {pattern}, skipping")
        continue

    print(f"  Found {len(day_files)} day pkl file(s)")

    # Merge traces across all days
    traces_corr   = {}
    traces_uncorr = {}
    metas_corr    = {}
    chans = []

    for fpath in day_files:
        day_tag = os.path.basename(fpath).split('_zip')[0].replace('sec3_day', '')
        try:
            with open(fpath, 'rb') as f:
                data = pickle.load(f)
        except Exception as e:
            print(f"  WARNING: could not load {fpath} — {e}"); continue

        day_chans = data.get('chans', list(data.get('traces_corr', {}).keys()))
        if not chans and day_chans:
            chans = day_chans

        tc = data.get('traces_corr', {})
        tu = data.get('traces_uncorr', {})
        tm = data.get('trace_meta', {})
        for c in day_chans:
            traces_corr.setdefault(c, []).extend(tc.get(c, []))
            traces_uncorr.setdefault(c, []).extend(tu.get(c, []))
            metas_corr.setdefault(c, []).extend(tm.get(c, []))

        n = sum(len(v) for v in tc.values())
        print(f"  Day {day_tag}: {n} traces loaded")

    if not chans:
        print("  No channel data found across all days, skipping"); continue

    for c in chans:
        print(f"  {c}: {len(traces_corr.get(c, []))} total traces")

    total_traces = sum(len(traces_corr.get(c, [])) for c in chans)
    if total_traces == 0:
        print("  No traces to plot, skipping"); continue

    # -- plot ------------------------------------------------------------------
    chans_have = [c for c in chans if traces_corr.get(c)]
    if not chans_have:
        print("  No channels with traces, skipping"); continue

    LO_FULL = SECTION3_RISE_INDEX - 500
    HI_FULL = SECTION3_RISE_INDEX + 3000
    LO_ZOOM = SECTION3_RISE_INDEX - 50
    HI_ZOOM = SECTION3_RISE_INDEX + 600

    n_ev_max  = max(len(traces_corr.get(c, [])) for c in chans_have)
    ev_colors = [plt.cm.tab20(i % 20) for i in range(n_ev_max)]

    ncols = min(4, len(chans_have))
    nrows = (len(chans_have) + ncols - 1) // ncols

    analytical_corr = {}
    for ch in chans_have:
        raw_traces = traces_corr.get(ch, [])
        raw_metas = metas_corr.get(ch, [])
        if raw_metas and len(raw_metas) != len(raw_traces):
            print(f"  WARNING: {ch} has {len(raw_traces)} traces but {len(raw_metas)} metadata rows")
        ch_analytic = []
        n_rejected = 0
        if raw_metas:
            for meta in raw_metas[:len(raw_traces)]:
                tr = analytical_trace_from_meta(meta)
                if tr is None:
                    n_rejected += 1
                    continue
                ch_analytic.append(tr)
            source = 'metadata'
        else:
            for raw in raw_traces:
                tr = analytical_trace_from_trace(raw)
                if tr is None:
                    n_rejected += 1
                    continue
                ch_analytic.append(tr)
            source = 'trace-fit'
        analytical_corr[ch] = ch_analytic
        print(f"  {ch}: 2-exp analytical kept {len(ch_analytic)}/{len(raw_traces)} "
              f"from {source} (rejected={n_rejected})")

    for traces_dict, fname_tag, suptitle, y_label in [
        (analytical_corr,
         'section3_corrected',
         'Analytical fit traces — fixed rise, baseline=0, peak-normalised',
         'Amplitude (norm.)'),
    ]:
        fig, axes = plt.subplots(nrows, ncols * 2,
                                 figsize=(5 * ncols * 2, 3.5 * nrows),
                                 sharex='col', sharey=True,
                                 squeeze=False)
        axes = axes.reshape(nrows, ncols * 2)
        fig.suptitle(f'Zip{det} [{os.path.basename(RUN_DIR)}] — {suptitle}',
                     fontsize=10)

        for idx, ch in enumerate(chans_have):
            row      = idx // ncols
            col_base = (idx % ncols) * 2
            ax_full  = axes[row, col_base]
            ax_zoom  = axes[row, col_base + 1]

            ch_traces = traces_dict.get(ch, [])
            for ei, tr in enumerate(ch_traces):
                tr  = np.asarray(tr, dtype=float)
                col = ev_colors[ei % len(ev_colors)]
                ax_full.plot(t_axis[LO_FULL:HI_FULL], tr[LO_FULL:HI_FULL],
                             color=col, lw=0.7, alpha=0.6)
                ax_zoom.plot(t_axis[LO_ZOOM:HI_ZOOM], tr[LO_ZOOM:HI_ZOOM],
                             color=col, lw=0.8, alpha=0.6)

            for ax, tag in [(ax_full, 'full'), (ax_zoom, 'zoom')]:
                ax.axvline(x=t_axis[SECTION3_RISE_INDEX], color='gray',
                           lw=0.8, ls='--', alpha=0.5)
                ax.set_title(f'{ch} (n={len(ch_traces)}) [{tag}]', fontsize=8)
                ax.grid(alpha=0.2, ls=':')
                ax.set_ylabel(y_label)
            ax_full.set_xlabel('Time (ms)')
            ax_zoom.set_xlabel('Time (ms)')

        for idx in range(len(chans_have), nrows * ncols):
            row = idx // ncols; col_base = (idx % ncols) * 2
            for ax in [axes[row, col_base], axes[row, col_base + 1]]:
                ax.set_visible(False)

        plt.tight_layout()
        out = os.path.join(OUT_DIR, f'zip{det}_{fname_tag}.png')
        plt.savefig(out, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {out}")

print("\nDone.")
