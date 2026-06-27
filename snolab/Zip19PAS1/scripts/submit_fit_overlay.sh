#!/bin/bash
set -euo pipefail

ROOT="$HOME/urop/snolab/Zip19PAS1"
RUN_DIR="$ROOT/run"
SCRIPT="$ROOT/scripts/fit_overlay_zip19_pas1.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR/plots" "$RUN_DIR/logs"

jid=$(sbatch --parsable \
    --job-name="zip19_overlay" \
    --time=3:00:00 \
    --ntasks=1 \
    --mem=48g \
    --partition=agsmall \
    --output="$RUN_DIR/logs/overlay_%j.out" \
    --export="ALL,ZIP19PAS1_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $SCRIPT")

echo "Submitted: $jid"
echo "Log: $RUN_DIR/logs/overlay_${jid}.out"
echo "Output: $RUN_DIR/plots/zip19_pas1_24260619_230219_raw_vs_ana_pinned.png"
