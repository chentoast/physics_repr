#!/usr/bin/env bash
#SBATCH --job-name=EventsPlinko
#SBATCH --output=SlurmOut/evplinko_%A_%a.out
#SBATCH --error=SlurmOut/evplinko_%A_%a.err
#SBATCH --mem=1G
#SBATCH -c 1
#SBATCH -t 1-0
#SBATCH --array=[1-100]

python parallel_plinko.py
rm core.*
