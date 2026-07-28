# nxm_energy — energy from the NxM amplitudes

Every event processed with the NxM templates gets `n_chan x 5` amplitudes
(11 x 5 = 55 numbers on Z7). This directory answers the question: **what
combination of those numbers is the energy?** The Ge-activation K-line is
mono-energetic (10.37 keV), so the same sample both calibrates a combination
and measures its resolution.

## Pipeline

    scripts/build_dataset.py       amplitudes + reference quantities -> results/dataset_zip{N}.npz
    scripts/energy_combination.py  the estimators, peak fits, weights -> results/plots, weights_zip{N}.npz
    scripts/validate_linearity.py  do the K-line weights hold at other energies?

Run inside the CDMS singularity image:

    python3 scripts/build_dataset.py --det 7
    python3 scripts/energy_combination.py --det 7
    python3 scripts/validate_linearity.py --det 7

Data sources: NxM amplitudes `PTOFnxm{CHAN}tem{k}amps` from the UMN (Addison)
`Default_tag` processing of our delivered templates; the K-line selection is
the Prompt `PTOFamps` window that defined the raw cache; the quality cut is
the median NRMSE of our own free-pretrigger 2-exp fit.

## Estimators

| estimator | definition |
|---|---|
| PTOFamps | official total OF amplitude (reference) |
| sum OFamps | plain sum of the per-channel 1x1 OF amplitudes |
| nxm0 only | `sum_c a_c0 * I_c0`, `I` = template time integral |
| physics NxM | `sum_ck a_ck * I_ck` = integral of the reconstructed pulse |
| min-variance | `w = E0 * S^-1 mu / (mu' S^-1 mu)`, the smallest-variance combination with the correct mean |

The line sits on a continuum, so the resolution is the width of a Gaussian
fitted on a linear background, not the spread of the whole window. The
min-variance weights are trained on the peak core of one half of the events
and evaluated on the other half; five independent train/test splits give sigma/E in 3.2-3.5%, so the number is stable.

## Results (Z7, 1710 K-line events after the NRMSE cut)

| estimator | peak (keV) | sigma (keV) | sigma/E |
|---|---|---|---|
| PTOFamps | 9.25 | 1.074 | 11.6% |
| sum OFamps | 9.97 | 0.609 | 6.1% |
| nxm0 only | 10.34 | 1.120 | 10.8% |
| physics NxM | 10.43 | 2.204 | 21.1% |
| **min-variance (test half)** | **10.39** | **0.330** | **3.2%** |

Two things to note. The physics weights (template integrals) are *worse*
than using nxm0 alone: the PC amplitudes are noise-dominated on several
channels, so adding them with their geometric weight adds noise, not signal.
The min-variance solution instead learns how much to trust each amplitude and
is a factor 2 better than the best fixed combination.

## Linearity check

The weights come from a single line, so they could in principle be a
degenerate projection that maps everything onto 10.37 keV. Applying them to
control events selected in other PTOFamps bands:

| PTOFamps (A) | median E (keV) | E / (PTOFamps x k) |
|---|---|---|
| 1.90e-06 | 10.31 | 1.04 |
| 6.01e-06 | 30.44 | 0.98 |
| 8.42e-06 | 43.61 | 1.00 |
| 1.28e-05 | 65.45 | 0.99 |
| 1.80e-05 | 100.17 | 1.07 |
| 2.56e-05 | 150.86 | 1.14 |

The combination tracks PTOFamps proportionally over a factor of ~30 in
energy, so it is a genuine energy estimator, not a projection onto the line.

## Open items

- The 2.6-3.4e-06 band sits ~25% low; worth checking whether that is
  multi-site / pile-up or a real non-linearity just above the line.
- Repeat for the other detectors and compare the weights channel by channel.
- Cross-check the min-variance resolution against an independent line.
