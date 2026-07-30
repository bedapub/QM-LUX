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
  echo "  1. number of cores for g16, default 8"
  echo "  2. amount of memory for g16, default 20GB"
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
  echo "  Lmod/module system:  module load Gaussian/16.B.01"
  echo "  Manual install:      source /path/to/g16/bsd/g16.profile"
  exit 1
fi

cd "$temp_dir" \
  && g16 < "$gjf_file" > "$out_file" \
  && cd "$workdir"

# Clean up the temporary directory
rm -rf "$temp_dir"

exit 0
