#!/bin/bash
# Submit template_from_pkl.py for all zips.
# Reads directly from 126G pkl cache — no rawio, much faster (~15-30 min/zip).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

NRMSE_MAX="${NRMSE_MAX:-0.15}"
NOISE_PCTILE="${NOISE_PCTILE:-75}"

ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)

for DET in "${ZIPS[@]}"; do
    sbatch --job-name="pkl_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem=24gb \
           -t 1:00:00 \
           -o "${LOG_DIR}/pkl_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 ${SCRIPT_DIR}/template_from_pkl.py \
               --det ${DET} \
               --nrmse-max ${NRMSE_MAX} \
               --noise-pctile ${NOISE_PCTILE}"
    echo "Submitted zip${DET}"
done

echo "All submitted. Monitor with: squeue -u $USER | grep pkl_z"
