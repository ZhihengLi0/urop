#!/usr/bin/env python3
# coding: utf-8
# Template shape overlay plots for the fifth iteration.
# Reads AllZips merged ROOT file (agnostic or specific) and per-zip caches.
# Usage: python plot_templates_v5.py --mode agnostic|specific

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
    ax_s1.legend(ncol=6, fontsize=7); ax_s1.set_ylim(-0.1, 1.15); ax_s1.grid(alpha=0.3)
    for i, ch in enumerate(S2_CHANS):
        if ch in tmpls:
            ax_s2.plot(t_axis, tmpls[ch], color=COLORS_S2[i], lw=1.2, label=ch)
    ax_s2.set_ylabel('Amplitude (norm.)'); ax_s2.set_title('S2 channels')
    ax_s2.legend(ncol=6, fontsize=7); ax_s2.set_ylim(-0.1, 1.15); ax_s2.grid(alpha=0.3)
    for ch, col, ls in [('PT','black','-'), ('PS1','steelblue','--'), ('PS2','darkorange','--')]:
        if ch in tmpls:
            ax_pt.plot(t_axis, tmpls[ch], color=col, lw=1.5, ls=ls, label=ch)
    ax_pt.set_ylabel('Amplitude (norm.)'); ax_pt.set_xlabel('Time (ms)')
    ax_pt.set_title('PT / PS1 / PS2'); ax_pt.legend(); ax_pt.set_ylim(-0.1, 1.15)
    ax_pt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f'zip{det}_templates_1x1.png'), dpi=150)
    plt.close()

    # Zoom
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
        with uproot.open(root_path) as f:
            base = f[f'zip{det}']
            fig3, axes3 = plt.subplots(n_comp, 1, figsize=(14, 3*n_comp), sharex=True)
            if n_comp == 1:
                axes3 = [axes3]
            for i in range(n_comp):
                k = f'{sample_chan}nxm{i}'
                try:
                    comp_vals = base[k].values()
                    axes3[i].plot(t_nxm, comp_vals[lo_nxm:hi_nxm], lw=0.9)
                    axes3[i].set_title(f'PC{i}', fontsize=10)
                    axes3[i].set_ylabel('Amplitude'); axes3[i].grid(alpha=0.3)
                except Exception:
                    pass
            axes3[-1].set_xlabel('Time (ms)')
            fig3.suptitle(f'Zip{det} — {MODE.capitalize()} NxM PCA components ({sample_chan})',
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
            fig4.suptitle(f'Zip{det} — Raw Aligned Traces', fontsize=13)
            for idx, ch in enumerate(chans_avail):
                ax = axes4[idx]
                traces = ch_traces[ch]
                col = COLORS_S1[S1_CHANS.index(ch)] if ch in S1_CHANS \
                      else COLORS_S2[S2_CHANS.index(ch)]
                for tr in traces[:30]:
                    ax.plot(t_axis, np.array(tr), color=col, alpha=0.25, lw=0.6)
                if ch in tmpls:
                    ax.plot(t_axis, tmpls[ch], color='black', lw=1.5)
                ax.set_title(f'{ch} ({len(traces)})', fontsize=9)
                ax.set_ylim(-0.15, 1.25); ax.grid(alpha=0.3)
            for ax in axes4[len(chans_avail):]:
                ax.set_visible(False)
            plt.tight_layout()
            plt.savefig(os.path.join(OUTDIR, f'zip{det}_raw_traces.png'), dpi=120)
            plt.close()

# PT comparison across all zips
fig_all, ax_all = plt.subplots(figsize=(14, 6))
ax_all.set_title(f'PT Template Comparison — All Zips [{MODE}]', fontsize=13)
colors_all = plt.cm.tab10(np.linspace(0, 1, len(ZIPS)))
for det, col in zip(ZIPS, colors_all):
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
print(f"\nDone. Plots in: {os.path.abspath(OUTDIR)}")
