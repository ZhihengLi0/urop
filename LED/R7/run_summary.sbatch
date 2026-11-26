#!/bin/bash -l
#SBATCH --job-name=led_r7_summary
#SBATCH --partition=agsmall
#SBATCH --account=yanliusp
#SBATCH --time=4:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=16
#SBATCH --output=%x_%j.out
# Usage: sbatch run_summary.sbatch   (run from LED/R7 after all extraction jobs; writes
# out/summary, out/stability, out/fit)
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
cd "$SLURM_SUBMIT_DIR"
run() { singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF python3 -u "$@"; }
run analyze_led.py && run stability_led.py && run fit_led.py "$SLURM_CPUS_PER_TASK"
