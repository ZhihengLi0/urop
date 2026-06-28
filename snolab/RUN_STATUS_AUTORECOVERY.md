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

---

## Update — 2026-06-28 (third session)

### Scan pipeline — chain exhausted, memory raised to 384 GB

By the morning of 2026-06-28 the entire scan rescue chain (rescue2–rescue5,
jobs 12065602, 12073791, 12077680, 12095921, 12095950, 12109836, 12115240)
had all failed with OUT_OF_MEMORY (exit 0:125). No scan jobs were running or
pending — the chain was completely dead.

Root cause: the OOM is NOT from the large series 16 (24260619_230219, 6458
events) — that series completed successfully at some point. The new OOM trigger
is series 21 (24260621_111527, 735 events, 19 raw MIDAS files). The process is
killed immediately after "Found 19 midas raw data files", before reading any
events. This suggests the raw MIDAS files for this series are individually very
large, and 256 GB is not enough headroom to load them.

State at time of intervention:
- `debug/run/all_zips_event_stats.tsv`: 922,501 rows (header + 922,500 data)
- `debug/run/scan.log`: 20/30 series complete (series 1–20)
- Series 21–30 remain; resume will pick up from series 21 automatically

Fix applied:
- Edited `debug/scripts/run_scan_rescue.sh`: changed follow-up job memory
  from `--mem=256g` to `--mem=384g`. Future auto-rescue jobs in the chain
  will now request 384 GB.
- Manually submitted `scan_rescue5` (job **12132314**) with `--mem=384g`,
  `--time=48:00:00`, `SCAN_RESUME=1`, `RESCUE_DEPTH=1`, `MAX_RESCUE_DEPTH=4`.
  This job will resume from series 21 and pre-submit a rescue chain (up to
  depth 4) at 384 GB each.

The agsmall nodes have ~514 GB physical RAM, so 384 GB is safely within limit.
If 384 GB still OOMs on a future series, the next step is 480 GB.

### Scan — how resume works (for the next AI)

The scan script (`debug/scripts/scan_all_data.py`) resumes by:
1. Reading `debug/run/scan.log` and collecting all series with a completed
   "events found in raw: ... rows written: ..." line.
2. Compacting the TSV: keeps rows only for completed series, drops partial
   rows. This prevents double-counting on resume.
3. Skipping completed series in the main loop.
4. After the main loop, rebuilding the full summary accumulator by re-reading
   the entire TSV from disk (lines 726–754 of scan_all_data.py). This is
   memory-intensive but only runs at the very end.

`SCAN_RESUME=1` is the default. Never set `SCAN_RESUME=0` unless you want to
wipe all progress and restart from scratch.

The final output files are:
- `debug/run/all_zips_event_stats.tsv` — one row per event per channel
- `debug/run/all_zips_summary.txt` — aggregate statistics; written last

Scan is complete when `scan.log` contains "TSV complete" AND
`all_zips_summary.txt` exists and is newer than the TSV.

### raw_without_filter pipeline — current state (2026-06-28 ~17:30)

All 13 zips are at rescue depth 2 (raw_rescue2_z*), running on agsmall with a
16-hour time limit. Per-series checkpoints are in place for all rescue-depth
jobs; if a job times out, the pre-submitted raw_rescue3 (all 12 pending with
Dependency) will fire and resume from the last completed series checkpoint.

Checkpoint location: `raw_without_filter/run/cache/zip{det}_series/{series}.pkl`
Merged output:       `raw_without_filter/run/cache/zip{det}_all_series.pkl`

Only zip16 has a merged pkl (it completed earlier). The other 12 zips will get
their merged pkl written automatically when their rescue job finishes all series.

Series counts completed as of this session (from per-series checkpoint files):

| zip | checkpoints | merged pkl |
|-----|-------------|------------|
|  1  |     16      |    no      |
|  4  |      7      |    no      |
|  6  |     17      |    no      |
|  7  |     26      |    no      |
|  9  |     25      |    no      |
| 10  |     22      |    no      |
| 13  |     22      |    no      |
| 15  |     16      |    no      |
| 16  |     30      |  **YES**   |
| 18  |      8      |    no      |
| 19  |     10      |    no      |
| 22  |     10      |    no      |
| 24  |      8      |    no      |

Zip18 is the highest-risk zip: it is the heaviest (23 series, each ~100 min),
has only 8 checkpoints done, and its raw_rescue2 job (12062549) had already
been running 8h42m at time of check — leaving ~7h before the 16h timeout.
raw_rescue3_z18 (12109827) is pre-queued and will fire automatically.

### How to check status (updated commands)

```bash
# Scan: is it running? what series?
squeue -u li004628 -o '%.18i %.24j %.10T %.10M %.32R' | grep -i scan

# Scan: how many series done?
grep "rows written:" ~/urop/snolab/debug/run/scan.log | wc -l
tail -30 ~/urop/snolab/debug/run/scan.log

# Scan: TSV size
wc -l ~/urop/snolab/debug/run/all_zips_event_stats.tsv

# Scan: latest rescue output (replace JOBID)
ls -lt ~/urop/snolab/debug/run/scan_rescue*.out | head -3
tail -40 ~/urop/snolab/debug/run/scan_rescue5_12132314.out

# Raw: checkpoint counts per zip
for det in 1 4 6 7 9 10 13 15 16 18 19 22 24; do
  n=$(find ~/urop/snolab/raw_without_filter/run/cache/zip${det}_series \
      -name "*.pkl" 2>/dev/null | wc -l)
  merged=$([ -f ~/urop/snolab/raw_without_filter/run/cache/zip${det}_all_series.pkl ] \
      && echo "MERGED" || echo "-")
  echo "zip${det}: ${n} series checkpoints  ${merged}"
done

# Queue: all jobs
squeue -u li004628 -o '%.18i %.24j %.10T %.10M %.32R'

# Failed/OOM jobs
sacct -u li004628 --starttime=today \
  --format=JobID,JobName,State,ExitCode,Elapsed --noheader \
  | grep -v "RUNNING\|PENDING\|extern\|batch\|COMPLETED"
```

### Changes made in this session (2026-06-28)

**`raw_without_filter/scripts/run_raw_rescue.sh`** — rewritten:
- `MAX_RESCUE_DEPTH` default raised from 4 → 6 (chain now goes rescue2…rescue6)
- Removed `exec` so code runs after the main python script exits
- SIGTERM trap (`_on_timeout`): when SLURM sends SIGTERM ~60s before the
  time limit, bash catches it, immediately runs `finalize_zip.py --det $DET`
  inside singularity, then exits 1 so the pre-submitted follow-up rescue fires
- Post-main finalize: even on normal or error exit, `finalize_zip.py` is
  called unconditionally so the merged pkl is always up to date
- Effect: after EVERY job exit (success / timeout / python error), the merged
  pkl `zip{det}_all_series.pkl` is rebuilt from all completed checkpoints

**`raw_without_filter/scripts/finalize_zip.py`** — new script:
- Reads all `zip{det}_series/{series}.pkl` checkpoints, merges them, and
  writes `zip{det}_all_series.pkl`, the plot png, and `zip{det}_summary.txt`
- Accepts `--det DET`, `--all` (all 13 zips), `--dry-run`
- Does NOT need rawio — runs in any env with numpy + matplotlib, or inside
  singularity for consistency
- Use this to force-produce final outputs at any time:
  ```bash
  # Inside singularity:
  IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
  singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
      python3 ~/urop/snolab/raw_without_filter/scripts/finalize_zip.py --all
  ```

**rescue3 jobs resubmitted** — all 12 old rescue3 jobs (MAX_DEPTH=4) were
cancelled and resubmitted with `MAX_RESCUE_DEPTH=6` and the same `afternotok`
dependencies on their rescue2 parents.

### What the next AI should do

1. Run the status commands above to assess current state.
2. **Scan**: if no scan job is running or pending, check `scan.log` for how
   many series are done. If fewer than 30, submit a new rescue job manually:
   ```bash
   ROOT_DIR="$HOME/urop/snolab/debug"
   RUN_DIR="$ROOT_DIR/run"
   jid=$(sbatch --parsable \
       --job-name="scan_rescue5" \
       --time=48:00:00 --ntasks=1 --mem=384g --partition=agsmall \
       --output="$RUN_DIR/scan_rescue5_%j.out" \
       --export="ALL,SCAN_RUN_DIR=$RUN_DIR,SCAN_RESUME=1,RESCUE_DEPTH=1,MAX_RESCUE_DEPTH=4" \
       --wrap="bash $ROOT_DIR/scripts/run_scan_rescue.sh")
   echo "Submitted: $jid"
   ```
   If it OOMs again, try `--mem=480g`.
3. **Raw**: if a zip's rescue chain is exhausted (raw_rescue3 already ran and
   failed, no rescue4 pending), submit a new job manually:
   ```bash
   det=18   # example
   ROOT_DIR="$HOME/urop/snolab/raw_without_filter"
   RUN_DIR="$ROOT_DIR/run"
   jid=$(sbatch --parsable \
       --job-name="raw_rescue4_z${det}" \
       --time=16:00:00 --ntasks=1 --mem=256g --partition=agsmall \
       --output="$RUN_DIR/logs/read_rescue4_z${det}_%j.out" \
       --export="ALL,RAW_WF_RUN_DIR=$RUN_DIR,RESCUE_DEPTH=4,MAX_RESCUE_DEPTH=4" \
       --wrap="bash $ROOT_DIR/scripts/run_raw_rescue.sh $det")
   echo "Submitted: $jid"
   ```
4. **Final merge check**: once all raw jobs complete and all zips have a
   merged pkl, and scan shows "TSV complete" in scan.log, both pipelines are
   done. No extra merge script is needed — the outputs are already the final
   combined files.
