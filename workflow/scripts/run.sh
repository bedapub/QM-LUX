#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0

set -uo pipefail
# NOTE: deliberately NOT `set -e`. The two snakemake invocations below run with
# --keep-going and their exit codes are accumulated and checked together, so an
# early abort would skip the combined status check and the report step.

function usage()
{
  echo ""
  echo "Usage: run.sh <config.yaml> [target] [cores]"
  echo ""
  echo "1 input argument(s) required:"
  echo "  1. input config.yaml file"
  echo ""
  echo "2 optional argument(s):"
  echo "  1. target rule -- run only up to this rule (default: full pipeline)"
  echo "  2. nr of cores -- giving this switches to a LOCAL run"
  echo ""
  echo "Execution mode is chosen by the number of arguments:"
  echo "  run.sh cfg.yaml                 cluster (SLURM profile), full pipeline"
  echo "  run.sh cfg.yaml xtb_conf        cluster (SLURM profile), stop after xtb_conf"
  echo "  run.sh cfg.yaml xtb_conf 8      local with 8 cores, stop after xtb_conf"
  echo "  run.sh cfg.yaml all 8           local with 8 cores, full pipeline"
  echo ""
  echo "The HTML report is generated only for a completed full run (target 'all'"
  echo "or no target); a run stopping at an intermediate rule has nothing to report."
  echo ""
  echo "Environment variables:"
  echo "  QM_LUX_SIF_DIR  directory containing qm-lux.sif (default: repo root)"
  echo ""
}

if [[ $# -lt 1 ]]; then usage && exit 1; fi
if [[ $# -gt 3 ]]; then
  echo "Error: too many arguments ($# given, at most 3 accepted)." >&2
  usage && exit 1
fi

config_file=$1
if [[ ! -f "$config_file" ]]; then
  echo "Error: config file not found: $config_file" >&2
  usage && exit 1
fi

# Target rule. Empty means "full pipeline" (both phases, see below).
target="${2:-}"
if [[ "$target" =~ ^[0-9]+$ ]]; then
  echo "Error: target '$target' looks like a core count." >&2
  echo "       The target rule comes before the core count:" >&2
  echo "         run.sh $config_file <target> $target" >&2
  usage && exit 1
fi

# Cores are given only for a local run; without them we submit to the cluster.
run_local=false
cores=""
if [[ $# -gt 2 ]]; then
  run_local=true
  cores=$3
  if [[ ! "$cores" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: cores must be a positive integer, got '$cores'." >&2
    usage && exit 1
  fi
fi

# snakemake runs on the HOST (it is not shipped in the container image), so a
# missing snakemake is an environment problem, not a workflow failure. Catch it
# here rather than letting two 'command not found' exits surface as a generic
# "one or more snakemake processes failed".
if ! command -v snakemake &>/dev/null; then
  echo "Error: snakemake not found in PATH." >&2
  echo "       Activate the conda/virtual environment that provides it before" >&2
  echo "       calling run.sh (see README, 'Running the workflow')." >&2
  exit 1
fi

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

function run_snakemake()
{
  # shellcheck disable=SC2086  # $snakemake_options and $singularity_args_param
  #                              are intentionally word-split into flags.
  snakemake --snakefile $snakemake_file \
         --configfile $config_file \
         $snakemake_options \
         --use-singularity \
         --singularity-prefix "$QM_LUX_SIF_DIR" \
         --singularity-args "$singularity_args_param" \
         -- "$1"
}

snakemake_exit_code=0

if [[ -n "$target" ]]; then
    # An explicit target: run exactly that and stop. Note 'all' is a valid
    # target here and does NOT re-run phase 1 -- this is the documented
    # phase-2 invocation, used after Gaussian has produced its log.out files.
    echo "Run snakemake up to target: $target"
    run_snakemake "$target"
    snakemake_exit_code=$?
else
    # No target: run both phases back to back. Phase 2 can only succeed if
    # Gaussian has already been run for this results directory (see the
    # two-phase section in the README), so on a cold run part 2 is expected
    # to do nothing.
    echo "Run snakemake part 1: preparation and xtb configuration"
    run_snakemake xtb_conf
    snakemake_exit_code=$?

    echo "Run snakemake part 2: prediction"
    run_snakemake all
    # Combine exit status of part 1 and part 2
    snakemake_exit_code=$((snakemake_exit_code + $?))
fi

# Ensure the script exits with an error if any snakemake command failed
if [[ $snakemake_exit_code -ne 0 ]]; then
    echo "Error: One or more snakemake processes failed."
    exit 1
fi

# Generate the HTML report only when the whole pipeline has completed -- i.e.
# for a full run (no target) or an explicit 'all'. A run stopping at an
# intermediate rule has no predictions to report on.
if [[ -z "$target" || "$target" == "all" ]]; then
    report_file="${results_directory}.html"
    echo "Generating report -> $report_file"
    bash "$(dirname "${BASH_SOURCE[0]}")/run_report.sh" "$config_file" "$report_file"
else
    echo "Target '$target' completed; skipping report generation (not a full run)."
fi

exit 0
