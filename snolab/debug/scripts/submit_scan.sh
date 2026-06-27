#!/bin/bash
set -euo pipefail

ROOT_DIR="$HOME/urop/snolab/debug"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/scan_all_data.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR"

jid=$(sbatch --parsable \
    --job-name="scan_all_zips" \
    --time=24:00:00 \
    --ntasks=1 \
    --mem=192g \
    --partition=agsmall \
    --output="$RUN_DIR/scan_%j.out" \
    --export="ALL,SCAN_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $SCRIPT")

echo "Submitted: $jid"
echo "Log (SLURM): $RUN_DIR/scan_${jid}.out"
echo "Log (script): $RUN_DIR/scan.log"
echo "Outputs:"
echo "  $RUN_DIR/all_zips_event_stats.tsv   <- per-event per-channel all metrics"
echo "  $RUN_DIR/all_zips_summary.txt        <- per-zip per-channel statistics"
