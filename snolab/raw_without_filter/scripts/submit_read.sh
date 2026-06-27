#!/bin/bash
# Submit one read job per zip (13 parallel jobs).
# Each job reads ALL series for that zip and saves a pkl.
set -euo pipefail

ROOT_DIR="$HOME/urop/snolab/raw_without_filter"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/read_zip_all_series.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR/cache" "$RUN_DIR/logs"

ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)
job_ids=()

for det in "${ZIPS[@]}"; do
    jid=$(sbatch --parsable \
        --job-name="raw_wf_z${det}" \
        --time=16:00:00 \
        --ntasks=1 \
        --mem=128g \
        --partition=agsmall \
        --output="$RUN_DIR/logs/read_z${det}_%j.out" \
        --export="ALL,RAW_WF_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPT --det $det")
    job_ids+=("$jid")
    echo "Submitted zip${det}: job $jid"
done

echo ""
echo "All ${#ZIPS[@]} zip jobs submitted — each job reads + plots its own zip."
echo "Logs:   $RUN_DIR/logs/"
echo "Plots:  $RUN_DIR/plots/   (one PNG per zip, ready as each job finishes)"
echo "Cache:  $RUN_DIR/cache/   (pkl saved for future reuse)"
