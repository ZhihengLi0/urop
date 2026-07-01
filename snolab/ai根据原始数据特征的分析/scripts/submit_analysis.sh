#!/bin/bash
# Submit per-event analysis for all zips that have pkl cache data.
# Stage 1: scans 126G pkl for per-event thresholds.
# Stage 2: rawio re-reads selected events per series (like the upstream rawio jobs).
# Memory: 256G matches upstream rawio jobs; time: 12h covers 30 series + fitting + plots.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$ROOT_DIR/run"
SCRIPT="$SCRIPT_DIR/per_event_analysis.py"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

mkdir -p "$RUN_DIR/plots" "$RUN_DIR/stats" "$RUN_DIR/logs"

# Only zips that have at least one series pkl in shared cache
PKL_BASE="/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache"
ZIPS=(1 4 6 7 9 10 13 15 16 18 19 22 24)

# Optional override: nrmse-max and noise-pctile can be passed as env vars
NRMSE_MAX="${NRMSE_MAX:-0.15}"
NOISE_PCTILE="${NOISE_PCTILE:-75}"
ONSET_FRAC="${ONSET_FRAC:-0.02}"

echo "Settings: NRMSE_MAX=$NRMSE_MAX  NOISE_PCTILE=$NOISE_PCTILE  ONSET_FRAC=$ONSET_FRAC"

for det in "${ZIPS[@]}"; do
    # Check that at least one pkl exists for this zip before submitting
    n_pkl=$(ls "$PKL_BASE/zip${det}_series/"*.pkl 2>/dev/null | wc -l)
    if [[ "$n_pkl" -eq 0 ]]; then
        echo "zip${det}: no pkl files found, skipping"
        continue
    fi

    jid=$(sbatch --parsable \
        --job-name="ai_z${det}" \
        --time=12:00:00 \
        --ntasks=1 \
        --mem=256g \
        --partition=agsmall \
        --output="$RUN_DIR/logs/ai_z${det}_%j.out" \
        --export="ALL,AI_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec \
            -B \$HOME,\$MSIPROJECT/shared/ \
            $IMAGE \
            python3 -u $SCRIPT \
            --det $det \
            --nrmse-max $NRMSE_MAX \
            --noise-pctile $NOISE_PCTILE \
            --onset-frac $ONSET_FRAC")
    echo "Submitted zip${det} ($n_pkl series): job $jid"
done
