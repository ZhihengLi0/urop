#!/bin/bash
# Run zip7 ai_v2 template/diagnostic generation after the corrected pkl cache
# job has finished. This script intentionally validates zip7 first; if the
# cache is incomplete or still old-format, no plots/ROOT/stats are regenerated.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNOLAB_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
RAW_SCRIPT_DIR="$SNOLAB_DIR/raw_without_filter/scripts"
SIF="/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif"
BIND="$HOME,/projects/standard/yanliusp/shared/"

echo "[$(date)] Validating corrected zip7 pkl cache"
"$RAW_SCRIPT_DIR/validate_shifted_cache_in_singularity.sh" --det 7

echo "[$(date)] zip7 cache validation passed; generating ai_v2 outputs"
cd "$SNOLAB_DIR/ai_v2"
singularity exec -B "$BIND" "$SIF" \
    python3 "$SCRIPT_DIR/template_from_pkl_v2.py" \
    --det 7

echo "[$(date)] zip7 ai_v2 outputs regenerated"
echo "Plots:      $SNOLAB_DIR/ai_v2/run/plots/zip7_*.png"
echo "ROOT files: $SNOLAB_DIR/ai_v2/run/root_files/Templates_SNOLAB_R4_zip7_*.root"
echo "Stats:      $SNOLAB_DIR/ai_v2/run/stats/time_constants_zip7.json"
