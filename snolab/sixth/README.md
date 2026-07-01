# SNOLAB template generation — sixth iteration

This directory is an independent sixth iteration for SNOLAB Run 4.

Core method:

- `scdms-V07` / `cdmsfull_V07-02-00.sif`
- causal fourth-order 4 kHz Butterworth low-pass after alignment and before all
  1x1/NxM fits
- nonlinear fits use every fourth sample (156.25 kHz effective fit rate), while
  written templates retain the full 625 kHz / 32768-sample representation
- reject a 4 kHz-filtered event when its post-peak tail has an undershoot deeper
  than 5% of that event's positive peak; pretrigger noise is not misclassified
  as a pulse undershoot
- constrained two- or three-exponential selection for 1x1 templates; boundary
  solutions are rejected
- waveform-defined 10–90% rise and peak-to-1/e fall comparisons
- reference-notebook-style two-exponential fits for each NxM event
- event amplitude preserved (no per-trace normalization), baseline zero, and
  first pretrigger fixed at sample `16250`; only final ROOT templates are
  normalized to unit peak
- centered PCA is fit to the event-level two-exponential waveforms; `nxm0` is
  the mean pulse and `nxm1`–`nxm4` are physical, non-negative pulses obtained
  by moving from the mean along the first four PCA directions

This keeps PCA as required while avoiding the fifth iteration's mistake of
using centered `PCA.components_[0]` directly as a physical pulse template.

Submit with:

```bash
bash scripts/submit_v6.sh
```

Outputs are written below `run/r4_v6_YYYYMMDD/`.
