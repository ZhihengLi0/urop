#!/bin/bash
set -euo pipefail

ROOT="$HOME/urop/snolab/Zip19PAS1"
RUN_DIR="$ROOT/run"
SCRIPT="$ROOT/scripts/fit_plot_zip19_pas1.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR/cache" "$RUN_DIR/plots" "$RUN_DIR/logs"

jid=$(sbatch --parsable \
    --job-name="zip19_pas1_allfit" \
    --time=24:00:00 \
    --ntasks=1 \
    --mem=192g \
    --partition=agsmall \
    --output="$RUN_DIR/logs/zip19_pas1_allfit_%j.out" \
    --export="ALL,ZIP19PAS1_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $SCRIPT")

echo "Submitted Zip19 PAS1 all-event fit job: $jid"
echo "Run directory: $RUN_DIR"
