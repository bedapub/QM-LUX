#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0

function usage()
{
  echo ""
  echo "2 input argument(s) required:"
  echo "  1. input gjf file name"
  echo "  2. output file name"
  echo ""
  echo "2 optional argument(s):"
  echo "  1. number of cores allocated to this job, default 8"
  echo "  2. amount of memory allocated to this job, default 20GB"
  echo ""
  echo "The optional arguments describe what the scheduler allocated. A .gjf"
  echo "header overrides GAUSS_PDEF/GAUSS_MDEF and the g16 -p=/-m= flags, so a"
  echo "%nprocshared above the allocated core count is capped (on a copy — the"
  echo "input file is not modified) and a %mem mismatch is warned about. With no"
  echo "header, the values are passed through as GAUSS_PDEF/GAUSS_MDEF."
  echo ""
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

gjf_file="$(realpath "$1")"
out_file="$(realpath "$2")"
if [[ $# -ge 3 ]]; then
  cores="$3"
else
  cores=8
fi
if [[ $# -ge 4 ]]; then
  memory="$4"
else
  memory=20GB
fi
workdir="$(pwd)"

set -e  # Exit immediately if a command exits with a non-zero status

# Check if the file size is not zero then exit
if [[ ! -s "$gjf_file" ]]; then
  touch $out_file
  exit 0
fi

# Create a temporary directory
temp_dir=$(mktemp -d)

# Check if the temporary directory was created successfully
if [[ ! -d "$temp_dir" ]]; then
  echo "Failed to create temporary directory"
  exit 1
fi

if ! command -v g16 &>/dev/null; then
  echo "ERROR: g16 not found in PATH. Activate Gaussian 16 before running this script."
  echo "  Manual install:      source /path/to/g16/bsd/g16.profile"
  exit 1
fi

# Gaussian resolves its resource request in this order: the .gjf Link0 header
# (%nprocshared / %mem) first, then GAUSS_PDEF / GAUSS_MDEF, then its built-in
# defaults. Measured on 16.B.01: a header of %nprocshared=2 wins over both
# GAUSS_PDEF=1 and `g16 -p=1`, and with the header absent GAUSS_PDEF is used.
#
# So exporting these covers a hand-written .gjf with no header, while the header
# written by `gaussian_preparation` — which is derived from the same config keys
# as this job's allocation — stays authoritative for workflow runs. Env vars are
# used rather than `g16 -p=/-m=` because an unknown flag would abort the run on a
# build that does not accept them, whereas an unread variable is harmless.
export GAUSS_PDEF="$cores"
export GAUSS_MDEF="$memory"

# Warn — do not fail — when the header does not match what was allocated. This
# is the situation that wastes an allocation or gets the job OOM-killed, and it
# is invisible in the Gaussian output unless you know to look for it.

# Normalise a Gaussian memory string (20GB, 20000MB, 20gb, bare 20 = MB per the
# Gaussian default) to MB, so 20GB and 20480MB do not read as a mismatch.
function mem_to_mb()
{
  local value unit number
  value="$(echo "$1" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')"
  number="${value%%[A-Z]*}"
  unit="${value#"$number"}"
  [[ "$number" =~ ^[0-9]+$ ]] || return 1
  case "$unit" in
    GB|GW) echo $(( number * 1024 )) ;;
    MB|MW|"") echo "$number" ;;
    KB|KW) echo $(( number / 1024 )) ;;
    *) return 1 ;;
  esac
}

header_nproc="$(grep -im1 '^%nprocshared=' "$gjf_file" | cut -d= -f2 | tr -d '[:space:]' || true)"
header_mem="$(grep -im1 '^%mem=' "$gjf_file" | cut -d= -f2 | tr -d '[:space:]' || true)"

# g16 reads its input from stdin, so it never sees this path — run from a copy so
# the header can be capped without touching the .gjf that Snakemake produced.
run_gjf="$temp_dir/$(basename "$gjf_file")"
cp "$gjf_file" "$run_gjf"

# Cap %nprocshared at the cores actually allocated. Snakemake lowers a rule's
# threads to fit --cores, so a local run with fewer cores than gaussian_threads
# gets a smaller allocation than the header — already baked in by an earlier
# rule — asks for. Capping here is what `crest` gets for free by passing
# {threads} on the command line. Never raised, only lowered: a larger header is
# the user's explicit request and honouring it cannot oversubscribe.
if [[ -n "$header_nproc" && "$header_nproc" =~ ^[0-9]+$ && "$cores" =~ ^[0-9]+$ ]]; then
  if (( header_nproc > cores )); then
    echo "NOTE: capping %nprocshared=$header_nproc to the $cores core(s) allocated to this job."
    echo "      Raise --cores, or lower gaussian_threads, to avoid the mismatch."
    sed -i "s/^%[Nn][Pp][Rr][Oo][Cc][Ss][Hh][Aa][Rr][Ee][Dd]=.*/%nprocshared=$cores/" "$run_gjf"
  fi
fi

# Memory is only warned about, not capped: nothing lowers resources.mem_mb the
# way --cores lowers threads, so a mismatch here means a hand-written .gjf or a
# config change since the .gjf was written — and silently shrinking %mem could
# push a job that would have completed into "insufficient memory" instead.
if [[ -n "$header_mem" ]]; then
  header_mb="$(mem_to_mb "$header_mem" || true)"
  alloc_mb="$(mem_to_mb "$memory" || true)"
  if [[ -n "$header_mb" && -n "$alloc_mb" && "$header_mb" != "$alloc_mb" ]]; then
    echo "WARNING: $gjf_file requests %mem=$header_mem but this job was allocated $memory."
    echo "         Gaussian obeys the header. Set gaussian_mem_gb in the config to change both."
  fi
fi

cd "$temp_dir" \
  && g16 < "$run_gjf" > "$out_file" \
  && cd "$workdir"

# Clean up the temporary directory
rm -rf "$temp_dir"

exit 0
