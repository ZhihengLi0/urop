# SNOLAB Run 4 Phonon Pulse Analysis

Author: Zhiheng Li

Phonon pulse analysis of the CDMS SNOLAB Run 4 data (13 Ge detectors,
12 phonon channels each), in Prof. Yan Liu's SuperCDMS group at the
University of Minnesota. Two lines of work:

| Directory | Project |
|---|---|
| [`phonon_pulse_template_generation/`](phonon_pulse_template_generation) | **SNOLAB R4 Phonon Pulse Template Generation** — K-shell PTOFamps event selection, raw-trace cache, free-pretrigger 2-exp fitting with quality cuts, 1×1 and N×M (PCA) templates for all 13 detectors, deployed in the cdmsbats `PulseTemplates` ROOT format; per-event energy regression from the N×M amplitudes; the July 2026 group-meeting talk. |
| [`collection_efficiency/`](collection_efficiency) | **Phonon collection efficiency of Z7** — every K-line event fitted with a two-exponential, converted to power through the TES equations and integrated in closed form; summed over 10 channels the TESs absorb **30.5 %** of the 10.37 keV (σ/μ = 7.5 %); the September 2026 talk. |

Each directory is self-contained, with its own README, `scripts/`, and
versioned final results. Large caches (`run/`, `*.pkl`, `*.root` except the
deliverable templates) stay on MSI and are not tracked.
