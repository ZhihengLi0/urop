# bias_point_check — the TES bias point behind the coefficients (2026-09-29)

The energy formula `δP = I₀(R_L − R₀)·δI + 2R_L·(δI)²` takes I₀, R₀, R_p, R_sh
from the detectorConfig of each series. `kline_energy_hist.py` reads the
detectorConfig of the first cached series (24260617_063934) and applies it to
all 30 series. This folder checks that assumption. The result files in
`../current_power_overlay/` are untouched.

| file | what |
|---|---|
| `zip7_I0_histogram.png` / `.txt` | I₀ per channel, one value per series, weighted by the 1827 events in the sum; red dashed = the value used. The txt lists every series' I₀, R₀ and the linear coefficient. |
| `zip7_kline_energy_sum_hist_seriesbias.png` | the summed energy recomputed with **each series' own** bias point (`kline_energy_hist.py --bias series`) |
| `zip7_kline_energy_hist_allchan_seriesbias.png` / `.txt` | the same per channel, with every event |

## Finding

The 30 series fall into two bias states, identically in all 11 channels:

| state | series | events in the sum | PBS1 I₀ | PBS1 R₀ | I₀(R_L − R₀) |
|---|---|---|---|---|---|
| 1 | June 17–20, 17 series | 1225 | −18.07 µA | 44.16 mΩ | 0.450 µV (used everywhere) |
| 2 | June 21–23, 13 series | 602 | −19.95 µA | 35.51 mΩ | 0.325 µV (−28 %) |

The change is mostly R₀ (×0.65 in R_L − R₀), partly offset by I₀ (×1.10).

Summed energy over the 10 channels (PDS2 left out):

| | all 1827 | state 1 (1225) | state 2 (602) |
|---|---|---|---|
| first series' bias point everywhere (the result) | 3162 eV = **30.5 %**, σ/μ 7.5 % | 30.4 % | 30.7 % |
| each series' own bias point | 2861 eV = 27.6 %, σ/μ 16.9 % — two peaks | 30.4 % (unchanged) | **22.2 %**, σ/μ 7.2 % |

Per event, the new energies differ from the old ones only by the coefficient
ratio (state 1: exactly 1.000; state 2: median 0.725) — the fits are the same.

Evidence on which bias point is real:
- the fitted pulses do not change between the states: summed energy 3155 vs
  3181 eV with one coefficient (0.8 %), rise and fall times within 3 %;
- the group's standard cdmsbats processing (`Processed/Default/Default_tag/
  Unmerged`, per-series detectorConfig) agrees with our energies event by
  event to 0.7 % in state 1 and is 16.5 % lower in state 2.

Whether Z7 was really re-biased on June 21 is not established here; the first
17 series alone give 30.4 %.

Rebuild:
```bash
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
singularity exec -B "$HOME" -B /projects $SIF python3 scripts/i0_histogram.py --det 7
singularity exec -B "$HOME" -B /projects $SIF python3 scripts/kline_energy_hist.py --det 7 --chan all --bias series
```
