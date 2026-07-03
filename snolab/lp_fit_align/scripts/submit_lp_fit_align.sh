#!/bin/bash
# Submit one Slurm job per zip for the LP + free-pretrigger fit + shift-align
# pipeline (lp_fit_align.py). Only run on zips whose raw PTOF cache is complete.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$SCRIPT_DIR/../run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

if [ "$#" -gt 0 ]; then
    ZIPS=("$@")
else
    ZIPS=(1 18 22)
fi

MEM="${MEM:-100gb}"
TIME_LIMIT="${TIME_LIMIT:-48:00:00}"

for DET in "${ZIPS[@]}"; do
    sbatch --job-name="lpfit_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=12 \
           --mem="${MEM}" \
           -t "${TIME_LIMIT}" \
           -o "${LOG_DIR}/lpfit_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 -u ${SCRIPT_DIR}/lp_fit_align.py --det ${DET}"
    echo "Submitted zip${DET} lp_fit_align (mem=${MEM}, time=${TIME_LIMIT})"
done

echo "Monitor with:"
echo "  squeue -u $USER | grep lpfit"
