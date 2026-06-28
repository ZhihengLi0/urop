#!/bin/bash
# Submit 256g chained raw rescues for all expected zips.
#
# Running original jobs get afternotok dependencies. Zips without an active
# original job are submitted immediately.
set -euo pipefail

ROOT="$HOME/urop/snolab"
RAW_RUN="$ROOT/raw_without_filter/run"
RAW_RESCUE="$ROOT/raw_without_filter/scripts/run_raw_rescue.sh"

mkdir -p "$RAW_RUN/cache" "$RAW_RUN/logs"

submit_dep() {
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
    echo "raw rescue dependency: zip=$det parent=$parent rescue=$jid"
}

submit_now() {
    local det="$1"
    local jid
    jid=$(sbatch --parsable \
        --job-name="raw_rescue_z${det}" \
        --time=16:00:00 \
        --ntasks=1 \
        --mem=256g \
        --partition=agsmall \
        --output="$RAW_RUN/logs/read_rescue_z${det}_%j.out" \
        --export="ALL,RAW_WF_RUN_DIR=$RAW_RUN,RESCUE_DEPTH=1,MAX_RESCUE_DEPTH=4" \
        --wrap="bash $RAW_RESCUE $det")
    echo "raw rescue immediate: zip=$det rescue=$jid"
}

submit_dep 1  12018017
submit_dep 4  12018018
submit_dep 6  12016292
submit_dep 7  12018019
submit_dep 9  12018020
submit_dep 10 12018021
submit_dep 13 12018022
submit_dep 15 12018023
submit_now 16
submit_now 18
submit_dep 19 12016300
submit_dep 22 12016301
submit_dep 24 12016302
