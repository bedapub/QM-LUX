# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux/utils/io.py (public subset)."""
import os
import pandas as pd
import numpy as np
import pytest

from qm_lux.utils.io import (
    CV_METRIC_COLUMN,
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


class TestGetResultsSelectsCrossValidationFilesOnly:
    """A ``results_ML*`` name alone does not mean cross-validation results.

    The prediction step writes ``ML_results/results_ML<descr><model>.csv`` --
    columns pred/prob/Descriptors/ML_Method, no metrics -- and that matched the
    same glob as the CV stats file. Two consequences, both measured on a real
    tree before this was changed:

    * against a ``data_ml*`` directory the only match was the prediction file,
      so the concatenation had no ``MCC`` and ``sort_values`` raised a bare
      ``KeyError: 'MCC'``;
    * against a genuine training-results directory it silently mixed the two --
      12 rows out of which 1 was a CV row and 11 were predictions with ``NaN``
      for every metric.

    Selection is now by content, so these pin the discrimination rather than a
    filename pattern.
    """

    def _cv_frame(self):
        return pd.DataFrame({CV_METRIC_COLUMN: [0.5, 0.3],
                             "Balanced Accuracy": [0.7, 0.6]})

    def _prediction_frame(self):
        return pd.DataFrame({"pred": [0.0, 1.0], "prob": [0.55, 0.74],
                             "Descriptors": ["fp_x", "fp_x"],
                             "ML_Method": ["RF", "RF"]})

    def test_prediction_rows_are_not_folded_into_the_cv_table(self, tmp_path):
        """The contamination case: both kinds present, only the CV rows kept."""
        (tmp_path / "RF_run1").mkdir()
        self._cv_frame().to_csv(tmp_path / "RF_run1" / "results_ML_RF.csv",
                                index=False)
        (tmp_path / "ML_results").mkdir()
        self._prediction_frame().to_csv(
            tmp_path / "ML_results" / "results_MLfp_xRF.csv", index=False)

        get_results(str(tmp_path) + os.sep)

        out = pd.read_csv(tmp_path / "database_results.csv")
        assert len(out) == 2, "only the two CV rows"
        assert out[CV_METRIC_COLUMN].notna().all()
        assert "pred" not in out.columns
        assert "prob" not in out.columns

    def test_a_tree_with_only_prediction_files_raises_instead_of_keyerror(
            self, tmp_path):
        """Previously ``KeyError: 'MCC'`` from inside pandas."""
        (tmp_path / "ML_results").mkdir()
        self._prediction_frame().to_csv(
            tmp_path / "ML_results" / "results_MLfp_xRF.csv", index=False)

        with pytest.raises(ValueError) as excinfo:
            get_results(str(tmp_path) + os.sep)

        message = str(excinfo.value)
        assert CV_METRIC_COLUMN in message
        assert str(tmp_path) in message
        assert "prediction file" in message

    def test_an_empty_tree_raises_without_claiming_predictions_were_found(
            self, tmp_path):
        (tmp_path / "RF_run1").mkdir()

        with pytest.raises(ValueError) as excinfo:
            get_results(str(tmp_path) + os.sep)

        assert "prediction file" not in str(excinfo.value)

    def test_a_skipped_file_is_named_on_stdout(self, tmp_path, capsys):
        """Skipping silently would just move the confusion somewhere else."""
        (tmp_path / "RF_run1").mkdir()
        self._cv_frame().to_csv(tmp_path / "RF_run1" / "results_ML_RF.csv",
                                index=False)
        (tmp_path / "ML_results").mkdir()
        self._prediction_frame().to_csv(
            tmp_path / "ML_results" / "results_MLfp_xRF.csv", index=False)

        get_results(str(tmp_path) + os.sep)

        out = capsys.readouterr().out
        assert "results_MLfp_xRF.csv" in out
        assert "Skipped" in out

    def test_a_non_csv_matching_the_prefix_is_skipped_not_parsed(self, tmp_path):
        """``results_ML_with_mol_UV.html`` starts with the same prefix."""
        (tmp_path / "RF_run1").mkdir()
        self._cv_frame().to_csv(tmp_path / "RF_run1" / "results_ML_RF.csv",
                                index=False)
        (tmp_path / "RF_run1" / "results_ML_with_mol_UV.html").write_text(
            "<html><body>not a csv</body></html>")

        get_results(str(tmp_path) + os.sep)

        out = pd.read_csv(tmp_path / "database_results.csv")
        assert len(out) == 2

    def test_a_directory_of_predictions_is_not_newly_listed_as_missing(
            self, tmp_path):
        """CVs_error_cal_folds.txt must not change shape for existing trees.

        "Did this directory produce any results" and "are they CV results" are
        different questions feeding different outputs. A directory holding only
        predictions has produced results, so it stays off the NO CVs list --
        otherwise every existing training tree would gain an ML_results entry.
        """
        (tmp_path / "RF_run1").mkdir()
        self._cv_frame().to_csv(tmp_path / "RF_run1" / "results_ML_RF.csv",
                                index=False)
        (tmp_path / "ML_results").mkdir()
        self._prediction_frame().to_csv(
            tmp_path / "ML_results" / "results_MLfp_xRF.csv", index=False)
        (tmp_path / "ETC_run1").mkdir()

        get_results(str(tmp_path) + os.sep)

        listed = (tmp_path / "CVs_error_cal_folds.txt").read_text()
        assert "ETC_run1" in listed
        assert "ML_results" not in listed
