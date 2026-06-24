#!/usr/bin/env python3
# coding: utf-8
# Per-channel cross-zip rise time / fall time comparison.
# Reads time_constants_zip{N}.json from both agnostic/ and specific/ subdirs.
# For each channel: bar chart of t1, t2, t3, t4 vs zip, plus a data table beneath.
# Also writes a CSV with all values.
#
# Run after template_single_zip_v5.py for all zips.

import os, json, csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

RUN_DIR  = os.environ.get("R4_RUN_DIR", ".").strip()
ZIPS     = [1, 4, 6, 7, 10, 15, 16, 18]
ZIP_LABELS = [f"Zip{z}" for z in ZIPS]

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

# Load from agnostic (1x1 fit is identical for both modes)
JSON_DIR = os.path.join(RUN_DIR, "agnostic", "root_files")
OUT_DIR  = os.path.join(RUN_DIR, "agnostic", "template_plots")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Collect data ───────────────────────────────────────────────────────────────
# Structure: data[chan][zip] = {t1, t2, t3, t4, mode}  (values in ms)
data = {chan: {} for chan in ALL_CHANS}
present_zips = []

for det in ZIPS:
    fpath = os.path.join(JSON_DIR, f"time_constants_zip{det}.json")
    if not os.path.exists(fpath):
        print(f"  Zip{det}: JSON not found, skipping")
        continue
    present_zips.append(det)
    with open(fpath) as f:
        tc = json.load(f)
    for chan in ALL_CHANS:
        if chan not in tc:
            continue
        entry = tc[chan]
        data[chan][det] = {
            't1': entry.get('t1', np.nan) * 1e3,   # → ms
            't2': entry.get('t2', np.nan) * 1e3,
            't3': entry.get('t3', np.nan) * 1e3,
            't4': entry.get('t4', np.nan) * 1e3,
            'mode': entry.get('mode', 'N/A'),
        }

if not present_zips:
    print("No JSON files found. Run template_single_zip_v5.py first.")
    raise SystemExit(1)

print(f"Loaded data for {len(present_zips)} zips: {present_zips}")

zip_labels_present = [f"Zip{z}" for z in present_zips]
n_zips = len(present_zips)
x_pos  = np.arange(n_zips)
w = 0.20

TC_KEYS   = ['t1', 't2', 't3', 't4']
TC_COLORS = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63']
TC_LABELS = ['t1 (rise)', 't2 (fall 1)', 't3 (fall 2)', 't4 (fall 3)']

# ── CSV export ─────────────────────────────────────────────────────────────────
csv_path = os.path.join(OUT_DIR, "timeconstants_all_channels_all_zips.csv")
with open(csv_path, 'w', newline='') as csvf:
    writer = csv.writer(csvf)
    header = ['Channel'] + [f"Zip{z}_{k}" for z in ZIPS for k in TC_KEYS]
    writer.writerow(header)
    for chan in ALL_CHANS:
        row = [chan]
        for det in ZIPS:
            entry = data[chan].get(det, {})
            for k in TC_KEYS:
                row.append(f"{entry.get(k, np.nan):.4f}" if isinstance(entry.get(k, np.nan), float) else '')
        writer.writerow(row)
print(f"CSV saved: {csv_path}")

# ── Per-channel plot: bar chart + data table ───────────────────────────────────
for chan in ALL_CHANS:
    chan_data = data[chan]
    if not chan_data:
        continue

    t_vals = {k: [] for k in TC_KEYS}
    for det in present_zips:
        entry = chan_data.get(det, {})
        for k in TC_KEYS:
            t_vals[k].append(entry.get(k, np.nan))

    all_vals = [v for vlist in t_vals.values() for v in vlist if np.isfinite(v)]
    if not all_vals:
        continue

    # Separate t1 (sub-ms) from fall times (multi-ms) for readability
    fig = plt.figure(figsize=(14, 11))
    gs  = gridspec.GridSpec(4, 1, figure=fig,
                            height_ratios=[2, 2, 0.05, 2.2],
                            hspace=0.55)

    ax_t1   = fig.add_subplot(gs[0])
    ax_fall = fig.add_subplot(gs[1])
    ax_tbl  = fig.add_subplot(gs[3])
    ax_tbl.axis('off')

    # Rise time bar
    vals_t1 = t_vals['t1']
    bars = ax_t1.bar(x_pos, vals_t1, color=TC_COLORS[0], width=0.5, alpha=0.85)
    for bar, v in zip(bars, vals_t1):
        if np.isfinite(v):
            ax_t1.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.02,
                       f'{v:.4f}', ha='center', va='bottom', fontsize=8)
    ax_t1.set_xticks(x_pos)
    ax_t1.set_xticklabels(zip_labels_present, rotation=30, ha='right')
    ax_t1.set_ylabel('t1 — rise time (ms)')
    ax_t1.set_title(f'{chan} — Rise time across zips', fontsize=11)
    ax_t1.grid(axis='y', alpha=0.3)

    # Fall time bars (grouped)
    for ki, k in enumerate(TC_KEYS[1:], start=1):
        offset = (ki - 2) * w + w/2
        bars = ax_fall.bar(x_pos + offset, t_vals[k], width=w,
                           color=TC_COLORS[ki], alpha=0.85, label=TC_LABELS[ki])
        for bar, v in zip(bars, t_vals[k]):
            if np.isfinite(v):
                ax_fall.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.02,
                             f'{v:.2f}', ha='center', va='bottom', fontsize=7, rotation=55)
    ax_fall.set_xticks(x_pos)
    ax_fall.set_xticklabels(zip_labels_present, rotation=30, ha='right')
    ax_fall.set_ylabel('Fall times (ms)')
    ax_fall.set_title(f'{chan} — Fall times across zips', fontsize=11)
    ax_fall.legend(loc='upper right', fontsize=8)
    ax_fall.grid(axis='y', alpha=0.3)

    # Numerical data table
    col_labels  = zip_labels_present
    row_labels  = TC_LABELS
    cell_text   = []
    for ki, k in enumerate(TC_KEYS):
        fmt = '.4f' if ki == 0 else '.3f'
        row = [f'{v:{fmt}}' if np.isfinite(v) else 'N/A' for v in t_vals[k]]
        cell_text.append(row)

    tbl = ax_tbl.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc='center', rowLoc='center',
        loc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.5)

    # Color-code header row and row labels
    for (r, c), cell in tbl.get_celld().items():
        if r == 0 or c == -1:
            cell.set_facecolor('#D7EAF9')
            cell.set_text_props(weight='bold')
        elif r % 2 == 0:
            cell.set_facecolor('#F8F8F8')

    ax_tbl.set_title('Numerical values (ms)', fontsize=10, pad=6)

    fig.suptitle(f'Channel {chan} — Rise & Fall Time Comparison Across Zips (4th run)',
                 fontsize=13, y=0.99)
    out_path = os.path.join(OUT_DIR, f'timeconstants_{chan}_all_zips.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")

# ── Summary plot: all channels, t1 only, side by side ─────────────────────────
chans_with_data = [c for c in ALL_CHANS if data[c]]
if chans_with_data:
    n_c   = len(chans_with_data)
    cols  = 3
    rows  = (n_c + cols - 1) // cols
    fig_s, axes_s = plt.subplots(rows, cols, figsize=(18, 4*rows), sharey=False)
    axes_flat = axes_s.flatten() if n_c > 1 else [axes_s]

    for idx, chan in enumerate(chans_with_data):
        ax = axes_flat[idx]
        vals = [data[chan].get(det, {}).get('t1', np.nan) for det in present_zips]
        bars = ax.bar(x_pos, vals, color=TC_COLORS[0], alpha=0.85, width=0.6)
        for bar, v in zip(bars, vals):
            if np.isfinite(v):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.02,
                        f'{v:.4f}', ha='center', va='bottom', fontsize=7)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(zip_labels_present, rotation=45, ha='right', fontsize=8)
        ax.set_title(chan, fontsize=10)
        ax.set_ylabel('t1 (ms)', fontsize=8)
        ax.grid(axis='y', alpha=0.3)

    for ax in axes_flat[n_c:]:
        ax.set_visible(False)

    fig_s.suptitle('Rise time t1 — All channels × All zips (4th run)', fontsize=14)
    fig_s.tight_layout()
    out_path = os.path.join(OUT_DIR, 'timeconstants_summary_t1_all_zips.png')
    fig_s.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig_s)
    print(f"Saved: {out_path}")

    # ── Summary plot: t2 ──────────────────────────────────────────────────────
    fig_s2, axes_s2 = plt.subplots(rows, cols, figsize=(18, 4*rows), sharey=False)
    axes_flat2 = axes_s2.flatten() if n_c > 1 else [axes_s2]

    for idx, chan in enumerate(chans_with_data):
        ax = axes_flat2[idx]
        vals = [data[chan].get(det, {}).get('t2', np.nan) for det in present_zips]
        bars = ax.bar(x_pos, vals, color=TC_COLORS[1], alpha=0.85, width=0.6)
        for bar, v in zip(bars, vals):
            if np.isfinite(v):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.02,
                        f'{v:.3f}', ha='center', va='bottom', fontsize=7)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(zip_labels_present, rotation=45, ha='right', fontsize=8)
        ax.set_title(chan, fontsize=10)
        ax.set_ylabel('t2 (ms)', fontsize=8)
        ax.grid(axis='y', alpha=0.3)

    for ax in axes_flat2[n_c:]:
        ax.set_visible(False)

    fig_s2.suptitle('Fall time t2 — All channels × All zips (4th run)', fontsize=14)
    fig_s2.tight_layout()
    out_path = os.path.join(OUT_DIR, 'timeconstants_summary_t2_all_zips.png')
    fig_s2.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig_s2)
    print(f"Saved: {out_path}")

print("\nTime constants cross-zip comparison complete.")
