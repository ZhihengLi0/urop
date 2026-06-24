#!/bin/bash
# Sixth-iteration template generation: agnostic + specific mean-plus-PCA NxM.
# Each per-zip job writes to both agnostic/ and specific/ subdirs.
set -euo pipefail

REPO="$HOME/urop/snolab/sixth"
DATE="$(date +%Y%m%d)"
RUN_DIR="$REPO/run/r4_v6_${DATE}"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
SCRIPTS="$REPO/scripts"

# ── Directory layout ──────────────────────────────────────────────────────────
mkdir -p "$RUN_DIR"/cache
mkdir -p "$RUN_DIR"/agnostic/{root_files,template_plots,slurm_logs}
mkdir -p "$RUN_DIR"/specific/{root_files,template_plots,slurm_logs}

echo "Run directory: $RUN_DIR"

# ── Step 1: per-zip jobs (each writes agnostic + specific ROOT files) ─────────
job_ids=()
for det in 1 4 6 7 10 15 16 18; do
    jid=$(sbatch --parsable \
        --job-name="r4v6_z${det}" \
        --time=5:00:00 \
        --ntasks=1 \
        --mem=48g \
        --partition=msismall \
        --output="$RUN_DIR/agnostic/slurm_logs/template_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPTS/template_single_zip_v6.py --det $det")
    job_ids+=("$jid")
    echo "Submitted Zip${det}: ${jid}"
done

dependency=$(IFS=:; echo "${job_ids[*]}")

# ── Step 2: merge agnostic ────────────────────────────────────────────────────
merge_ag=$(sbatch --parsable \
    --job-name="r4v6_merge_ag" \
    --dependency="afterok:$dependency" \
    --time=0:15:00 \
    --ntasks=1 --mem=8g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/merge_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/merge_all_zips_agnostic.py")
echo "Submitted agnostic merge: $merge_ag"

# ── Step 3: merge specific ────────────────────────────────────────────────────
merge_sp=$(sbatch --parsable \
    --job-name="r4v6_merge_sp" \
    --dependency="afterok:$dependency" \
    --time=0:15:00 \
    --ntasks=1 --mem=8g --partition=msismall \
    --output="$RUN_DIR/specific/slurm_logs/merge_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/merge_all_zips_specific.py")
echo "Submitted specific merge: $merge_sp"

# ── Step 4: time constants cross-zip comparison plot ─────────────────────────
tc_plot_id=$(sbatch --parsable \
    --job-name="r4v6_tc_plot" \
    --dependency="afterok:$dependency" \
    --time=0:20:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/tc_plot_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_timeconstants_table.py")
echo "Submitted time-constants plot: $tc_plot_id"

# ── Step 5: template shape plots (after all per-zip jobs finish) ──────────────
shape_ag=$(sbatch --parsable \
    --job-name="r4v6_plot_ag" \
    --dependency="afterok:$dependency" \
    --time=0:30:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/plot_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_templates_v6.py --mode agnostic")
echo "Submitted agnostic shape plot: $shape_ag"

shape_sp=$(sbatch --parsable \
    --job-name="r4v6_plot_sp" \
    --dependency="afterok:$dependency" \
    --time=0:30:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/specific/slurm_logs/plot_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_templates_v6.py --mode specific")
echo "Submitted specific shape plot: $shape_sp"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "All jobs submitted. Run directory: $RUN_DIR"
echo "  Agnostic ROOT files: $RUN_DIR/agnostic/root_files/"
echo "  Specific  ROOT files: $RUN_DIR/specific/root_files/"
echo ""
squeue -u "$USER" --format="%.10i %.15j %.8T %.10M %.6D %R" 2>/dev/null | head -20
