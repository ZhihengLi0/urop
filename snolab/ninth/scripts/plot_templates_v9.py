#!/usr/bin/env python3
# coding: utf-8
# Template shape overlay plots for the ninth iteration.
# Reads AllZips merged ROOT file (agnostic or specific) and per-zip caches.
# Usage: python plot_templates_v9.py --mode agnostic|specific

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['agnostic', 'specific'], default='agnostic')
args = parser.parse_args()
MODE = args.mode

import os, pickle
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import uproot

RUN_DIR = os.environ.get("R4_RUN_DIR", ".").strip()
if RUN_DIR:
    RUN_DIR = os.path.abspath(RUN_DIR)
CACHE_DIR = os.path.join(RUN_DIR, "cache")
ROOT_DIR  = os.path.join(RUN_DIR, MODE, "root_files")
OUTDIR    = os.path.join(RUN_DIR, MODE, "template_plots")
os.makedirs(OUTDIR, exist_ok=True)

SAMPLERATE  = 625000
TRACELENGTH = 32768
ZIPS        = [1, 4, 6, 7, 10, 15, 16, 18]

WRITE_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
               'PAS2','PBS2','PCS2','PDS2','PES2','PFS2','PT','PS1','PS2']
S1_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1']
S2_CHANS = ['PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
COLORS_S1 = plt.cm.Blues(np.linspace(0.4, 0.9, 6))
COLORS_S2 = plt.cm.Oranges(np.linspace(0.4, 0.9, 6))

t_axis = np.arange(TRACELENGTH) / SAMPLERATE * 1e3  # ms

def load_root(root_path, det):
    out = {}
    try:
        with uproot.open(root_path) as f:
            base = f[f'zip{det}']
            for ch in WRITE_CHANS:
                try:
                    out[ch] = base[ch].values()
                except Exception:
                    pass
    except Exception as e:
        print(f"  ERROR: {e}")
    return out

def load_cache(det):
    path = os.path.join(CACHE_DIR, f"traces_cache_zip{det}.pkl")
    if not os.path.exists(path):
        return None, None
    with open(path, 'rb') as f:
        d = pickle.load(f)
    return d.get('channel_traces', {}), d.get('pf_traces', [])

for det in ZIPS:
    root_path = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_{MODE}.root")
    if not os.path.exists(root_path):
        print(f"Zip{det}: {root_path} not found, skipping")
        continue

    print(f"\n=== Zip{det} [{MODE}] ===")
    tmpls = load_root(root_path, det)
    if not tmpls:
        continue
    ch_traces, pf_traces = load_cache(det)

    # 1x1 templates
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    fig.suptitle(f'Zip{det} — {MODE.capitalize()} Templates (1×1)', fontsize=14)
    ax_s1, ax_s2, ax_pt = axes
    for i, ch in enumerate(S1_CHANS):
        if ch in tmpls:
            ax_s1.plot(t_axis, tmpls[ch], color=COLORS_S1[i], lw=1.2, label=ch)
    ax_s1.set_ylabel('Amplitude (norm.)'); ax_s1.set_title('S1 channels')
    if ax_s1.lines:
        ax_s1.legend(ncol=6, fontsize=7)
    ax_s1.set_ylim(-0.1, 1.15); ax_s1.grid(alpha=0.3)
    for i, ch in enumerate(S2_CHANS):
        if ch in tmpls:
            ax_s2.plot(t_axis, tmpls[ch], color=COLORS_S2[i], lw=1.2, label=ch)
    ax_s2.set_ylabel('Amplitude (norm.)'); ax_s2.set_title('S2 channels')
    if ax_s2.lines:
        ax_s2.legend(ncol=6, fontsize=7)
    ax_s2.set_ylim(-0.1, 1.15); ax_s2.grid(alpha=0.3)
    for ch, col, ls in [('PT','black','-'), ('PS1','steelblue','--'), ('PS2','darkorange','--')]:
        if ch in tmpls:
            ax_pt.plot(t_axis, tmpls[ch], color=col, lw=1.5, ls=ls, label=ch)
    ax_pt.set_ylabel('Amplitude (norm.)'); ax_pt.set_xlabel('Time (ms)')
    ax_pt.set_title('PT / PS1 / PS2'); ax_pt.legend(); ax_pt.set_ylim(-0.1, 1.15)
    ax_pt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f'zip{det}_templates_1x1.png'), dpi=150)
    plt.close()

    # Rise region zoom
    lo, hi = 13500, 17500
    t_zoom = t_axis[lo:hi]
    fig2, axes2 = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig2.suptitle(f'Zip{det} — Rise Region Zoom [{MODE}]', fontsize=13)
    ax2_top, ax2_bot = axes2
    for i, ch in enumerate(S1_CHANS):
        if ch in tmpls:
            ax2_top.plot(t_zoom, tmpls[ch][lo:hi], color=COLORS_S1[i], lw=1.2, label=ch)
    for i, ch in enumerate(S2_CHANS):
        if ch in tmpls:
            ax2_top.plot(t_zoom, tmpls[ch][lo:hi], color=COLORS_S2[i], lw=1.2, label=ch)
    ax2_top.legend(ncol=6, fontsize=7); ax2_top.grid(alpha=0.3)
    ax2_top.set_ylabel('Amplitude (norm.)')
    for ch, col, ls in [('PT','black','-'), ('PS1','steelblue','--'), ('PS2','darkorange','--')]:
        if ch in tmpls:
            ax2_bot.plot(t_zoom, tmpls[ch][lo:hi], color=col, lw=1.5, ls=ls, label=ch)
    ax2_bot.legend(); ax2_bot.grid(alpha=0.3)
    ax2_bot.set_ylabel('Amplitude (norm.)'); ax2_bot.set_xlabel('Time (ms)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f'zip{det}_templates_zoom.png'), dpi=150)
    plt.close()

    # NxM components
    try:
        with uproot.open(root_path) as f:
            base = f[f'zip{det}']
            keys = list(base.keys())
            nxm_chans = {}
            for k in keys:
                if 'nxm' in k:
                    ch_name = k.split('nxm')[0]
                    nxm_chans.setdefault(ch_name, []).append(k)
    except Exception:
        nxm_chans = {}

    if nxm_chans:
        sample_chan = next(iter(nxm_chans))
        comps = nxm_chans[sample_chan]
        n_comp = len(comps)
        lo_nxm = 13000; hi_nxm = 22000
        t_nxm = t_axis[lo_nxm:hi_nxm]
        _comp_colors = plt.cm.tab10(np.linspace(0, 0.9, n_comp))
        with uproot.open(root_path) as f:
            base = f[f'zip{det}']
            fig3, ax3 = plt.subplots(figsize=(14, 5))
            for i in range(n_comp):
                k = f'{sample_chan}nxm{i}'
                try:
                    comp_vals = base[k].values()
                    label = ('nxm0 — mean pulse' if i == 0 else
                             f'nxm{i} — PC{i-1}')
                    ax3.plot(t_nxm, comp_vals[lo_nxm:hi_nxm], lw=1.0,
                             color=_comp_colors[i], label=label)
                except Exception:
                    pass
            ax3.set_xlabel('Time (ms)'); ax3.set_ylabel('Amplitude (norm.)')
            ax3.legend(fontsize=9); ax3.grid(alpha=0.3)
            fig3.suptitle(f'Zip{det} — {MODE.capitalize()} NxM mean + PCA ({sample_chan})',
                          fontsize=12)
            fig3.tight_layout()
            plt.savefig(os.path.join(OUTDIR, f'zip{det}_nxm_components.png'), dpi=150)
            plt.close()
        print(f"  NxM components plot saved.")

    # Raw traces overlay
    if ch_traces:
        chans_avail = [c for c in S1_CHANS + S2_CHANS if c in ch_traces and ch_traces[c]]
        if chans_avail:
            ncols = min(4, len(chans_avail))
            nrows = (len(chans_avail) + ncols - 1) // ncols
            fig4, axes4 = plt.subplots(nrows, ncols, figsize=(5*ncols, 3.5*nrows), sharex=True)
            axes4 = np.array(axes4).flatten()
            fig4.suptitle(f'Zip{det} — 100 kHz LP Aligned Traces', fontsize=13)
            for idx, ch in enumerate(chans_avail):
                ax = axes4[idx]
                traces = ch_traces[ch]
                col = COLORS_S1[S1_CHANS.index(ch)] if ch in S1_CHANS \
                      else COLORS_S2[S2_CHANS.index(ch)]
                for tr in traces[:30]:
                    ax.plot(t_axis, np.array(tr), color=col, alpha=0.25, lw=0.6)
                ax.set_title(f'{ch} ({len(traces)})', fontsize=9)
                ax.set_ylabel('Amplitude (ADC)')
                ax.grid(alpha=0.3)
            for ax in axes4[len(chans_avail):]:
                ax.set_visible(False)
            plt.tight_layout()
            plt.savefig(os.path.join(OUTDIR, f'zip{det}_raw_traces.png'), dpi=120)
            plt.close()

# PT comparison across all zips
fig_all, ax_all = plt.subplots(figsize=(14, 6))
ax_all.set_title(f'PT Template Comparison — All Zips [{MODE}]', fontsize=13)
zip_colors = plt.cm.tab10(np.linspace(0, 0.9, len(ZIPS)))
for det, col in zip(ZIPS, zip_colors):
    root_path = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_{MODE}.root")
    if not os.path.exists(root_path):
        continue
    tmpls = load_root(root_path, det)
    if 'PT' in tmpls:
        ax_all.plot(t_axis, tmpls['PT'], color=col, lw=1.4, label=f'Zip{det}')
ax_all.set_xlabel('Time (ms)'); ax_all.set_ylabel('Amplitude (norm.)')
ax_all.legend(ncol=4, fontsize=9); ax_all.set_ylim(-0.1, 1.15); ax_all.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, 'all_zips_PT_comparison.png'), dpi=150)
plt.close()

# All analytic pulses: load all ROOT files once
all_data = {}
for det, col in zip(ZIPS, zip_colors):
    root_path = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_{MODE}.root")
    if os.path.exists(root_path):
        all_data[det] = (load_root(root_path, det), col)

lo_ch, hi_ch = 12500, 22000
t_zoom_ch = t_axis[lo_ch:hi_ch]

# S1 and S2: 2x3 grid, one subplot per channel, all zips overlaid
for grp_name, grp_chans in [('S1', S1_CHANS), ('S2', S2_CHANS)]:
    fig_g, axes_g = plt.subplots(2, 3, figsize=(16, 9), sharex=True, sharey=True)
    fig_g.suptitle(f'All Analytic Pulses — {grp_name} channels, all zips [{MODE}]', fontsize=13)
    for ax, chan in zip(axes_g.flat, grp_chans):
        for det, (tmpls, col) in all_data.items():
            if chan in tmpls:
                ax.plot(t_zoom_ch, tmpls[chan][lo_ch:hi_ch], color=col, lw=1.1,
                        alpha=0.9, label=f'Zip{det}')
        ax.set_title(chan, fontsize=10)
        ax.set_ylim(-0.1, 1.15)
        ax.grid(alpha=0.3)
    axes_g[0, 0].legend(ncol=2, fontsize=7)
    for ax in axes_g[1]:
        ax.set_xlabel('Time (ms)')
    for ax in axes_g[:, 0]:
        ax.set_ylabel('Amplitude (norm.)')
    fig_g.tight_layout()
    out_g = os.path.join(OUTDIR, f'all_analytic_{grp_name}_channels.png')
    plt.savefig(out_g, dpi=150)
    plt.close()
    print(f"Saved: {out_g}")

# PT / PS1 / PS2: 1x3 subplots, all zips overlaid
fig_pt, axes_pt = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
fig_pt.suptitle(f'All Analytic Pulses — PT / PS1 / PS2, all zips [{MODE}]', fontsize=13)
for ax, chan in zip(axes_pt, ['PT', 'PS1', 'PS2']):
    for det, (tmpls, col) in all_data.items():
        if chan in tmpls:
            ax.plot(t_zoom_ch, tmpls[chan][lo_ch:hi_ch], color=col, lw=1.2,
                    alpha=0.9, label=f'Zip{det}')
    ax.set_title(chan, fontsize=11)
    ax.set_xlabel('Time (ms)')
    ax.set_ylim(-0.1, 1.15)
    ax.grid(alpha=0.3)
axes_pt[0].set_ylabel('Amplitude (norm.)')
axes_pt[0].legend(ncol=2, fontsize=8)
fig_pt.tight_layout()
out_pt = os.path.join(OUTDIR, 'all_analytic_PT_PS1_PS2.png')
plt.savefig(out_pt, dpi=150)
plt.close()
print(f"Saved: {out_pt}")

print(f"\nDone. Plots in: {os.path.abspath(OUTDIR)}")
