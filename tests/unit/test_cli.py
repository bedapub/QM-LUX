# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the qm_lux CLI entry point.

The script is run as a subprocess to verify exit codes and help-text content.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_CLI = str(REPO_ROOT / "src" / "qm_lux" / "cli.py")


def _run(*args):
    """Run the CLI script with the current interpreter; return CompletedProcess."""
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
    )


class TestMLPhototoxCLI:
    # ------------------------------------------------------------------ help
    def test_help_exits_zero(self):
        r = _run(ML_CLI, "--help")
        assert r.returncode == 0

    def test_help_lists_all_subcommands(self):
        r = _run(ML_CLI, "--help")
        for cmd in (
            "data_preparation",
            "xtb_conf",
            "xtb_runner",
            "get_pred_UVvis",
            "get_results",
            "prediction",
        ):
            assert cmd in r.stdout, f"Expected '{cmd}' in --help output"

    def test_gaussian_runner_absent(self):
        assert "Gaussian_runner" not in _run(ML_CLI, "--help").stdout

    # -------------------------------------------------------- removed commands
    def test_training_subcommand_absent(self):
        assert "training" not in _run(ML_CLI, "--help").stdout

    def test_hyper_opt_absent(self):
        assert "hyper_opt" not in _run(ML_CLI, "--help").stdout

    def test_update_train_set_absent(self):
        assert "update_train_set" not in _run(ML_CLI, "--help").stdout

    def test_prediction_smk_absent(self):
        assert "prediction_smk" not in _run(ML_CLI, "--help").stdout

    def test_get_results_smk_absent(self):
        assert "get_results_smk" not in _run(ML_CLI, "--help").stdout

    # ------------------------------------------------- per-subcommand --help
    def test_data_preparation_help(self):
        r = _run(ML_CLI, "data_preparation", "--help")
        assert r.returncode == 0
        assert "--input" in r.stdout
        assert "--outdir" in r.stdout      # required for Snakemake -o flag

    def test_xtb_conf_help(self):
        r = _run(ML_CLI, "xtb_conf", "--help")
        assert r.returncode == 0
        assert "--input" in r.stdout

    def test_xtb_runner_help(self):
        r = _run(ML_CLI, "xtb_runner", "--help")
        assert r.returncode == 0

    def test_get_pred_uvvis_help(self):
        r = _run(ML_CLI, "get_pred_UVvis", "--help")
        assert r.returncode == 0

    def test_get_results_help(self):
        r = _run(ML_CLI, "get_results", "--help")
        assert r.returncode == 0
        assert "--input" in r.stdout
        assert "--output" in r.stdout
        assert "--type" in r.stdout

    def test_prediction_help(self):
        r = _run(ML_CLI, "prediction", "--help")
        assert r.returncode == 0
        assert "--input" in r.stdout
        assert "--pkl" in r.stdout
        assert "--csv" in r.stdout
        assert "--srn" in r.stdout
        assert "--descriptor" in r.stdout
