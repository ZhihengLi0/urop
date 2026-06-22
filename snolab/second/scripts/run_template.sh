#!/bin/bash -l
#SBATCH --time=8:00:00
#SBATCH --ntasks=1
#SBATCH --mem=64g
#SBATCH --partition=msismall
#SBATCH --output=slurm_logs/template_%j.out

SINGULARITY_IMG="$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif"

cd ~/urop/snolab

singularity exec -B $HOME,$MSIPROJECT/shared/ \
    $SINGULARITY_IMG \
    python3 ~/urop/snolab/scripts/SNOLAB_R4_TemplateGeneration.py
