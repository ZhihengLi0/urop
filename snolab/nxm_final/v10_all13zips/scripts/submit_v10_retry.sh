#!/bin/bash
# Re-run template generation for zips that timed out, split by series.
# Pipeline per zip:
#   30 per-series collect jobs → merge job → original template job (loads cache)
set -euo pipefail

REPO="$HOME/urop/snolab/more_data_analysis"
IMAGE="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
SCRIPTS="$REPO/scripts"

# Re-use the existing run directory from the previous submission
RUN_DIR="$REPO/run/r4_v10_20260625"

echo "Retry run directory: $RUN_DIR"

ALL_SERIES=(
    "24260617_063934" "24260617_175849" "24260617_190838" "24260617_234805"
    "24260618_013000" "24260618_062713" "24260618_073543" "24260618_202553"
    "24260619_023225" "24260619_061249" "24260619_075448" "24260619_093653"
    "24260619_144815" "24260619_174938" "24260619_210312" "24260619_230219"
    "24260620_032928" "24260621_021444" "24260621_041432" "24260621_075659"
    "24260621_111527" "24260621_145024" "24260622_022708" "24260622_042718"
    "24260622_073439" "24260622_210215" "24260622_232541" "24260623_012553"
    "24260623_035656" "24260623_064608"
)

RETRY_DETS=(6 7 9 10 16 19)

all_template_ids=()

for det in "${RETRY_DETS[@]}"; do
    echo ""
    echo "── Zip${det} ──────────────────────────────────────────"

    # Submit one collect job per series
    collect_ids=()
    for series in "${ALL_SERIES[@]}"; do
        jid=$(sbatch --parsable \
            --job-name="col_z${det}_${series}" \
            --time=3:00:00 \
            --ntasks=1 \
            --mem=64g \
            --partition=agsmall \
            --output="$RUN_DIR/agnostic/slurm_logs/collect_zip${det}_${series}_%j.out" \
            --export="ALL,R4_RUN_DIR=$RUN_DIR" \
            --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                    python3 -u $SCRIPTS/template_collect_series_v10.py \
                    --det $det --series $series")
        collect_ids+=("$jid")
        echo "  Submitted collect Zip${det}/${series}: ${jid}"
    done

    collect_dep=$(IFS=:; echo "${collect_ids[*]}")

    # Merge job — runs after ALL series collect jobs finish (even if some fail)
    merge_id=$(sbatch --parsable \
        --job-name="merge_z${det}" \
        --dependency="afterany:${collect_dep}" \
        --time=0:15:00 \
        --ntasks=1 --mem=64g --partition=msismall \
        --output="$RUN_DIR/agnostic/slurm_logs/merge_traces_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPTS/template_merge_traces_v10.py --det $det")
    echo "  Submitted merge Zip${det}: ${merge_id}"

    # Template fitting job — loads merged cache, skips raw reading
    tmpl_id=$(sbatch --parsable \
        --job-name="tmpl_z${det}" \
        --dependency="afterok:${merge_id}" \
        --time=4:00:00 \
        --ntasks=1 --mem=128g --partition=agsmall \
        --output="$RUN_DIR/agnostic/slurm_logs/template_zip${det}_%j.out" \
        --export="ALL,R4_RUN_DIR=$RUN_DIR" \
        --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
                python3 -u $SCRIPTS/template_single_zip_v10.py --det $det")
    echo "  Submitted template Zip${det}: ${tmpl_id}"
    all_template_ids+=("$tmpl_id")
done

# After all 6 template jobs: re-run merge and plot scripts
all_tmpl_dep=$(IFS=:; echo "${all_template_ids[*]}")

merge_ag=$(sbatch --parsable \
    --job-name="r4v10_merge_ag" \
    --dependency="afterany:${all_tmpl_dep}" \
    --time=0:15:00 \
    --ntasks=1 --mem=8g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/merge_final_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/merge_all_zips_agnostic.py")
echo ""
echo "Submitted final agnostic merge: $merge_ag"

merge_sp=$(sbatch --parsable \
    --job-name="r4v10_merge_sp" \
    --dependency="afterany:${all_tmpl_dep}" \
    --time=0:15:00 \
    --ntasks=1 --mem=8g --partition=msismall \
    --output="$RUN_DIR/specific/slurm_logs/merge_final_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/merge_all_zips_specific.py")
echo "Submitted final specific merge: $merge_sp"

tc_plot=$(sbatch --parsable \
    --job-name="r4v10_tc_plot" \
    --dependency="afterany:${all_tmpl_dep}" \
    --time=0:20:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/tc_plot_final_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_timeconstants_table.py")
echo "Submitted time-constants plot: $tc_plot"

shape_ag=$(sbatch --parsable \
    --job-name="r4v10_plot_ag" \
    --dependency="afterany:${all_tmpl_dep}" \
    --time=0:30:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/agnostic/slurm_logs/plot_final_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_templates_v10.py --mode agnostic")
echo "Submitted agnostic shape plot: $shape_ag"

shape_sp=$(sbatch --parsable \
    --job-name="r4v10_plot_sp" \
    --dependency="afterany:${all_tmpl_dep}" \
    --time=0:30:00 \
    --ntasks=1 --mem=16g --partition=msismall \
    --output="$RUN_DIR/specific/slurm_logs/plot_final_%j.out" \
    --export="ALL,R4_RUN_DIR=$RUN_DIR" \
    --wrap="singularity exec -B \$HOME,\$MSIPROJECT/shared/ $IMAGE \
            python3 -u $SCRIPTS/plot_templates_v10.py --mode specific")
echo "Submitted specific shape plot: $shape_sp"

echo ""
echo "All jobs submitted."
echo "  180 collect jobs + 6 merge + 6 template + 5 final post-processing"
echo "  Results will appear in: $RUN_DIR"
