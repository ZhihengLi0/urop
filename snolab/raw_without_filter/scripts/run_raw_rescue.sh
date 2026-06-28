#!/bin/bash
# Run one raw-without-filter zip and pre-submit one follow-up rescue.
# After the main script exits (any exit code), always run finalize_zip.py
# to merge all completed per-series checkpoints into the final pkl.
# A SIGTERM trap ensures the merge also runs when SLURM kills on timeout.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 DET" >&2
    exit 2
fi

DET="$1"
ROOT_DIR="$HOME/urop/snolab/raw_without_filter"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/read_zip_all_series.py"
FINALIZE="$ROOT_DIR/scripts/finalize_zip.py"
SELF="$ROOT_DIR/scripts/run_raw_rescue.sh"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

DEPTH="${RESCUE_DEPTH:-1}"
MAX_DEPTH="${MAX_RESCUE_DEPTH:-6}"

mkdir -p "$RUN_DIR/cache" "$RUN_DIR/logs"

# Pre-submit follow-up rescue job (afternotok = only fires if this job fails/times out)
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

# SIGTERM trap: fires when SLURM approaches time limit (sent ~60s before kill)
# Runs finalize to merge whatever checkpoints exist, then exits non-zero
# so the pre-submitted rescue job will fire.
_on_timeout() {
    echo "[$(date '+%T')] SIGTERM received — merging checkpoints for zip${DET}..."
    singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
        python3 "$FINALIZE" --det "$DET" || echo "finalize failed (non-fatal)"
    exit 1
}
trap _on_timeout TERM

# Run main script in background so bash stays alive to handle SIGTERM
singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
    python3 -u "$SCRIPT" --det "$DET" &
MAIN_PID=$!
wait $MAIN_PID
MAIN_EXIT=$?

# Always finalize after main exits (normal completion or error)
echo "[$(date '+%T')] Main exited ($MAIN_EXIT) — merging checkpoints for zip${DET}..."
singularity exec -B "$HOME,$MSIPROJECT/shared/" "$IMAGE" \
    python3 "$FINALIZE" --det "$DET" || echo "finalize failed (non-fatal)"

exit $MAIN_EXIT
