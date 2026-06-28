#!/bin/bash
# Attach automatic rescue jobs to the currently running debug/raw jobs.
#
# The rescue jobs use afternotok, so they run only if the current job fails,
# is cancelled, or hits its time limit. Successful current jobs do not trigger
# rescue work.
set -euo pipefail

ROOT="$HOME/urop/snolab"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

DEBUG_RUN="$ROOT/debug/run"
DEBUG_RESCUE="$ROOT/debug/scripts/run_scan_rescue.sh"
RAW_RUN="$ROOT/raw_without_filter/run"
RAW_RESCUE="$ROOT/raw_without_filter/scripts/run_raw_rescue.sh"

mkdir -p "$DEBUG_RUN" "$RAW_RUN/cache" "$RAW_RUN/logs"

submit_scan_rescue() {
    local parent="$1"
    local jid
    jid=$(sbatch --parsable \
        --job-name="scan_rescue" \
        --dependency="afternotok:${parent}" \
        --time=24:00:00 \
        --ntasks=1 \
        --mem=192g \
        --partition=agsmall \
        --output="$DEBUG_RUN/scan_rescue_%j.out" \
        --export="ALL,SCAN_RUN_DIR=$DEBUG_RUN,SCAN_RESUME=1,RESCUE_DEPTH=1,MAX_RESCUE_DEPTH=4" \
        --wrap="bash $DEBUG_RESCUE")
    echo "scan rescue: parent=$parent rescue=$jid"
}

submit_raw_rescue() {
    local det="$1"
    local parent="$2"
    local jid
    jid=$(sbatch --parsable \
        --job-name="raw_rescue_z${det}" \
        --dependency="afternotok:${parent}" \
        --time=16:00:00 \
        --ntasks=1 \
        --mem=256g \
        --partition=agsmall \
        --output="$RAW_RUN/logs/read_rescue_z${det}_%j.out" \
        --export="ALL,RAW_WF_RUN_DIR=$RAW_RUN,RESCUE_DEPTH=1,MAX_RESCUE_DEPTH=4" \
        --wrap="bash $RAW_RESCUE $det")
    echo "raw rescue: zip=$det parent=$parent rescue=$jid"
}

# Current jobs as of this rescue setup.
submit_scan_rescue 12019812

submit_raw_rescue 1  12018017
submit_raw_rescue 4  12018018
submit_raw_rescue 6  12016292
submit_raw_rescue 7  12018019
submit_raw_rescue 9  12018020
submit_raw_rescue 10 12018021
submit_raw_rescue 13 12018022
submit_raw_rescue 15 12018023
submit_raw_rescue 19 12016300
submit_raw_rescue 22 12016301
submit_raw_rescue 24 12016302

echo ""
echo "Auto-rescue dependencies submitted."
echo "They remain pending while parent jobs run and are cancelled automatically by SLURM if parents complete successfully."
