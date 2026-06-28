#!/bin/bash
# Run one raw-without-filter zip and pre-submit one follow-up rescue.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 DET" >&2
    exit 2
fi

DET="$1"
ROOT_DIR="$HOME/urop/snolab/raw_without_filter"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/read_zip_all_series.py"
SELF="$ROOT_DIR/scripts/run_raw_rescue.sh"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

DEPTH="${RESCUE_DEPTH:-1}"
MAX_DEPTH="${MAX_RESCUE_DEPTH:-4}"

mkdir -p "$RUN_DIR/cache" "$RUN_DIR/logs"

if [[ -n "${SLURM_JOB_ID:-}" && "$DEPTH" -lt "$MAX_DEPTH" ]]; then
    next_depth=$((DEPTH + 1))
    next_jid=$(sbatch --parsable \
        --job-name="raw_rescue${next_depth}_z${DET}" \
        --dependency="afternotok:${SLURM_JOB_ID}" \
        --time=16:00:00 \
        --ntasks=1 \
        --mem=256g \
        --partition=agsmall \
        --output="$RUN_DIR/logs/read_rescue${next_depth}_z${DET}_%j.out" \
        --export="ALL,RAW_WF_RUN_DIR=$RUN_DIR,RESCUE_DEPTH=$next_depth,MAX_RESCUE_DEPTH=$MAX_DEPTH" \
        --wrap="bash $SELF $DET")
    echo "Submitted follow-up raw rescue depth $next_depth for zip $DET: $next_jid"
fi

exec singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
    python3 -u "$SCRIPT" --det "$DET"
