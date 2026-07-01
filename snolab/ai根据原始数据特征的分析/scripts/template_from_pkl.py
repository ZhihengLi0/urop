#!/usr/bin/env python3
"""
Template generation directly from 126G pkl cache (no rawio needed).

For each zip:
  1. Read per-series pkl files (raw_without_filter cache).
  2. Filter events per channel: fit_ok=True, nrmse <= NRMSE_MAX,
     pretrigger noise (from raw_traces) <= p75 threshold.
  3. Collect ana_traces — 2-exp analytical fits already aligned to
     SECTION3_RISE_IDX=16050 and peak-normalised to 1.
  4. Mean template (nxm0) + centered PCA (nxm1-nxm4).
  5. Write agnostic ROOT (shared PCA basis) + specific ROOT (per-channel PCA).
  6. Write diagnostic plots and JSON time constants.

Usage:
    python template_from_pkl.py --det 4
    python template_from_pkl.py --det 4 --nrmse-max 0.12 --noise-pctile 75
"""

import argparse, os, pickle, json, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

try:
    import ROOT
    from ROOT import TFile, TH1D
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    print("WARNING: ROOT not available — skipping ROOT output")

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det',          type=int,   required=True)
parser.add_argument('--nrmse-max',    type=float, default=0.15)
parser.add_argument('--noise-pctile', type=int,   default=75)
args = parser.parse_args()
det          = args.det
NRMSE_MAX    = args.nrmse_max
NOISE_PCTILE = args.noise_pctile

# ── Paths ─────────────────────────────────────────────────────────────────────
PKL_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")
RUN_DIR   = os.environ.get(
    "AI_RUN_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'run')))
PLOT_DIR  = os.path.join(RUN_DIR, 'plots')
ROOT_DIR  = os.path.join(RUN_DIR, 'root_files')
STATS_DIR = os.path.join(RUN_DIR, 'stats')
for d in [PLOT_DIR, ROOT_DIR, STATS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLERATE        = 625000
TRACELENGTH       = 32768
SECTION3_RISE_IDX = 16050     # canonical pretrigger point in pkl ana_traces
NOISE_LO          = 12000     # pretrigger noise window
NOISE_HI          = 15500
N_COMPONENTS      = 5         # nxm0 (mean) + nxm1-4 (PCA)
PCA_COMPONENTS    = N_COMPONENTS - 1
MAX_NXM           = 500       # max traces per channel for PCA
MIN_EVENTS        = 5         # minimum per channel to build template

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

print(f"=== Zip{det}  NRMSE_MAX={NRMSE_MAX}  NOISE_PCTILE={NOISE_PCTILE} ===")

# ── Load pkl series ────────────────────────────────────────────────────────────
series_dir = os.path.join(PKL_CACHE, f"zip{det}_series")
if not os.path.isdir(series_dir):
    raise FileNotFoundError(f"No pkl cache dir: {series_dir}")

pkl_files = sorted([
    os.path.join(series_dir, f)
    for f in os.listdir(series_dir) if f.endswith('.pkl')
])
print(f"Found {len(pkl_files)} series pkl files")

# Pass 1: collect noise values for per-channel threshold
noise_collect = {c: [] for c in ALL_CHANS}
nrmse_collect = {c: [] for c in ALL_CHANS}

for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    try:
        with open(pkl_path, 'rb') as fh:
            data = pickle.load(fh)
    except Exception as exc:
        print(f"  {series}: load error — {exc}")
        continue
    for c in ALL_CHANS:
        rts = data.get('raw_traces', {}).get(c, [])
        oks = data.get('fit_ok_mask', {}).get(c, [])
        fps = data.get('fit_params_ch', {}).get(c, [])
        for i, raw in enumerate(rts):
            ok = bool(oks[i]) if i < len(oks) else False
            fp = fps[i]        if i < len(fps) else None
            if not ok or fp is None:
                continue
            if float(fp['nrmse']) > NRMSE_MAX:
                continue
            raw = np.asarray(raw, dtype=np.float64)
            noise = float(np.std(raw[NOISE_LO:NOISE_HI]))
            noise_collect[c].append(noise)
            nrmse_collect[c].append(float(fp['nrmse']))

noise_thr = {}
for c in ALL_CHANS:
    if noise_collect[c]:
        noise_thr[c] = float(np.percentile(noise_collect[c], NOISE_PCTILE))
    else:
        noise_thr[c] = np.inf

print(f"\nNoise thresholds (p{NOISE_PCTILE}):")
for c in ALL_CHANS:
    n = len(noise_collect[c])
    print(f"  {c}: thr={noise_thr[c]:.4f}  candidates={n}")

# Pass 2: collect selected ana_traces
channel_traces  = {c: [] for c in ALL_CHANS}   # final selected ana_traces
channel_trises  = {c: [] for c in ALL_CHANS}
channel_tfalls  = {c: [] for c in ALL_CHANS}
channel_nrmses  = {c: [] for c in ALL_CHANS}

for pkl_path in pkl_files:
    series = os.path.basename(pkl_path).replace('.pkl', '')
    try:
        with open(pkl_path, 'rb') as fh:
            data = pickle.load(fh)
    except Exception:
        continue
    for c in ALL_CHANS:
        rts  = data.get('raw_traces',    {}).get(c, [])
        anas = data.get('ana_traces',    {}).get(c, [])
        oks  = data.get('fit_ok_mask',   {}).get(c, [])
        fps  = data.get('fit_params_ch', {}).get(c, [])
        for i, raw in enumerate(rts):
            ok  = bool(oks[i]) if i < len(oks) else False
            fp  = fps[i]        if i < len(fps) else None
            ana = anas[i]       if i < len(anas) else None
            if not ok or fp is None or ana is None:
                continue
            nrmse = float(fp['nrmse'])
            if nrmse > NRMSE_MAX:
                continue
            raw = np.asarray(raw, dtype=np.float64)
            noise = float(np.std(raw[NOISE_LO:NOISE_HI]))
            if noise > noise_thr[c]:
                continue
            ana = np.asarray(ana, dtype=np.float64)
            # enforce pretrigger = 0 (should already be, but be safe)
            ana[:SECTION3_RISE_IDX + 1] = 0.0
            # re-normalise peak to 1
            pk = float(np.max(ana))
            if pk <= 0:
                continue
            ana /= pk
            channel_traces[c].append(ana.astype(np.float32))
            channel_trises[c].append(float(fp['t_rise']))
            channel_tfalls[c].append(float(fp['t_fall']))
            channel_nrmses[c].append(nrmse)

print(f"\nSelected events after all cuts:")
for c in ALL_CHANS:
    print(f"  {c}: {len(channel_traces[c])}")

# ── Helper: build NxM templates from trace list ────────────────────────────────
def build_nxm(traces, n_comp=PCA_COMPONENTS, max_ev=MAX_NXM):
    """
    Returns (templates, var_explained) where templates[0] is mean,
    templates[1..n_comp] are physical non-negative PCA-displaced pulses.
    """
    arr = np.array(traces, dtype=np.float64)
    if len(arr) > max_ev:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr), max_ev, replace=False)
        arr = arr[idx]

    mean_tr = arr.mean(axis=0)
    # enforce pretrigger = 0 on mean
    mean_tr[:SECTION3_RISE_IDX + 1] = 0.0
    mean_pk = float(np.max(mean_tr))
    if mean_pk > 0:
        mean_tr /= mean_pk

    if len(arr) < n_comp + 1:
        return [mean_tr] + [mean_tr.copy() for _ in range(n_comp)], [0.0] * n_comp

    centered = arr - arr.mean(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca = PCA(n_components=n_comp)
        scores = pca.fit_transform(centered)

    var_exp = pca.explained_variance_ratio_.tolist()
    templates = [mean_tr]

    for i in range(n_comp):
        comp   = pca.components_[i]
        scale  = float(np.std(scores[:, i]))
        cand_p = mean_tr + scale * comp
        cand_m = mean_tr - scale * comp
        # pick the candidate whose post-rise region is more non-negative
        post_p = cand_p[SECTION3_RISE_IDX:]
        post_m = cand_m[SECTION3_RISE_IDX:]
        neg_p  = float(np.sum(np.minimum(post_p, 0.0) ** 2))
        neg_m  = float(np.sum(np.minimum(post_m, 0.0) ** 2))
        best   = cand_p if neg_p <= neg_m else cand_m
        best[:SECTION3_RISE_IDX + 1] = 0.0
        best = np.maximum(best, 0.0)
        pk = float(np.max(best))
        if pk > 0:
            best /= pk
        templates.append(best)

    return templates, var_exp

# ── Build per-channel templates (specific) ─────────────────────────────────────
specific_templates = {}   # chan -> list of 5 arrays
specific_var       = {}

for c in ALL_CHANS:
    trs = channel_traces[c]
    if len(trs) < MIN_EVENTS:
        print(f"  {c}: only {len(trs)} events — skipping template")
        specific_templates[c] = None
        continue
    tmpl, var = build_nxm(trs)
    specific_templates[c] = tmpl
    specific_var[c] = var
    print(f"  {c}: {len(trs)} events → PCA var explained: "
          f"{[f'{v:.3f}' for v in var]}")

# ── Build agnostic templates (shared PCA basis across all channels) ────────────
all_traces_concat = []
all_traces_by_chan = {}
for c in ALL_CHANS:
    trs = channel_traces[c]
    if len(trs) >= MIN_EVENTS:
        all_traces_by_chan[c] = np.array(trs, dtype=np.float64)
        all_traces_concat.extend(trs)

agnostic_templates = {}

if len(all_traces_concat) >= PCA_COMPONENTS + 1:
    arr_all = np.array(all_traces_concat, dtype=np.float64)
    if len(arr_all) > MAX_NXM * len(all_traces_by_chan):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr_all),
                         min(len(arr_all), MAX_NXM * len(all_traces_by_chan)),
                         replace=False)
        arr_all = arr_all[idx]

    centered_all = arr_all - arr_all.mean(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca_all = PCA(n_components=PCA_COMPONENTS)
        pca_all.fit(centered_all)

    for c in ALL_CHANS:
        trs = channel_traces[c]
        if len(trs) < MIN_EVENTS:
            agnostic_templates[c] = None
            continue
        arr_c = np.array(trs, dtype=np.float64)
        mean_c = arr_c.mean(axis=0)
        mean_c[:SECTION3_RISE_IDX + 1] = 0.0
        pk = float(np.max(mean_c))
        if pk > 0:
            mean_c /= pk

        centered_c = arr_c - arr_c.mean(axis=0)
        scores_c = pca_all.transform(centered_c)

        tmpl = [mean_c]
        for i in range(PCA_COMPONENTS):
            comp  = pca_all.components_[i]
            scale = float(np.std(scores_c[:, i]))
            cp    = mean_c + scale * comp
            cm    = mean_c - scale * comp
            post_p = cp[SECTION3_RISE_IDX:]
            post_m = cm[SECTION3_RISE_IDX:]
            best   = cp if np.sum(np.minimum(post_p, 0) ** 2) <= np.sum(np.minimum(post_m, 0) ** 2) else cm
            best[:SECTION3_RISE_IDX + 1] = 0.0
            best = np.maximum(best, 0.0)
            pk2  = float(np.max(best))
            if pk2 > 0:
                best /= pk2
            tmpl.append(best)
        agnostic_templates[c] = tmpl

# ── Write ROOT files ───────────────────────────────────────────────────────────
x_full = np.arange(TRACELENGTH, dtype=np.float64)

def write_root(out_path, templates_dict):
    if not HAS_ROOT:
        return
    tf = TFile(out_path, "RECREATE")
    for c, tmpl in templates_dict.items():
        if tmpl is None:
            continue
        for k, tr in enumerate(tmpl):
            name  = f"nxm{k}_zip{det}_{c}"
            title = f"Zip{det} {c} NxM{k}"
            h = TH1D(name, title, TRACELENGTH, -0.5, TRACELENGTH - 0.5)
            for j, v in enumerate(tr):
                h.SetBinContent(j + 1, float(v))
            h.Write()
    tf.Close()
    print(f"Saved ROOT: {out_path}")

write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_agnostic.root"),
           agnostic_templates)
write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_specific.root"),
           specific_templates)

# ── Write JSON time constants ─────────────────────────────────────────────────
time_consts = {}
for c in ALL_CHANS:
    trs = channel_trises[c]
    tfs = channel_tfalls[c]
    ns  = channel_nrmses[c]
    if not trs:
        time_consts[c] = None
        continue
    time_consts[c] = {
        "n_events":      len(trs),
        "t_rise_ms":     {"median": float(np.median(trs)*1e3),
                          "std":    float(np.std(trs)*1e3),
                          "p16":    float(np.percentile(trs,16)*1e3),
                          "p84":    float(np.percentile(trs,84)*1e3)},
        "t_fall_ms":     {"median": float(np.median(tfs)*1e3),
                          "std":    float(np.std(tfs)*1e3),
                          "p16":    float(np.percentile(tfs,16)*1e3),
                          "p84":    float(np.percentile(tfs,84)*1e3)},
        "nrmse":         {"median": float(np.median(ns)),
                          "p95":    float(np.percentile(ns,95))},
    }

json_path = os.path.join(STATS_DIR, f"time_constants_zip{det}.json")
with open(json_path, 'w') as fh:
    json.dump(time_consts, fh, indent=2)
print(f"Saved stats: {json_path}")

# ── Plots ─────────────────────────────────────────────────────────────────────
t_ms = x_full / SAMPLERATE * 1e3
PLOT_LO  = SECTION3_RISE_IDX - 500
PLOT_HI  = min(TRACELENGTH, SECTION3_RISE_IDX + 8000)
ZOOM_LO  = SECTION3_RISE_IDX - 50
ZOOM_HI  = SECTION3_RISE_IDX + 2000

active = [c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS]

# 1. Aligned overlay plot
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} — aligned ana_traces overlay  "
                 f"(NRMSE≤{NRMSE_MAX}, noise≤p{NOISE_PCTILE})", fontsize=10)
    for row, c in enumerate(active):
        arr = np.array(channel_traces[c], dtype=np.float64)
        # full window
        ax = axes[row, 0]
        for tr in arr[:200]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI],
                    lw=0.4, alpha=0.15, color='steelblue')
        if specific_templates[c]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], specific_templates[c][0][PLOT_LO:PLOT_HI],
                    lw=1.5, color='crimson', label='mean')
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.set_title(f"{c}  n={len(arr)}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7)
        ax.set_ylabel("Norm. amp.", fontsize=7)
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.2)
        # zoom
        ax2 = axes[row, 1]
        for tr in arr[:200]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], tr[ZOOM_LO:ZOOM_HI],
                     lw=0.5, alpha=0.2, color='steelblue')
        if specific_templates[c]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], specific_templates[c][0][ZOOM_LO:ZOOM_HI],
                     lw=1.5, color='crimson')
        ax2.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax2.set_title(f"{c} zoom", fontsize=8)
        ax2.set_xlabel("Time (ms)", fontsize=7)
        ax2.tick_params(labelsize=6)
        ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_aligned_overlay.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_aligned_overlay.png")

# 2. NxM templates plot (specific)
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(10, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} — NxM specific templates", fontsize=10)
    colors = ['black', 'crimson', 'royalblue', 'darkorange', 'forestgreen']
    for row, c in enumerate(active):
        ax = axes[row, 0]
        tmpl = specific_templates[c]
        if tmpl is None:
            continue
        labels = ['mean (nxm0)'] + [f'nxm{i}' for i in range(1, N_COMPONENTS)]
        for k, (tr, col, lbl) in enumerate(zip(tmpl, colors, labels)):
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI],
                    lw=1.2, color=col, label=lbl, alpha=0.85)
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        n = len(channel_traces[c])
        var = specific_var.get(c, [])
        var_str = '  '.join([f"PC{i+1}:{v:.2f}" for i, v in enumerate(var)])
        ax.set_title(f"{c}  n={n}   {var_str}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7)
        ax.set_ylabel("Norm. amp.", fontsize=7)
        ax.legend(fontsize=7, ncol=N_COMPONENTS)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_nxm_specific.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_nxm_specific.png")

# 3. t_rise / t_fall distributions
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 2.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} — t_rise / t_fall distributions", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3   # ms
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax1, ax2 = axes[row, 0], axes[row, 1]
        ax1.hist(trs, bins=40, color='steelblue', edgecolor='white', lw=0.3)
        ax1.set_title(f"{c} t_rise  median={np.median(trs):.3f}ms", fontsize=8)
        ax1.set_xlabel("t_rise (ms)", fontsize=7)
        ax1.tick_params(labelsize=6)
        ax1.grid(alpha=0.2)
        ax2.hist(tfs, bins=40, color='darkorange', edgecolor='white', lw=0.3)
        ax2.set_title(f"{c} t_fall  median={np.median(tfs):.3f}ms", fontsize=8)
        ax2.set_xlabel("t_fall (ms)", fontsize=7)
        ax2.tick_params(labelsize=6)
        ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_time_constants.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_time_constants.png")

print(f"\nDone. Zip{det} complete.")
