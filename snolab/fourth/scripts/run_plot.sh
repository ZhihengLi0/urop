#!/bin/bash -l
#SBATCH --time=0:30:00
#SBATCH --ntasks=1
#SBATCH --mem=16g
#SBATCH --partition=msismall
#SBATCH --output=plot_templates_%j.out

SINGULARITY_IMG="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

cd ~/urop/snolab

singularity exec -B $HOME,$MSIPROJECT/shared/ \
    $SINGULARITY_IMG \
    python3 ~/urop/snolab/scripts/plot_templates.py
