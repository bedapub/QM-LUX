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
  echo "Usage: run.sh <config.yaml> [--cores N] [--target RULE]"
  echo ""
  echo "Runs the complete QM-LUX pipeline -- conformer generation, CREST/XTB,"
  echo "Gaussian TD-DFT, UV-Vis descriptors, ML prediction and the HTML report."
  echo "Gaussian is part of the workflow; you do not run it yourself."
  echo ""
  echo "Required:"
  echo "  <config.yaml>       input configuration file"
  echo ""
  echo "Options:"
  echo "  --cores N           run LOCALLY on N cores."
  echo "                      Omit to submit through the SLURM profile."
  echo "  --target RULE       stop after RULE instead of running everything."
  echo "                      For debugging a single stage; 'all' means the"
  echo "                      full pipeline and is the same as omitting it."
  echo "  -h, --help          show this help and exit"
  echo ""
  echo "Examples:"
  echo "  run.sh cfg.yaml                        cluster, full pipeline"
  echo "  run.sh cfg.yaml --cores 8              local on 8 cores, full pipeline"
  echo "  run.sh cfg.yaml --target xtb_conf      cluster, stop after xtb_conf"
  echo "  run.sh cfg.yaml --target xtb_conf --cores 8"
  echo "                                         local on 8 cores, stop after xtb_conf"
  echo ""
  echo "Positional form (still supported, equivalent to the above):"
  echo "  run.sh cfg.yaml [target] [cores]       e.g. run.sh cfg.yaml xtb_conf 8"
  echo "  run.sh cfg.yaml [cores]                e.g. run.sh cfg.yaml 8"
  echo ""
  echo "The HTML report is generated for a complete run only; a run stopping at"
  echo "an intermediate rule has no predictions to report on."
  echo ""
  echo "Environment variables:"
  echo "  QM_LUX_SIF_DIR         directory containing qm-lux.sif (default: repo root)"
  echo "  QM_LUX_NO_AUTO_BIND    set to 1 to disable deriving Singularity --bind"
  echo "                         mounts from the paths named in the config file"
  echo "  QM_LUX_CLUSTER_PROFILE snakemake workflow profile used for a cluster run"
  echo "                         (default: profiles/slurm). Point this at your own"
  echo "                         profile directory to run on a non-SLURM scheduler."
  echo ""
}

# Argument parsing accepts named options and the original positional form. Named
# options win where both could apply, and giving the same thing twice is an error
# rather than a silent last-one-wins.
config_file=""
target=""
cores=""
target_set=false
cores_set=false
positional=()

# Rejects a missing value, and a value that is itself a flag -- otherwise
# `--target --cores 8` would silently take "--cores" as the rule name.
function need_value()
{
  # $1 = flag name, $2 = "has next arg" (true/false), $3 = next arg
  if [[ "$2" != true ]]; then
    echo "Error: $1 requires a value." >&2
    usage && exit 1
  fi
  if [[ "$3" == -* ]]; then
    echo "Error: $1 requires a value, got the flag '$3'." >&2
    usage && exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --target)
      [[ $# -gt 1 ]] && has_next=true || has_next=false
      need_value "--target" "$has_next" "${2:-}"
      if $target_set; then
        echo "Error: --target given more than once." >&2
        usage && exit 1
      fi
      target="$2"; target_set=true; shift 2
      ;;
    --target=*)
      if $target_set; then
        echo "Error: --target given more than once." >&2
        usage && exit 1
      fi
      target="${1#--target=}"
      if [[ -z "$target" ]]; then
        echo "Error: --target requires a value." >&2
        usage && exit 1
      fi
      target_set=true; shift
      ;;
    --cores)
      [[ $# -gt 1 ]] && has_next=true || has_next=false
      need_value "--cores" "$has_next" "${2:-}"
      if $cores_set; then
        echo "Error: --cores given more than once." >&2
        usage && exit 1
      fi
      cores="$2"; cores_set=true; shift 2
      ;;
    --cores=*)
      if $cores_set; then
        echo "Error: --cores given more than once." >&2
        usage && exit 1
      fi
      cores="${1#--cores=}"
      if [[ -z "$cores" ]]; then
        echo "Error: --cores requires a value." >&2
        usage && exit 1
      fi
      cores_set=true; shift
      ;;
    -*)
      echo "Error: unknown option '$1'." >&2
      usage && exit 1
      ;;
    *)
      positional+=("$1")
      shift
      ;;
  esac
done

n_pos=${#positional[@]}
if [[ $n_pos -lt 1 ]]; then usage && exit 1; fi
if [[ $n_pos -gt 3 ]]; then
  echo "Error: too many positional arguments ($n_pos given, at most 3 accepted)." >&2
  usage && exit 1
fi

config_file="${positional[0]}"
if [[ ! -f "$config_file" ]]; then
  echo "Error: config file not found: $config_file" >&2
  usage && exit 1
fi

# Positional 2 is either a target rule or, when it is a number, the core count,
# so that `run.sh cfg.yaml 8` needs no target. A rule genuinely named like a
# number is still reachable with --target.
if [[ $n_pos -ge 2 ]]; then
  pos2="${positional[1]}"
  if [[ "$pos2" =~ ^[0-9]+$ ]]; then
    if [[ $n_pos -gt 2 ]]; then
      echo "Error: '$pos2' was read as a core count, so '${positional[2]}' is unexpected." >&2
      echo "       Use either 'run.sh $config_file $pos2'" >&2
      echo "       or      'run.sh $config_file <target> $pos2'." >&2
      usage && exit 1
    fi
    if $cores_set; then
      echo "Error: core count given twice (--cores $cores and positional $pos2)." >&2
      usage && exit 1
    fi
    cores="$pos2"; cores_set=true
  else
    if $target_set; then
      echo "Error: target given twice (--target $target and positional $pos2)." >&2
      usage && exit 1
    fi
    target="$pos2"; target_set=true
    if [[ $n_pos -ge 3 ]]; then
      if $cores_set; then
        echo "Error: core count given twice (--cores $cores and positional ${positional[2]})." >&2
        usage && exit 1
      fi
      cores="${positional[2]}"; cores_set=true
    fi
  fi
fi

# 'all' is the full pipeline, which is exactly what an empty target means. Treat
# them as the same thing so `--target all` runs the complete pipeline rather than
# a single cold 'all' invocation -- see the two-invocation note below for why
# that distinction matters.
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

# Resolve the working directory to its physical path before doing anything else.
#
# Singularity takes the container's working directory from $PWD (the LOGICAL path,
# which keeps symlinks), while snakemake computes the --home bind from getcwd()
# (the PHYSICAL path, with symlinks resolved). If the workflow directory was
# entered through a symlink the two disagree, and singularity then silently
# fabricates an empty directory tree at the logical path inside the container --
# no warning -- so every relative path in every rule resolves into an empty
# phantom directory. The symptom is a baffling "No such file or directory" for a
# file that plainly exists on the host.
#
# This is the same directory either way, so the change is safe: the Snakefile,
# config/, the config file argument and the .sif path all still resolve.
if [[ "$PWD" != "$(pwd -P)" ]]; then
  cd -P . || exit 1
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

# ── Derive bind mounts from the paths configured in the config file ─────────
#
# A container sees only what is bound into it, so a configured path outside the
# working directory is invisible unless it is bound. The example config gets away
# with `--cleanenv --bind /tmp` only because some sites list `bind path =
# /projects` (or /gpfs, /scratch) in singularity.conf and mount those
# automatically. That is site configuration this repository does not control: on
# a default singularity.conf the very same config fails to find
# model_local_folder and qmlux_image. Deriving the mounts removes that
# dependency.
#
# singularity_args_param stays authoritative -- whatever it lists is kept as
# given, and a path already covered by it, or by the working directory (which
# snakemake binds as the container home), is skipped rather than repeated. Set
# QM_LUX_NO_AUTO_BIND=1 to turn the derivation off.
#
# The keys are an allow-list on purpose: model_github_url and
# model_arv_keepweb_url hold URLs, and model_descriptor is not a path at all, so
# no "looks like a path" test would be safe. 'file' means bind the containing
# directory and 'dir' the path itself -- fixed per key rather than decided by
# stat, because results_directory does not exist yet on a cold run.
_bind_spec=(
  "input_file:file"
  "results_directory:dir"
  "model_local_folder:dir"
  "chirality_current_df:file"
  "qmlux_image:file"
)

# Nearest existing ancestor of $1; fails if the walk reaches "/". A bind source
# that does not exist is FATAL, not skipped -- singularity aborts with
# "container creation failed: ... mount source ... doesn't exist" -- and
# results_directory legitimately does not exist before the first run.
function nearest_existing()
{
  local p="$1"
  while [[ "$p" != "/" && ! -e "$p" ]]; do
    p="$(dirname "$p")"
  done
  [[ "$p" == "/" ]] && return 1
  printf '%s\n' "$p"
}

# True when $1 is $2 or lies inside it.
function covered_by()
{
  [[ "$1" == "$2" || "$1" == "$2"/* ]]
}

if [[ "${QM_LUX_NO_AUTO_BIND:-0}" != "1" ]]; then
  # What the container can already reach: the working directory, plus everything
  # the config's own --bind entries cover. Those values may be comma-separated
  # and may carry :dest[:ro], hence the splitting below.
  _covered=( "$PWD" )
  # shellcheck disable=SC2206  # deliberate word-splitting, as everywhere else
  #                              singularity_args_param is handled.
  _sap=( $singularity_args_param )
  _i=0
  while [[ $_i -lt ${#_sap[@]} ]]; do
    _val=""
    case "${_sap[$_i]}" in
      --bind|-B) _val="${_sap[$((_i + 1))]:-}"; _i=$((_i + 2)) ;;
      --bind=*)  _val="${_sap[$_i]#--bind=}";   _i=$((_i + 1)) ;;
      *)                                        _i=$((_i + 1)) ;;
    esac
    [[ -z "$_val" ]] && continue
    IFS=',' read -ra _parts <<< "$_val"
    for _p in "${_parts[@]}"; do
      _p="${_p%%:*}"
      [[ -n "$_p" ]] && _covered+=( "$(realpath -m "$_p" 2>/dev/null || printf '%s' "$_p")" )
    done
  done

  _derived=()
  for _entry in "${_bind_spec[@]}"; do
    _key="${_entry%%:*}"
    _kind="${_entry##*:}"
    _raw="$(grep -w -m1 "^${_key}:" "$config_file" | awk '{print $2}' | sed "s/['\"]//g")"
    [[ -z "$_raw" ]] && continue
    [[ "$_raw" == *"://"* ]] && continue   # a URL, not a path
    [[ "$_kind" == "file" ]] && _raw="$(dirname "$_raw")"
    # realpath, not the literal string: binding a path that still contains a
    # symlink reproduces the $PWD problem handled above -- singularity would
    # fabricate an empty directory inside the container.
    _abs="$(realpath -m "$_raw" 2>/dev/null)" || continue
    if ! _abs="$(nearest_existing "$_abs")"; then
      echo "Warning: not binding '$_key' -- no existing ancestor of '$_raw'." >&2
      continue
    fi
    _derived+=( "$_abs" )
  done

  # An ancestor sorts before its descendants, so walking the sorted list and
  # skipping anything already covered keeps the set minimal and avoids
  # singularity's "destination is already in the mount point list" warning.
  _added=()
  while IFS= read -r _abs; do
    [[ -z "$_abs" ]] && continue
    _skip=false
    for _c in "${_covered[@]}"; do
      if covered_by "$_abs" "$_c"; then _skip=true; break; fi
    done
    $_skip && continue
    _covered+=( "$_abs" )
    _added+=( "$_abs" )
    singularity_args_param="$singularity_args_param --bind $_abs"
  done < <(printf '%s\n' ${_derived[@]+"${_derived[@]}"} | sort -u)

  if [[ ${#_added[@]} -gt 0 ]]; then
    echo "Auto-bound from $config_file: ${_added[*]}"
  fi
fi

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
    # --executor local is explicit on purpose. A site-wide profile (anything in
    # $SNAKEMAKE_PROFILE, e.g. a cluster module's default) can set "executor:
    # slurm", and that applies to EVERY snakemake call on the host -- including
    # this one. Measured: without this flag, `--cores 4` still submitted xtb_conf
    # to SLURM, so the local/cluster switch below silently did nothing. The
    # command line wins over a profile, so naming the executor here restores it.
    snakemake_options="$snakemake_options --cores $cores --executor local"
    echo "Run the pipeline locally with $cores cores"
else
    # The cluster profile is overridable so this is not SLURM-only: a site with
    # LSF/SGE/PBS can point QM_LUX_CLUSTER_PROFILE at a profile of its own that
    # sets the matching executor. The default ships with the repo and declares
    # "executor: slurm" itself, so cluster mode does not depend on a site-wide
    # profile to actually reach a scheduler.
    cluster_profile="${QM_LUX_CLUSTER_PROFILE:-profiles/slurm}"
    if [[ ! -f "$cluster_profile/config.yaml" ]]; then
      echo "Error: cluster profile '$cluster_profile' has no config.yaml." >&2
      echo "       Set QM_LUX_CLUSTER_PROFILE to a snakemake profile directory," >&2
      echo "       or pass --cores N to run locally." >&2
      exit 1
    fi
    snakemake_options="$snakemake_options --jobs 100 --workflow-profile $cluster_profile"
    echo "Submit the pipeline through profile: $cluster_profile"

    # --slurm-keep-successful-logs is contributed by snakemake-executor-plugin-slurm,
    # NOT by snakemake core, so it only parses when that plugin is installed. Passing
    # it unconditionally makes a cluster run abort at argument parsing with
    # "snakemake: error: unrecognized arguments: --slurm-keep-successful-logs"
    # on any host whose snakemake lacks the plugin -- an error about a flag the user
    # never typed. Add it only when the snakemake being used actually advertises it.
    if snakemake --help 2>/dev/null | grep -q -- '--slurm-keep-successful-logs'; then
        snakemake_options="$snakemake_options --slurm-keep-successful-logs"
    elif [[ "$cluster_profile" == "profiles/slurm" ]]; then
        # The default profile asks for "executor: slurm", which without the plugin
        # fails at argument parsing ("invalid choice: 'slurm'"). Say so up front --
        # that error names --executor, a flag the user never typed.
        echo "Warning: this snakemake has no SLURM executor plugin" >&2
        echo "         (snakemake-executor-plugin-slurm), so the default cluster" >&2
        echo "         profile cannot work and the run will fail with" >&2
        echo "         \"--executor/-e: invalid choice: 'slurm'\"." >&2
        echo "         Install the plugin, set QM_LUX_CLUSTER_PROFILE to a profile" >&2
        echo "         for your scheduler, or pass --cores N to run locally." >&2
    fi
fi

function run_snakemake()
{
  # The target is passed WITHOUT a '--' separator, deliberately. Snakemake appends
  # arguments derived from any active profile AFTER the command line it was given,
  # and everything following '--' is parsed as a positional target -- so each
  # profile key turns into a phantom target and the run dies with e.g.
  # "MissingRuleException: No rule to produce xtb:mem_mb=20000". Since run.sh always
  # passes --workflow-profile in cluster mode, a '--' here breaks every cluster run.
  # ('--' IS needed for `snakemake --rulegraph <target>`, where the target would
  # otherwise be read as --rulegraph's value, but that is a different command.)
  # shellcheck disable=SC2086  # $snakemake_options and $singularity_args_param
  #                              are intentionally word-split into flags.
  snakemake --snakefile $snakemake_file \
         --configfile $config_file \
         $snakemake_options \
         --use-singularity \
         --singularity-prefix "$QM_LUX_SIF_DIR" \
         --singularity-args "$singularity_args_param" \
         "$1"
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
