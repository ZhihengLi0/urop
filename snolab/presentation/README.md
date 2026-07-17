# presentation/ — 10-min group-meeting talk (July 15, 2026)

Slides and speaker script for the SNOLAB R4 phonon pulse-template talk.

| file | what |
|---|---|
| `SNOLAB_R4_pulse_templates_20260715.pptx` | 13 slides (11 main + 2 backup: weak detectors, τ_rise ceiling), 16:9, English; each slide has English speaker notes |
| `SNOLAB_R4_pulse_templates_20260715.pdf` | PDF export of the deck |
| `speech_script.md` / `.pdf` | speaker script, per-slide Chinese + English paragraph pairs, with timing hints and Q&A backup answers |
| `figures/` | slide-sized crops of the tall multi-channel diagnostic figures in `lp_fit_align/results/plots/` and of the Ge-activation ops PDF (page 5, Z7) |
| `make_crops.py` | regenerates `figures/` from the versioned diagnostic PNGs |
| `build_pptx.py` | regenerates the .pptx (python-pptx); PDF export was done via PowerPoint |

Slide flow: title → K-line selection & raw cache → fit-quality grids
(data overview) → per-trace algorithm → alignment result → NRMSE cut
derivation → rejected = noise → follow-up: slow-fall tail = PDS2 one-channel
artifact, no cut → 2-exp weighted 1x1 → NxM PCA → deliverables & open items
→ backup 1: weak detectors (Z22 example) → backup 2: τ_rise ≤ 0.3 ms ceiling.

The main narrative uses **one detector/channel throughout — Z7 PBS1** (per
Prof. Saab); the weak-detector picture (NRMSE histogram, kept-vs-cut fan,
post-cut fan for Z22) lives on the backup slide with keyword notes only.

Terminology: the genuine slow-rise population (a slower "echo" behind the main
pulse) is called **echo-trigger** (per Prof. Saab). The `shadow_events/` figure
folder in `lp_fit_align/` keeps its original name.

11 main slides + 2 backup. The echo-trigger (slow-rise) slide was dropped per Prof. Saab; the τ_rise-ceiling slide is now a backup (removal fractions relative to the NRMSE step: Z7 1.6% — mostly the bad channel PDS2 — vs 55–74% on the weak zips, 54% pooled; see `lp_fit_align/scripts/trise_cut_stats.py`). Slide 7 (slow-fall follow-up) is the designated skip-slide if running long.
