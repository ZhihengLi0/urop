#!/bin/bash -l
#SBATCH --job-name=led_r7_lpcombine
#SBATCH --partition=agsmall
#SBATCH --account=yanliusp
#SBATCH --time=3:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=4
#SBATCH --output=%x_%j.out
# Usage: sbatch run_lpcombine.sbatch [EXAMPLE_CELL_ID]   (after all run_lpfit.sbatch jobs)
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
cd "$SLURM_SUBMIT_DIR"
singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF python3 -u lp_template_combine.py ${1:-P1-07}
singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF bash -c "cd presentation && python3 -u make_figures.py"
singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF python3 -u qa_led.py
