#!/bin/bash
# Submit one SLURM job per zip detector.
# Usage: bash submit_all_zips.sh

SINGULARITY_IMG="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"
SCRIPT="$HOME/urop/snolab/scripts/template_single_zip.py"

for DET in 1 4 6 7 10 15 16 18; do
    sbatch --job-name="tmpl_zip${DET}" \
           --time=4:00:00 \
           --ntasks=1 \
           --mem=32g \
           --partition=msismall \
           --output="$HOME/urop/snolab/slurm_logs/template_zip${DET}_%j.out" \
           --wrap="cd \$HOME/urop/snolab && singularity exec -B \$HOME,\$MSIPROJECT/shared/ \
               $SINGULARITY_IMG \
               python3 $SCRIPT --det $DET"
    echo "Submitted zip${DET}"
done
