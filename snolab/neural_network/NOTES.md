# Energy from the NxM amplitudes: linear fit first, then a network

## Goal

Learn a per-event map from the NxM amplitudes to the event energy, so that an
energy can be assigned to pulses the direct method cannot handle: small pulses,
noisy pulses, pulses whose two-exponential fit fails. Once the map is trusted it
is used as a known relation, and other populations are traced back through it.

Accuracy is the whole point of the exercise, so every step is checked before the
next one is built.

## Inputs

For one detector, the NxM amplitudes of one event:

    Z7: 11 usable channels x 5 templates = 55 amplitudes
        (PFS2 has no data; a detector with a different channel count gets a
         different number, and every detector is fitted separately)

The whiteboard also writes 66 = 55 + 11, the 11 per-channel delays, as an input
set to try once 55 works.

## Model, stage 1: linear

    E_pred(event) = c_1 * amp(ch 1, template 0) + c_2 * amp(ch 1, template 1)
                  + ... + c_5  * amp(ch 1, template 4)
                  + c_6 * amp(ch 2, template 0) + ...
                  + c_55 * amp(ch 11, template 4)
                  = c . S      with c = [c_1 ... c_55], S the amplitude vector

One coefficient vector per detector, shared by all its events. Fitted by least
squares over the training events:

    minimise  sum_events [ E_pred(c) - E_true ]^2         (squared so that
                                                           over- and under-shoots
                                                           cannot cancel)
    i.e.      d/dc sum_events [ E_pred(c) - E_true ]^2 = 0

## Training target

Every K-line event of the Gaussian is used, not only the events sitting at its
centre: each event carries its own energy, which is known per event rather than
being the nominal line value. The target is therefore **not** the constant
10.37 keV.

## Event selection

Start where the data is cleanest and widen later: a good detector (Z7), good
events, low noise. Half the events train, half test, e.g. 1000 and 1000 out of
the roughly 1900 K-line events per channel on Z7. The test half is never used
for fitting.

## Model, stage 2: the network

With the linear solution in hand as the baseline to beat, the same inputs and the
same loss go into a neural network trained by backpropagation, which is free to
find a nonlinear combination. The whiteboard sketch is 55 (or 66) inputs, a
hidden layer of order 1000, and a single output, the energy; the depth is open.

## What the result is judged on

The reconstructed energy against the true energy: a calibration curve of E_reco
versus E_true, plus the width of the residual. The linear estimator already in
the repository is the number to beat.

## Error budget, settled before this project starts

The three power formulas differ by less than 1% on K-line pulses (method 1 is
+0.58% against the exact expansion, method 2 is -1.15%), so the choice of formula
is **not** the dominant error and **method 1 is used throughout**. The dominant
width in the energy histogram comes from the detector itself, which is what this
project is meant to model.

## Background already established

- collection efficiency = summed energy over all channels of a detector divided
  by the event energy; for Z7 it is 32 +- 1%;
- the per-event energies come from the two-exponential fit and the closed-form
  power integral, cached in `differentialequations/run/fit_cache`;
- the single-channel energy spread is 15 to 27% and falls to 7.5% once the
  channels are summed, because most of the single-channel spread is event
  position rather than noise.

## Open question, to settle before writing code

What exactly is `E_true` in the loss?

1. **the per-event absorbed energy** computed by the power method (sum over the
   channels of that event). The network then reproduces a physics estimator
   cheaply and works where the fit fails, which matches the stated purpose. Its
   ceiling is the accuracy of that estimator, and it inherits its noise.
2. **the deposited energy, 10.37 keV for every K-line event.** The fit then
   pushes every event onto one value and the figure of merit is the residual
   width, which is the classical energy-estimator problem; the repository's
   minimum-variance combination already reaches 3.2% this way.

The description points at 1, since the target is said to differ from 10.37 keV
event by event. The two give different training data and different figures of
merit, so it is fixed first.
