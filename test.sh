#!/bin/bash
#SBATCH --job-name test
#SBATCH --cpus-per-task 6
#SBATCH --output /projects/ovcare/classification/cchen/ml/slurm/test.%j.out
#SBATCH --error  /projects/ovcare/classification/cchen/ml/slurm/test.%j.out
#SBATCH -w {w}
#SBATCH -p {p}
#SBATCH --gres=gpu:1
#SBATCH --time=3-00:00:00
#SBATCH --chdir /projects/ovcare/classification/cchen/ml/singularity_extract_annotated_patches
#SBATCH --mem=30G

PATH="{$PATH}:/opt/singularity-3.4.0/bin"
cd /projects/ovcare/classification/cchen/ml/singularity_extract_annotated_patches
source /projects/ovcare/classification/cchen/{pyenv}

mkdir -p extract_annotated_patches/tests/outputs
mkdir -p extract_annotated_patches/tests/mock/patches
# pytest -s -vv extract_annotated_patches/tests/test_auxiliary.py
pytest -s -vv extract_annotated_patches/tests/test_extract_annotated_patches.py
# pytest -s -vv extract_annotated_patches/tests/
