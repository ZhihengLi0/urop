# K-line population: event counts, rates, and the activation decay

Two questions about the Ge activation run, both anchored on slide 2 of the deck
(the 13 per-detector `Summed PTOFamps` histograms from the ops note,
`reference/Ge Activation Data - Ops Shift 2_*.pdf`):

1. how many events sit in the high-amplitude hump above the 10.37 keV K line, and
   at what rate (`scripts/zip10_hump_counts.py`, Z10 in detail);
2. the same counts for all 13 detectors, plus a histogram of the K-line events
   against time (`scripts/all_detectors_and_kline_time.py`).

## Run

```bash
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/zip10_hump_counts.py --figure
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/all_detectors_and_kline_time.py
```

Outputs: `results/zip10_hump_counts.txt`, `results/all_detectors_counts.txt`,
`results/all_detectors_event_counts.csv` (the table below, bare, for download),
`results/plots/kline_counts_vs_time_13dets.png`,
`results/plots/kline_rate_vs_time.png`.

## Rate check

The quoted 4800 / 36 h = 0.037 Hz holds: Z10 has **4862 hump events in 37.2 h =
0.0363 Hz** (0.0368 Hz over the 36.7 h the processed events actually cover).

## All 13 detectors

`hump` is defined per detector as `PTOFamps` above 3x the top of that detector's
K-line window, which is where the Z10 valley sits. Run time is the ops note's
Duration column over the series that detector uses.

| det | series | run [h] | K-line events | K rate [mHz] | hump events | hump rate [Hz] |
|---|---|---|---|---|---|---|
| Z1 | 26 | 35.9 | 9582 | 75.1 | 4133 | 0.0319 |
| Z4 | 27 | 37.2 | 23240 | 175.8 | 4148 | 0.0309 |
| Z6 | 27 | 37.2 | 14689 | 111.1 | 5100 | 0.0380 |
| Z7 | 27 | 37.2 | 1888 | 14.3 | 4520 | 0.0337 |
| Z9 | 27 | 37.2 | 2273 | 17.2 | 4584 | 0.0342 |
| Z10 | 27 | 37.2 | 6861 | 51.9 | 4862 | 0.0363 |
| Z13 | 26 | 35.2 | 8235 | 66.0 | 3631 | 0.0287 |
| Z15 | 22 | 32.6 | 2405 | 20.8 | 2572 | 0.0219 |
| Z16 | 27 | 37.2 | 1363 | 10.3 | 4167 | 0.0311 |
| Z18 | 18 | 25.3 | 16332 | 182.8 | 2571 | 0.0282 |
| Z19 | 27 | 37.2 | 19948 | 150.9 | 4235 | 0.0316 |
| Z22 | 21 | 28.6 | 21333 | 207.9 | 4627 | 0.0450 |
| Z24 | 27 | 37.2 | 19763 | 149.5 | 5579 | 0.0416 |

**The hump rate is the same in every detector to within a factor 2 (0.022 to
0.045 Hz)** even though the detectors differ wildly in resolution and in K-line
yield. A population that is this uniform across the tower is an external one,
not a per-detector artifact.

**The K-line column is not uniform (10 to 208 mHz) and should not be read as a
physical rate.** Where the window sits at a few times 1e-7 A it overlaps the
noise-trigger population and the counts are inflated: only Z7, Z13, Z15, Z16 and
Z18 have windows above 1e-6 A and therefore clean counts. Z7 gives 14 mHz.

## The K-line versus time, and the 71Ge decay

`kline_counts_vs_time_13dets.png` is the requested histogram: counts per 2 h bin
per detector, with a red dashed curve showing the same total spread over each
bin's exposure and decaying with the 71Ge half-life.

`kline_rate_vs_time.png` divides by the exposure so the decay can be read
directly. It is restricted to the five clean detectors, uses 6 h bins and drops
bins with under 1 h of exposure: on 2 h bins the low-exposure bins produced 500
mHz spikes that are not rate measurements, and the contaminated detectors swamped
everything when the trigger threshold was lowered part way through the run. The
lower panel normalises each detector to its own best-fit 71Ge level, and shows one
clear instrumental feature: between 100 and 111 h every detector drops to 0.25-0.5
of its level and then recovers. That stretch is the six noise-dominated series,
where the trigger rate costs live time; it is deadtime, not decay, and it is why
those series are dropped from the test below.

The important scale fact: **the 27 series hold 37.2 h of live time but span 132 h
(5.5 days) of wall clock**, so the 11.43 d half-life of 71Ge predicts a real drop
of about 15% between the first and second half of the run, not a negligible one.

Measured second-half / first-half rate ratio on the clean sample (windows above
1e-6 A, and dropping the six noise-dominated series, all of which fall in the
second half):

| det | first | second | measured | 71Ge |
|---|---|---|---|---|
| Z7 | 1233 | 578 | 0.891 ± 0.045 | 0.846 |
| Z13 | 4982 | 2511 | 0.853 ± 0.020 | 0.852 |
| Z15 | 1414 | 809 | 1.102 ± 0.049 | 0.837 |
| Z16 | 808 | 488 | 1.147 ± 0.065 | 0.846 |
| Z18 | 5920 | 7511 | 0.873 ± 0.015 | 0.896 |

Inverse-variance mean **0.889 ± 0.011 against 0.875 predicted**: the K-line
population decays on a multi-day timescale consistent with 71Ge electron capture,
which is the expected origin of the 10.37 keV line after the Cf activation.

## Caveats

- Combining detectors by summing counts is wrong here and was corrected: the
  detectors have very different K-line rates and different exposure in each half
  (Z18 drops the first nine series), so the sum-of-counts ratio came out at 1.33.
  The per-detector ratios are combined by inverse variance instead.
- Taking all 13 detectors and all 27 series gives 0.758, well below the 71Ge
  expectation. Two contaminations pull it down: windows that overlap the noise
  triggers, and the six noise-dominated series whose trigger rates cost live time
  that the event-time coverage cannot see.
- Exposure per bin is the span the processed events cover, not the ops Duration,
  because Prompt truncates high-rate series (24260620_032928 keeps 181849 of
  1286120 triggers). Both are reported in the table.
- `PTOFamps` is already in amperes, so the ADC to amp factor (3.145728e9 ADC/A)
  must not be applied to it. It belongs to raw traces only, as in
  `differentialequations/`.
