# SNOLAB template generation — fifth iteration

This directory is the fifth template-generation iteration for SNOLAB Run 4.

Key NxM settings:

- CDMS environment: `scdms-V07` / `cdmsfull_V07-02-00.sif`
- fixed first-pretrigger sample: `16250`
- reject a normalized input trace before NxM fitting when its negative
  excursion exceeds 5% of its positive peak (`min(trace) < -0.05`)
- generate both agnostic and channel-specific PCA templates

Submit all ZIP jobs with:

```bash
bash scripts/submit_v5.sh
```

Outputs are created under `run/r4_v5_YYYYMMDD/`. Fourth-iteration caches and
ROOT/plot outputs are intentionally not copied into this directory.
