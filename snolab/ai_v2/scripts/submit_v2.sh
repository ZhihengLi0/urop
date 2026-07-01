#!/bin/bash
# Submit template_from_pkl_v2.py for all zips.
# v2 changes: fit_ok + NRMSE<=0.15 kept, no noise p75, NxM = PCA components (teacher's method)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

# Skip zip7 — teacher confirmed it's fine with v1 results
ZIPS=(1 4 6 9 10 13 15 16 18 19 22 24)

for DET in "${ZIPS[@]}"; do
    sbatch --job-name="v2_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem=24gb \
           -t 1:00:00 \
           -o "${LOG_DIR}/v2_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 ${SCRIPT_DIR}/template_from_pkl_v2.py \
               --det ${DET}"
    echo "Submitted zip${DET}"
done

echo "All submitted. Monitor with: squeue -u $USER | grep v2_z"
