#!/bin/bash
set -euo pipefail

REPO="$HOME/urop/snolab"
RUN_DIR="$REPO/runs/r4_fixed_v2_20260621"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
TEMPLATE_SCRIPT="$REPO/scripts/template_single_zip_fixed_v2.py"
PLOT_SCRIPT="$REPO/scripts/plot_templates_fixed_v2.py"

mkdir -p "$RUN_DIR"/{cache,root_files,template_plots,slurm_logs}

job_ids=()
for det in 1 4 6 7 10 15 16 18; do
    job_id=$(sbatch --parsable \
        --job-name="r4v2_z${det}" \
        --time=4:00:00 \
        --ntasks=1 \
        --mem=32g \
        --partition=msismall \
        --output="$RUN_DIR/slurm_logs/template_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="cd $REPO && singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $TEMPLATE_SCRIPT --det $det")
    job_ids+=("$job_id")
    echo "Submitted Zip${det}: ${job_id}"
done

dependency=$(IFS=:; echo "${job_ids[*]}")
plot_id=$(sbatch --parsable \
    --job-name="r4v2_plots" \
    --dependency="afterok:$dependency" \
    --time=0:30:00 \
    --ntasks=1 \
    --mem=16g \
    --partition=msismall \
    --output="$RUN_DIR/slurm_logs/plot_templates_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="cd $REPO && singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE python3 -u $PLOT_SCRIPT")

printf '%s\n' "${job_ids[@]}" > "$RUN_DIR/template_job_ids.txt"
printf '%s\n' "$plot_id" > "$RUN_DIR/plot_job_id.txt"
echo "Submitted dependent plotting job: $plot_id"
echo "Results: $RUN_DIR"
