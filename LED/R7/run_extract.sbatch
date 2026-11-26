#!/bin/bash -l
#SBATCH --job-name=led_r7_extract
#SBATCH --partition=agsmall
#SBATCH --account=yanliusp
#SBATCH --time=1:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=4
#SBATCH --output=%x_%j.out
# Usage: sbatch run_extract.sbatch SERIES   (run from LED/R7; writes out/SERIES/)
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
cd "$SLURM_SUBMIT_DIR"
singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF \
  python3 -u extract_led_events.py "$1"
