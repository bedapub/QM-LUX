#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0

function usage()
{
  echo ""
  echo "1 input argument(s) required:"
  echo "  1. input config.yaml file"
  echo ""
  echo "2 optional argument(s):"
  echo "  1. target rule for local run"
  echo "  2. nr of cores for local run"
  echo ""
  echo "Environment variables:"
  echo "  QM_LUX_SIF_DIR  directory containing qm-lux.sif (default: repo root)"
  echo ""
}

run_local=false
if [[ $# -lt 1 ]]; then usage && exit 1; fi
if [[ $# -gt 1 ]]; then
  run_local=true;
  if [[ $# -gt 2 ]]; then
    cores=$3;
  else
    cores=1;
  fi
fi

config_file=$1
if [ ! -e $config_file ]; then usage && exit 1; fi

results_directory="$(grep -w -m1 '^results_directory:' "$config_file" | awk '{print $2}' | sed "s/'//g")"
model_method="$(grep -w -m1 '^model_method:' "$config_file" | awk '{print $2}' | sed "s/'//g")"
model_descriptor="$(grep -w -m1 '^model_descriptor:' "$config_file" | awk '{print $2}' | sed "s/'//g")"

singularity_args_param="$(grep -w -m1 '^singularity_args_param:' "$config_file" | sed "s/singularity_args_param://g" | xargs)"

snakemake_file=Snakefile
# Singularity image directory: override with QM_LUX_SIF_DIR env variable if set.
# Default: repository root (two levels above this script), which is where
# `singularity pull` places qm-lux.sif by default.
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QM_LUX_SIF_DIR="${QM_LUX_SIF_DIR:-$(cd "$_script_dir/../.." && pwd)}"

echo "results_directory=$results_directory"
echo "model_method=$model_method"
echo "model_descriptor=$model_descriptor"

snakemake_options="--latency-wait 10 --rerun-incomplete --keep-going "
snakemake_options="$snakemake_options --printshellcmds "

if $run_local; then
    snakemake_options="$snakemake_options --cores $cores"
    echo "Run the pipeline locally with $cores cores"
else
    snakemake_options="$snakemake_options --jobs 100 --workflow-profile profiles/slurm --slurm-keep-successful-logs"
fi

echo "Run snakemake part 1: preparation and xtb configuration"
snakemake --snakefile $snakemake_file \
       --configfile $config_file \
       $snakemake_options \
       --use-singularity \
       --singularity-prefix "$QM_LUX_SIF_DIR" \
       --singularity-args "$singularity_args_param" \
       xtb_conf

# Capture exit status of part 1
snakemake_exit_code=$?

echo "Run snakemake part 2: prediction"
snakemake --snakefile $snakemake_file \
       --configfile $config_file \
       $snakemake_options \
       --use-singularity \
       --singularity-prefix "$QM_LUX_SIF_DIR" \
       --singularity-args "$singularity_args_param" \
       all

# Combine exit status of part 1 and part 2
snakemake_exit_code=$((snakemake_exit_code + $?))

# Ensure the script exits with an error if any snakemake command failed
if [[ $snakemake_exit_code -ne 0 ]]; then
    echo "Error: One or more snakemake processes failed."
    exit 1
fi

# Generate HTML report after a successful full run.
report_file="${results_directory}.html"
echo "Generating report -> $report_file"
bash "$(dirname "${BASH_SOURCE[0]}")/run_report.sh" "$config_file" "$report_file"

exit 0
