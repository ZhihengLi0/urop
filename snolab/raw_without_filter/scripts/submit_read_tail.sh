#!/bin/bash
# Submit raw-without-filter jobs for only the tail of the series list.
#
# Usage:
#   bash scripts/submit_read_tail.sh 24260619_144815
#   bash scripts/submit_read_tail.sh 24260619_144815 1 4 6
set -euo pipefail

ROOT_DIR="$HOME/urop/snolab/raw_without_filter"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$ROOT_DIR/scripts/read_zip_all_series.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 SERIES_FROM [zip ...]" >&2
    exit 2
fi

SERIES_FROM="$1"
shift

mkdir -p "$RUN_DIR/cache" "$RUN_DIR/logs"

if [[ $# -gt 0 ]]; then
    ZIPS=("$@")
else
    ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)
fi

for det in "${ZIPS[@]}"; do
    jid=$(sbatch --parsable \
        --job-name="raw_tail_z${det}" \
        --time=16:00:00 \
        --ntasks=1 \
        --mem=256g \
        --partition=agsmall \
        --output="$RUN_DIR/logs/read_tail_z${det}_%j.out" \
        --export="ALL,RAW_WF_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPT --det $det --series-from $SERIES_FROM")
    echo "Submitted zip${det} tail from ${SERIES_FROM}: job $jid"
done
