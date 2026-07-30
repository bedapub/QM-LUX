# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux/utils/io.py (public subset)."""
import os
import pandas as pd
import numpy as np
import pytest

from qm_lux.utils.io import (
    remove_chk_files,
    get_results,
)


# ---------------------------------------------------------------------------
# remove_chk_files
# ---------------------------------------------------------------------------

class TestRemoveChkFiles:
    def test_removes_chk_in_root(self, tmp_path):
        chk = tmp_path / "job.chk"
        chk.write_text("checkpoint")
        remove_chk_files(str(tmp_path))
        assert not chk.exists()

    def test_removes_chk_recursively(self, tmp_path):
        subdir = tmp_path / "sub" / "nested"
        subdir.mkdir(parents=True)
        chk = subdir / "nested.chk"
        chk.write_text("checkpoint")
        remove_chk_files(str(tmp_path))
        assert not chk.exists()

    def test_preserves_non_chk_files(self, tmp_path):
        keep = tmp_path / "important.log"
        chk = tmp_path / "delete.chk"
        keep.write_text("keep me")
        chk.write_text("delete me")
        remove_chk_files(str(tmp_path))
        assert keep.exists()
        assert not chk.exists()

    def test_empty_directory_no_error(self, tmp_path):
        remove_chk_files(str(tmp_path))  # must not raise

    def test_removes_multiple_chk_files(self, tmp_path):
        chk_files = ["a.chk", "b.chk", "c.chk"]
        for name in chk_files:
            (tmp_path / name).write_text("x")
        remove_chk_files(str(tmp_path))
        for name in chk_files:
            assert not (tmp_path / name).exists()


# ---------------------------------------------------------------------------
# get_results
# ---------------------------------------------------------------------------

class TestGetResults:
    def _make_results_dir(self, tmp_path):
        """Create minimal directory structure expected by get_results.

        get_results uses `path + directory` (string concatenation) so path
        must end with os.sep.  One subdir contains a results_ML*.csv with
        an MCC column; a second subdir has no results file.
        """
        path = str(tmp_path) + os.sep
        subdir_with_results = tmp_path / "RF_run1"
        subdir_with_results.mkdir()
        df = pd.DataFrame({"MCC": [0.5, 0.3], "Balanced Accuracy": [0.7, 0.6]})
        df.to_csv(subdir_with_results / "results_ML_RF.csv", index=False)

        subdir_no_results = tmp_path / "ETC_run1"
        subdir_no_results.mkdir()
        # no results_ML file here → should appear in CVs_error_cal_folds.txt

        return path

    def test_creates_database_results_csv(self, tmp_path):
        path = self._make_results_dir(tmp_path)
        get_results(path)
        assert (tmp_path / "database_results.csv").exists()

    def test_creates_cvs_error_txt(self, tmp_path):
        path = self._make_results_dir(tmp_path)
        get_results(path)
        assert (tmp_path / "CVs_error_cal_folds.txt").exists()

    def test_database_csv_contains_mcc_column(self, tmp_path):
        path = self._make_results_dir(tmp_path)
        get_results(path)
        result = pd.read_csv(tmp_path / "database_results.csv")
        assert "MCC" in result.columns

    def test_error_txt_lists_missing_dirs(self, tmp_path):
        path = self._make_results_dir(tmp_path)
        get_results(path)
        lines = (tmp_path / "CVs_error_cal_folds.txt").read_text().splitlines()
        listed = "\n".join(lines)
        assert "ETC_run1" in listed
