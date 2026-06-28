#!/bin/bash
# Run scan resume and pre-submit one follow-up rescue for this rescue job.
set -euo pipefail

ROOT_DIR="$HOME/urop/snolab/debug"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/scan_all_data.py"
SELF="$ROOT_DIR/scripts/run_scan_rescue.sh"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

DEPTH="${RESCUE_DEPTH:-1}"
MAX_DEPTH="${MAX_RESCUE_DEPTH:-4}"

mkdir -p "$RUN_DIR"

if [[ -n "${SLURM_JOB_ID:-}" && "$DEPTH" -lt "$MAX_DEPTH" ]]; then
    next_depth=$((DEPTH + 1))
    next_jid=$(sbatch --parsable \
        --job-name="scan_rescue${next_depth}" \
        --dependency="afternotok:${SLURM_JOB_ID}" \
        --time=48:00:00 \
        --ntasks=1 \
        --mem=384g \
        --partition=agsmall \
        --output="$RUN_DIR/scan_rescue${next_depth}_%j.out" \
        --export="ALL,SCAN_RUN_DIR=$RUN_DIR,SCAN_RESUME=1,RESCUE_DEPTH=$next_depth,MAX_RESCUE_DEPTH=$MAX_DEPTH" \
        --wrap="bash $SELF")
    echo "Submitted follow-up scan rescue depth $next_depth: $next_jid"
fi

exec singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
    python3 -u "$SCRIPT"
