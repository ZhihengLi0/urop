#!/bin/bash
# Submit one automatic rescue job for each currently queued/running ptofraw_z*
# job. The rescue job starts only if the primary job fails, times out, or is
# otherwise completed unsuccessfully. If the primary job succeeds, Slurm will
# not run the rescue job.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"
CACHE_DIR="/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache"
MEM="${MEM:-150gb}"
TIME_LIMIT="${TIME_LIMIT:-30:00:00}"

mapfile -t JOBS < <(squeue -u "$USER" -h -o "%i %j" | awk '$2 ~ /^ptofraw_z[0-9]+$/ {print $1, $2}')

if [ "${#JOBS[@]}" -eq 0 ]; then
    echo "No current ptofraw_z* jobs found."
    exit 0
fi

for ROW in "${JOBS[@]}"; do
    JOB_ID="$(awk '{print $1}' <<< "$ROW")"
    JOB_NAME="$(awk '{print $2}' <<< "$ROW")"
    DET="${JOB_NAME#ptofraw_z}"

    sbatch --job-name="ptofrescue_z${DET}" \
           --dependency="afternotok:${JOB_ID}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem="${MEM}" \
           -t "${TIME_LIMIT}" \
           -o "${LOG_DIR}/ptofrescue_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 -u ${SCRIPT_DIR}/read_ptof_selected_events.py \
               --det ${DET} \
               --cache-dir ${CACHE_DIR}"
    echo "Submitted automatic rescue for zip${DET} after failed job ${JOB_ID}"
done

echo "Monitor with:"
echo "  squeue -u $USER | grep -E 'ptofraw|ptofrescue'"
