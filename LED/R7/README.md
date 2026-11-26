# R7 LED analysis (LEDStability series after the Cf calibration)

Who triggers on which LED, stability over a week, and pulse templates for the SNOLAB R7 LED series
taken with the sequencer scripts `../SR1a_post-activation_LEDStability_0V_23Det_2026091{3,8}.msl`
and `..._20261004.msl` (LED settings identical in all three). Raw data:
`/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R7/Raw/<series>/`; series list:
`~/series_lists/led_after_cf_2026-09-22.csv` (47 series; `24260916_232802` (74 events) and
`24260918_084531` (no LED flashes) are dropped, 45 are analysed).

Data products (`out/`) and job logs (`*.out`, `logs/`) stay out of git. The talk (slides, PDF, speaker
script, figures) is in `presentation/`.

## What a run looks like

* ~1500 begin-of-run randoms (files F0001/F0002, skipped), then the LEDs come on at ~875-888 s
  (the script waits 800 s; the rest is sequencer overhead).
* **Phase 1**: 15 detectors flash one LED each, **3 s off**, **phase 2**: 12 detectors flash one
  LED each (8 detectors use a *different* LED than in phase 1). Every LED flashes at 1 Hz,
  **151 times per phase** in all 45 series; pulses are 100 us wide (Z17 200 us, Z20 50 us).
* Every triggered event reads out **one** detector (the one that triggered).
* Each LED flashes at a fixed point within the second, so its triggers sit at a fixed
  `TriggerTime mod 1 s` (+-13 us = one tick). The flash time of the Z20 LEDs itself jitters by
  +-0.7 ms: Z20 and the neighbours that see its LEDs all show the same wide peak.
* The LEDs of a phase are switched on one after the other, so several of them often flash within a
  few ms of each other; two LEDs within ~0.2 ms cannot be told apart in that run.

## Pipeline

| step | script | how | output |
|---|---|---|---|
| per-event features, flash groups, rise-aligned templates | `extract_led_events.py SERIES` | `sbatch run_extract.sbatch SERIES` (~12 min, ~33 GB) | `out/SERIES/{events.npz, timing.json, templates.pkl, run_info.pkl}` |
| LED of every flash group, who triggers on which LED, cells | `analyze_led.py` | `sbatch run_summary.sbatch` | `out/summary/` |
| amplitude and trigger-fraction stability | `stability_led.py` | `run_summary.sbatch` | `out/stability/` |
| analytic fit of the rise-aligned templates (cross-check) | `fit_led.py [NPROC]` | `run_summary.sbatch` | `out/fit/` |
| per-pulse fits with the Z7 template chain | `lp_template_led.py SERIES` | `sbatch run_lpfit.sbatch SERIES` (~20-30 min, 8 CPUs, ~30 GB) | `out/SERIES/lpfit.pkl` |
| one template per cell, analytic pulse, example pulses | `lp_template_combine.py [CELL_ID]` | `sbatch run_lpcombine.sbatch` (~30 min) | `out/lpfit/` |
| consistency checks | `qa_led.py` | container, ~2 min | PASS / FAIL lines |
| talk (PPTX, PDF, speaker script) | `presentation/make_figures.py`, `presentation/build_pptx.py`, `presentation/make_pdf.sh` | container / host python3 / `bash -lc` | `presentation/` |

All analysis scripts run in the V07-02 container
(`/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif`); the system
python cannot read the pickles.

### extract_led_events.py
* **Pulse features** per (event, channel): the cuts of the R37 / v3 algorithm
  (`~/minidas/led_templates/make_led_templates_v3.py`: baseline rails and drift, polarity, rise = last
  20 % crossing before the peak, SNR >= 8, glitch = dip < -10 sigma just before the rise, bipolar =
  negative lobe > 0.5 x peak), applied to the **despiked** trace (11-sample running median). When an
  LED is driven, its own detector's readout picks up a spike a few samples wide; on the raw trace
  that spike was taken as the pulse (amplitude = spike height). A phonon pulse passes the filter
  unchanged. Noise is measured on the raw trace: SNR = despiked peak / raw noise. `spike` = the
  largest excursion the filter removed; `pol` = polarity. Tags: good, glitch, nopulse, baseline,
  norise, edge, bipolar.
* **Phases**: the 3 s pause is the largest gap between LED triggers in the middle of the LED period;
  the LED period is where triggers repeat at 1 Hz (three within 3.5 s), so a single background
  trigger cannot start or end it.
* **Flash groups**: per detector and phase, the peaks of `TriggerTime mod 1 s` (0.5 ms bins, >= 20
  triggers), each with its own centre and width. Peaks of different detectors are one flash group
  when their centres are within 0.2 ms (single linkage; 0.3 x the width for the wide Z20 peaks).
  Measured: detectors that trigger on the same flash do so within -115 ... +179 us of the LED
  owner's detector.
* **Source of an event**: the nearest peak of its own detector that contains it; else the nearest
  peak of any detector that contains it; else background. (A group-wide window cut off part of
  Z20's wide peak when it was merged with a neighbour's narrow one.)
* **Flashes** per phase = the longest first-to-last span of a group (151); groups that start or stop
  1-3 s late have that many triggers less.
* `templates.pkl`: mean of the peak-normalised good (despiked) pulses aligned at sample 8000, keyed
  `(detector, phase, channel, flash group)`; a quick look per series, superseded by `out/lpfit`.

### analyze_led.py
* `identify()` decides which LED each flash group is. Candidates: the LED of every member detector
  whose LED is on, and the LED a member stands in for (`LED_ALIAS`: a detector without LED on that
  sees a neighbour's LED whose own detector does not always trigger). An LED is *required* in a
  group when it has no other candidate group, or when its own detector triggers there and nowhere
  else. One required LED -> the group is that LED and the other members only see it; two or more ->
  two LEDs flash within the link tolerance, **ambiguous**: the group is not used, and that series is
  left out for those LEDs (grey in the maps). A second peak of the same LED within 1 ms is the same
  flash (Z16 triggers up to 0.5 ms before Z17); further away it is a **re-trigger** (Z1, 13 ms).
* `flash_groups.csv` (every group, its kind, peaks and triggers), `ambiguous_leds.csv`,
  `visibility.csv` + `visibility_phase{1,2}.png` (fraction of each LED's 151 flashes on which a
  detector triggers, mean over the series; with the trigger-time offset from the owner's peak),
  `cells.csv`: every non-zero cell (fraction >= 0.05) with its ID `P1-01 ...` / `P2-01 ...`.
* `shapes.csv`, `templates_<series>.png`: quick look at the rise-aligned templates per series.
* Limitation: one detector is read out per trigger, so a response below a detector's own trigger
  threshold is not seen. The fractions are lower limits of "sees the light".

### stability_led.py
Per (series, detector, channel, LED): median amplitude (despiked peak, ADC) of the good pulses and
its spread, fraction of low pulses, drift inside the phase, median 10-90 % rise and 1/e decay;
summary per (detector, channel, LED); trigger fraction per (series, detector, LED).
Script version per series from the run log (0913 until 2026-09-18 22:00, then 0918); the ODB start
comment kept the 0913 text and is not used.

### lp_template_led.py / lp_template_combine.py (templates per cell)
* Per pulse, the unchanged Z7 template chain
  (`snolab_phonon_pulse_analysis/phonon_pulse_template_generation/R4/lp_fit_align/scripts/lp_fit_align.py`)
  after the same 11-sample median filter: 100 kHz low-pass, baseline (median of samples 2000-12000),
  / peak, 2-exp fit with free start, measured pulse aligned on the fitted start.
  Event selection (the Z7 analogue): the cell's detector triggered on that LED's flash.
* Template per (cell, channel) = mean of the aligned pulses of all series. "No signal" when fewer
  than 30 % of the cell's events have a pulse in that channel (SNR >= 8, rise found). Analytic pulse
  = `fit_led.fit`: `A1 (exp(-t/tf1) - exp(-t/tr)) + A2 (exp(-t/tf2) - exp(-t/tr))`, 2-exp fallback,
  flags `at_bound`, `tf1~tf2`, `one_component`, `rise~fall`. A slow fall time longer than the 24 ms
  fit window is not constrained. Detector template = signal channels weighted by their amplitude.
* The median filter removes only the narrow part of the LED-drive pickup. Own-LED cells of some
  detectors keep a transient at the pulse start (`presentation/stats.json`, `pickup_cells`); the neighbour
  cells of the same LED are clean.
* Example pulses (Prof. Liu): one typical PSum (unweighted sum of the 12 raw channels) per series
  for a cell (default `P1-07`, Z7 in Z7's LED), light -> dark in time, and the per-series rise and
  fall times of the single-pulse fits.

## Reproduce

```bash
cd ~/urop/LED/R7
SER=$(grep -oE '^2426[0-9]{4}_[0-9]{6}' ~/series_lists/led_after_cf_2026-09-22.csv | sort -u | grep -v -e 24260916_232802 -e 24260918_084531)
for s in $SER; do sbatch run_extract.sbatch $s; done
sbatch run_summary.sbatch                       # after all extractions: summary, stability, fit
for s in $SER; do sbatch run_lpfit.sbatch $s; done   # after run_summary (needs out/summary/cells.csv)
sbatch run_lpcombine.sbatch P1-07               # after all lpfit jobs: templates, talk figures, QA
cd presentation && python3 build_pptx.py && bash -lc ./make_pdf.sh
```
