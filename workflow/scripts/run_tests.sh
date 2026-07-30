#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
# run_tests.sh — Integration test runner for the phototox/qm-lux Snakemake workflow.
#
# Runs both canonical test datasets through the full pipeline and validates
# that key output files exist and contain expected content.
#
# Usage (from snakemake_workflow/):
#   ./scripts/run_tests.sh [--clean] [--dry-run]
#
#   --clean    Remove existing results directories before running (force re-run)
#   --dry-run  Print what would be done without executing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; RESET='\033[0m'
pass() { echo -e "  ${GREEN}✔${RESET} $*"; }
fail() { echo -e "  ${RED}✘${RESET} $*"; FAILURES=$((FAILURES+1)); }
info() { echo -e "  ${YELLOW}→${RESET} $*"; }

# ── Options ───────────────────────────────────────────────────────────────────
CLEAN=false
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --clean)   CLEAN=true ;;
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

# ── Test definitions ──────────────────────────────────────────────────────────
# Each entry: "config_file|results_dir|model_subdir|expected_srns"
#   expected_srns: comma-separated list of SRN names expected in results_ML.csv
declare -a TESTS=(
  "config/config_isoquinoline.yaml|results_resources-input-isoquinoline_fp_Morganclean__descriptors_SMILES_CLEAN__100-1000|fp_Morganclean__descriptors_SMILES_CLEAN__100-1000.RF|Isoquinoline"
  "config/config_simple.yaml|results_resources-input-simple_fp_Morganclean__descriptors_SMILES_CLEAN__250-700|fp_Morganclean__descriptors_SMILES_CLEAN__250-700.RF|CPD-001,CPD-002"
)

# ── Helpers ───────────────────────────────────────────────────────────────────
check_file_exists() {
  local f="$1"
  if [[ -f "$f" ]]; then
    pass "$(basename "$f") exists"
  else
    fail "MISSING: $f"
  fi
}

check_file_nonempty() {
  local f="$1"
  if [[ -f "$f" && -s "$f" ]]; then
    pass "$(basename "$f") non-empty ($(wc -l < "$f") lines)"
  else
    fail "EMPTY or MISSING: $f"
  fi
}

check_results_csv() {
  local csv="$1"
  local expected_srns="$2"   # comma-separated
  if [[ ! -f "$csv" ]]; then
    fail "results_ML.csv missing: $csv"
    return
  fi
  local nrows
  nrows=$(tail -n +2 "$csv" | grep -c . || true)
  if [[ "$nrows" -eq 0 ]]; then
    fail "results_ML.csv has no data rows"
    return
  fi
  pass "results_ML.csv has $nrows data row(s)"
  # Check pred column contains 0 or 1 (phototoxicity class)
  if tail -n +2 "$csv" | awk -F',' '{print $2}' | grep -qE '^[01](\.[0-9]+)?$'; then
    pass "pred column contains valid class values"
  else
    fail "pred column has unexpected values"
  fi
  # Check prob column is between 0 and 1
  if tail -n +2 "$csv" | awk -F',' '{print $3}' | grep -qE '^0?\.[0-9]+$|^1(\.0+)?$'; then
    pass "prob column in [0,1] range"
  else
    fail "prob column out of expected [0,1] range"
  fi
}

check_failed_molecules() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    fail "failed_molecules.txt missing"
    return
  fi
  local n
  n=$(wc -l < "$f" || echo 0)
  if [[ "$n" -eq 0 ]]; then
    pass "failed_molecules.txt is empty (no failures)"
  else
    fail "failed_molecules.txt has $n failed molecule(s)"
    cat "$f" | while read -r line; do info "  failed: $line"; done
  fi
}

run_workflow() {
  local config="$1"
  local label="$2"
  echo ""
  echo -e "${BOLD}Running workflow: $label${RESET}"
  echo "  Config: $config"
  if $DRY_RUN; then
    info "DRY-RUN: would execute: cd $WORKFLOW_DIR && ./scripts/run.sh $config"
    return 0
  fi
  cd "$WORKFLOW_DIR"
  ./scripts/run.sh "$config"
}

# ── Main ──────────────────────────────────────────────────────────────────────
FAILURES=0
START_TIME=$(date +%s)

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   PhotoTox / QM-LUX  Integration Test Suite     ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo "  Workflow dir : $WORKFLOW_DIR"
echo "  Date         : $(date)"
echo "  Clean mode   : $CLEAN"
echo "  Dry-run mode : $DRY_RUN"
echo ""

cd "$WORKFLOW_DIR"

for TEST in "${TESTS[@]}"; do
  IFS='|' read -r CONFIG RESULTS_DIR MODEL_SUBDIR EXPECTED_SRNS <<< "$TEST"
  LABEL="$(basename "$CONFIG" .yaml)"

  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD}TEST: $LABEL${RESET}"
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

  # Optionally clean previous results
  if $CLEAN && [[ -d "$RESULTS_DIR" ]]; then
    info "Removing existing results: $RESULTS_DIR"
    $DRY_RUN || rm -rf "$RESULTS_DIR"
  fi

  # Run the workflow
  if ! run_workflow "$CONFIG" "$LABEL"; then
    fail "Workflow run failed for $LABEL"
    continue
  fi

  # ── Validate outputs ────────────────────────────────────────────────────
  echo ""
  echo -e "  ${BOLD}Checking outputs in: $RESULTS_DIR${RESET}"

  # Top-level outputs
  check_file_nonempty "$RESULTS_DIR/preparation.out"
  check_file_nonempty "$RESULTS_DIR/xtb_conf.out"
  check_file_nonempty "$RESULTS_DIR/summary.csv"

  # ML inputs
  check_file_nonempty "$RESULTS_DIR/data_ml/input.csv"
  check_file_nonempty "$RESULTS_DIR/data_ml/test_set_with_fP_rdkit_prop_UVvis.pkl"
  check_file_nonempty "$RESULTS_DIR/data_ml/UVvis.csv"

  # Model files
  check_file_nonempty "$RESULTS_DIR/model/model.sav"
  check_file_nonempty "$RESULTS_DIR/model/scaler.pkl"

  # Final prediction outputs
  local_model_dir="$RESULTS_DIR/$MODEL_SUBDIR"
  check_results_csv   "$local_model_dir/results_ML.csv" "$EXPECTED_SRNS"
  check_file_exists   "$local_model_dir/results_ML_with_mol_UV.html"
  check_failed_molecules "$local_model_dir/failed_molecules.txt"

  echo ""
done

# ── Summary ───────────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}TEST SUMMARY${RESET}"
echo "  Duration : ${ELAPSED}s"
if [[ "$FAILURES" -eq 0 ]]; then
  echo -e "  Result   : ${GREEN}${BOLD}ALL CHECKS PASSED${RESET}"
  exit 0
else
  echo -e "  Result   : ${RED}${BOLD}$FAILURES CHECK(S) FAILED${RESET}"
  exit 1
fi
