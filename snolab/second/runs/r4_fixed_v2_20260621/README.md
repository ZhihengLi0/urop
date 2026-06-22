# SNOLAB R4 fixed-v2 run

This directory contains an isolated rerun of the R4 template pipeline using the
`scdms-V07-02` software environment. It preserves the existing caches, ROOT
files, plots, and logs outside this directory.

Changes under validation:

- use the processed RQ baseline with a raw pre-trigger fallback;
- reject aligned traces whose positive peak is outside the physical window;
- locate the pulse onset from the steepest smoothed leading edge;
- retain 4-, 3-, and 2-exponential fits while enforcing decay times longer
  than the rise time;
- constrain baseline and pretrigger and reject nonphysical converged fits;
- build PF only when all available detector channels are present.

Subdirectories `cache/`, `root_files/`, `template_plots/`, and `slurm_logs/`
are populated by the SLURM jobs. The versioned entry points are
`scripts/template_single_zip_fixed_v2.py` and
`scripts/plot_templates_fixed_v2.py`.
