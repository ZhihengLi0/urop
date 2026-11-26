#!/bin/bash -l
#SBATCH --job-name=led_r7_lpfit
#SBATCH --partition=agsmall
#SBATCH --account=yanliusp
#SBATCH --time=3:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --output=%x_%j.out
# Usage: sbatch run_lpfit.sbatch SERIES   (run from LED/R7 after analyze_led.py wrote out/summary/cells.csv)
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
cd "$SLURM_SUBMIT_DIR"
singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF \
  python3 -u lp_template_led.py "$1" "$SLURM_CPUS_PER_TASK"
