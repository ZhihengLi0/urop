# neural_network

Per-event energy regressed from the NxM amplitudes: a linear least-squares fit
over the 55 amplitudes first, then a neural network on the same inputs and the
same loss. The purpose is to assign an energy to pulses the direct
fit-and-integrate method cannot handle. Full specification in `NOTES.md`.

## Run

```bash
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
BIND="$HOME,/projects/standard/yanliusp/shared/"
singularity exec -B "$BIND" $SIF python3 scripts/build_dataset.py --det 7
singularity exec -B "$BIND" $SIF python3 scripts/linear_fit.py  --det 7
singularity exec -B "$BIND" $SIF python3 scripts/mlp_fit.py     --det 7
```

## What goes in and what comes out

| | |
|---|---|
| input | the 55 NxM amplitudes of one event, 11 channels x 5 templates |
| target | that event's own absorbed energy: each channel's two-exponential fit integrated in closed form, summed over the 10 channels whose fit acceptance is above 90% |
| model | one coefficient vector per detector, `E = c . S`, least squares |
| split | half the events fitted, half held back and reported on |

The target is the energy of the individual event, **not** the nominal 10.37 keV
of the line: events are spread across the whole Gaussian and each carries its own
value.

## Stage 1, the linear fit

| model | test core width | test RMS |
|---|---|---|
| **55 amplitudes** | **72.2 eV = 2.28%** | 120.7 eV |
| best single scaling of the template-0 sum | 234.8 eV = 7.43% | 363.0 eV |
| best single scaling of the sum of all 55 | 442.8 eV = 14.01% | 611.1 eV |

The 55 coefficients cut the width by 69%. The target's own core width is 6.92%,
so the amplitudes explain 89% of the event-to-event variance.

Both a root-mean-square and a 2-sigma-clipped core width are quoted throughout,
because the RMS alone is misleading here: on the first run the test RMS was 213 eV
against a core of 82 eV, and the whole difference was two pathological events.

## Checks that were run

- the train and test halves are disjoint and cover every event;
- `lstsq` agrees with solving the normal equations `(S'S)c = S'E` directly to
  5e-13, so what is reported really is the closed-form minimum;
- five different random splits give test core widths of 2.18 to 2.34%, and the
  coefficient vectors correlate at 0.94 or better across them. The individual
  coefficients scatter by about 20%, which is expected with correlated inputs:
  the prediction is what is stable, not each coefficient;
- train and test core widths agree to 1.2%, against 0.93 expected for
  55 parameters on 806 events, so nothing is being fitted to noise. Condition
  number of the training matrix: 209.

## The late-pulse events

Seven events are cut on the fitted pulse start `t0`. Their pulses arrive 1 to
2 ms after the trigger, so our fit finds them using its 4.8 ms of pretrigger
freedom while the NxM amplitudes, measured in the standard window, see nothing:
input and target then describe different things. Two of them were the entire
reason the first run's test RMS looked bad, predicting 62 eV for a true 3998 eV
event and 347 eV for a true 3021 eV one.

Adding the 11 per-channel delays as inputs, the 66 = 55 + 11 of the whiteboard,
is what would let these events back in.

## Stage 2, the network

`scripts/mlp_fit.py`. Same inputs, same squared-error loss, and the split of
stage 1 reused so the comparison is like for like. Inputs and target are
standardised on the training half only, since a network cannot train on
amplitudes of order 1e-7. Architecture and regularisation are chosen on a
validation split taken out of the **training** half, and the test half is touched
exactly once at the end. The whiteboard's hidden layer of order 1000 is 56000
weights for 806 training events, so the scan also includes smaller networks and
several regularisation strengths and lets the validation score decide.

Three models are compared on the same test half:

| model | test core width |
|---|---|
| linear, 55 coefficients | 72.2 eV = 2.28% |
| network on the amplitudes | 72.4 eV = 2.29% |
| linear + network on the residual | 69.4 eV = 2.20% |

**The network does not beat the linear model.** The hybrid is 3.9% narrower, and
the linear model itself moves by about 3.5% between random splits, so that is not
a result.

The first attempt left early stopping off and the network memorised the training
half: train core 3.5 eV against test 97 eV, worse than linear. With early
stopping it is 44.9 against 72.4, healthy but no better.

The reason is measured, not guessed. **The target is itself a measurement.** The
fit-based and official-window energies of the same events disagree by a core
width of 62.0 eV, 1.96%, so each carries at least about 1.4% of noise. A residual
of 2.28% is therefore already close to what the target can resolve, and that caps
what any model can gain. Going further needs a better target or more events, not
a bigger network:

- more events, by adding the other twelve detectors or the control events at
  other energies;
- a better target, by making PDS2 fittable so the sum uses all eleven channels;
- the 66-input version with the delays, which would also readmit the late pulses.

## Layout

| path | holds |
|---|---|
| `scripts/` | dataset building, the linear fit, the network |
| `results/` | dataset, coefficients, metrics |
| `results/plots/` | figures |
| `项目.jpg` | the whiteboard photo the specification came from |
