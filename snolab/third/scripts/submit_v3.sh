#!/bin/bash
set -euo pipefail

REPO="$HOME/urop/snolab/第三次"
RUN_DIR="$REPO/run/r4_v3_20260622"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
SCRIPTS="$REPO/scripts"

mkdir -p "$RUN_DIR"/{cache,root_files,template_plots,slurm_logs}

# ── Step 1: per-zip template jobs ───────────────────────────────────────────
job_ids=()
for det in 1 4 6 7 10 15 16 18; do
    jid=$(sbatch --parsable \
        --job-name="r4v3_z${det}" \
        --time=4:00:00 \
        --ntasks=1 \
        --mem=32g \
        --partition=msismall \
        --output="$RUN_DIR/slurm_logs/template_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPTS/template_single_zip.py --det $det")
    job_ids+=("$jid")
    echo "Submitted Zip${det}: ${jid}"
done

dependency=$(IFS=:; echo "${job_ids[*]}")

# ── Step 2: merge all 8 per-zip ROOT files into one AllZips file ─────────────
merge_id=$(sbatch --parsable \
    --job-name="r4v3_merge" \
    --dependency="afterok:$dependency" \
    --time=0:15:00 \
    --ntasks=1 \
    --mem=8g \
    --partition=msismall \
    --output="$RUN_DIR/slurm_logs/merge_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/merge_all_zips.py")
echo "Submitted merge job: $merge_id"

# ── Step 3: plots (cross-zip time-constant comparison + NxM diagnostics) ────
plot_id=$(sbatch --parsable \
    --job-name="r4v3_plots" \
    --dependency="afterok:$dependency" \
    --time=0:30:00 \
    --ntasks=1 \
    --mem=16g \
    --partition=msismall \
    --output="$RUN_DIR/slurm_logs/plot_templates_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_templates_fixed_v2.py")
echo "Submitted plot job: $plot_id"

# ── Record all job IDs ───────────────────────────────────────────────────────
printf '%s\n' "${job_ids[@]}" > "$RUN_DIR/template_job_ids.txt"
echo "$merge_id"            >> "$RUN_DIR/template_job_ids.txt"
echo "$plot_id"             >> "$RUN_DIR/plot_job_id.txt"

echo ""
echo "All jobs submitted. Results will appear in: $RUN_DIR"
echo "  8 per-zip ROOT files:  $RUN_DIR/root_files/Templates_SNOLAB_R4_zip*_1x1.root"
echo "  Merged AllZips file:   $RUN_DIR/root_files/Templates_SNOLAB_R4_AllZips_1x1.root"
echo "  Template plots:        $RUN_DIR/template_plots/"
