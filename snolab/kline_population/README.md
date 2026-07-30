# Z10 high-amplitude hump: event count and run time

Slide 2 of the deck shows the 13 per-detector `Summed (N series) PTOFamps,
rejecting SumPF/PT less than 0.05` histograms lifted from the Ge Activation ops
note (`reference/Ge Activation Data - Ops Shift 2_*.pdf`). Z10 has three
populations: noise triggers near 2e-7 A, the 10.37 keV K line at 8.7e-7 A (red
marker), and a broad hump from ~4e-6 to ~7e-5 A. This answers two questions
about that hump: how many events are in it, and how much run time it took.

## Run

```bash
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/zip10_hump_counts.py --figure
```

Output: `results/zip10_hump_counts.txt`.

## Answer

| quantity | from MSI data (27 series) | from the published figure |
|---|---|---|
| PTOFamps > 3e-6 A (whole hump) | 4886 | 4089 |
| PTOFamps > 1e-5 A | **4110** | 3395 |
| PTOFamps > 2e-5 A | 2261 | 1987 |
| PTOFamps > 3e-5 A | 978 | 960 |
| PTOFamps > 5e-5 A | 19 | 37 |
| right edge of the population | 6.73e-5 A | 6.62e-5 A |

Run time: **37.2 h for the 27 series**, so about 35-37 h (~1.5 days) for the
note's 26. Rate in the hump: 131 events/h above 3e-6 A, 110 events/h above
1e-5 A.

The hump's median amplitude is 1.90e-5 A = 22x the K line, i.e. of order
200 keV if the response were linear (it is not, at the top end).

## Two independent methods, and why they differ by 10-20%

1. **Data**: `PTOFamps` for zip10 from the Prompt processing, one file per
   series, sentinel `-999999` events dropped.
2. **Figure**: the published histogram integrated out of the PDF pixel by pixel
   (axis calibration from the visible gridlines, 34 bins/decade recovered from
   the bar width). Needs no series list, so it is a true independent check.

They agree to 2% at 3e-5 A and to 17% at 1e-5 A. The data numbers are the higher
ones for two reasons: this set has 27 series against the note's 26, and the pixel
method undercounts wherever adjacent equal-height bars merge into one run.

## Caveats

- **The note never prints its series list.** Its plots say "26 series"; 18 of
  them are provable from its own per-detector `SERIES_LIST.remove()` calls, and
  the 27 used here are those plus our analysis list over the same dates. So this
  set contains the note's 26 with at most one extra series (worth 0.4-2.2 h).
  The per-series table in the output lets any subset be re-summed.
- **The quoted junk cut does not reproduce the note's plot.** Read literally,
  `SumPF/PT > 0.05` (PF = the PF channels) keeps 235418 of 235711 valid events,
  while the note's histogram holds only 7716. Their cut must be stricter than the
  wording. It does not affect the hump: the numbers above move by less than 0.1%
  when it is applied.
- **`LiveTime` is not filled** in this processing (all zeros), so run time comes
  from the note's Duration column, cross-checked against the largest
  `TriggerTime` in each series (38.3 h summed, agreeing with 37.2 h to 3%).
- **Prompt processing is truncated** for the high-rate series (e.g.
  24260620_032928: 181849 of 1286120 triggers), which is why those series
  contribute few hump events.
