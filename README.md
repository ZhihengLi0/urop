# SuperCDMS UROP Research Code

Analysis code and documentation from my undergraduate research (UROP Fellowship)
in Prof. Yan Liu's SuperCDMS group, School of Physics & Astronomy,
University of Minnesota — Twin Cities.

| Directory | Project |
|---|---|
| [`snolab_run4_phonon_pulse_analysis/`](snolab_run4_phonon_pulse_analysis) | **SNOLAB Run 4 phonon pulse analysis** — two lines of work: **pulse template generation** (K-shell event selection, raw-trace cache, free-pretrigger 2-exp fitting with quality cuts, 1×1 and PCA N×M templates for all 13 Ge detectors in the cdmsbats PulseTemplates format) and the **Z7 phonon collection efficiency** (per-event two-exponential fits converted to power through the TES equations, 30.5 % over 10 channels). See [snolab_run4_phonon_pulse_analysis/README.md](snolab_run4_phonon_pulse_analysis/README.md) |
| [`LED/`](LED) | **LED calibration & glitch event analysis pipeline** (CUTE R37 run) — pulse selection/alignment, glitch identification, exponential fitting, ML exploration. See [LED/README.md](LED/README.md) |
| [`RuOx/`](RuOx) | **RuOx thermometer calibration curve extension** to the full 5 mK – 300 K range of the BlueFors dilution refrigerator, producing controller-loadable Lake Shore `.340` files. See [RuOx/README.md](RuOx/README.md) |
| [`database/`](database) | **BlueFors CS2 control-system database documentation** — background and table-by-table structure of the PostgreSQL monitoring database |

## Related repositories

- [cdms_spotlight](https://github.com/ZhihengLi0/cdms_spotlight) — natural-language series selection & query system for the SuperCDMS DQM database (Slack bot + CLI)
- [column_monitor](https://github.com/ZhihengLi0/column_monitor) — BlueFors fridge real-time monitoring & Slack alert system

---

More about me: [zhihengli0.github.io](https://zhihengli0.github.io)
