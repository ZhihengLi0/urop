#!/usr/bin/env python3
"""
Template generation v2 — directly from 126G pkl cache.
See CONTEXT_FOR_NEXT_AI.md for full context and teacher feedback.

Changes from v1 (ai根据原始数据特征的分析):
  - Removed noise p75 filter (circular definition, no physical basis)
  - Removed NRMSE cut (only fit_ok=True required)
  - NxM algorithm changed to match teacher's notebook (NxM_cedar.ipynb):
      templates = PCA components themselves, not mean ± scale × component
      components can be negative (they are basis vectors, not physical pulses)

Filter logic:
  PTOFamps window (done in pkl generation)
  → 100kHz LP filter (done in pkl generation)
  → fit_ok = True
  → collect ana_traces → PCA → templates = components

Usage:
    python template_from_pkl_v2.py --det 7
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
parser.add_argument('--det', type=int, required=True)
args = parser.parse_args()
det = args.det

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
SECTION3_RISE_IDX = 16050
N_COMPONENTS      = 5        # nxm0 (mean) + nxm1-4 (PC1-4)
PCA_COMPONENTS    = N_COMPONENTS - 1
MAX_NXM           = 500      # max traces for PCA
MIN_EVENTS        = 5

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

print(f"=== Zip{det} v2  (fit_ok only, no NRMSE cut, no noise cut) ===")

# ── Load pkl series ────────────────────────────────────────────────────────────
series_dir = os.path.join(PKL_CACHE, f"zip{det}_series")
if not os.path.isdir(series_dir):
    raise FileNotFoundError(f"No pkl cache dir: {series_dir}")

pkl_files = sorted([
    os.path.join(series_dir, f)
    for f in os.listdir(series_dir) if f.endswith('.pkl')
])
print(f"Found {len(pkl_files)} series pkl files")

# ── Single pass: collect ana_traces for fit_ok=True events ────────────────────
channel_traces = {c: [] for c in ALL_CHANS}
channel_trises = {c: [] for c in ALL_CHANS}
channel_tfalls = {c: [] for c in ALL_CHANS}
channel_nrmses = {c: [] for c in ALL_CHANS}

n_total      = {c: 0 for c in ALL_CHANS}
n_fitok      = {c: 0 for c in ALL_CHANS}
n_ana_none   = {c: 0 for c in ALL_CHANS}

for pkl_path in pkl_files:
    try:
        with open(pkl_path, 'rb') as fh:
            data = pickle.load(fh)
    except Exception as exc:
        print(f"  load error: {exc}")
        continue

    for c in ALL_CHANS:
        rts  = data.get('raw_traces',    {}).get(c, [])
        anas = data.get('ana_traces',    {}).get(c, [])
        oks  = data.get('fit_ok_mask',   {}).get(c, [])
        fps  = data.get('fit_params_ch', {}).get(c, [])

        for i in range(len(rts)):
            n_total[c] += 1
            ok  = bool(oks[i]) if i < len(oks) else False
            fp  = fps[i]       if i < len(fps) else None
            ana = anas[i]      if i < len(anas) else None

            if not ok:
                continue
            n_fitok[c] += 1

            if ana is None:
                n_ana_none[c] += 1
                continue

            ana = np.asarray(ana, dtype=np.float64)
            # enforce pretrigger = 0
            ana[:SECTION3_RISE_IDX + 1] = 0.0
            pk = float(np.max(ana))
            if pk <= 0:
                continue
            ana /= pk

            channel_traces[c].append(ana.astype(np.float32))
            if fp:
                channel_trises[c].append(float(fp['t_rise']))
                channel_tfalls[c].append(float(fp['t_fall']))
                channel_nrmses[c].append(float(fp['nrmse']))

print(f"\nEvent counts per channel:")
print(f"{'Chan':6} {'total':>7} {'fit_ok':>7} {'selected':>9} {'drop%':>7}")
for c in ALL_CHANS:
    tot = n_total[c]
    ok  = n_fitok[c]
    sel = len(channel_traces[c])
    drop = 100 * (1 - sel / tot) if tot > 0 else 0
    print(f"  {c:6} {tot:>7} {ok:>7} {sel:>9} {drop:>6.1f}%")

# ── Helper: build NxM templates (teacher's version) ───────────────────────────
def build_nxm(traces, n_comp=PCA_COMPONENTS, max_ev=MAX_NXM):
    """
    Teacher's NxM (NxM_cedar.ipynb):
      - templates[0] = mean trace (nxm0)
      - templates[1..n_comp] = PCA components themselves (not mean ± component)
      Components can be negative — they are basis vectors, not physical pulses.
      The optimal filter fits each event as: sum_i amp_i * template_i
    """
    arr = np.array(traces, dtype=np.float64)
    if len(arr) > max_ev:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr), max_ev, replace=False)
        arr = arr[idx]

    mean_tr = arr.mean(axis=0)
    mean_tr[:SECTION3_RISE_IDX + 1] = 0.0
    pk = float(np.max(mean_tr))
    if pk > 0:
        mean_tr /= pk

    if len(arr) < n_comp + 1:
        return [mean_tr] + [np.zeros_like(mean_tr) for _ in range(n_comp)], [0.0] * n_comp

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca = PCA(n_components=n_comp, svd_solver='full')
        pca.fit(arr)

    var_exp = pca.explained_variance_ratio_.tolist()

    # Templates = mean + PCA components directly (teacher's approach)
    templates = [mean_tr]
    for i in range(n_comp):
        comp = pca.components_[i].copy()
        templates.append(comp)

    return templates, var_exp


# ── Build per-channel templates (specific) ─────────────────────────────────────
specific_templates = {}
specific_var       = {}

print(f"\nBuilding specific templates:")
for c in ALL_CHANS:
    trs = channel_traces[c]
    if len(trs) < MIN_EVENTS:
        print(f"  {c}: only {len(trs)} events — skipping")
        specific_templates[c] = None
        continue
    tmpl, var = build_nxm(trs)
    specific_templates[c] = tmpl
    specific_var[c] = var
    print(f"  {c}: {len(trs)} events → PCA var: {[f'{v:.3f}' for v in var]}")

# ── Build agnostic templates (shared PCA basis) ───────────────────────────────
all_traces_concat = []
for c in ALL_CHANS:
    if len(channel_traces[c]) >= MIN_EVENTS:
        all_traces_concat.extend(channel_traces[c])

agnostic_templates = {}

if len(all_traces_concat) >= PCA_COMPONENTS + 1:
    arr_all = np.array(all_traces_concat, dtype=np.float64)
    if len(arr_all) > MAX_NXM * len([c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS]):
        rng = np.random.default_rng(42)
        n_cap = MAX_NXM * len([c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS])
        idx = rng.choice(len(arr_all), min(len(arr_all), n_cap), replace=False)
        arr_all = arr_all[idx]

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pca_all = PCA(n_components=PCA_COMPONENTS, svd_solver='full')
        pca_all.fit(arr_all)

    for c in ALL_CHANS:
        trs = channel_traces[c]
        if len(trs) < MIN_EVENTS:
            agnostic_templates[c] = None
            continue
        arr_c   = np.array(trs, dtype=np.float64)
        mean_c  = arr_c.mean(axis=0)
        mean_c[:SECTION3_RISE_IDX + 1] = 0.0
        pk = float(np.max(mean_c))
        if pk > 0:
            mean_c /= pk

        tmpl = [mean_c]
        for i in range(PCA_COMPONENTS):
            tmpl.append(pca_all.components_[i].copy())
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
        "n_events":  len(trs),
        "t_rise_ms": {"median": float(np.median(trs)*1e3),
                      "std":    float(np.std(trs)*1e3),
                      "p16":    float(np.percentile(trs,16)*1e3),
                      "p84":    float(np.percentile(trs,84)*1e3)},
        "t_fall_ms": {"median": float(np.median(tfs)*1e3),
                      "std":    float(np.std(tfs)*1e3),
                      "p16":    float(np.percentile(tfs,16)*1e3),
                      "p84":    float(np.percentile(tfs,84)*1e3)},
        "nrmse":     {"median": float(np.median(ns)),
                      "p95":    float(np.percentile(ns,95))},
    }

json_path = os.path.join(STATS_DIR, f"time_constants_zip{det}.json")
with open(json_path, 'w') as fh:
    json.dump(time_consts, fh, indent=2)
print(f"Saved stats: {json_path}")

# ── Plots ─────────────────────────────────────────────────────────────────────
t_ms    = x_full / SAMPLERATE * 1e3
PLOT_LO = SECTION3_RISE_IDX - 500
PLOT_HI = min(TRACELENGTH, SECTION3_RISE_IDX + 8000)
ZOOM_LO = SECTION3_RISE_IDX - 50
ZOOM_HI = SECTION3_RISE_IDX + 2000

active = [c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS]

# 1. Aligned overlay
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v2 — aligned ana_traces (fit_ok only)", fontsize=10)
    for row, c in enumerate(active):
        arr = np.array(channel_traces[c], dtype=np.float64)
        ax  = axes[row, 0]
        for tr in arr[:200]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI],
                    lw=0.4, alpha=0.15, color='steelblue')
        if specific_templates[c]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], specific_templates[c][0][PLOT_LO:PLOT_HI],
                    lw=1.5, color='crimson', label='mean')
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.set_title(f"{c}  n={len(arr)}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7); ax.set_ylabel("Norm. amp.", fontsize=7)
        ax.legend(fontsize=7); ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
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
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_aligned_overlay.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_aligned_overlay.png")

# 2. NxM templates plot (specific)
# Teacher's components look like heartbeat/EKG (can be negative)
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(10, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v2 — NxM specific (PCA components, teacher's method)", fontsize=10)
    colors = ['black', 'crimson', 'royalblue', 'darkorange', 'forestgreen']
    labels = ['mean (nxm0)', 'PC1 (nxm1)', 'PC2 (nxm2)', 'PC3 (nxm3)', 'PC4 (nxm4)']
    for row, c in enumerate(active):
        ax   = axes[row, 0]
        tmpl = specific_templates[c]
        if tmpl is None:
            continue
        for k, (tr, col, lbl) in enumerate(zip(tmpl, colors, labels)):
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI],
                    lw=1.2, color=col, label=lbl, alpha=0.85)
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.axhline(0, color='gray', lw=0.5, ls='--')
        n   = len(channel_traces[c])
        var = specific_var.get(c, [])
        var_str = '  '.join([f"PC{i+1}:{v:.2f}" for i, v in enumerate(var)])
        ax.set_title(f"{c}  n={n}   {var_str}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7); ax.set_ylabel("Amp.", fontsize=7)
        ax.legend(fontsize=7, ncol=N_COMPONENTS)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_nxm_specific.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_nxm_specific.png")

# 3. t_rise / t_fall distributions
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 2.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v2 — t_rise / t_fall distributions", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax1, ax2 = axes[row, 0], axes[row, 1]
        ax1.hist(trs, bins=40, color='steelblue', edgecolor='white', lw=0.3)
        ax1.set_title(f"{c} t_rise  median={np.median(trs):.3f}ms", fontsize=8)
        ax1.set_xlabel("t_rise (ms)", fontsize=7)
        ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
        ax2.hist(tfs, bins=40, color='darkorange', edgecolor='white', lw=0.3)
        ax2.set_title(f"{c} t_fall  median={np.median(tfs):.3f}ms", fontsize=8)
        ax2.set_xlabel("t_fall (ms)", fontsize=7)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_time_constants.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_time_constants.png")

# 4. t_rise vs t_fall 2D scatter (new: diagnose bimodal structure)
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(8, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v2 — t_rise vs t_fall scatter", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax  = axes[row, 0]
        ax.scatter(trs, tfs, s=2, alpha=0.3, color='steelblue')
        ax.set_xlabel("t_rise (ms)", fontsize=7); ax.set_ylabel("t_fall (ms)", fontsize=7)
        ax.set_title(f"{c}  n={len(trs)}", fontsize=8)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_trise_vs_tfall.png"),
                dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_trise_vs_tfall.png")

print(f"\nDone. Zip{det} v2 complete.")
