# presentation/ — 10-min group-meeting talk (July 15, 2026)

Slides and speaker script for the SNOLAB R4 phonon pulse-template talk.

| file | what |
|---|---|
| `SNOLAB_R4_pulse_templates_20260715.pptx` | 13 slides, 16:9, English; each slide has English speaker notes |
| `SNOLAB_R4_pulse_templates_20260715.pdf` | PDF export of the deck |
| `speech_script.md` / `.pdf` | speaker script, per-slide Chinese + English paragraph pairs, with timing hints and Q&A backup answers |
| `figures/` | slide-sized crops of the tall multi-channel diagnostic figures in `lp_fit_align/results/plots/` and of the Ge-activation ops PDF (page 5, Z7) |
| `make_crops.py` | regenerates `figures/` from the versioned diagnostic PNGs |
| `build_pptx.py` | regenerates the .pptx (python-pptx); PDF export was done via PowerPoint |

Slide flow (investigation order): title → K-line selection & raw cache →
per-trace algorithm (+ fan before/after NRMSE cut) → fit grids → NRMSE cut
derivation → rejected = noise → follow-up 1: slow-fall tail = PDS2 one-channel
artifact, no cut → follow-up 2: echo-trigger slow-rise = real pulses →
τ_rise ≤ 0.3 ms ceiling against drift (trade-off pending) → 2-exp weighted 1x1
→ NxM PCA (+ final peak normalization) → deliverables & open items.

Terminology: the genuine slow-rise population (a slower "echo" behind the main
pulse) is called **echo-trigger** (per Prof. Saab). The `shadow_events/` figure
folder in `lp_fit_align/` keeps its original name.

Slide 7 (slow-fall follow-up) is the designated skip-slide if running long.
