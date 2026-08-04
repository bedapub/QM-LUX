#!/usr/bin/env bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
#
# Argument-handling and dispatch tests for workflow/scripts/run.sh.
#
# run.sh is the only entry point most users touch, and until now nothing
# executed it -- the unit tests are Python and the integration tests call
# snakemake directly (which is how the profile bug B38b reached a tag
# unnoticed). This closes that gap cheaply: a stub `snakemake` on PATH plus a
# small config file exercises every argument path, both run modes and the
# derived singularity binds without running a single real job.
#
# Needs nothing but bash, python3 and coreutils -- no Snakemake, no
# Singularity, no Gaussian -- so it runs in CI and finishes in seconds.
#
# Usage:
#   bash tests/cli/test_run_sh.sh

set -uo pipefail   # not -e: every case must run so the summary is complete

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SMK_DIR="$REPO_ROOT/workflow"
RUN_SH="$SMK_DIR/scripts/run.sh"

if [[ ! -f "$RUN_SH" ]]; then
    echo "ERROR: run.sh not found at $RUN_SH" >&2
    exit 1
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/qm_lux_run_sh_test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

BIN="$TMP/bin"
mkdir -p "$BIN"
STUB_LOG="$TMP/snakemake.log"
: > "$STUB_LOG"

# ── stub snakemake ──────────────────────────────────────────────────────────
# Records one block per invocation and exits 0. `--help` is answered separately
# because run.sh greps it to decide whether the SLURM executor plugin is
# present; STUB_SNAKEMAKE_HAS_SLURM_LOGS toggles that answer. `--report FILE`
# creates FILE so that run_report.sh's post-processing has something to read.
cat > "$BIN/snakemake" <<'STUB'
#!/usr/bin/env bash
if [[ "${1:-}" == "--help" ]]; then
    echo "usage: snakemake [options]"
    if [[ "${STUB_SNAKEMAKE_HAS_SLURM_LOGS:-0}" == "1" ]]; then
        echo "  --slurm-keep-successful-logs  keep logs of successful jobs"
    fi
    exit 0
fi
{
    echo "### invocation"
    echo "cwd=$(pwd -P)"
    echo "arvados=${SINGULARITYENV_ARVADOS_API_TOKEN:-<unset>}"
    echo "argv: $*"
    echo "target=${!#}"
} >> "$STUB_LOG"
_prev=""
for _a in "$@"; do
    [[ "$_prev" == "--report" ]] && : > "$_a"
    _prev="$_a"
done
exit "${STUB_SNAKEMAKE_RC:-0}"
STUB
chmod +x "$BIN/snakemake"

# A g16 stub, used only by the case that checks the warning is suppressed when
# Gaussian *is* on PATH. Kept out of $BIN so the default is "absent".
G16_BIN="$TMP/g16bin"
mkdir -p "$G16_BIN"
printf '#!/usr/bin/env bash\nexit 0\n' > "$G16_BIN/g16"
chmod +x "$G16_BIN/g16"

# A pruned PATH so the host's real snakemake/g16 (if any) cannot leak in and
# make a negative assertion pass for the wrong reason.
BASE_PATH="/usr/bin:/bin"
export PATH="$BIN:$BASE_PATH"
export STUB_LOG

# The caller's own Arvados token would otherwise be inherited and make the
# "nothing is forwarded" case pass or fail depending on who runs the test.
unset ARVADOS_API_TOKEN SINGULARITYENV_ARVADOS_API_TOKEN
unset QM_LUX_SIF_DIR QM_LUX_NO_AUTO_BIND QM_LUX_CLUSTER_PROFILE

# ── fixtures ────────────────────────────────────────────────────────────────
# Two sibling trees, so the derived bind set has two independent members and
# neither subsumes the other. results_directory is deliberately NOT created:
# run.sh must fall back to its nearest existing ancestor ($TMP/out), because a
# bind source that does not exist aborts singularity outright.
mkdir -p "$TMP/sif" "$TMP/out"
RESULTS_DIR="$TMP/out/results"
FAKE_SIF="$TMP/sif/qm-lux.sif"
: > "$FAKE_SIF"
# Nested under $TMP/sif on purpose: it must be subsumed by that bind, not
# added as a second, redundant one.
MODEL_DIR="$TMP/sif/models"
mkdir -p "$MODEL_DIR"

CONFIG="$TMP/config.yaml"
cat > "$CONFIG" <<EOF
input_file: resources/input.csv
results_directory: $RESULTS_DIR
qmlux_image: $FAKE_SIF
model_local_folder: $MODEL_DIR
model_method: RF
model_descriptor: fp_Morganclean__descriptors_SMILES_CLEAN__100-1000
singularity_args_param: "--cleanenv --bind /tmp"
EOF

# The same config with no --bind of its own. $TMPDIR is often under /tmp, so the
# config above already covers every fixture path and correctly derives nothing;
# the derivation itself needs a config that binds nothing.
CONFIG_NOBIND="$TMP/config_nobind.yaml"
sed 's|^singularity_args_param:.*|singularity_args_param: "--cleanenv"|' \
    "$CONFIG" > "$CONFIG_NOBIND"

# ── harness ─────────────────────────────────────────────────────────────────
PASSED=0
FAILED=0
DESC=""
OUT=""
RC=0
WORKDIR="$SMK_DIR"

function fail() {
    echo "  FAIL: $1"
    FAILED=$((FAILED + 1))
}

function ok() {
    PASSED=$((PASSED + 1))
}

# run_case <description> [args...] -- invokes run.sh, capturing rc and output.
function run_case() {
    DESC="$1"; shift
    : > "$STUB_LOG"
    echo "- $DESC"
    OUT="$(cd "$WORKDIR" && bash "$RUN_SH" "$@" 2>&1)"
    RC=$?
}

function expect_rc() {
    if [[ $RC -eq $1 ]]; then ok; else
        fail "expected exit $1, got $RC"
        echo "    output: $(head -3 <<<"$OUT" | tr '\n' '|')"
    fi
}

function expect_out() {
    if grep -qF -- "$1" <<<"$OUT"; then ok; else fail "output missing: $1"; fi
}

function expect_no_out() {
    if grep -qF -- "$1" <<<"$OUT"; then fail "output should not contain: $1"; else ok; fi
}

function expect_log() {
    if grep -qF -- "$1" "$STUB_LOG"; then ok; else fail "snakemake was never called with: $1"; fi
}

function expect_no_log() {
    if grep -qF -- "$1" "$STUB_LOG"; then fail "snakemake should not be called with: $1"; else ok; fi
}

function expect_calls() {
    local got
    got="$(grep -c '^### invocation' "$STUB_LOG")"
    if [[ "$got" -eq "$1" ]]; then ok; else fail "expected $1 snakemake invocation(s), got $got"; fi
}

function expect_targets() {
    # Every target=, in order, joined by spaces.
    local got
    got="$(grep '^target=' "$STUB_LOG" | sed 's/^target=//' | paste -sd' ' -)"
    if [[ "$got" == "$1" ]]; then ok; else fail "expected targets [$1], got [$got]"; fi
}

echo "=== run.sh argument handling ==="

run_case "--help exits 0 and prints usage" --help
expect_rc 0
expect_out "Usage: run.sh"
expect_calls 0

run_case "-h exits 0" -h
expect_rc 0
expect_out "Usage: run.sh"

run_case "no arguments is an error"
expect_rc 1

run_case "missing config file is an error" "$TMP/does-not-exist.yaml"
expect_rc 1
expect_out "config file not found"

run_case "unknown option is an error" --frobnicate "$CONFIG"
expect_rc 1
expect_out "unknown option"

run_case "--target without a value is an error" "$CONFIG" --target
expect_rc 1
expect_out "--target requires a value"

run_case "--target followed by a flag is an error" "$CONFIG" --target --cores 8
expect_rc 1
expect_out "got the flag"

run_case "empty --target= is an error" "$CONFIG" --target=
expect_rc 1
expect_out "--target requires a value"

run_case "--cores without a value is an error" "$CONFIG" --cores
expect_rc 1
expect_out "--cores requires a value"

run_case "empty --cores= is an error" "$CONFIG" --cores=
expect_rc 1
expect_out "--cores requires a value"

run_case "--target twice is an error" "$CONFIG" --target xtb --target crest
expect_rc 1
expect_out "--target given more than once"

run_case "--target= twice is an error" "$CONFIG" --target=xtb --target=crest
expect_rc 1
expect_out "--target given more than once"

run_case "--cores twice is an error" "$CONFIG" --cores 2 --cores 4
expect_rc 1
expect_out "--cores given more than once"

run_case "--cores= twice is an error" "$CONFIG" --cores=2 --cores=4
expect_rc 1
expect_out "--cores given more than once"

run_case "four positionals are an error" "$CONFIG" a 1 b c
expect_rc 1
expect_out "too many positional arguments"

run_case "trailing junk after a positional core count is an error" "$CONFIG" 8 extra
expect_rc 1
expect_out "was read as a core count"

run_case "core count from both --cores and positional is an error" "$CONFIG" --cores 4 8
expect_rc 1
expect_out "core count given twice"

run_case "target from both --target and positional is an error" "$CONFIG" xtb_conf --target crest
expect_rc 1
expect_out "target given twice"

run_case "positional target+cores plus --cores is an error" "$CONFIG" xtb_conf 8 --cores 4
expect_rc 1
expect_out "core count given twice"

run_case "zero cores is an error" "$CONFIG" --cores 0
expect_rc 1
expect_out "cores must be a positive integer"

run_case "non-numeric cores is an error" "$CONFIG" --cores lots
expect_rc 1
expect_out "cores must be a positive integer"

echo "=== environment checks ==="

DESC="a missing snakemake is reported as an environment problem"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && PATH="$BASE_PATH" bash "$RUN_SH" "$CONFIG" --cores 4 2>&1)"
RC=$?
expect_rc 1
expect_out "snakemake not found in PATH"

echo "=== local mode ==="

# One snakemake call, not two: 'checkpoint xtb_conf' in the Snakefile lets a
# single process re-plan the DAG once the per-molecule directories exist. The
# second call is run_report.sh's --report, which is a separate step.
run_case "a full local run makes one invocation, then the report" "$CONFIG" --cores 4
expect_rc 0
expect_calls 2
expect_targets "all $RESULTS_DIR.html"
expect_log "--cores 4"
expect_log "--executor local"
expect_no_log "--workflow-profile"
expect_out "Run the pipeline locally with 4 cores"
expect_out "Generating report"

run_case "a targeted local run makes one invocation and no report" "$CONFIG" --target xtb_conf --cores 4
expect_rc 0
expect_calls 1
expect_targets "xtb_conf"
expect_out "skipping report generation"

run_case "--target all means the full pipeline" "$CONFIG" --target all --cores 4
expect_rc 0
expect_calls 2
expect_targets "all $RESULTS_DIR.html"

run_case "positional core count is equivalent to --cores" "$CONFIG" 4
expect_rc 0
expect_log "--cores 4"
expect_log "--executor local"

run_case "positional target and core count are both honoured" "$CONFIG" xtb_conf 4
expect_rc 0
expect_calls 1
expect_targets "xtb_conf"
expect_log "--cores 4"

DESC="a failing snakemake fails the run and skips the report"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && STUB_SNAKEMAKE_RC=1 bash "$RUN_SH" "$CONFIG" --cores 4 2>&1)"
RC=$?
expect_rc 1
expect_out "snakemake reported one or more failed jobs"
expect_no_out "Generating report"

echo "=== cluster mode ==="

run_case "omitting --cores submits through the default profile" "$CONFIG"
expect_rc 0
expect_log "--workflow-profile profiles/slurm"
expect_log "--jobs 100"
expect_no_log "--executor local"
expect_out "Submit the pipeline through profile: profiles/slurm"

DESC="a cluster profile without config.yaml is an error"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && QM_LUX_CLUSTER_PROFILE="$TMP/no-such-profile" bash "$RUN_SH" "$CONFIG" 2>&1)"
RC=$?
expect_rc 1
expect_out "has no config.yaml"
expect_calls 0

ALT_PROFILE="$TMP/altprofile"
mkdir -p "$ALT_PROFILE"
printf 'executor: local\n' > "$ALT_PROFILE/config.yaml"

DESC="QM_LUX_CLUSTER_PROFILE selects a different profile"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && QM_LUX_CLUSTER_PROFILE="$ALT_PROFILE" bash "$RUN_SH" "$CONFIG" 2>&1)"
RC=$?
expect_rc 0
expect_log "--workflow-profile $ALT_PROFILE"

DESC="--slurm-keep-successful-logs is passed only when snakemake advertises it"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && STUB_SNAKEMAKE_HAS_SLURM_LOGS=1 bash "$RUN_SH" "$CONFIG" 2>&1)"
RC=$?
expect_rc 0
expect_log "--slurm-keep-successful-logs"
expect_no_out "has no SLURM executor plugin"

run_case "without the plugin, the default profile warns up front" "$CONFIG"
expect_rc 0
expect_no_log "--slurm-keep-successful-logs"
expect_out "has no SLURM executor plugin"

DESC="a non-default profile without the plugin does not get that warning"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && QM_LUX_CLUSTER_PROFILE="$ALT_PROFILE" bash "$RUN_SH" "$CONFIG" 2>&1)"
RC=$?
expect_no_out "has no SLURM executor plugin"

echo "=== Gaussian warning ==="

run_case "a full run warns when g16 is absent" "$CONFIG" --cores 4
expect_out "Warning: g16 not found in PATH"

run_case "a pre-Gaussian target does not warn about g16" "$CONFIG" --target xtb_conf --cores 4
expect_no_out "Warning: g16 not found in PATH"

DESC="no warning when g16 is on PATH"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && PATH="$G16_BIN:$PATH" bash "$RUN_SH" "$CONFIG" --cores 4 2>&1)"
RC=$?
expect_rc 0
expect_no_out "Warning: g16 not found in PATH"

echo "=== singularity binds and environment forwarding ==="

PTMP="$(cd "$TMP" && pwd -P)"   # binds are realpath'd, and $TMPDIR may be a symlink

run_case "binds are derived from the config paths" "$CONFIG_NOBIND" --cores 4
expect_rc 0
expect_out "Auto-bound from"
expect_log "--bind $PTMP/sif"
# results_directory does not exist yet, so its nearest existing ancestor is
# bound instead -- the whole point of nearest_existing().
expect_log "--bind $PTMP/out"
# model_local_folder lives under $TMP/sif, which is already bound; binding it
# again would make singularity warn about a duplicate mount point.
expect_no_log "--bind $PTMP/sif/models"
expect_log "--cleanenv"

# A path the config already covers must not be bound twice; singularity warns
# about "destination is already in the mount point list" if it is. $TMP is
# under /tmp here, so the config's own "--bind /tmp" covers every fixture.
run_case "a path already covered by the config is not bound again" "$CONFIG" --cores 4
expect_rc 0
expect_no_out "Auto-bound from"
expect_log "--cleanenv --bind /tmp"

DESC="QM_LUX_NO_AUTO_BIND=1 leaves singularity_args_param untouched"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && QM_LUX_NO_AUTO_BIND=1 bash "$RUN_SH" "$CONFIG_NOBIND" --cores 4 2>&1)"
RC=$?
expect_rc 0
expect_no_out "Auto-bound from"
expect_no_log "--bind $PTMP/sif"
expect_log "--singularity-args --cleanenv"

DESC="ARVADOS_API_TOKEN is forwarded under the SINGULARITYENV_ prefix"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$WORKDIR" && ARVADOS_API_TOKEN=tok-12345 bash "$RUN_SH" "$CONFIG" --cores 4 2>&1)"
RC=$?
expect_rc 0
expect_log "arvados=tok-12345"

run_case "no token means nothing is forwarded" "$CONFIG" --cores 4
expect_log "arvados=<unset>"

echo "=== symlinked working directory ==="

# run.sh resolves $PWD to its physical path before doing anything, because
# singularity and snakemake otherwise disagree about the working directory.
LINK="$TMP/workflow-link"
ln -s "$SMK_DIR" "$LINK"
DESC="run.sh resolves a symlinked working directory to its physical path"
echo "- $DESC"
: > "$STUB_LOG"
OUT="$(cd "$LINK" && bash scripts/run.sh "$CONFIG" --cores 4 2>&1)"
RC=$?
expect_rc 0
expect_log "cwd=$(cd "$SMK_DIR" && pwd -P)"

echo ""
echo "=========================================="
echo "  passed: $PASSED   failed: $FAILED"
echo "=========================================="
[[ $FAILED -eq 0 ]] || exit 1
echo "All run.sh CLI tests passed."
