#!/bin/bash
# Submit read_zip_all_series_v2.py for all 13 zips — fills gaps in the 126GB
# shared cache AND replaces the old fixed-pretrigger fit with a free-pretrigger
# fit (align-to-reference happens after the fit, not inside it). See
# CONTEXT_FOR_NEXT_AI.md sections 7-8 for full background.
#
# All 13 zips are submitted, including zip16 and zip7: even zips whose series
# COUNT is already complete still have the OLD fixed-pretrigger fit baked into
# their checkpoints and need the refit pass (read_zip_all_series_v2.py handles
# this automatically — it skips only series already tagged
# fit_method="free_pretrigger").
#
# Resource sizing (per user instruction 2026-06-30: "脚本的内存和时间要给足"):
#   - Single-series refit test (zip7, ~1850 traces, 11 channels, 442MB pkl on
#     disk) took ~6 min, peak RSS ~913MB (~2.07x the pkl file size — refit
#     temporarily holds the old payload's raw_traces+ana_traces+fit fields
#     AND the newly-built ana_traces/fit_params_ch alive at once before the
#     old ones are dropped).
#   - 126GB is the SUM across ~300 series files, not a single load — each job
#     only ever holds ONE series in memory at a time. So the number that
#     matters per zip is that zip's LARGEST single series pkl, not the zip
#     total. Checked directly (`find ... -printf '%s'`): zip18 has a 5205MB
#     outlier series, zip6 has a 3726MB one; every other zip tops out under
#     2150MB. Applying the ~2.07x ratio: zip18 ~10.8GB, zip6 ~7.7GB worst
#     case — 64gb for those two, 32gb for the rest, leaves 3-6x headroom
#     everywhere. Cluster nodes have 514GB RAM each (`sinfo -p agsmall`), so
#     this is cheap to be generous about.
#   - A full zip (~27-30 series) refit-only is estimated at roughly 3-5
#     hours; series that are genuine gaps (need rawio read) will be slower
#     still. 24h ceiling gives large headroom rather than risking a mid-run
#     timeout that wastes the SLURM allocation.
#   - Two prior real OOM kills on this cluster happened around ~5.8GB RSS in
#     an *interactive* cgroup-limited session — unrelated to SLURM's own
#     --mem accounting, but the same reason to not under-request here.
#   - Shared filesystem has 1.5PB free (`df -h` on /projects/standard), so
#     the cache growing from ~126GB towards ~250GB is not a storage concern.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)

# per-zip memory override for the two outlier zips with a huge single series
declare -A MEM_GB=( [6]=64 [18]=64 )

for DET in "${ZIPS[@]}"; do
    MEM="${MEM_GB[$DET]:-32}gb"
    sbatch --job-name="rv2_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem="${MEM}" \
           -t 24:00:00 \
           -o "${LOG_DIR}/rv2_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 ${SCRIPT_DIR}/read_zip_all_series_v2.py \
               --det ${DET}"
    echo "Submitted zip${DET} (mem=${MEM})"
done

echo "All submitted. Monitor with: squeue -u $USER | grep rv2_z"
echo "This writes DIRECTLY into the shared 126GB cache in place:"
echo "  /projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache/zip{N}_series/"
