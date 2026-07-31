# neural_network

Neural-network project for the CDMS SNOLAB Run 4 phonon data.

Per-event energy regressed from the NxM amplitudes: a linear least-squares fit
over the 55 amplitudes first, then a neural network on the same inputs and the
same loss. The purpose is to assign an energy to pulses the direct
fit-and-integrate method cannot handle. Full specification in `NOTES.md`.

## Layout

| path | holds |
|---|---|
| `scripts/` | training, evaluation and plotting code |
| `results/` | metrics, saved models metadata, small summary tables |
| `results/plots/` | figures |

## Conventions inherited from the repository

- one self-contained directory per algorithm, only final results kept;
- large artefacts (`run/`, `*.pkl`, `*.root`, checkpoints) stay out of git;
- anything that takes more than about ten minutes goes through SLURM, with a
  checkpoint cache so a killed job resumes instead of restarting.
