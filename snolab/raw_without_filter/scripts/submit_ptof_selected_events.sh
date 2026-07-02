#!/bin/bash
# Submit one Slurm job per zip to save raw traces for PTOFamps-selected events.
# This does not fit, filter, normalize, align, or require all channels.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"
CACHE_DIR="/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache"

if [ "$#" -gt 0 ]; then
    ZIPS=("$@")
else
    ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)
fi

MEM="${MEM:-150gb}"
TIME_LIMIT="${TIME_LIMIT:-30:00:00}"

for DET in "${ZIPS[@]}"; do
    sbatch --job-name="ptofraw_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem="${MEM}" \
           -t "${TIME_LIMIT}" \
           -o "${LOG_DIR}/ptofraw_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 -u ${SCRIPT_DIR}/read_ptof_selected_events.py \
               --det ${DET} \
               --cache-dir ${CACHE_DIR}"
    echo "Submitted zip${DET} PTOF-selected raw cache (mem=${MEM}, time=${TIME_LIMIT})"
done

echo "Monitor with:"
echo "  squeue -u $USER | grep ptofraw"
