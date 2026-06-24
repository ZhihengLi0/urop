#!/bin/bash
# Section-3 plot pipeline: per-day trace reading → merge → plot.
#
# Step 1: 7 days × 13 detectors = 91 jobs (process_day_section3.py)
#         Each reads one day's raw traces for one detector, saves pkl.
# Step 2: 13 plot jobs (plot_section3_all_events.py)
#         Loads all day pkls per detector, merges, outputs corrected/uncorrected pngs.
#
# Usage:
#   bash submit_section3.sh                   # creates a new run dir dated today
#   bash submit_section3.sh /path/to/run_dir  # reuse an existing run dir
set -euo pipefail

REPO="$HOME/urop/snolab/more_data_analysis"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
SCRIPTS="$REPO/scripts"

if [[ -n "${1:-}" ]]; then
    RUN_DIR="$1"
else
    DATE="$(date +%Y%m%d)"
    RUN_DIR="$REPO/run/r4_v10_${DATE}"
fi

mkdir -p "$RUN_DIR/cache"
mkdir -p "$RUN_DIR/agnostic/template_plots"
mkdir -p "$RUN_DIR/agnostic/slurm_logs"

echo "Run directory: $RUN_DIR"

DAYS=(260617 260618 260619 260620 260621 260622 260623)
DETS=(1 4 6 7 9 10 13 15 16 18 19 22 24)

# ── Step 1: per-day, per-detector trace reading ───────────────────────────────
job_ids=()
for det in "${DETS[@]}"; do
    for day in "${DAYS[@]}"; do
        jid=$(sbatch --parsable \
            --job-name="sec3_z${det}_d${day}" \
            --time=2:00:00 \
            --ntasks=1 \
            --mem=32g \
            --partition=msismall \
            --output="$RUN_DIR/agnostic/slurm_logs/sec3_zip${det}_day${day}_%j.out" \
            --export="ALL,R4_RUN_DIR=$RUN_DIR" \
            --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                    python3 -u $SCRIPTS/process_day_section3.py --det $det --day $day")
        job_ids+=("$jid")
        echo "  Submitted Zip${det} Day${day}: job ${jid}"
    done
done

dependency=$(IFS=:; echo "${job_ids[*]}")
echo ""
echo "All ${#job_ids[@]} reading jobs submitted."

# ── Step 2: merge + plot per detector (runs after all reading jobs finish) ────
echo ""
for det in "${DETS[@]}"; do
    plot_jid=$(sbatch --parsable \
        --job-name="sec3_plot_z${det}" \
        --dependency="afterok:$dependency" \
        --time=0:30:00 \
        --ntasks=1 \
        --mem=16g \
        --partition=msismall \
        --output="$RUN_DIR/agnostic/slurm_logs/sec3_plot_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPTS/plot_section3_all_events.py --det $det")
    echo "  Submitted Section3 plot Zip${det}: job ${plot_jid}"
done

echo ""
echo "Pipeline submitted. Outputs will appear in:"
echo "  $RUN_DIR/agnostic/template_plots/zip*_section3_*.png"
echo "  $RUN_DIR/agnostic/slurm_logs/"
echo ""
squeue -u "$USER" --format="%.10i %.20j %.8T %.10M %.6D %R" 2>/dev/null | head -30
