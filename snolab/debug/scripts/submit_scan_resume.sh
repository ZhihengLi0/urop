#!/bin/bash
# Resume scan_all_data.py using existing scan.log + TSV.
set -euo pipefail

ROOT_DIR="$HOME/urop/snolab/debug"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/scan_all_data.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR"

jid=$(sbatch --parsable \
    --job-name="scan_resume" \
    --time=24:00:00 \
    --ntasks=1 \
    --mem=192g \
    --partition=agsmall \
    --output="$RUN_DIR/scan_resume_%j.out" \
    --export="ALL,SCAN_RUN_DIR=$RUN_DIR,SCAN_RESUME=1" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $SCRIPT")

echo "Submitted resume scan: $jid"
echo "Existing complete series in $RUN_DIR/scan.log will be skipped."
echo "Rows will append to $RUN_DIR/all_zips_event_stats.tsv."
