#!/bin/bash -l
#SBATCH --job-name=led_r7_finish
#SBATCH --partition=agsmall
#SBATCH --account=yanliusp
#SBATCH --time=1:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=2
#SBATCH --output=%x_%j.out
# Usage: sbatch run_finish.sbatch   (after run_lpcombine: redraw the summary figures, talk figures + stats, QA)
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
cd "$SLURM_SUBMIT_DIR"
run() { singularity exec -B $HOME,/projects/standard/yanliusp/shared/ $SIF "$@"; }
[ -f out/summary/trigger_epochs.csv ] || run python3 -u trigger_settings.py
run python3 -u analyze_led.py
run bash -c "cd presentation && python3 -u make_figures.py"
run python3 -u qa_led.py
