#!/usr/bin/env python3
# coding: utf-8
"""Cross-zip comparison of waveform-defined rise and fall times."""

import csv
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

RUN_DIR = os.environ.get('R4_RUN_DIR', '.').strip()
ZIPS = [1, 4, 6, 7, 10, 15, 16, 18]
ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
JSON_DIR = os.path.join(RUN_DIR, 'agnostic', 'root_files')
OUT_DIR = os.path.join(RUN_DIR, 'agnostic', 'template_plots')
os.makedirs(OUT_DIR, exist_ok=True)

data = {chan: {} for chan in ALL_CHANS}
for det in ZIPS:
    path = os.path.join(JSON_DIR, f'time_constants_zip{det}.json')
    if not os.path.exists(path):
        print(f'Zip{det}: JSON not found, skipping')
        continue
    with open(path) as handle:
        values = json.load(handle)
    for chan, entry in values.items():
        if chan not in data:
            continue
        data[chan][det] = {
            'rise_10_90': float(entry.get('rise_10_90', np.nan)) * 1e3,
            'fall_1e': float(entry.get('fall_1e', np.nan)) * 1e3,
            'mode': entry.get('mode', 'N/A'),
            't4': float(entry.get('t4', np.nan)) * 1e3,
        }

csv_path = os.path.join(OUT_DIR, 'shape_times_all_channels_all_zips.csv')
with open(csv_path, 'w', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['Channel', 'Zip', 'Model', 'Rise10_90_ms', 'Fall1e_ms', 't4_ms'])
    for chan in ALL_CHANS:
        for det in ZIPS:
            entry = data[chan].get(det)
            if entry:
                writer.writerow([chan, det, entry['mode'],
                                 f"{entry['rise_10_90']:.6f}",
                                 f"{entry['fall_1e']:.6f}",
                                 f"{entry['t4']:.6f}"])
print(f'CSV saved: {csv_path}')

for chan in ALL_CHANS:
    present = [det for det in ZIPS if det in data[chan]]
    if not present:
        continue
    x = np.arange(len(present))
    rise = [data[chan][det]['rise_10_90'] for det in present]
    fall = [data[chan][det]['fall_1e'] for det in present]
    labels = [f'Zip{det}' for det in present]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, vals, color, ylabel, title in [
            (axes[0], rise, '#2196F3', '10–90% rise time (ms)', 'Rise time'),
            (axes[1], fall, '#4CAF50', 'Peak-to-1/e fall time (ms)', 'Fall time')]:
        bars = ax.bar(x, vals, color=color, alpha=0.85, width=0.6)
        for bar, value in zip(bars, vals):
            if np.isfinite(value):
                ax.text(bar.get_x() + bar.get_width()/2, value * 1.02,
                        f'{value:.4f}', ha='center', va='bottom', fontsize=8)
        ax.set_ylabel(ylabel)
        ax.set_title(f'{chan} — {title} across zips')
        ax.grid(axis='y', alpha=0.3)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha='right')
    fig.suptitle(f'Channel {chan} — Waveform Rise & Fall Comparison (8th iteration)',
                 fontsize=13)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, f'shape_times_{chan}_all_zips.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out}')

for key, ylabel, filename in [
        ('rise_10_90', '10–90% rise time (ms)', 'shape_times_summary_rise.png'),
        ('fall_1e', 'Peak-to-1/e fall time (ms)', 'shape_times_summary_fall.png')]:
    fig, axes = plt.subplots(4, 3, figsize=(18, 16))
    for ax, chan in zip(axes.flat, ALL_CHANS):
        vals = [data[chan].get(det, {}).get(key, np.nan) for det in ZIPS]
        ax.bar(np.arange(len(ZIPS)), vals, color='#607D8B', alpha=0.85)
        ax.set_xticks(np.arange(len(ZIPS)))
        ax.set_xticklabels([f'Z{det}' for det in ZIPS], rotation=45)
        ax.set_title(chan)
        ax.set_ylabel(ylabel)
        ax.grid(axis='y', alpha=0.3)
    fig.suptitle(f'{ylabel} — all channels and zips (8th iteration)', fontsize=14)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, filename)
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out}')

print('Waveform-defined time comparison complete.')
