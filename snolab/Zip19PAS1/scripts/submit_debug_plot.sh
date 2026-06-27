#!/bin/bash
set -euo pipefail

ROOT="$HOME/urop/snolab/Zip19PAS1"
RUN_DIR="$ROOT/run"
SCRIPT="$ROOT/scripts/debug_plot_zip19_pas1.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR/debug_plots" "$RUN_DIR/logs"

jid=$(sbatch --parsable \
    --job-name="zip19_debug_plot" \
    --time=1:00:00 \
    --ntasks=1 \
    --mem=32g \
    --partition=agsmall \
    --output="$RUN_DIR/logs/debug_plot_%j.out" \
    --export="ALL,ZIP19PAS1_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $SCRIPT")

echo "Submitted debug plot job: $jid"
echo "Logs: $RUN_DIR/logs/debug_plot_${jid}.out"
echo "Output: $RUN_DIR/debug_plots/"
