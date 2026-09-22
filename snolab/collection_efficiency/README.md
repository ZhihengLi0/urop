# collection_efficiency

How much of a 10.37 keV K-line event ends up as energy in the TESs of Z7.
Result: **30.5 %**, relative uncertainty σ/μ = 7.5 % (± 2.3 percentage points), from
the 10 channels other than PDS2 (1827 events). PDS2 is left out: it fits on only
42 % of the events, the ones near it, so its subsample depends on position
(Prof. Yan Liu, September 2026; the earlier 32 ± 1 % bracket is withdrawn).

The recorded trace is a current, and the area under a current is a charge, not
an energy. So each trace is fitted with a two-exponential, the fitted current is
turned into power with the TES equations (`P = I₀(R_L − R₀)·δI + 2R_L·(δI)²`,
bias point per channel from `detectorConfig`), and the power is integrated in
closed form. Summed over the channels of an event, that is the absorbed energy;
divided by 10.37 keV, the collection efficiency.

| path | holds |
|---|---|
| `scripts/plot_fitted_current_power.py` | current and power overlay, cumulative energy, one series, 15 events and all channels of one event |
| `scripts/plot_peak_raw_vs_lowpass.py` | one pulse on the peak, read as ADC / µA / fW; why the height comes from the fit |
| `scripts/kline_energy_hist.py` | every K-line event fitted and integrated (fit cache in `run/fit_cache/`), per-channel histograms, the summed histogram and the efficiency |
| `results/plots/current_power_overlay/` | the figures and the text files with every number |
| `NOTES.md` | the derivation, the constants and where they come from, the official Eabs definition, what was tried and corrected |
| `derivation_zh.html` | the power formula derived step by step (Chinese) |
| `presentation/` | the 13-min talk: slides, PDF, bilingual speaker script |

Run inside the CDMS singularity image, e.g.

```bash
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/kline_energy_hist.py --det 7 --chan all
```

The fit cache makes re-plotting take seconds; the first pass over 30 series
takes about an hour and must go through SLURM.

Open items: only Z7 so far; the HV bias of Z7 in these series is not
established (all numbers assume 0 V); no dI/dV data on MSI, so the loop gain and
the inductor term are unknown; PDS2's low-frequency artefact is the ±1 %; 276 of
the 2207 events (12.5 %) fit in no channel and are not in the histograms.
