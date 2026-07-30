#!/usr/bin/env bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
# Smoke test with alternate molecules (formaldehyde C=O, acetylene C#C).
# No reference comparison — just checks that all steps complete and both
# molecules appear in summary.csv as SUCCESS.
#
# Usage (from workflow/):
#   bash ../tests/integration/run_alt_test.sh /path/to/qm-lux.sif [cores] [model_dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMK_DIR="$(cd "$SCRIPT_DIR/../../workflow" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v g16 &>/dev/null; then
    echo "ERROR: g16 not found in PATH."
    exit 1
fi

SIF="${1:-${QM_LUX_SIF:-}}"
CORES="${2:-4}"
MODEL_DIR="${3:-${QM_LUX_MODEL_DIR:-}}"

if [[ -z "$SIF" ]]; then
    echo "ERROR: Provide the path to qm-lux.sif as argument or set QM_LUX_SIF."
    exit 1
fi
if [[ ! -f "$SIF" ]]; then
    echo "ERROR: SIF file not found: $SIF"
    exit 1
fi
SIF="$(realpath "$SIF")"
SIF_DIR="$(dirname "$SIF")"

if [[ -n "$MODEL_DIR" ]]; then
    MODEL_DIR="$(realpath "$MODEL_DIR")"
fi

RESULTS_DIR="$(mktemp -d "${SMK_DIR}/results_alt_test.XXXXXX")"
trap 'echo "Cleaning up $RESULTS_DIR"; rm -rf "$RESULTS_DIR"' EXIT

CONFIG_FILE="$(mktemp /tmp/qm_lux_alt_test.XXXXXX.yaml)"
trap 'rm -f "$CONFIG_FILE"' EXIT

BIND_MOUNTS="$SIF_DIR --bind $HOME --bind $REPO_ROOT"
if [[ -n "$MODEL_DIR" ]]; then
    BIND_MOUNTS="$BIND_MOUNTS --bind $MODEL_DIR"
fi

if [[ -n "$MODEL_DIR" ]]; then
    MODEL_CONFIG="model_local_folder: ${MODEL_DIR}"
else
    MODEL_CONFIG="model_github_url: https://github.com/bedapub/QM-LUX/releases/download/v1.0.0"
fi

cat > "$CONFIG_FILE" <<EOF
input_file: resources/input_alt.csv
results_directory: ${RESULTS_DIR}
crest_threads: 4
gaussian_threads: ${CORES}
qmlux_image: ${SIF}
${MODEL_CONFIG}
model_method: RF
model_descriptor: fp_Morganclean__descriptors_SMILES_CLEAN__100-1000
singularity_args_param: "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}"
EOF

echo "=== QM-LUX alt molecule test (formaldehyde + acetylene) ==="
echo "SIF:     $SIF"
echo "Results: $RESULTS_DIR"
echo "Config:  $CONFIG_FILE"
echo "Cores:   $CORES"
echo ""

cd "$SMK_DIR"

START=$(date +%s)

echo "--- Phase 1: preparation and xtb configuration ---"
snakemake --snakefile Snakefile \
    --configfile "$CONFIG_FILE" \
    --use-singularity \
    --singularity-prefix "$SIF_DIR" \
    --singularity-args "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}" \
    --cores "$CORES" \
    --latency-wait 30 \
    --rerun-incomplete \
    xtb_conf

echo ""
echo "--- Phase 2: Gaussian, prediction, results ---"
snakemake --snakefile Snakefile \
    --configfile "$CONFIG_FILE" \
    --use-singularity \
    --singularity-prefix "$SIF_DIR" \
    --singularity-args "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}" \
    --cores "$CORES" \
    --latency-wait 30 \
    --rerun-incomplete \
    all

END=$(date +%s)
ELAPSED=$(( END - START ))

DESCRIPTOR="fp_Morganclean__descriptors_SMILES_CLEAN__100-1000"
RESULTS_ML_DIR="${RESULTS_DIR}/${DESCRIPTOR}.RF"

PASS=0
FAIL=0

check() {
    local label="$1"
    local condition="$2"
    if eval "$condition"; then
        echo "[PASS] $label"
        ((PASS++)) || true
    else
        echo "[FAIL] $label"
        ((FAIL++)) || true
    fi
}

echo ""
echo "--- Validation ---"
check "summary.csv: formaldehyde (CPD-A01) SUCCESS" \
    "grep -q 'CPD-A01,SUCCESS' '${RESULTS_DIR}/summary.csv'"
check "summary.csv: acetylene   (CPD-A02) SUCCESS" \
    "grep -q 'CPD-A02,SUCCESS' '${RESULTS_DIR}/summary.csv'"
check "no failed molecules" \
    "[[ ! -s '${RESULTS_ML_DIR}/failed_molecules.txt' ]]"
check "results_ML.csv exists" \
    "[[ -f '${RESULTS_ML_DIR}/results_ML.csv' ]]"
check "HTML report exists" \
    "[[ -f '${RESULTS_ML_DIR}/results_ML_with_mol_UV.html' ]]"

echo ""
echo "Wall time: ${ELAPSED}s"
echo "Results: $PASS passed, $FAIL failed."

if [[ $FAIL -gt 0 ]]; then
    echo "ALT MOLECULE TEST FAILED"
    exit 1
fi

echo "All checks passed."
exit 0
