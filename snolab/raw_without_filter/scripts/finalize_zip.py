#!/usr/bin/env python3
"""
Merge all per-series checkpoint pkls for one zip into the final
zip{det}_all_series.pkl, plot, and summary txt.

Run this AFTER the rescue chain finishes (or when it stalls and you want to
force-produce the final outputs from whatever checkpoints exist).

Usage (inside singularity or any env with numpy + matplotlib):
    python3 finalize_zip.py --det 18
    python3 finalize_zip.py --det 18 --dry-run   # just print what would happen
    python3 finalize_zip.py --all                 # all 13 zips
"""

import argparse, os, pickle, datetime
import numpy as np

# ── constants (must match read_zip_all_series.py) ─────────────────────────────
SAMPLERATE        = 625000
TRACELENGTH       = 32768
SECTION3_RISE_IDX = 16050

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

ALL_ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]

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

WINDOWS = [
    ("full", SECTION3_RISE_IDX - 600,  SECTION3_RISE_IDX + 5500),
    ("zoom", SECTION3_RISE_IDX - 80,   SECTION3_RISE_IDX + 800),
]

# ── helpers ───────────────────────────────────────────────────────────────────

def finalize_one(det, run_dir, dry_run=False):
    cache_dir      = os.path.join(run_dir, "cache")
    series_dir     = os.path.join(cache_dir, f"zip{det}_series")
    out_pkl        = os.path.join(cache_dir, f"zip{det}_all_series.pkl")
    plot_dir       = os.path.join(run_dir, "plots")
    out_png        = os.path.join(plot_dir, f"zip{det}_all_channels_raw_vs_ana.png")
    out_txt        = os.path.join(plot_dir, f"zip{det}_summary.txt")

    ptof_lo, ptof_hi = PTOF_RANGES[det]
    excluded = set(SERIES_EXCLUSIONS.get(det, []))
    series_list = [s for s in ALL_SERIES if s not in excluded]

    # Discover checkpoints
    if not os.path.isdir(series_dir):
        print(f"[zip{det}] No series checkpoint dir found: {series_dir}")
        return False

    available = {f[:-4] for f in os.listdir(series_dir) if f.endswith(".pkl")}
    found     = [s for s in series_list if s in available]
    missing   = [s for s in series_list if s not in available]

    print(f"\n[zip{det}] {len(found)}/{len(series_list)} series checkpointed "
          f"({len(missing)} missing)")
    if missing:
        print(f"  Missing: {missing}")
    if not found:
        print(f"  Nothing to merge.")
        return False

    if dry_run:
        print(f"  [dry-run] would write: {out_pkl}")
        return True

    # Merge checkpoints
    raw_traces    = {c: [] for c in ALL_CHANS}
    ana_traces    = {c: [] for c in ALL_CHANS}
    fit_ok_mask   = {c: [] for c in ALL_CHANS}

    for series in found:
        ckpt_path = os.path.join(series_dir, f"{series}.pkl")
        try:
            with open(ckpt_path, "rb") as f:
                payload = pickle.load(f)
        except Exception as exc:
            print(f"  WARNING: cannot read {ckpt_path}: {exc} — skipping")
            continue
        for c in ALL_CHANS:
            raw_traces[c].extend(payload.get("raw_traces", {}).get(c, []))
            ana_traces[c].extend(payload.get("ana_traces", {}).get(c, []))
            fit_ok_mask[c].extend(payload.get("fit_ok_mask", {}).get(c, []))

    # Summary to stdout
    for c in ALL_CHANS:
        n = len(raw_traces[c])
        n_ok = sum(fit_ok_mask[c])
        if n:
            print(f"  {c}: {n} traces, {n_ok} fit OK ({n_ok/n*100:.0f}%)")

    # Save merged pkl
    ana_clean = {}
    for c in ALL_CHANS:
        ana_clean[c] = [
            tr if tr is not None else np.zeros(TRACELENGTH, dtype=np.float32)
            for tr in ana_traces[c]
        ]

    os.makedirs(cache_dir, exist_ok=True)
    tmp_pkl = out_pkl + ".tmp"
    with open(tmp_pkl, "wb") as f:
        pickle.dump({
            "det":         det,
            "ptof_lo":     ptof_lo,
            "ptof_hi":     ptof_hi,
            "series_list": found,
            "chans":       [c for c in ALL_CHANS if raw_traces[c]],
            "samplerate":  SAMPLERATE,
            "tracelength": TRACELENGTH,
            "rise_idx":    SECTION3_RISE_IDX,
            "raw_traces":  {c: np.array(raw_traces[c], dtype=np.float32)
                            for c in ALL_CHANS if raw_traces[c]},
            "ana_traces":  {c: np.array(ana_clean[c], dtype=np.float32)
                            for c in ALL_CHANS if raw_traces[c]},
            "fit_ok":      {c: np.array(fit_ok_mask[c], dtype=bool)
                            for c in ALL_CHANS if raw_traces[c]},
        }, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_pkl, out_pkl)
    print(f"  Saved pkl: {out_pkl}")

    # Plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(plot_dir, exist_ok=True)
        active_chans = [c for c in ALL_CHANS if raw_traces[c]]
        t_ms = np.arange(TRACELENGTH, dtype=np.float64) / SAMPLERATE * 1e3

        if active_chans:
            nrows = len(active_chans)
            fig, axes = plt.subplots(nrows, 4, figsize=(24, 3.5 * nrows), squeeze=False)
            fig.suptitle(
                f"Zip{det}  —  blue=raw LP-filtered  red dashed=2-exp analytical fit\n"
                f"PTOFamps [{ptof_lo:.2e}, {ptof_hi:.2e}]  |  pretrigger pinned @ {SECTION3_RISE_IDX}"
                f"  |  {len(found)}/{len(series_list)} series  |  no quality cuts",
                fontsize=9,
            )
            for row, chan in enumerate(active_chans):
                raw_arr = np.array(raw_traces[chan], dtype=np.float32)
                ok_arr  = np.array(fit_ok_mask[chan], dtype=bool)
                ana_arr = ana_clean[chan]
                n_ev = len(raw_arr)
                n_ok = int(ok_arr.sum())
                for win_idx, (win_tag, lo, hi) in enumerate(WINDOWS):
                    col_r = win_idx * 2
                    col_o = win_idx * 2 + 1
                    ax_r, ax_o = axes[row, col_r], axes[row, col_o]
                    for tr in raw_arr:
                        ax_r.plot(t_ms[lo:hi], tr[lo:hi], lw=0.5, alpha=0.15, color="steelblue")
                    ax_r.axvline(t_ms[SECTION3_RISE_IDX], color="k", lw=0.8, ls=":", alpha=0.5)
                    ax_r.set_title(f"{chan} raw [{win_tag}]  n={n_ev}", fontsize=7)
                    ax_r.set_xlabel("Time (ms)", fontsize=7); ax_r.set_ylabel("Norm. amp.", fontsize=7)
                    ax_r.grid(alpha=0.2, ls=":"); ax_r.tick_params(labelsize=6)
                    for tr_r, tr_a, ok in zip(raw_arr, ana_arr, ok_arr):
                        ax_o.plot(t_ms[lo:hi], tr_r[lo:hi], lw=0.5, alpha=0.15, color="steelblue")
                        if ok:
                            ax_o.plot(t_ms[lo:hi], tr_a[lo:hi], lw=0.8, alpha=0.35,
                                      color="crimson", ls="--")
                    ax_o.axvline(t_ms[SECTION3_RISE_IDX], color="k", lw=0.8, ls=":", alpha=0.5)
                    ax_o.set_title(f"{chan} raw+fit [{win_tag}]  fit_ok={n_ok}/{n_ev}", fontsize=7)
                    ax_o.set_xlabel("Time (ms)", fontsize=7)
                    ax_o.grid(alpha=0.2, ls=":"); ax_o.tick_params(labelsize=6)
            fig.tight_layout(rect=[0, 0, 1, 0.97])
            fig.savefig(out_png, dpi=130, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved plot: {out_png}")
    except Exception as exc:
        print(f"  WARNING: plot failed: {exc}")

    # Text summary
    try:
        os.makedirs(plot_dir, exist_ok=True)
        lines = [
            "=" * 70,
            f"SUMMARY: Zip{det}   (generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})",
            "=" * 70,
            f"PTOFamps range : [{ptof_lo:.3e}, {ptof_hi:.3e}]",
            f"Series used    : {len(found)}/{len(series_list)}  "
            f"(excluded: {sorted(excluded) if excluded else 'none'})",
            f"Missing series : {missing if missing else 'none'}",
            "",
        ]
        for c in ALL_CHANS:
            n = len(raw_traces[c])
            n_ok = sum(fit_ok_mask[c])
            if n:
                lines.append(f"  {c}: {n} traces  fit_ok={n_ok} ({n_ok/n*100:.0f}%)")
        lines.append("")
        with open(out_txt, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  Saved summary: {out_txt}")
    except Exception as exc:
        print(f"  WARNING: summary write failed: {exc}")

    return True


# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--det", type=int, help="Detector zip number")
parser.add_argument("--all", action="store_true", help="Run for all 13 zips")
parser.add_argument("--dry-run", action="store_true",
                    help="Print what would happen without writing files")
parser.add_argument("--run-dir", default=None,
                    help="Override RUN_DIR (default: ~/urop/snolab/raw_without_filter/run)")
args = parser.parse_args()

run_dir = args.run_dir or os.path.join(
    os.path.expanduser("~"), "urop", "snolab", "raw_without_filter", "run")

if args.all:
    for d in ALL_ZIPS:
        finalize_one(d, run_dir, dry_run=args.dry_run)
elif args.det:
    finalize_one(args.det, run_dir, dry_run=args.dry_run)
else:
    parser.error("Specify --det DET or --all")
