#!/usr/bin/env python3
"""
Template generation v3 (TEST SCRIPT) — reuses the existing 126GB pkl cache's
`raw_traces` field (clean, fit-independent: just baseline-subtract + 100kHz
LP filter + peak-normalize, NOT touched by the old broken fit), and redoes
ONLY the fit step with a free pretrigger, then aligns + builds PCA templates.

Why this is different from ai_v2/scripts/raw_to_template_v3.py:
  raw_to_template_v3.py re-reads raw MIDAS from scratch (rawio + uproot),
  which is the slow path and was written before this finding. Investigation
  (2026-06-30, see CONTEXT_FOR_NEXT_AI.md section 6.5) showed the cached
  `raw_traces` array is independent of the old fit's pretrigger bug — it is
  NOT a fit result, just signal-processed raw waveform at native trigger
  time. So we can skip rawio/uproot entirely and just re-fit traces that are
  already sitting in the 126GB cache. This script is the one meant to
  actually be run; raw_to_template_v3.py is kept as a from-scratch fallback
  in case the cache itself ever needs regenerating.

Fit/align split (teacher's correction, relayed by user 2026-06-30):
  "现在就是我们做的时候需要先fit,fit在哪就在哪,只有在align的时候才改成一个
   定数,钉死rise的点。"
  1. FIT: pretrigger free (curve_fit parameter), bounded to
     [SECTION3_RISE_IDX ± PRETRIGGER_FREEDOM] so the optimizer stays stable.
  2. ALIGN: re-evaluate the same closed-form 2-exp curve with the FITTED
     (amp, t_rise, t_fall) but pretrigger overridden to SECTION3_RISE_IDX.
     Exact substitution, no interpolation needed (analytic function).

IMPORTANT: because the fit model changed, zip7's results also change —
zip7 is NOT skipped here (v1/v2 skipped it because teacher had approved the
OLD fixed-pretrigger zip7 result; that approval doesn't carry over to a
different fit model).

Usage:
    python template_from_pkl_v3.py --det 7
    python template_from_pkl_v3.py --det 7 --nrmse-max 0.15
    python template_from_pkl_v3.py --det 7 --series 24260617_063934   # quick test, 1 series only
"""

import argparse, os, glob, pickle, json, warnings, datetime
import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

try:
    import ROOT
    from ROOT import TFile, TH1D
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    print("WARNING: ROOT not available — skipping ROOT output")

# ── paths ────────────────────────────────────────────────────────────────────
PKL_CACHE = ("/projects/standard/yanliusp/shared/zhiheng/snolab"
             "/raw_without_filter/run/cache")          # READ-ONLY source: raw_traces only
RUN_DIR   = os.environ.get(
    "AI_V3_RUN_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'run')))
CACHE_DIR = os.path.join(RUN_DIR, 'cache_v3')           # owned by this script: fit results only (small)
PLOT_DIR  = os.path.join(RUN_DIR, 'plots')
ROOT_DIR  = os.path.join(RUN_DIR, 'root_files')
STATS_DIR = os.path.join(RUN_DIR, 'stats')
for d in [CACHE_DIR, PLOT_DIR, ROOT_DIR, STATS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── constants ────────────────────────────────────────────────────────────────
SAMPLERATE          = 625000
TRACELENGTH         = 32768
SECTION3_RISE_IDX   = 16050             # ALIGNMENT reference only — not a fit constraint
PRETRIGGER_FREEDOM  = 3000              # samples of freedom for the fit around the reference
FIT_LO              = max(0, SECTION3_RISE_IDX - PRETRIGGER_FREEDOM - 500)
FIT_HI              = min(TRACELENGTH, SECTION3_RISE_IDX + PRETRIGGER_FREEDOM + 5000)
FIT_STRIDE          = 4

N_COMPONENTS        = 5                 # nxm0 (mean) + nxm1-4 (PC1-4)
PCA_COMPONENTS      = N_COMPONENTS - 1
MAX_NXM             = 500
MIN_EVENTS          = 5
MIN_CLUSTER_EVENTS  = 20
N_EXAMPLES          = 20

ALL_CHANS = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
             'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']

X_FULL = np.arange(TRACELENGTH, dtype=np.float64)
X_FIT  = X_FULL[FIT_LO:FIT_HI:FIT_STRIDE]

# ── fit model: FREE pretrigger ──────────────────────────────────────────────
def two_exp_free_pt(x, amp, t_rise, t_fall, baseline, pretrigger):
    dt = (x - pretrigger) / SAMPLERATE
    pulse = -(amp * np.exp(-dt / t_rise) - amp * np.exp(-dt / t_fall))
    return np.where(x <= pretrigger, baseline, pulse + baseline)


def refit_one(raw_trace):
    """
    raw_trace: already baseline~0, 100kHz LP-filtered, peak-normalized to 1
    (this is exactly what's stored in the 126GB cache's raw_traces field).
    Only the curve_fit itself needs redoing — no signal processing here.
    Returns fit_ok, reason, fit_params dict (amp, t_rise, t_fall, nrmse, pretrigger).
    """
    y = np.asarray(raw_trace, dtype=np.float64)
    y_fit = y[FIT_LO:FIT_HI:FIT_STRIDE]
    try:
        popt, _ = curve_fit(
            two_exp_free_pt, X_FIT, y_fit,
            p0=[1.0, 6e-5, 2.8e-4, 0.0, float(SECTION3_RISE_IDX)],
            bounds=([0.0,     1e-6,  1e-5, -0.5, SECTION3_RISE_IDX - PRETRIGGER_FREEDOM],
                    [np.inf,  8e-4,  8e-3,  0.5, SECTION3_RISE_IDX + PRETRIGGER_FREEDOM]),
            maxfev=50000,
        )
        amp, t_rise, t_fall, bl, pt = [float(v) for v in popt]
        if not (amp > 0 and 0 < t_rise < t_fall):
            raise ValueError("unphysical")
        residuals = y_fit - two_exp_free_pt(X_FIT, amp, t_rise, t_fall, bl, pt)
        nrmse = float(np.sqrt(np.mean(residuals**2)))
        return True, None, {"amp": amp, "t_rise": t_rise, "t_fall": t_fall,
                             "nrmse": nrmse, "pretrigger": pt}
    except Exception as exc:
        return False, str(exc), None


# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
parser.add_argument('--nrmse-max', type=float, default=0.15)
parser.add_argument('--series', nargs='*', default=None,
                     help='Optional explicit series subset (for quick tests)')
args = parser.parse_args()
det       = args.det
NRMSE_MAX = args.nrmse_max

print(f"=== Zip{det} v3 (refit from cached raw_traces, free pretrigger) ===")

src_dir = os.path.join(PKL_CACHE, f"zip{det}_series")
if not os.path.isdir(src_dir):
    raise FileNotFoundError(f"No cached raw_traces dir: {src_dir}")

series_files = sorted(glob.glob(os.path.join(src_dir, "*.pkl")))
if args.series:
    wanted = set(args.series)
    series_files = [f for f in series_files if os.path.splitext(os.path.basename(f))[0] in wanted]
print(f"Found {len(series_files)} series pkl files")

ckpt_dir = os.path.join(CACHE_DIR, f"zip{det}_series")
os.makedirs(ckpt_dir, exist_ok=True)

# ── refit (with per-series checkpoint of fit RESULTS ONLY — small, fast to redo) ──
channel_traces = {c: [] for c in ALL_CHANS}   # ana_aligned, selected (fit_ok & nrmse<=cut)
channel_raws   = {c: [] for c in ALL_CHANS}   # raw_traces (native trigger time), selected
channel_trises = {c: [] for c in ALL_CHANS}
channel_tfalls = {c: [] for c in ALL_CHANS}
channel_nrmses = {c: [] for c in ALL_CHANS}
channel_pretrg = {c: [] for c in ALL_CHANS}

n_total_c = {c: 0 for c in ALL_CHANS}
n_fitok_c = {c: 0 for c in ALL_CHANS}
n_nrmse_c = {c: 0 for c in ALL_CHANS}

for series_pkl in series_files:
    series = os.path.splitext(os.path.basename(series_pkl))[0]
    with open(series_pkl, 'rb') as f:
        data = pickle.load(f)

    ckpt_path = os.path.join(ckpt_dir, f"{series}_fit.pkl")
    if os.path.exists(ckpt_path):
        with open(ckpt_path, 'rb') as f:
            fit_payload = pickle.load(f)
        print(f"  {series}: loaded fit checkpoint")
    else:
        fit_payload = {'fit_ok_mask': {}, 'fit_params_ch': {}}
        for c in ALL_CHANS:
            raws = data.get('raw_traces', {}).get(c, [])
            ok_list, params_list = [], []
            for raw in raws:
                ok, reason, fp = refit_one(raw)
                ok_list.append(ok)
                params_list.append(fp)
            fit_payload['fit_ok_mask'][c] = ok_list
            fit_payload['fit_params_ch'][c] = params_list
        tmp = ckpt_path + '.tmp'
        with open(tmp, 'wb') as f:
            pickle.dump(fit_payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, ckpt_path)
        print(f"  {series}: refit done, checkpoint saved")

    for c in ALL_CHANS:
        raws = data.get('raw_traces', {}).get(c, [])
        oks  = fit_payload['fit_ok_mask'].get(c, [])
        fps  = fit_payload['fit_params_ch'].get(c, [])
        for i in range(len(raws)):
            n_total_c[c] += 1
            ok = oks[i] if i < len(oks) else False
            fp = fps[i] if i < len(fps) else None
            if not ok or fp is None:
                continue
            n_fitok_c[c] += 1
            if fp['nrmse'] > NRMSE_MAX:
                continue
            n_nrmse_c[c] += 1

            # ── ALIGN step: pin pretrigger to reference, keep fitted shape params ──
            y_ana = two_exp_free_pt(X_FULL, fp['amp'], fp['t_rise'], fp['t_fall'],
                                     0.0, float(SECTION3_RISE_IDX))
            ana_peak = float(np.max(y_ana))
            if ana_peak <= 0:
                continue
            ana_aligned = (y_ana / ana_peak).astype(np.float32)

            channel_traces[c].append(ana_aligned)
            channel_raws[c].append(np.asarray(raws[i], dtype=np.float32))
            channel_trises[c].append(fp['t_rise'])
            channel_tfalls[c].append(fp['t_fall'])
            channel_nrmses[c].append(fp['nrmse'])
            channel_pretrg[c].append(fp['pretrigger'])

print(f"\nEvent counts per channel:")
print(f"{'Chan':6} {'total':>7} {'fit_ok':>7} {'nrmse_ok':>9}")
for c in ALL_CHANS:
    print(f"  {c:6} {n_total_c[c]:>7} {n_fitok_c[c]:>7} {n_nrmse_c[c]:>9}")

# ── PCA template builder (identical algorithm to v2's build_nxm) ───────────────
def build_nxm(traces, n_comp=PCA_COMPONENTS, max_ev=MAX_NXM):
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
    templates = [mean_tr] + [pca.components_[i].copy() for i in range(n_comp)]
    return templates, var_exp

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
    print(f"  {c}: {len(trs)} events -> PCA var: {[f'{v:.3f}' for v in var]}")

all_traces_concat = []
for c in ALL_CHANS:
    if len(channel_traces[c]) >= MIN_EVENTS:
        all_traces_concat.extend(channel_traces[c])

agnostic_templates = {}
if len(all_traces_concat) >= PCA_COMPONENTS + 1:
    arr_all = np.array(all_traces_concat, dtype=np.float64)
    n_active = len([c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS])
    if len(arr_all) > MAX_NXM * n_active:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(arr_all), min(len(arr_all), MAX_NXM * n_active), replace=False)
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
        arr_c  = np.array(trs, dtype=np.float64)
        mean_c = arr_c.mean(axis=0)
        mean_c[:SECTION3_RISE_IDX + 1] = 0.0
        pk = float(np.max(mean_c))
        if pk > 0:
            mean_c /= pk
        agnostic_templates[c] = [mean_c] + [pca_all.components_[i].copy() for i in range(PCA_COMPONENTS)]

# ── ROOT output ──────────────────────────────────────────────────────────────
def write_root(out_path, templates_dict):
    if not HAS_ROOT:
        return
    tf = TFile(out_path, "RECREATE")
    for c, tmpl in templates_dict.items():
        if tmpl is None:
            continue
        for k, tr in enumerate(tmpl):
            name  = f"nxm{k}_zip{det}_{c}"
            title = f"Zip{det} {c} NxM{k} (v3, free-pretrigger refit + align)"
            h = TH1D(name, title, TRACELENGTH, -0.5, TRACELENGTH - 0.5)
            for j, v in enumerate(tr):
                h.SetBinContent(j + 1, float(v))
            h.Write()
    tf.Close()
    print(f"Saved ROOT: {out_path}")

write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_v3_agnostic.root"), agnostic_templates)
write_root(os.path.join(ROOT_DIR, f"Templates_SNOLAB_R4_zip{det}_v3_specific.root"), specific_templates)

# ── JSON stats (includes pretrigger — the new free fit parameter) ─────────────
time_consts = {}
for c in ALL_CHANS:
    trs = channel_trises[c]
    tfs = channel_tfalls[c]
    ns  = channel_nrmses[c]
    pts = channel_pretrg[c]
    if not trs:
        time_consts[c] = None
        continue
    time_consts[c] = {
        "n_events":  len(trs),
        "t_rise_ms": {"median": float(np.median(trs)*1e3), "std": float(np.std(trs)*1e3),
                      "p16": float(np.percentile(trs,16)*1e3), "p84": float(np.percentile(trs,84)*1e3)},
        "t_fall_ms": {"median": float(np.median(tfs)*1e3), "std": float(np.std(tfs)*1e3),
                      "p16": float(np.percentile(tfs,16)*1e3), "p84": float(np.percentile(tfs,84)*1e3)},
        "nrmse":     {"median": float(np.median(ns)), "p95": float(np.percentile(ns,95))},
        "pretrigger": {"median": float(np.median(pts)), "std": float(np.std(pts)),
                       "p16": float(np.percentile(pts,16)), "p84": float(np.percentile(pts,84)),
                       "reference": SECTION3_RISE_IDX},
    }

json_path = os.path.join(STATS_DIR, f"time_constants_zip{det}_v3.json")
with open(json_path, 'w') as fh:
    json.dump(time_consts, fh, indent=2)
print(f"Saved stats: {json_path}")

# ── plots ────────────────────────────────────────────────────────────────────
t_ms    = X_FULL / SAMPLERATE * 1e3
PLOT_LO = SECTION3_RISE_IDX - 500
PLOT_HI = min(TRACELENGTH, SECTION3_RISE_IDX + 8000)
ZOOM_LO = SECTION3_RISE_IDX - 50
ZOOM_HI = SECTION3_RISE_IDX + 2000

active = [c for c in ALL_CHANS if len(channel_traces[c]) >= MIN_EVENTS]

# 1. Aligned overlay
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — aligned ana_traces (free-pretrigger refit, fit_ok + NRMSE<={NRMSE_MAX})", fontsize=10)
    for row, c in enumerate(active):
        arr = np.array(channel_traces[c], dtype=np.float64)
        ax  = axes[row, 0]
        for tr in arr[:200]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI], lw=0.4, alpha=0.15, color='steelblue')
        if specific_templates[c]:
            ax.plot(t_ms[PLOT_LO:PLOT_HI], specific_templates[c][0][PLOT_LO:PLOT_HI], lw=1.5, color='crimson', label='mean')
        ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax.set_title(f"{c}  n={len(arr)}", fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7); ax.set_ylabel("Norm. amp.", fontsize=7)
        ax.legend(fontsize=7); ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
        ax2 = axes[row, 1]
        for tr in arr[:200]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], tr[ZOOM_LO:ZOOM_HI], lw=0.5, alpha=0.2, color='steelblue')
        if specific_templates[c]:
            ax2.plot(t_ms[ZOOM_LO:ZOOM_HI], specific_templates[c][0][ZOOM_LO:ZOOM_HI], lw=1.5, color='crimson')
        ax2.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
        ax2.set_title(f"{c} zoom", fontsize=8)
        ax2.set_xlabel("Time (ms)", fontsize=7)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_aligned_overlay.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_aligned_overlay.png")

# 2. NxM templates (specific)
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(10, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — NxM specific (PCA components, free-pretrigger refit + align)", fontsize=10)
    colors = ['black', 'crimson', 'royalblue', 'darkorange', 'forestgreen']
    labels = ['mean (nxm0)', 'PC1 (nxm1)', 'PC2 (nxm2)', 'PC3 (nxm3)', 'PC4 (nxm4)']
    for row, c in enumerate(active):
        ax   = axes[row, 0]
        tmpl = specific_templates[c]
        if tmpl is None:
            continue
        for k, (tr, col, lbl) in enumerate(zip(tmpl, colors, labels)):
            ax.plot(t_ms[PLOT_LO:PLOT_HI], tr[PLOT_LO:PLOT_HI], lw=1.2, color=col, label=lbl, alpha=0.85)
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
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_nxm_specific.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_nxm_specific.png")

# 3. t_rise / t_fall distributions
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 2.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — t_rise / t_fall distributions (free-pretrigger refit)", fontsize=10)
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
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_time_constants.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_time_constants.png")

# 4. t_rise vs t_fall scatter
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(8, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — t_rise vs t_fall scatter", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax  = axes[row, 0]
        ax.scatter(trs, tfs, s=2, alpha=0.3, color='steelblue')
        ax.set_xlabel("t_rise (ms)", fontsize=7); ax.set_ylabel("t_fall (ms)", fontsize=7)
        ax.set_title(f"{c}  n={len(trs)}", fontsize=8)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_trise_vs_tfall.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_trise_vs_tfall.png")

# 5. pretrigger diagnostics — directly tests teacher's PDF claim ("significant
#    correlation for risetime and pretrigger"), impossible to check in v1/v2
#    because pretrigger was pinned constant in the fit.
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 3.0 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — fitted pretrigger diagnostics (new: pretrigger was NOT free in v1/v2)", fontsize=10)
    for row, c in enumerate(active):
        pts = np.array(channel_pretrg[c])
        trs = np.array(channel_trises[c]) * 1e3
        ax1, ax2 = axes[row, 0], axes[row, 1]
        ax1.hist(pts, bins=40, color='slategray', edgecolor='white', lw=0.3)
        ax1.axvline(SECTION3_RISE_IDX, color='crimson', lw=1, ls='--', label='align reference')
        ax1.set_title(f"{c} fitted pretrigger  median={np.median(pts):.1f}  std={np.std(pts):.1f}", fontsize=8)
        ax1.set_xlabel("pretrigger (sample)", fontsize=7)
        ax1.legend(fontsize=6); ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
        ax2.scatter(pts, trs, s=2, alpha=0.3, color='darkorange')
        corr = float(np.corrcoef(pts, trs)[0, 1]) if len(pts) > 2 else float('nan')
        ax2.set_xlabel("pretrigger (sample)", fontsize=7); ax2.set_ylabel("t_rise (ms)", fontsize=7)
        ax2.set_title(f"{c}  pretrigger vs t_rise  corr={corr:.2f}", fontsize=8)
        ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_pretrigger_diagnostics.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_pretrigger_diagnostics.png")

# 6. Rise/fall cluster correspondence
rise_fall_concordance = {}
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 1, figsize=(8, 3.8 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — rise/fall cluster correspondence (KMeans k=2)", fontsize=10)
    for row, c in enumerate(active):
        trs = np.array(channel_trises[c]) * 1e3
        tfs = np.array(channel_tfalls[c]) * 1e3
        ax  = axes[row, 0]
        n   = len(trs)
        if n < MIN_CLUSTER_EVENTS:
            ax.text(0.5, 0.5, f"{c}: only {n} events, skip clustering", transform=ax.transAxes, ha='center', fontsize=8)
            ax.set_title(c, fontsize=8)
            continue
        km_r = KMeans(n_clusters=2, n_init=10, random_state=0).fit(trs.reshape(-1, 1))
        km_f = KMeans(n_clusters=2, n_init=10, random_state=0).fit(tfs.reshape(-1, 1))
        r_order = np.argsort(km_r.cluster_centers_.ravel())
        f_order = np.argsort(km_f.cluster_centers_.ravel())
        rise_slow = (km_r.labels_ == r_order[1])
        fall_slow = (km_f.labels_ == f_order[1])
        both_fast = (~rise_slow) & (~fall_slow)
        both_slow = ( rise_slow) & ( fall_slow)
        rise_only = ( rise_slow) & (~fall_slow)
        fall_only = (~rise_slow) & ( fall_slow)
        concord = (both_fast.sum() + both_slow.sum()) / n
        rise_fall_concordance[c] = concord
        ax.scatter(trs[both_fast], tfs[both_fast], s=3, alpha=0.4, color='steelblue', label=f'rise-fast&fall-fast (n={int(both_fast.sum())})')
        ax.scatter(trs[both_slow], tfs[both_slow], s=3, alpha=0.4, color='crimson', label=f'rise-slow&fall-slow (n={int(both_slow.sum())})')
        ax.scatter(trs[rise_only], tfs[rise_only], s=3, alpha=0.4, color='darkorange', label=f'rise-slow,fall-fast (n={int(rise_only.sum())})')
        ax.scatter(trs[fall_only], tfs[fall_only], s=3, alpha=0.4, color='forestgreen', label=f'rise-fast,fall-slow (n={int(fall_only.sum())})')
        rs_bound = km_r.cluster_centers_.ravel()[r_order[1]]
        fs_bound = km_f.cluster_centers_.ravel()[f_order[1]]
        ax.set_xlabel("t_rise (ms)", fontsize=7); ax.set_ylabel("t_fall (ms)", fontsize=7)
        ax.set_title(f"{c}  n={n}  concordance={concord*100:.0f}%  (rise-slow~{rs_bound:.3f}ms, fall-slow~{fs_bound:.3f}ms)", fontsize=7)
        ax.legend(fontsize=6, loc='upper left')
        ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_rise_fall_correspondence.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_rise_fall_correspondence.png")

# 7. Raw trace examples (native trigger time, NOT aligned) by rise-fast vs rise-slow
if active:
    nrows = len(active)
    fig, axes = plt.subplots(nrows, 2, figsize=(14, 3.5 * nrows), squeeze=False)
    fig.suptitle(f"Zip{det} v3 — raw trace examples (native time): rise-fast (blue) vs rise-slow (red)", fontsize=10)
    for row, c in enumerate(active):
        trs  = np.array(channel_trises[c]) * 1e3
        raws = channel_raws[c]
        n    = len(trs)
        ax_full, ax_zoom = axes[row, 0], axes[row, 1]
        if n < MIN_CLUSTER_EVENTS or len(raws) != n:
            ax_full.text(0.5, 0.5, f"{c}: only {n} events, skip", transform=ax_full.transAxes, ha='center', fontsize=8)
            ax_full.set_title(c, fontsize=8); ax_zoom.set_title(c, fontsize=8)
            continue
        km_r = KMeans(n_clusters=2, n_init=10, random_state=0).fit(trs.reshape(-1, 1))
        r_order  = np.argsort(km_r.cluster_centers_.ravel())
        fast_idx = np.where(km_r.labels_ == r_order[0])[0]
        slow_idx = np.where(km_r.labels_ == r_order[1])[0]
        rng = np.random.default_rng(0)
        fast_sample = rng.choice(fast_idx, min(N_EXAMPLES, len(fast_idx)), replace=False)
        slow_sample = rng.choice(slow_idx, min(N_EXAMPLES, len(slow_idx)), replace=False)
        for ax, lo, hi in [(ax_full, PLOT_LO, PLOT_HI), (ax_zoom, ZOOM_LO, ZOOM_HI)]:
            for i in fast_sample:
                ax.plot(t_ms[lo:hi], raws[i][lo:hi], lw=0.6, alpha=0.4, color='steelblue')
            for i in slow_sample:
                ax.plot(t_ms[lo:hi], raws[i][lo:hi], lw=0.6, alpha=0.4, color='crimson')
            ax.axvline(t_ms[SECTION3_RISE_IDX], color='k', lw=0.8, ls=':')
            ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
        rise_fast_c = km_r.cluster_centers_.ravel()[r_order[0]]
        rise_slow_c = km_r.cluster_centers_.ravel()[r_order[1]]
        ax_full.set_title(f"{c} full  fast~{rise_fast_c:.3f}ms (n={len(fast_idx)})  slow~{rise_slow_c:.3f}ms (n={len(slow_idx)})", fontsize=7)
        ax_zoom.set_title(f"{c} zoom (rise region)", fontsize=7)
        ax_full.set_xlabel("Time (ms)", fontsize=7); ax_full.set_ylabel("Norm. raw amp.", fontsize=7)
        ax_zoom.set_xlabel("Time (ms)", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, f"zip{det}_v3_raw_examples_by_rise_peak.png"), dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: zip{det}_v3_raw_examples_by_rise_peak.png")

# ── text summary ────────────────────────────────────────────────────────────
txt_path = os.path.join(PLOT_DIR, f"zip{det}_v3_summary.txt")
lines = []
lines.append("=" * 70)
lines.append(f"SUMMARY: Zip{det} v3  (generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})")
lines.append("=" * 70)
lines.append("Source: cached raw_traces from 126GB pkl (raw_without_filter/run/cache) — "
              "raw_traces is fit-independent, only re-fit here, no raw MIDAS re-read")
lines.append("Fit: 2-exp, pretrigger FREE (curve_fit), bounded to "
              f"[{SECTION3_RISE_IDX-PRETRIGGER_FREEDOM}, {SECTION3_RISE_IDX+PRETRIGGER_FREEDOM}]")
lines.append(f"Align: ana_traces built by re-evaluating fitted (amp,t_rise,t_fall) "
              f"with pretrigger pinned to {SECTION3_RISE_IDX} (align step only, not in fit)")
lines.append(f"Quality cut: fit_ok AND nrmse<={NRMSE_MAX}")
lines.append("zip7 included (NOT skipped) — fit model changed, old teacher approval doesn't carry over")
lines.append("")
for c in ALL_CHANS:
    n_t, n_f, n_n = n_total_c[c], n_fitok_c[c], n_nrmse_c[c]
    if n_t == 0:
        continue
    lines.append(f"{c}: total={n_t}  fit_ok={n_f} ({n_f/n_t*100:.1f}%)  "
                 f"nrmse_ok={n_n} ({n_n/n_t*100:.1f}%)")
    if c in rise_fall_concordance:
        lines.append(f"  rise/fall concordance={rise_fall_concordance[c]*100:.1f}%")
with open(txt_path, 'w') as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved summary: {txt_path}")

print(f"\nDone. Zip{det} v3 complete.")
