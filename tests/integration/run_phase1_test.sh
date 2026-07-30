#!/usr/bin/env bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
# Integration test: phase-1 smoke test (preparation + xtb_conf)
# Uses methane (C) and ethane (CC) from resources/input.csv.
# Requires: Singularity, Snakemake >=8 on the host.
# Does NOT require: Gaussian, Arvados credentials.
#
# Usage (from workflow/):
#   bash ../tests/integration/run_phase1_test.sh /path/to/qm-lux.sif
#
# Or set QM_LUX_SIF env var and omit the argument:
#   QM_LUX_SIF=/path/to/qm-lux.sif bash ../tests/integration/run_phase1_test.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMK_DIR="$(cd "$SCRIPT_DIR/../../workflow" && pwd)"

# ---------- resolve SIF path ----------
SIF="${1:-${QM_LUX_SIF:-}}"
if [[ -z "$SIF" ]]; then
    echo "ERROR: Provide the path to qm-lux.sif as argument or set QM_LUX_SIF."
    echo "  Usage: $0 /path/to/qm-lux.sif"
    exit 1
fi
if [[ ! -f "$SIF" ]]; then
    echo "ERROR: SIF file not found: $SIF"
    exit 1
fi
SIF="$(realpath "$SIF")"
SIF_DIR="$(dirname "$SIF")"

# ---------- temporary results directory ----------
RESULTS_DIR="$(mktemp -d "${SMK_DIR}/results_integration_test.XXXXXX")"
trap 'echo "Cleaning up $RESULTS_DIR"; rm -rf "$RESULTS_DIR"' EXIT

# ---------- generate config on the fly ----------
CONFIG_FILE="$(mktemp /tmp/qm_lux_integration_test.XXXXXX.yaml)"
trap 'rm -f "$CONFIG_FILE"' EXIT

# Bind mounts: SIF dir + $HOME (Snakemake passes --home=<canonical-CWD> to
# Singularity, which disables the default $HOME auto-mount; bind it explicitly).
# Add extra --bind entries here if your SIF or results live outside both paths.
BIND_MOUNTS="$SIF_DIR --bind $HOME"

cat > "$CONFIG_FILE" <<EOF
input_file: resources/input.csv
results_directory: ${RESULTS_DIR}
crest_threads: 2
gaussian_threads: 4
qmlux_image: ${SIF}
model_github_url: https://github.com/bedapub/QM-LUX/releases/download/v1.0.0
model_method: RF
model_descriptor: fp_Morganclean__descriptors_SMILES_CLEAN__100-1000
singularity_args_param: "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}"
EOF

echo "=== QM-LUX integration test (phase 1) ==="
echo "SIF:     $SIF"
echo "Results: $RESULTS_DIR"
echo "Config:  $CONFIG_FILE"
echo ""

# ---------- run snakemake phase 1 ----------
cd "$SMK_DIR"
snakemake --snakefile Snakefile \
    --configfile "$CONFIG_FILE" \
    --use-singularity \
    --singularity-prefix "$SIF_DIR" \
    --singularity-args "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}" \
    --cores 2 \
    --latency-wait 30 \
    --rerun-incomplete \
    xtb_conf

# ---------- validate outputs ----------
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

# xtb_input.pkl must exist
check "preparation: xtb_input.pkl created" \
    "[[ -f '${RESULTS_DIR}/data_ml/xtb_input.pkl' ]]"

# Two molecule directories (0/0/ and 0/1/)
check "xtb_conf: molecule 0 directory exists" \
    "[[ -d '${RESULTS_DIR}/data_ml/0/0' ]]"
check "xtb_conf: molecule 1 directory exists" \
    "[[ -d '${RESULTS_DIR}/data_ml/0/1' ]]"

# SDF files for methane (molecule 0) and ethane (molecule 1)
check "methane (C): SDF file present" \
    "[[ -f '${RESULTS_DIR}/data_ml/0/0/0.sdf' ]]"
check "ethane (CC): SDF file present" \
    "[[ -f '${RESULTS_DIR}/data_ml/0/1/1.sdf' ]]"

# Each SDF should contain exactly 1 conformer (MMFF94s pruning produces 1 for CH4 and C2H6).
# Use grep -cF (fixed-string) to count literal $$$$ record terminators; || true
# prevents exit-1 (no matches) from aborting the script under set -e.
cnt0=$(grep -cF '$$$$' "${RESULTS_DIR}/data_ml/0/0/0.sdf" 2>/dev/null || true)
cnt1=$(grep -cF '$$$$' "${RESULTS_DIR}/data_ml/0/1/1.sdf" 2>/dev/null || true)
check "methane (C): exactly 1 conformer in SDF" "[[ ${cnt0:-0} -eq 1 ]]"
check "ethane (CC): exactly 1 conformer in SDF" "[[ ${cnt1:-0} -eq 1 ]]"

# xtb_conf.out log file
check "xtb_conf.out log created" \
    "[[ -f '${RESULTS_DIR}/xtb_conf.out' ]]"

echo ""
echo "Results: $PASS passed, $FAIL failed."

if [[ $FAIL -gt 0 ]]; then
    echo "INTEGRATION TEST FAILED"
    exit 1
fi

echo "All checks passed."
exit 0
