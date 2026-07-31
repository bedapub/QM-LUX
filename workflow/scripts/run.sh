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
  echo "       run.sh <config.yaml> [cores]"
  echo ""
  echo "1 input argument(s) required:"
  echo "  1. input config.yaml file"
  echo ""
  echo "2 optional argument(s):"
  echo "  1. target rule -- stop after this rule (default: run everything)"
  echo "  2. nr of cores -- giving this switches to a LOCAL run"
  echo ""
  echo "Common cases -- both run the COMPLETE pipeline, Gaussian included:"
  echo "  run.sh cfg.yaml                 cluster (SLURM profile)"
  echo "  run.sh cfg.yaml 8               local with 8 cores"
  echo ""
  echo "The core count may also be given after an explicit 'all', which means"
  echo "the same thing as omitting the target:"
  echo "  run.sh cfg.yaml all             cluster (SLURM profile)"
  echo "  run.sh cfg.yaml all 8           local with 8 cores"
  echo ""
  echo "Stopping early is for debugging a single stage:"
  echo "  run.sh cfg.yaml xtb_conf        cluster, stop after xtb_conf"
  echo "  run.sh cfg.yaml xtb_conf 8      local with 8 cores, stop after xtb_conf"
  echo ""
  echo "The HTML report is generated for a complete run only; a run stopping at"
  echo "an intermediate rule has no predictions to report on."
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

# Argument 2 is either a target rule or, when it is a number, the core count --
# so that the common "run everything locally" case is just `run.sh cfg.yaml 8`
# and does not have to name a target at all.
target="${2:-}"
cores=""
if [[ "$target" =~ ^[0-9]+$ ]]; then
  if [[ $# -gt 2 ]]; then
    echo "Error: '$target' was read as a core count, so '$3' is unexpected." >&2
    echo "       Use either 'run.sh $config_file $target'" >&2
    echo "       or      'run.sh $config_file <target> $3'." >&2
    usage && exit 1
  fi
  cores=$target
  target=""
elif [[ $# -gt 2 ]]; then
  cores=$3
fi

# 'all' is the full pipeline, which is exactly what an empty target means. Treat
# them as the same thing so `run.sh cfg.yaml all 8` runs the complete pipeline
# rather than a single cold 'all' invocation -- see the two-invocation note below
# for why that distinction matters.
if [[ "$target" == "all" ]]; then
  target=""
fi

# Cores are given only for a local run; without them we submit to the cluster.
run_local=false
if [[ -n "$cores" ]]; then
  run_local=true
  if [[ ! "$cores" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: cores must be a positive integer, got '$cores'." >&2
    usage && exit 1
  fi
fi

# snakemake orchestrates the containers, so it has to be on the HOST -- the image
# does ship a snakemake env (Dockerfile), but that copy is not what drives this
# run. A missing host snakemake is an environment problem, not a workflow
# failure, so catch it here rather than letting two 'command not found' exits
# surface as a generic "one or more snakemake processes failed".
if ! command -v snakemake &>/dev/null; then
  echo "Error: snakemake not found in PATH." >&2
  echo "       Activate the conda/virtual environment that provides it before" >&2
  echo "       calling run.sh (see README, 'Running the workflow')." >&2
  exit 1
fi

# Gaussian check -- a WARNING, never a hard failure.
#
# 'gaussian_runner' is the one rule with no container: directive, so it needs g16
# on the host. Two reasons this must not be fatal:
#   * on a cluster the rule runs via SLURM on a COMPUTE node, which may provide
#     g16 even when the submit node's PATH does not;
#   * calculate_uvvis.sh already checks g16 at the point of use and errors there
#     with an actionable message.
# It is also irrelevant to targets that never reach gaussian_runner, so only warn
# for targets that do. Keep this list in sync with the Snakefile: these are the
# phase-1 rules upstream of gaussian_runner (plus 'model', which is independent).
phase1_targets=" preparation xtb_conf crest xtb model gaussian_preparation "
if [[ "$phase1_targets" != *" ${target:-} "* ]] && ! command -v g16 &>/dev/null; then
  echo "Warning: g16 not found in PATH." >&2
  echo "         The gaussian_runner rule runs on the host and needs Gaussian 16." >&2
  echo "         Ignore this if g16 is provided on the compute nodes rather than" >&2
  echo "         here; otherwise activate it (source /path/to/g16/bsd/g16.profile)" >&2
  echo "         before the Gaussian step. Continuing." >&2
fi

# Forward the Arvados token into the container.
#
# The 'model' rule runs inside the image and mode 3 reads $ARVADOS_API_TOKEN
# there, but the documented singularity_args_param includes --cleanenv, which
# strips the host environment -- so the plain variable never arrives and the
# rule fails on an unset variable. Singularity passes SINGULARITYENV_*-prefixed
# variables through even under --cleanenv, and strips the prefix on the way in,
# so exporting the prefixed name here makes $ARVADOS_API_TOKEN visible to the
# rule without weakening --cleanenv for anything else.
if [[ -n "${ARVADOS_API_TOKEN:-}" ]]; then
  export SINGULARITYENV_ARVADOS_API_TOKEN="$ARVADOS_API_TOKEN"
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
    # An intermediate target: run exactly that and stop. Only reachable for
    # targets other than 'all', which was normalised to "" above.
    echo "Running up to target: $target"
    run_snakemake "$target"
    snakemake_exit_code=$?
else
    # Complete run. This is deliberately TWO snakemake invocations, and it is an
    # internal implementation detail -- not two things the user has to run, and
    # not a manual Gaussian step in between. Gaussian is rule gaussian_runner and
    # is scheduled by snakemake in the second invocation like any other rule.
    #
    # Why two: rule uvvis derives its inputs by listing the per-molecule
    # directories under <results_directory>/data_ml/0/, and snakemake evaluates
    # that while BUILDING the DAG. On a cold run those directories do not exist
    # yet -- rule preparation creates them -- so a single invocation plans a DAG
    # with crest, xtb, gaussian_preparation and gaussian_runner missing entirely
    # and uvvis holding no inputs, which then fails at uvvis.
    #
    # Running the first invocation to completion puts the directories on disk;
    # because the second invocation is a separate PROCESS it re-evaluates the
    # listing and builds the complete DAG. Converting preparation to a snakemake
    # checkpoint would collapse this into one invocation and let this branch go
    # away; until then, do not "simplify" it into a single call.
    echo "Stage 1 of 2: preparation and conformer setup"
    run_snakemake xtb_conf
    snakemake_exit_code=$?

    echo "Stage 2 of 2: CREST/XTB, Gaussian, UV-Vis descriptors and prediction"
    run_snakemake all
    # Combine exit status of part 1 and part 2
    snakemake_exit_code=$((snakemake_exit_code + $?))
fi

# Ensure the script exits with an error if any snakemake command failed
if [[ $snakemake_exit_code -ne 0 ]]; then
    echo "Error: One or more snakemake processes failed."
    exit 1
fi

# Generate the HTML report only when the whole pipeline has completed. A run
# stopping at an intermediate rule has no predictions to report on. ('all' was
# normalised to an empty target above, so -z covers both spellings.)
if [[ -z "$target" ]]; then
    report_file="${results_directory}.html"
    echo "Generating report -> $report_file"
    bash "$(dirname "${BASH_SOURCE[0]}")/run_report.sh" "$config_file" "$report_file"
else
    echo "Target '$target' completed; skipping report generation (not a full run)."
fi

exit 0
