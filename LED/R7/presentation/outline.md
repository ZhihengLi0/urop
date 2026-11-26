# Outline and frozen facts for the R7 LED talk

Audience: SuperCDMS group meeting (Prof. Yan Liu). Speaker: Zhiheng Li (UMN undergraduate).
Length: about 8 minutes, 11 main slides, then backup (simplified 2026-11-26 at the user's request: follow Prof. Liu's
points only, one figure and at most three short lines per slide, few numbers, no dashes or arrows in titles and text). Slides in English. Speaker script: Chinese + English
per slide, short simple sentences that can be read aloud.

Every number on a slide must be read from `stats.json` or the CSV files named below, never typed.
Where this file quotes a number it is only to say what to expect; if `stats.json` differs, `stats.json` wins
and the difference must be reported.

## Prof. Liu's outline (Slack)
1. visibility plot (phase 1; phase 2)
2. stability: amplitude vs time — mostly stable; some cases to look at again
3. stability: trigger fraction vs time
4. template generation; show example pulses, e.g. Z7 PSum in Z7's LED, drawn together, to see the pulse shape
   change with time

## Data and method (2-3 slides)
- Opening slide (asked for by Prof. Liu: start with the basic information and a timeline): `fig_week_timeline.png`,
  all LED runs of the week on a time axis and one sequencer cycle; numbers in `stats.campaign` (47 runs, 45
  analysed, blocks of consecutive runs, low-background run 100 min -> LED run ~20 min -> relock, one LED run
  about every 132 min; the cycle is read from the script's wait times and the measured spacing of the series).
- 45 LEDStability series, 15-21 September 2026, after the Cf calibration. Two more dropped: 24260916_232802
  (74 events), 24260918_084531 (no LED flashes).
- One run: ~880 s wait, phase 1 (15 LEDs), 3 s off, phase 2 (12 LEDs). Each LED flashes at 1 Hz, 151 times per
  phase in every series. One detector is read out per trigger. Figure `fig_run_timeline.png`.
- Which LED made a trigger: each LED flashes at a fixed time within the second, so `TriggerTime mod 1 s` has
  one peak per LED (`fig_flash_groups.png`). Detectors that trigger on the same flash do so within 0.2 ms
  (`stats.offset_us_range`). The script says which LEDs are on; the LED's own detector, or elimination, names
  the peak. Two LEDs within 0.2 ms of each other cannot be separated: `len(stats.ambiguous)` flash groups of
  `stats.n_groups`, left out (grey in the maps). Z1 triggers a second time 13 ms after some flashes in
  `len(stats.retrigger)` series; not counted.

## Part 1 — who triggers on which LED
- `visibility_phase1.png`, `visibility_phase2.png`; cells from `out/summary/cells.csv` (id, phase, led, det,
  fraction, own_led). `stats.n_cells` non-zero cells, each with an ID (P1-01 ...).
- The LED's own detector triggers on essentially every flash (fraction 1.00) for most LEDs.
- Light reaches the detector with the adjacent number and never further: `stats.cells_not_adjacent` is empty.
- No pair crosses Z6|Z7, Z12|Z13, Z18|Z19 (`stats.cells_across_towers` empty): all pairs lie inside Z1-6, Z7-12,
  Z13-18, Z19-24. The ODB shows the same grouping (Z1-6 and Z19-24 have one DCRC, Z7-18 two). Say "groups of
  six"; do not assert more about the hardware than this.
- Direction (`stats.led_table`: own / prev / next fraction per LED): LED 0 and 1 are seen by the detector with
  the number below, LED 3, 4, 5 by the one above. At the end of a group there is no neighbour, so those LEDs are
  seen only by their own detector. Two exceptions, to be stated: Z19 LED0 is seen by Z20 (30 %); Z23 LED3 is not
  seen by Z24.
- LEDs that do not (always) trigger their own detector: from `led_table` (own < 0.9), e.g. Z11 LED0 and Z22 LED0
  never; Z9 LED4, Z18 LED3 partly. These depend on the trigger thresholds (Part 3).
- Limitation: only the triggering detector is read out, so light below a detector's threshold is invisible.
  The fractions are lower limits.

## Part 2 — amplitude vs time
- Amplitude = median over a series of the despiked pulse peak (ADC) of the good pulses, per channel, divided
  by that channel's median over all series; cell value = median over its channels. `fig_amp_map.png`.
- `stats.amp_within_5pct` % of the (cell, series) values are within 5 %, `stats.amp_within_10pct` % within 10 %.
  Most cells decline slowly: `stats.slope_pct_per_day` (median, n_negative of n_cells).
- Whose change is it? `fig_same_led.png`, `stats.same_led_corr`, `stats.same_det_corr`: two detectors that see
  the same LED move together (r up to 0.99), one detector with its two LEDs does not. So the changes are in the
  LED light, not in the detectors. (Exceptions to mention if on the slide: Z17 LED0 pair r 0.2, Z18 LED1 pair
  r 0.47; for Z20 both of its LEDs dropped together.)
- Cases to look at again (`fig_stab_cases.png`, `stats.z20_low`, `z20_led3_low`, `z19_low`, `stats.cell_amp`):
  18 Sep 02:09-06:33, Z20's LEDs: Z20 at ~0.25 (LED0) and ~0.34 (LED3), Z19 seeing Z20's LED0 at 0.56 while
  Z19 with its own LED is normal -> Z20's LEDs were dim. The next run (08:45) had no LED flashes; normal again at
  13:03. LED settings in the ODB unchanged. Also: first day (15 Sep) ~20 % high for a few cells (Z1 LED0, Z7 LED0,
  Z13 LED5, Z16 with Z15's LED4); see `cell_amp[...].first_day`.

## Part 3 — trigger fraction vs time
- `fig_trig_map.png` (one row per cell, one column per series; black lines = L1 trigger thresholds changed).
- Own-LED cells with fraction ~1 stay at 1 in every series.
- The steps follow the L1 trigger thresholds in the ODB: `stats.epochs` (6 epochs; `out/summary/
  trigger_epochs.csv`, `trigger_settings.csv`). Z9 and Z10 trigger on LEDs only in the series of the low-threshold
  epochs (`stats.series_z9_z10`). `stats.trig_epoch[cell]` gives mean / min / max per epoch.
- So the steps are settings, not instability. Inside an epoch a few cells near threshold still drift
  (e.g. Z21 seeing Z20's LED3, Z20 seeing Z19's LED0).

## Part 4 — templates
- One template per cell and channel, all series together, made like the Z7 template (per pulse: 100 kHz low-pass,
  baseline, / peak, 2-exp fit with free start, aligned on the fitted start, averaged). LED data only: an 11-sample
  (18 us) median filter first, against the LED-drive pickup spikes. Analytic pulse: one rise, two falls
  (2-exp fallback). `out/lpfit/LED_cell_templates.csv` (per cell and channel, plus channel = "detector").
  Counts: `stats.n_pulses_fit_ok`, `stats.chan_signal`, `stats.det_templates`.
- One clean cell as the example (default P1-02, `cell_P1-02.png`).
- Pickup: own-LED cells of some detectors keep a transient at the pulse start (`stats.pickup_cells`); the
  neighbour cells of the same LED are clean. Z18 PFS2 with its own LED3 is a large negative transient, not a
  phonon pulse. Show `cell_P1-07.png` (Z7, Prof. Liu's example detector).
- All cells: `cells_overview.png`. Table of the analytic pulse for the detector templates (`stats.det_table`);
  a slow fall longer than the 24 ms fit window is not constrained (print as "> 20 000 us").
- Example pulses (Prof. Liu): `example_pulses_P1-07.png`, Z7 PSum (unweighted sum of the 12 raw channels) on
  Z7's LED0, one typical pulse per series, light -> dark in time; `shape_vs_time_P1-07.png` for the numbers.
  Say what the figure shows; do not claim more stability than the figure supports.

## Summary and open points
- Every LED trigger is assigned to one LED; light goes to the adjacent detector, in a fixed direction per LED.
- Amplitudes: mostly within 10 %; changes follow the LED. Trigger fractions: steps = threshold changes.
- Templates and analytic pulses for all cells; Z7 PSum over the week.
- To look at: Z20's LEDs on 18 Sep; pickup in own-LED cells; Z1 second trigger 13 ms after the flash;
  the 0918 script should switch off Z17's L1 trigger, but the ODB shows it enabled in all 45 series and Z17
  keeps triggering (script version per run log: 0913 until 18 Sep 22:00, then 0918).

## Backup
- `amplitude_vs_time.png`, `trigger_fraction.png` (every channel / every cell vs time).
- How events are assigned to an LED (details).
- One slide per cell: `cell_<ID>.png`.

## Format
As `~/urop/snolab_phonon_pulse_analysis/didv/presentation/` (python-pptx, 16:9, Arial, navy titles, speaker notes
on every slide, page numbers, `make_pdf.sh`, `speech_script.md` with timing line and likely questions,
`build_speech_pdf.py`). Tone: plain and factual, percentages first, no showy wording.
