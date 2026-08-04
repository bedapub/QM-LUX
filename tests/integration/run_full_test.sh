#!/usr/bin/env bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
# Integration test: full workflow (all rules including Gaussian and ML prediction).
# Uses methane (C) and ethane (CC) from resources/input.csv and validates
# outputs against reference files in tests/integration/reference/:
#   results_ML_simple.csv   — ML predictions (pred exact, prob within 1e-4)
#   summary_simple.csv      — per-molecule pipeline status (exact match)
#   html_text_simple.txt    — HTML report text content, base64 images stripped (exact match)
#
# Requires: Singularity, Snakemake >=8, g16 (Gaussian 16) in PATH, Python 3.
#
# Usage (from workflow/):
#   bash ../tests/integration/run_full_test.sh /path/to/qm-lux.sif [cores] [model_dir]
#
# Or set QM_LUX_SIF / QM_LUX_MODEL_DIR and omit the arguments:
#   QM_LUX_SIF=/path/to/qm-lux.sif bash ../tests/integration/run_full_test.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMK_DIR="$(cd "$SCRIPT_DIR/../../workflow" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REF_CSV="$SCRIPT_DIR/reference/results_ML_simple.csv"
REF_SUMMARY="$SCRIPT_DIR/reference/summary_simple.csv"
REF_HTML_TEXT="$SCRIPT_DIR/reference/html_text_simple.txt"

# ---------- check prerequisites ----------
if ! command -v g16 &>/dev/null; then
    echo "ERROR: g16 not found in PATH. Activate Gaussian 16 before running:"
    echo "  Lmod/module system:  module load Gaussian/16.B.01"
    echo "  Manual install:      source /path/to/g16/bsd/g16.profile"
    exit 1
fi

# ---------- resolve SIF path, core count, and optional local model dir ----------
SIF="${1:-${QM_LUX_SIF:-}}"
CORES="${2:-4}"
MODEL_DIR="${3:-${QM_LUX_MODEL_DIR:-}}"

if [[ -z "$SIF" ]]; then
    echo "ERROR: Provide the path to qm-lux.sif as argument or set QM_LUX_SIF."
    echo "  Usage: $0 /path/to/qm-lux.sif [cores] [model_dir]"
    exit 1
fi
if [[ ! -f "$SIF" ]]; then
    echo "ERROR: SIF file not found: $SIF"
    exit 1
fi
SIF="$(realpath "$SIF")"
SIF_DIR="$(dirname "$SIF")"

if [[ -n "$MODEL_DIR" ]]; then
    if [[ ! -d "$MODEL_DIR" ]]; then
        echo "ERROR: model_dir not found: $MODEL_DIR"
        exit 1
    fi
    MODEL_DIR="$(realpath "$MODEL_DIR")"
fi

# ---------- temporary results directory and config ----------
RESULTS_DIR="$(mktemp -d "${SMK_DIR}/results_full_test.XXXXXX")"
REPORT_FILE="${RESULTS_DIR}.html"
CONFIG_FILE="$(mktemp /tmp/qm_lux_full_test.XXXXXX.yaml)"
trap 'echo "Cleaning up $RESULTS_DIR"; rm -rf "$RESULTS_DIR" "$REPORT_FILE"; rm -f "$CONFIG_FILE"' EXIT

BIND_MOUNTS="$SIF_DIR --bind $HOME --bind $REPO_ROOT"
if [[ -n "$MODEL_DIR" ]]; then
    # Avoid double-binding if MODEL_DIR is already under a bound path
    BIND_MOUNTS="$BIND_MOUNTS --bind $MODEL_DIR"
fi

# Model sourcing: local directory (arg 3) takes priority over GitHub release download.
if [[ -n "$MODEL_DIR" ]]; then
    MODEL_CONFIG="model_local_folder: ${MODEL_DIR}"
else
    MODEL_CONFIG="model_github_url: https://github.com/bedapub/QM-LUX/releases/download/v1.0.0"
fi

cat > "$CONFIG_FILE" <<EOF
input_file: resources/input.csv
results_directory: ${RESULTS_DIR}
crest_threads: 4
gaussian_threads: ${CORES}
qmlux_image: ${SIF}
${MODEL_CONFIG}
model_method: RF
model_descriptor: fp_Morganclean__descriptors_SMILES_CLEAN__100-1000
singularity_args_param: "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}"
EOF

echo "=== QM-LUX integration test (full workflow) ==="
echo "SIF:     $SIF"
echo "Results: $RESULTS_DIR"
echo "Config:  $CONFIG_FILE"
echo "Cores:   $CORES"
echo ""

# ---------- run snakemake ----------
cd "$SMK_DIR"

# One invocation covers the whole pipeline: 'checkpoint xtb_conf' in the
# Snakefile makes snakemake re-plan the DAG once the per-molecule directories
# exist, so the per-molecule rules and uvvis are no longer invisible on a cold
# run. This used to be two calls, xtb_conf then all.
echo "--- Running the full workflow ---"
snakemake --snakefile Snakefile \
    --configfile "$CONFIG_FILE" \
    --use-singularity \
    --singularity-prefix "$SIF_DIR" \
    --singularity-args "--cleanenv --bind /tmp --bind ${BIND_MOUNTS}" \
    --cores "$CORES" \
    --latency-wait 30 \
    --rerun-incomplete \
    all

# ---------- generate Snakemake HTML report ----------
echo ""
echo "--- Generating Snakemake HTML report ---"
bash "${SMK_DIR}/scripts/run_report.sh" "$CONFIG_FILE" "$REPORT_FILE"

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

echo ""
echo "--- Validation ---"

DESCRIPTOR="fp_Morganclean__descriptors_SMILES_CLEAN__100-1000"
RESULTS_ML_DIR="${RESULTS_DIR}/${DESCRIPTOR}.RF"
ACTUAL_CSV="${RESULTS_ML_DIR}/results_ML.csv"

check "summary.csv: methane (CPD-001) SUCCESS" \
    "grep -q 'CPD-001,SUCCESS' '${RESULTS_DIR}/summary.csv'"
check "summary.csv: ethane  (CPD-002) SUCCESS" \
    "grep -q 'CPD-002,SUCCESS' '${RESULTS_DIR}/summary.csv'"
check "no failed molecules" \
    "[[ ! -s '${RESULTS_ML_DIR}/failed_molecules.txt' ]]"
check "results_ML.csv exists" \
    "[[ -f '${ACTUAL_CSV}' ]]"
check "HTML report exists" \
    "[[ -f '${RESULTS_ML_DIR}/results_ML_with_mol_UV.html' ]]"
check "Snakemake report generated" \
    "[[ -f '$REPORT_FILE' ]]"

# ---------- reference comparison of ML predictions ----------
if [[ -f "${ACTUAL_CSV}" ]]; then
    cmp_result=$(python3 - <<PYEOF
import csv, sys, math

tol = 1e-4
ref_rows, actual_rows = [], []

with open("${REF_CSV}") as f:
    ref_rows = list(csv.DictReader(f))
with open("${ACTUAL_CSV}") as f:
    actual_rows = list(csv.DictReader(f))

failures = []

if len(ref_rows) != len(actual_rows):
    failures.append(f"row count: reference={len(ref_rows)}, actual={len(actual_rows)}")
else:
    labels = ["CPD-001/methane (row 0)", "CPD-002/ethane  (row 1)"]
    for i, (ref, act) in enumerate(zip(ref_rows, actual_rows)):
        lbl = labels[i] if i < len(labels) else f"row {i}"
        if ref["pred"] != act["pred"]:
            failures.append(f"{lbl}: pred expected={ref['pred']}, got={act['pred']}")
        diff = abs(float(ref["prob"]) - float(act["prob"]))
        if diff > tol:
            failures.append(
                f"{lbl}: prob diff={diff:.2e} > tol={tol} "
                f"(ref={float(ref['prob']):.8f}, got={float(act['prob']):.8f})"
            )

if failures:
    print("FAIL:" + "|".join(failures))
else:
    print("PASS")
PYEOF
)

    if [[ "$cmp_result" == "PASS" ]]; then
        echo "[PASS] results_ML.csv matches reference (pred exact, prob within 1e-4)"
        ((PASS++)) || true
    else
        echo "[FAIL] results_ML.csv does not match reference:"
        echo "$cmp_result" | sed 's/^FAIL://' | tr '|' '\n' | sed 's/^/         /'
        ((FAIL++)) || true
    fi
fi

# ---------- summary.csv exact match ----------
check "summary.csv matches reference (exact)" \
    "diff -q '${RESULTS_DIR}/summary.csv' '${REF_SUMMARY}' >/dev/null"

# ---------- HTML text content match (base64 image lines stripped) ----------
ACTUAL_HTML="${RESULTS_ML_DIR}/results_ML_with_mol_UV.html"
if [[ -f "${ACTUAL_HTML}" ]]; then
    actual_html_text=$(grep -v 'base64\|data:image' "${ACTUAL_HTML}")
    ref_html_text=$(cat "${REF_HTML_TEXT}")
    if [[ "$actual_html_text" == "$ref_html_text" ]]; then
        echo "[PASS] HTML text content matches reference (images excluded)"
        ((PASS++)) || true
    else
        echo "[FAIL] HTML text content does not match reference:"
        diff <(echo "$actual_html_text") <(echo "$ref_html_text") | head -20 | sed 's/^/         /'
        ((FAIL++)) || true
    fi
fi

echo ""
echo "Results: $PASS passed, $FAIL failed."

if [[ $FAIL -gt 0 ]]; then
    echo "INTEGRATION TEST FAILED"
    exit 1
fi

echo "All checks passed."
exit 0
