# SNOLAB Run 4 — Phonon Pulse Template Project

Author: Zhiheng Li

Goal: build high-quality phonon pulse templates for the CDMS SNOLAB Run 4
detectors — 13 zips (Z1, Z4, Z6, Z7, Z9, Z10, Z13, Z15, Z16, Z18, Z19, Z22,
Z24), 12 phonon channels each (PAS1…PFS1, PAS2…PFS2) — and deliver them as
ROOT `TH1D` template files for the cdmsbats optimal filter (1x1 and NxM).

Everything below is our own work: event selection, raw-data caching, fitting,
alignment, event-quality diagnostics, template construction (analytic 2-exp
and PCA/NxM), and deployment in the official `PulseTemplates` format.

---

## 1. Data and event selection

**Upstream data (MSI, read-only):**
- Processed ROOT RQs: `/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged/`
- Raw MIDAS: `/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw/`

**Event selection — PTOFamps window only.** For each detector we select
events whose total-phonon optimal-filter amplitude (`PTOFamps`) falls inside
a window bracketing that detector's 10.37 keV K-shell activation line
(window ≈ K-line position ×/÷ 1.35, per detector). No trigger-type cut, no
channel-completeness cut, no pulse-quality cut at this stage — the selection
is deliberately minimal so every later cut is explicit and reversible.

**Raw event cache** (`raw_without_filter/`): one SLURM job per zip reads the
processed ROOT for the selection and then extracts, for every selected event,
the completely unprocessed raw MIDAS traces of all available channels, plus
full event-level metadata (`EventNumber`, `PTOFamps`, `TriggerType`,
per-channel RQ baselines, per-event/per-channel bookkeeping in
`event_stats`, missing channels recorded rather than dropped). Output is one
pickle per series:

```
/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache/zip{N}_series/{series}.pkl
payload_schema_version = "raw_ptof_selected_event_v1"
```

Writes are atomic (`.tmp` + `os.replace`); reruns skip existing series, so an
interrupted job resumes for free. Each primary job carries an automatic
`afternotok` rescue job — when the Z15 primary hit its 30 h wall-time limit,
the rescue completed the remaining series unattended. Final cache:
13 zips / ~120 GB / 27–30 series per zip, verified complete and duplicate-free.

## 2. Fit-and-align pipeline (`lp_fit_align/`)

Per trace (script `scripts/lp_fit_align.py`, one SLURM job per zip,
channel-parallel with a process pool):

1. **Low-pass** — 100 kHz 4th-order Butterworth (`scipy.signal.sosfilt`
   with steady-state initial conditions, eliminating the filter start-up
   transient that would otherwise corrupt a global peak search).
2. **Baseline** — median of samples 2000–12000, subtracted.
3. **Normalize** — divide by the *global* trace peak (no peak-window
   restriction).
4. **Free-pretrigger 2-exp fit** —
   `y = A·(exp(−t/τ_fall) − exp(−t/τ_rise))`, all **5 parameters free**
   including the pretrigger (onset) time: `amp, t_rise, t_fall, baseline,
   pretrigger` with `pretrigger ∈ 16050 ± 3000` samples, `maxfev = 10000`.
   The onset is *never* pinned inside the fit — real trigger times vary
   event-by-event (fitted onsets cluster ≈ 230 samples after the nominal
   16050) and pinning them distorts every other parameter.
   Fit window: samples 12550–24050 (16050 − 3000 − 500 to 16050 + 8000),
   stride 4; parameter bounds amp ∈ [0, 10], t_rise ∈ [1 µs, 5 ms],
   t_fall ∈ [10 µs, 20 ms], baseline ∈ [−0.5, 0.5].
5. **Quality numbers** — `fit_ok := amp>0 and 0<t_rise<t_fall`;
   `NRMSE := RMS(fit residual)/fitted pulse peak` (recorded for every trace;
   used as a cut only downstream).
6. **Align** — shift the *measured* low-passed trace by
   `(fitted pretrigger − 16050)` with sub-sample `np.interp`. Alignment is a
   pure translation of the data; no analytic re-generation.

Fit results are checkpointed per series
(`run/checkpoints/zip{N}/{series}_fit.pkl`, parameters only, ~170 MB for all
13 zips) and index-aligned with the cache's `event_numbers_ch`, so every fit
is traceable to an `EventNumber` and downstream analyses never refit.

## 3. Quality cuts and how they were derived

- **`fit_ok`** rejects non-converged / unphysical fits, but noise can still
  converge to physical-looking parameters.
- **`NRMSE ≤ 0.4`** — the NRMSE distribution of fit_ok events is *bimodal*
  (log-log histograms in `results/plots/nrmse/`): a good-fit population
  (median ≈ 0.05–0.1 on quiet detectors) and a noise-trigger population
  (≈ 1–2), separated by a valley at ≈ 0.4–0.5. The cut sits in the valley.
  Event grids of the rejected population (`slow_events/`) show pure noise in
  the raw traces, confirming the cut removes noise triggers, not physics.
- **`t_rise ≤ 0.3 ms`** — on noisy-window detectors a smooth slow baseline
  drift can survive the NRMSE cut (a slow 2-exp hugs it with a small
  residual). The fast-pulse population sits at t_rise ≈ 0.1 ms with its p90
  ≈ 0.15 ms, cleanly separated from the drift tail, so the 0.3 ms ceiling
  removes the leakage at ~2–5 % signal cost on quiet detectors. Known
  trade-off (documented, pending final decision): it also trims the small
  population of genuine slow-rise pulses.

**Detector context.** The PTOF windows are correct for every zip, but on the
weak detectors (Z1, Z4, Z6, Z18, Z19, Z22, Z24) the K-line blob overlaps the
noise-trigger population, so their windows admit a noise-dominated mixture —
the cuts above are what extract the real-pulse population from it. Quiet
detectors (Z7 best, then Z9/Z13/Z15/Z16…) pass almost intact.

## 4. Event-quality studies (figure catalogue)

All figures live under `lp_fit_align/results/plots/<type>/`, one sub-folder
per figure type, all zips together. Every PNG carries the full processing
chain plus a one-line description stamped at the top, so each file is
self-documenting.

| folder | contents |
|---|---|
| `aligned_overlay/` | shift-aligned measured traces (blue sample) + point-by-point mean of ALL fit_ok events (red) + NRMSE-weighted mean of fitted curves, w = 1/max(NRMSE,0.01)² (orange); legend names every curve |
| `fitted_curves_overlay/` | "fan" plots: every fit re-evaluated at common pretrigger 16050, peak-normalized — pure shape distribution; variants without cut, with NRMSE≤0.4, and with NRMSE≤0.4 + t_rise≤0.3 ms |
| `fit_examples/` | event grid: first 15 selected events × all channels, LP trace vs fit, per-panel NRMSE — cross-channel consistency of single events at a glance |
| `raw_vs_fit_examples/` | same 15 events, three layers per panel: raw (gray) / 100 kHz LP (blue) / fit (red) |
| `overlay_fan_cut/` | three-in-one: aligned measured traces + fitted curves passing the NRMSE cut (green) + rejected (red), median NRMSE of both populations stamped per channel |
| `nrmse/`, `pretrigger/`, `time_constants/` | full-statistics distributions (log-log NRMSE; fitted onset; t_rise/t_fall) |
| `slow_events/` | event grid of the NRMSE-rejected population — raw traces show they are noise triggers |
| `ghost_events/` | event grid of well-fit slow-rise events (median NRMSE ≤ 0.4 and median t_rise > 0.2 ms) — raw traces show real, genuinely slow pulses (the faint displaced bundle visible in aligned overlays) |
| `slow_fall_events/` | random sample of events with long fitted t_fall on a reference channel, all channels drawn — showed that Z7 "slow-fall" events are real pulses in 11 channels while the long t_fall is a PDS2 single-channel low-frequency artifact |
| `pca_templates/` | final NxM PCA templates per channel (nxm0–nxm4) with explained-variance ratios |

Key findings from these studies:
- NRMSE separates noise triggers from real pulses; the rejected population is
  noise (verified in raw), the kept population is physics.
- A small population of *genuine* slow-rise pulses exists on quiet detectors
  (candidate surface/bulk effect); it survives NRMSE and is distinct from
  noise — this is exactly the shape variation the NxM multi-template method
  is meant to capture.
- Long-t_fall events on Z7 are not slow physics: the same events are normal
  fast pulses in 11 channels, and the long fall is a PDS2-only low-frequency
  disturbance.
- Fits hitting the parameter bounds (t_rise 5 ms / t_fall 20 ms) pile up as
  isolated spikes at histogram edges — a fit-boundary artifact concentrated
  in the noise population and removed by the NRMSE cut.

## 5. Templates

Two template families, both 32768-bin `TH1D`, both peak-normalized:

**(a) Analytic 2-exp weighted template** (`scripts/write_2exp_templates_root.py`)
— per channel, the NRMSE-weighted mean of all fit_ok fitted curves at common
pretrigger 16050 (weight `1/max(NRMSE,0.01)²`: badly-fit events count less
but are never excluded), re-normalized to peak 1. Local archive:
`results/root_files/Templates_SNOLAB_R4_zip{N}_2expfit_weighted.root`.

**(b) NxM PCA templates** (`scripts/build_pca_templates.py`,
`scripts/normalize_pca_templates.py`) — per channel, PCA over the fitted
curves that pass `fit_ok + NRMSE≤0.4 + t_rise≤0.3 ms` (curves at common
pretrigger, peak-normalized; PCA window samples 15550–24050, i.e.
16050 − 500 to 16050 + 8000; at most 3000 curves per channel, seeded random
subsample). Templates are `nxm0` = mean curve and
`nxm1..nxm4` = the first four principal components (oscillating basis
vectors, may be negative; a real pulse is fit as Σᵢ ampᵢ·nxmᵢ). PC1+PC2
capture 96–98 % of the shape variance. All five are peak-normalized to 1 in
the delivered files. Local archive:
`results/root_files/Templates_SNOLAB_R4_zip{N}_nxm_pca.root`.

**Deployment (cdmsbats `PulseTemplates` format).** The official layout is a
top-level `zip{N}` `TDirectory` containing `{chan}` (1x1 template),
`{chan}nxm0..4`, and summed templates `PT`/`PS1`/`PS2` (peak-normalized
averages of the channel templates). Deployed under
`/projects/standard/yanliusp/shared/software/cdmsbats_config/PulseTemplates/files/` as:

```
SNOLAB_R4_20260706_ZhihengLi_zip{N}.root        # 2-exp weighted templates
SNOLAB_R4_20260707_ZhihengLi_pca_zip{N}.root    # PCA nxm templates (normalized)
```

(13 files each, N ∈ {1,4,6,7,9,10,13,15,16,18,19,22,24}, mode 777.)

## 6. Interactive notebooks (`lp_fit_align/notebooks/`)

- `nrmse_cut_explorer.ipynb` — single zip: edit `DET`/`NRMSE_MAX`, rerun →
  pass-rate table, log NRMSE histogram with the cut line, fan plots and
  t_rise/t_fall before/after the cut.
- `fan_cut_compare_all_zips.ipynb` — all zips at once: one before/after fan
  figure per zip plus a cross-zip pass-rate table. Checkpoints are loaded
  once; changing the threshold and rerunning takes seconds.

## 7. Repository conventions

- **One algorithm = one self-contained directory** (`scripts/` in git,
  `results/plots|stats` for finals, git-ignored `run/` for logs and
  checkpoints). Current layout:
  - `raw_without_filter/` — stage 1: PTOFamps-window event selection and the
    unprocessed raw-trace pickle cache (section 1);
  - `lp_fit_align/` — stage 2: the fit/align/diagnostics/template pipeline
    (sections 2–6). This is the definitive analysis.
  Earlier template iterations (`1x1_final/`, `nxm_final/` — pinned-pretrigger
  fits, superseded methodology) were removed from the tree; their history is
  preserved in git tags v0.1–v5.0.
- Deliverables (code, notebooks, figures, commit messages) are in English.
- Large artifacts (pkl / png / root) stay on MSI storage and out of git;
  the repository tracks code and small JSON summaries only.
- Milestones are annotated tags: `v6.0` lp_fit_align pipeline, `v6.1`
  12-zip diagnostics, `v6.2` all-13-zip completion, `v7.0` NxM PCA
  templates.

## 8. Reproducing

```bash
# raw cache (one job per zip; safe to rerun, resumes at missing series)
bash raw_without_filter/scripts/submit_ptof_selected_events.sh

# fit + align + diagnostics (checkpoints make reruns cheap)
bash lp_fit_align/scripts/submit_lp_fit_align.sh 7

# templates
python3 lp_fit_align/scripts/write_2exp_templates_root.py --det 7
python3 lp_fit_align/scripts/build_pca_templates.py --det 7
python3 lp_fit_align/scripts/normalize_pca_templates.py --det 7 --date YYYYMMDD
python3 lp_fit_align/scripts/export_cdmsbats_templates.py --det 7 --date YYYYMMDD
```

All Python runs inside the CDMS singularity image
(`cdmsfull_V07-02-00.sif`) for PyROOT / scipy / rawio.
