# neural_network

Neural-network project for the CDMS SNOLAB Run 4 phonon data.

Specification pending: this README, the scripts and the results are filled in as
the goal, the inputs and the training target are defined.

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
