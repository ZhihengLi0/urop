#!/usr/bin/env python3
"""
Load all zip pkls and plot raw LP-filtered traces + analytical fits overlaid.
One PNG per zip: grid of all channels, full + zoom view.
"""

import os, pickle, glob
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN_DIR   = os.environ.get("RAW_WF_RUN_DIR", os.path.abspath("raw_without_filter/run"))
CACHE_DIR = os.path.join(RUN_DIR, "cache")
PLOT_DIR  = os.path.join(RUN_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

SAMPLERATE        = 625000
TRACELENGTH       = 32768
SECTION3_RISE_IDX = 16050

t_ms = np.arange(TRACELENGTH) / SAMPLERATE * 1e3

# View windows: (label, lo_sample, hi_sample)
WINDOWS = [
    ("full", SECTION3_RISE_IDX - 600,  SECTION3_RISE_IDX + 5500),
    ("zoom", SECTION3_RISE_IDX - 80,   SECTION3_RISE_IDX + 800),
]

for det in ZIPS:
    pkl_path = os.path.join(CACHE_DIR, f"zip{det}_all_series.pkl")
    if not os.path.exists(pkl_path):
        print(f"zip{det}: pkl not found, skipping")
        continue

    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    chans     = data.get("chans", [])
    raw_dict  = data.get("raw_traces", {})
    ana_dict  = data.get("ana_traces", {})
    fit_ok    = data.get("fit_ok", {})
    ptof_lo   = data.get("ptof_lo", 0)
    ptof_hi   = data.get("ptof_hi", 0)
    rise_idx  = data.get("rise_idx", SECTION3_RISE_IDX)

    if not chans:
        print(f"zip{det}: no channels in pkl, skipping")
        continue

    n_chans = len(chans)
    ncols   = 2   # full + zoom per channel
    nrows   = n_chans

    fig, axes = plt.subplots(nrows, ncols * 2,
                             figsize=(6 * ncols * 2, 3.5 * nrows),
                             squeeze=False)
    fig.suptitle(
        f"Zip{det}  —  raw LP-filtered (blue) + 2-exp analytical fit (red dashed)\n"
        f"PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}]  |  pretrigger pinned @ {rise_idx}  |  no quality cuts",
        fontsize=9,
    )

    for row, chan in enumerate(chans):
        raw_arr = raw_dict.get(chan)
        ana_arr = ana_dict.get(chan)
        ok_arr  = fit_ok.get(chan, np.ones(len(raw_arr) if raw_arr is not None else 0, dtype=bool))

        if raw_arr is None or len(raw_arr) == 0:
            for col in range(ncols * 2):
                axes[row, col].set_visible(False)
            continue

        n_ev     = len(raw_arr)
        n_fit_ok = int(np.sum(ok_arr))

        for win_idx, (win_tag, lo, hi) in enumerate(WINDOWS):
            ax_col = win_idx * 2
            ax_raw = axes[row, ax_col]
            ax_ana = axes[row, ax_col + 1]

            # raw traces
            for i, tr in enumerate(raw_arr):
                ax_raw.plot(t_ms[lo:hi], tr[lo:hi],
                            lw=0.5, alpha=0.15, color="steelblue")
            ax_raw.axvline(t_ms[rise_idx], color="k", lw=0.8, ls=":", alpha=0.5)
            ax_raw.set_title(f"{chan}  raw  [{win_tag}]  n={n_ev}", fontsize=7)
            ax_raw.set_xlabel("Time (ms)", fontsize=7)
            ax_raw.set_ylabel("Norm. amp.", fontsize=7)
            ax_raw.grid(alpha=0.2, ls=":")
            ax_raw.tick_params(labelsize=6)

            # raw + analytical overlay (fit_ok events only)
            for i, (tr_r, tr_a, ok) in enumerate(zip(raw_arr, ana_arr, ok_arr)):
                ax_ana.plot(t_ms[lo:hi], tr_r[lo:hi],
                            lw=0.5, alpha=0.15, color="steelblue")
                if ok:
                    ax_ana.plot(t_ms[lo:hi], tr_a[lo:hi],
                                lw=0.8, alpha=0.35, color="crimson", ls="--")
            ax_ana.axvline(t_ms[rise_idx], color="k", lw=0.8, ls=":", alpha=0.5)
            ax_ana.set_title(f"{chan}  raw+fit  [{win_tag}]  fit_ok={n_fit_ok}/{n_ev}", fontsize=7)
            ax_ana.set_xlabel("Time (ms)", fontsize=7)
            ax_ana.grid(alpha=0.2, ls=":")
            ax_ana.tick_params(labelsize=6)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_png = os.path.join(PLOT_DIR, f"zip{det}_all_channels_raw_vs_ana.png")
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")

print("All zips plotted.")
