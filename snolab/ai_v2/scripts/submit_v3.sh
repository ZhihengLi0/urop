#!/bin/bash
# Submit template_from_pkl_v3.py for all zips.
# v3: refits from cached raw_traces (126GB cache, raw_without_filter) with a
# FREE pretrigger (was pinned in v1/v2's underlying fit), then aligns by
# re-evaluating the fitted curve with pretrigger pinned to the reference.
# See CONTEXT_FOR_NEXT_AI.md section 6 for full context.
#
# Unlike submit_v2.sh, zip7 is NOT skipped here: the fit model changed, so
# teacher's earlier approval of the old fixed-pretrigger zip7 result does not
# carry over to this new fit.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$(cd "$SCRIPT_DIR/../run" && pwd)"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)

for DET in "${ZIPS[@]}"; do
    sbatch --job-name="v3_z${DET}" \
           -p agsmall \
           --ntasks=1 \
           --cpus-per-task=2 \
           --mem=24gb \
           -t 2:00:00 \
           -o "${LOG_DIR}/v3_z${DET}_%j.out" \
           --wrap="singularity exec -B ${BIND} ${SIF} \
               python3 ${SCRIPT_DIR}/template_from_pkl_v3.py \
               --det ${DET}"
    echo "Submitted zip${DET}"
done

echo "All submitted. Monitor with: squeue -u $USER | grep v3_z"
