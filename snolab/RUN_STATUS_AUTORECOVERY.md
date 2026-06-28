# SNOLAB Run Status and Auto-Recovery Handoff

Date written: 2026-06-27

## Current goal

We are running long SNOLAB R4 diagnostic jobs and need complete outputs without
losing progress to SLURM time limits.

Primary outputs wanted:

- `debug/run/all_zips_event_stats.tsv`
- `debug/run/all_zips_summary.txt`
- `raw_without_filter/run/cache/zip{det}_all_series.pkl`
- `raw_without_filter/run/plots/zip{det}_all_channels_raw_vs_ana.png`
- `raw_without_filter/run/plots/zip{det}_summary.txt`

## Jobs running when auto-recovery was attached

Original running jobs:

- `12019812` `scan_all_zips`
- `12018017` `raw_wf_z1`
- `12018018` `raw_wf_z4`
- `12016292` `raw_wf_z6`
- `12018019` `raw_wf_z7`
- `12018020` `raw_wf_z9`
- `12018021` `raw_wf_z10`
- `12018022` `raw_wf_z13`
- `12018023` `raw_wf_z15`
- `12016300` `raw_wf_z19`
- `12016301` `raw_wf_z22`
- `12016302` `raw_wf_z24`

Auto-rescue jobs submitted with `afternotok` dependencies. The raw rescue jobs
were later re-submitted with `256g` memory after the audit, replacing the first
`128g` raw rescue batch:

- `12061390` `scan_rescue`
- `12062520` `raw_rescue_z1`
- `12062521` `raw_rescue_z4`
- `12062522` `raw_rescue_z6`
- `12062523` `raw_rescue_z7`
- `12062524` `raw_rescue_z9`
- `12062525` `raw_rescue_z10`
- `12062526` `raw_rescue_z13`
- `12062527` `raw_rescue_z15`
- `12062530` `raw_rescue_z19`
- `12062531` `raw_rescue_z22`
- `12062532` `raw_rescue_z24`

These rescue jobs are pending with reason `(Dependency)`. They should only run
if the corresponding original job fails, is cancelled, or hits the time limit.
If the original job completes successfully, SLURM should not run the rescue job.

## Code changes made

### `debug/scripts/scan_all_data.py`

The scan script now supports resume by default.

Resume behavior:

- Reads `debug/run/scan.log`.
- Detects series that have a completed log line:
  `events found in raw: ... rows written: ...`
- Before appending, compacts `debug/run/all_zips_event_stats.tsv`:
  - keeps rows for completed series;
  - drops rows for partial or unfinished series.
- Skips completed series and reruns only unfinished series.
- Rebuilds `all_zips_summary.txt` from the full TSV after resume, so the summary
  is full-run, not just the last rescue segment.

Important environment variable:

- `SCAN_RESUME=1` enables resume. This is the default.
- `SCAN_RESUME=0` forces a fresh write.

### `raw_without_filter/scripts/read_zip_all_series.py`

The raw diagnostic script now writes per-series checkpoints.

Checkpoint behavior:

- For detector `det`, checkpoints are under:
  `raw_without_filter/run/cache/zip{det}_series/{series}.pkl`
- Each completed series is saved atomically via `.tmp` then `os.replace`.
- On rerun, existing per-series checkpoints are loaded and skipped.
- At the end, the script merges all loaded/new per-series payloads into:
  `raw_without_filter/run/cache/zip{det}_all_series.pkl`
- It then writes the combined plot and text summary.

New CLI options:

- `--series SERIES ...`
- `--series-from SERIES`
- `--series-after SERIES`

### Rescue wrapper scripts

Added:

- `debug/scripts/run_scan_rescue.sh`
- `raw_without_filter/scripts/run_raw_rescue.sh`
- `scripts/submit_autorescue_current.sh`
- `debug/scripts/submit_scan_resume.sh`
- `raw_without_filter/scripts/submit_read_tail.sh`

`run_scan_rescue.sh` and `run_raw_rescue.sh` pre-submit one follow-up rescue job
for themselves using `afternotok:${SLURM_JOB_ID}`. This creates a chained rescue
path up to `MAX_RESCUE_DEPTH=4`.

If a rescue job succeeds, the follow-up remains dependency-blocked and should
not run. If a rescue job fails or times out, the follow-up starts automatically.

## Validation already done

The following checks passed:

```bash
python3 -m py_compile debug/scripts/scan_all_data.py raw_without_filter/scripts/read_zip_all_series.py
bash -n debug/scripts/run_scan_rescue.sh raw_without_filter/scripts/run_raw_rescue.sh scripts/submit_autorescue_current.sh debug/scripts/submit_scan_resume.sh raw_without_filter/scripts/submit_read_tail.sh
```

Queue was checked after re-submission and showed the new rescue jobs pending on
dependencies while originals were still running.

## How to check status next time

Run:

```bash
squeue -u li004628 -o '%.18i %.24j %.10T %.10M %.32R'
```

Check scan progress:

```bash
tail -n 80 debug/run/scan.log
wc -l debug/run/all_zips_event_stats.tsv
ls -lh debug/run/all_zips_event_stats.tsv debug/run/all_zips_summary.txt
```

Check raw outputs:

```bash
find raw_without_filter/run/cache -maxdepth 2 -type f | sort
find raw_without_filter/run/plots -maxdepth 1 -type f | sort
tail -n 30 raw_without_filter/run/logs/read*.out
tail -n 30 raw_without_filter/run/logs/read_rescue*.out
```

## Completion criteria

Scan is complete when:

- `squeue` has no running/pending `scan_all_zips` or `scan_rescue*` jobs.
- `debug/run/scan.log` shows `TSV complete`.
- `debug/run/all_zips_summary.txt` exists and is newer than the final TSV update.

Raw diagnostics are complete when, for all expected zips
`1 4 6 7 9 10 13 15 16 18 19 22 24`:

- `raw_without_filter/run/cache/zip{det}_all_series.pkl` exists.
- `raw_without_filter/run/plots/zip{det}_all_channels_raw_vs_ana.png` exists.
- `raw_without_filter/run/plots/zip{det}_summary.txt` exists.
- There are no active `raw_wf_z*` or `raw_rescue*` jobs.

Zips `16` and `18` had older failed logs from before this handoff and were not
running when the first auto-rescue pass was attached. They are now running as
immediate `256g` chained rescue jobs:

- `12062528` `raw_rescue_z16`
- `12062529` `raw_rescue_z18`

Older duplicate `zip16/zip18` rescue jobs from the first pass were cancelled:
`12062370`, `12062371`, `12062460`, `12062461`.

## Update — 2026-06-27 (second session)

### Scan pipeline OOM issue and fix

All four auto-rescue scan jobs (scan_rescue2 through scan_rescue4) failed with
OUT_OF_MEMORY (exit code 0:125) at the same point: series `24260619_230219`
(series 16/30), which selects 6458 total events across all zips — ~10x a typical
series. The jobs were each requesting 192GB, which was exactly the limit hit.

Fix:
- Updated `debug/scripts/run_scan_rescue.sh` to request `--mem=256g` and
  `--time=48:00:00` for all future rescue jobs in the chain.
- Manually submitted a new rescue job `scan_rescue5` (job 12095921) with
  `SCAN_RESUME=1`, 256GB, 48h on agsmall.
- A pre-submitted follow-up `scan_rescue2` (job 12095902) is already pending
  with `afternotok:12095921` in case 256GB is still not enough.

TSV state at time of fix:
- 683,501 rows (header + 683,500 data rows)
- 15/30 series complete; scan_rescue5 resumes from series 16

Also deleted duplicate status file `~/urop/snolab/PROJECT_STATUS.md`
(this file is the canonical handoff document).

### raw_without_filter pipeline — current progress

As of ~23:00 on 2026-06-27:
- All 13 zips running (raw_rescue depth 1)
- Zip 16 (job 12062528): 20/30 series done, running ~12.5h
- Zip 18 (job 12062529): 6/23 series done, running ~12.5h — heaviest zip,
  each series ~100 min; expected to need rescue depth 2-3
- rescue2 jobs for all zips pre-submitted, will fire automatically on failure

### Completion check commands

```bash
# Scan TSV progress
wc -l ~/urop/snolab/debug/run/all_zips_event_stats.tsv
tail -20 ~/urop/snolab/debug/run/scan_rescue5_12095921.out

# Queue status
squeue -u li004628 -o '%.18i %.24j %.10T %.10M %.32R'

# Failed jobs today
sacct -u li004628 --starttime=2026-06-27T00:00:00 \
  --format=JobID,JobName,State,ExitCode --noheader | grep -v "RUNNING\|PENDING\|extern\|batch"
```

## Important caveat

The original raw jobs were already running before checkpoint support was added.
If one of those original jobs fails, its first rescue may have to process that
zip from the beginning. From the rescue job onward, per-series checkpoints prevent
loss of completed series.

This setup protects against time-limit loss. It cannot automatically fix a
permanent data corruption, rawio bug, or cluster-level failure that repeatedly
prevents a specific series from being read.
