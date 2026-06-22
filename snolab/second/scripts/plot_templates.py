#!/usr/bin/env python3
"""
Read completed ROOT template files and pkl trace caches,
generate PNG summary plots for each zip.
"""
import os, pickle, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import uproot

RUN_DIR = os.environ.get("R4_RUN_DIR", "").strip()
if RUN_DIR:
    RUN_DIR = os.path.abspath(RUN_DIR)
    OUTDIR = os.path.join(RUN_DIR, "template_plots")
    CACHE_DIR = os.path.join(RUN_DIR, "cache")
    ROOT_DIR = os.path.join(RUN_DIR, "root_files")
else:
    OUTDIR = "template_plots"
    CACHE_DIR = "."
    ROOT_DIR = "root_files"
SAMPLERATE = 625000
TRACELENGTH = 32768
os.makedirs(OUTDIR, exist_ok=True)

ZIPS = [1, 4, 6, 7, 10, 15, 16, 18]

WRITE_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
               'PAS2','PBS2','PCS2','PDS2','PES2','PFS2',
               'PT','PS1','PS2']

t_axis = np.arange(TRACELENGTH) / SAMPLERATE * 1e3  # in ms

# ─── color maps ───────────────────────────────────────────────────────────────
S1_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1']
S2_CHANS = ['PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
COLORS_S1 = plt.cm.Blues(np.linspace(0.4, 0.9, 6))
COLORS_S2 = plt.cm.Oranges(np.linspace(0.4, 0.9, 6))

def load_root_templates(root_path, det):
    templates = {}
    try:
        with uproot.open(root_path) as f:
            base = f[f'zip{det}']
            for ch in WRITE_CHANS:
                try:
                    h = base[ch]
                    vals = h.values()
                    templates[ch] = vals
                except Exception:
                    pass
    except Exception as e:
        print(f"  ERROR opening {root_path}: {e}")
    return templates

def load_cache(det):
    path = os.path.join(CACHE_DIR, f"traces_cache_zip{det}.pkl")
    if not os.path.exists(path):
        return None, None
    with open(path, 'rb') as f:
        d = pickle.load(f)
    return d.get('channel_traces', {}), d.get('pf_traces', [])

# ─── per-zip plot ──────────────────────────────────────────────────────────────
for det in ZIPS:
    root_path = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_1x1.root")
    if not os.path.exists(root_path):
        print(f"Zip{det}: ROOT file not found, skipping")
        continue

    print(f"\n=== Zip{det} ===")
    tmpls = load_root_templates(root_path, det)
    if not tmpls:
        print(f"  No templates loaded")
        continue

    ch_traces, pf_traces = load_cache(det)

    # ── Figure 1: all individual channels + PT/PS1/PS2 ──────────────────────
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    fig.suptitle(f'Zip{det} — Average Templates (1×1)', fontsize=14)

    ax_s1, ax_s2, ax_pt = axes

    for i, ch in enumerate(S1_CHANS):
        if ch in tmpls:
            ax_s1.plot(t_axis, tmpls[ch], color=COLORS_S1[i], lw=1.2, label=ch)
    ax_s1.set_ylabel('Amplitude (norm.)')
    ax_s1.set_title('S1 channels')
    ax_s1.legend(ncol=6, fontsize=7, loc='upper right')
    ax_s1.set_ylim(-0.1, 1.15)
    ax_s1.grid(True, alpha=0.3)

    for i, ch in enumerate(S2_CHANS):
        if ch in tmpls:
            ax_s2.plot(t_axis, tmpls[ch], color=COLORS_S2[i], lw=1.2, label=ch)
    ax_s2.set_ylabel('Amplitude (norm.)')
    ax_s2.set_title('S2 channels')
    ax_s2.legend(ncol=6, fontsize=7, loc='upper right')
    ax_s2.set_ylim(-0.1, 1.15)
    ax_s2.grid(True, alpha=0.3)

    if 'PT' in tmpls:
        ax_pt.plot(t_axis, tmpls['PT'], color='black', lw=1.5, label='PT')
    if 'PS1' in tmpls:
        ax_pt.plot(t_axis, tmpls['PS1'], color='steelblue', lw=1.2, ls='--', label='PS1')
    if 'PS2' in tmpls:
        ax_pt.plot(t_axis, tmpls['PS2'], color='darkorange', lw=1.2, ls='--', label='PS2')
    ax_pt.set_ylabel('Amplitude (norm.)')
    ax_pt.set_xlabel('Time (ms)')
    ax_pt.set_title('PT / PS1 / PS2')
    ax_pt.legend(fontsize=8, loc='upper right')
    ax_pt.set_ylim(-0.1, 1.15)
    ax_pt.grid(True, alpha=0.3)

    plt.tight_layout()
    out1 = os.path.join(OUTDIR, f'zip{det}_templates_1x1.png')
    plt.savefig(out1, dpi=150)
    plt.close()
    print(f"  Saved: {out1}")

    # ── Figure 2: zoomed-in rise region (13500–17000 samples) ────────────────
    lo, hi = 13500, 17500
    t_zoom = t_axis[lo:hi]

    fig2, axes2 = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig2.suptitle(f'Zip{det} — Template Rise Region Zoom', fontsize=13)

    ax2_top, ax2_bot = axes2
    for i, ch in enumerate(S1_CHANS):
        if ch in tmpls:
            ax2_top.plot(t_zoom, tmpls[ch][lo:hi], color=COLORS_S1[i], lw=1.2, label=ch)
    for i, ch in enumerate(S2_CHANS):
        if ch in tmpls:
            ax2_top.plot(t_zoom, tmpls[ch][lo:hi], color=COLORS_S2[i], lw=1.2, label=ch)
    ax2_top.set_ylabel('Amplitude (norm.)')
    ax2_top.set_title('All channels — rise region')
    ax2_top.legend(ncol=6, fontsize=7, loc='upper left')
    ax2_top.grid(True, alpha=0.3)

    if 'PT' in tmpls:
        ax2_bot.plot(t_zoom, tmpls['PT'][lo:hi], color='black', lw=1.8, label='PT')
    if 'PS1' in tmpls:
        ax2_bot.plot(t_zoom, tmpls['PS1'][lo:hi], color='steelblue', lw=1.3, ls='--', label='PS1')
    if 'PS2' in tmpls:
        ax2_bot.plot(t_zoom, tmpls['PS2'][lo:hi], color='darkorange', lw=1.3, ls='--', label='PS2')
    ax2_bot.set_ylabel('Amplitude (norm.)')
    ax2_bot.set_xlabel('Time (ms)')
    ax2_bot.set_title('PT / PS1 / PS2 — rise region')
    ax2_bot.legend(fontsize=8)
    ax2_bot.grid(True, alpha=0.3)

    plt.tight_layout()
    out2 = os.path.join(OUTDIR, f'zip{det}_templates_zoom.png')
    plt.savefig(out2, dpi=150)
    plt.close()
    print(f"  Saved: {out2}")

    # ── Figure 3: raw traces overlay (up to 30 per channel, from cache) ───────
    if ch_traces:
        chans_avail = [c for c in S1_CHANS + S2_CHANS if c in ch_traces and len(ch_traces[c]) > 0]
        ncols = min(4, len(chans_avail))
        nrows = (len(chans_avail) + ncols - 1) // ncols if ncols > 0 else 1

        if chans_avail:
            fig3, axes3 = plt.subplots(nrows, ncols,
                                       figsize=(5 * ncols, 3.5 * nrows),
                                       sharex=True)
            axes3 = np.array(axes3).flatten()
            fig3.suptitle(f'Zip{det} — Raw Aligned Traces (≤30/channel)', fontsize=13)

            for idx, ch in enumerate(chans_avail):
                ax = axes3[idx]
                traces = ch_traces[ch]
                n_show = min(30, len(traces))
                color = COLORS_S1[S1_CHANS.index(ch)] if ch in S1_CHANS \
                        else COLORS_S2[S2_CHANS.index(ch)]
                for tr in traces[:n_show]:
                    ax.plot(t_axis, np.array(tr), color=color, alpha=0.25, lw=0.6)
                # overlay average template from ROOT
                if ch in tmpls:
                    ax.plot(t_axis, tmpls[ch], color='black', lw=1.5, label='template')
                ax.set_title(f'{ch} ({len(traces)} traces)', fontsize=9)
                ax.set_ylim(-0.15, 1.25)
                ax.grid(True, alpha=0.3)
                if idx >= (nrows - 1) * ncols:
                    ax.set_xlabel('Time (ms)', fontsize=8)

            # hide empty axes
            for idx in range(len(chans_avail), len(axes3)):
                axes3[idx].set_visible(False)

            plt.tight_layout()
            out3 = os.path.join(OUTDIR, f'zip{det}_raw_traces.png')
            plt.savefig(out3, dpi=120)
            plt.close()
            print(f"  Saved: {out3}")

# ─── Summary comparison plot: PT for all zips ────────────────────────────────
fig_all, ax_all = plt.subplots(figsize=(14, 6))
ax_all.set_title('PT Template Comparison — All Zips', fontsize=13)
colors_all = plt.cm.tab10(np.linspace(0, 1, len(ZIPS)))

for det, col in zip(ZIPS, colors_all):
    root_path = os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_1x1.root")
    if not os.path.exists(root_path):
        continue
    tmpls = load_root_templates(root_path, det)
    if 'PT' in tmpls:
        ax_all.plot(t_axis, tmpls['PT'], color=col, lw=1.4, label=f'Zip{det}')

ax_all.set_xlabel('Time (ms)')
ax_all.set_ylabel('Amplitude (norm.)')
ax_all.legend(ncol=4, fontsize=9)
ax_all.set_ylim(-0.1, 1.15)
ax_all.grid(True, alpha=0.3)
plt.tight_layout()
out_all = os.path.join(OUTDIR, 'all_zips_PT_comparison.png')
plt.savefig(out_all, dpi=150)
plt.close()
print(f"\nSaved summary: {out_all}")
print("\nDone. All plots in:", os.path.abspath(OUTDIR))
