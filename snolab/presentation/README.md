# presentation/ — 10-min group-meeting talk (July 15, 2026)

Slides and speaker script for the SNOLAB R4 phonon pulse-template talk.

| file | what |
|---|---|
| `SNOLAB_R4_pulse_templates_20260715.pptx` | 15 slides (11 main + 4 backup: weak detectors, τ_rise ceiling, τ_rise good-vs-bad-channel Z7, τ_rise removed=drift Z22), 16:9, English; each slide has English speaker notes |
| `SNOLAB_R4_pulse_templates_20260715.pdf` | PDF export of the deck |
| `speech_script.md` / `.pdf` | speaker script, per-slide Chinese + English paragraph pairs, with timing hints and Q&A backup answers |
| `figures/` | slide-sized crops of the tall multi-channel diagnostic figures in `lp_fit_align/results/plots/` and of the Ge-activation ops PDF (page 5, Z7) |
| `make_crops.py` | regenerates `figures/` from the versioned diagnostic PNGs |
| `build_pptx.py` | regenerates the .pptx (python-pptx); PDF export was done via PowerPoint |

Slide flow: title → K-line selection & raw cache → fit-quality grids
(data overview) → per-trace algorithm → alignment result → NRMSE cut
derivation → rejected = noise → follow-up: slow-fall tail = PDS2 one-channel
artifact, no cut → 2-exp weighted 1x1 → NxM PCA → deliverables & open items
→ backup 1: weak detectors (Z22) → backup 2: τ_rise ≤ 0.3 ms ceiling (numbers) → backup 3: τ_rise cut good (PBS1) vs bad (PDS2) channel on Z7 → backup 4: what τ_rise removes = slow drift (Z22 slow-rise raw traces).

The main narrative uses **one detector/channel throughout — Z7 PBS1** (per
Prof. Saab); the weak-detector picture (NRMSE histogram, kept-vs-cut fan,
post-cut fan for Z22) lives on the backup slide with keyword notes only.

Terminology: the genuine slow-rise population (a slower "echo" behind the main
pulse) is called **echo-trigger** (per Prof. Saab). The `shadow_events/` figure
folder in `lp_fit_align/` keeps its original name.

11 main slides + 2 backup. The echo-trigger (slow-rise) slide was dropped per Prof. Saab; the τ_rise-ceiling slide is now a backup (removal fractions relative to the NRMSE step: Z7 1.6% — mostly the bad channel PDS2 — vs 55–74% on the weak zips, 54% pooled; see `lp_fit_align/scripts/trise_cut_stats.py`). Slide 7 (slow-fall follow-up) is the designated skip-slide if running long.

## Backup gallery (appendix)

Per Prof. Liu's request the deck now ends with a **Z7 full-results gallery**:
29 backup slides: each Z7 figure gets an overview slide (tall figures auto-split into side-by-side columns) plus a companion 1:1 detail slide (top region at full resolution, in-figure labels readable) (aligned overlay, the
three fitted-curve fans no-cut → NRMSE → NRMSE+τ_rise, raw-vs-fit and
fit-example event grids, overlay_fan_cut, NRMSE / pretrigger / time-constant
distributions, slow-rise / shadow / slow-fall studies, PCA templates, and the
summed 1x1 PT/PS1/PS2). Each slide shows the full figure with its file name
and a one-paragraph how-to-read note; source PNGs are copied under
`figures/backup_zip7/`. Note: the .pdf export is regenerated from PowerPoint,
so it lags the .pptx until re-exported.

## Revision (round 2, July 26)

Slide flow now: title → Table of Contents → dataset (real per-zip event
counts) → fit-quality grids (NOISE vs REAL PULSE, visual comparison, no
claims about per-channel pass/fail) → per-trace algorithm (baseline method,
fit-parameter definitions) → alignment → NRMSE cut → rejected = noise →
slow-fall follow-up (+ PDS2 conclusion and the temporary PDS1-for-PDS2
substitution, applied in the delivered ROOT files) → 1x1 templates (weighted
vs plain-mean comparison, plain mean = nxm0) → NxM PCA → Template file →
Future Steps → backups (4 topic slides + 29-slide Z7 gallery). 46 slides.
Speech script renumbered to match; Q2b (rise = L/R electrical, fall = C/G
thermal) added to the likely-questions list.
