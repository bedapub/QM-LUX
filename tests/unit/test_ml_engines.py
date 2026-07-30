# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.ml_engines."""
import pickle

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from qm_lux.ml_engines import run_prediction


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DESCRIPTOR = "fp_test"
_N_FEATURES = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_pkl(tmp_path, n=10, with_descriptor=True):
    """Write a synthetic test-set pickle; each descriptor value is a 1-D array."""
    rng = np.random.default_rng(42)
    X = rng.random((n, _N_FEATURES))
    df = pd.DataFrame({"SRN": [f"mol{i}" for i in range(n)]})
    if with_descriptor:
        df[_DESCRIPTOR] = list(X)
    pkl_path = tmp_path / "test.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(df, f)
    return pkl_path


def _make_model_dir(tmp_path):
    """Train a minimal RF + scaler and write them into <tmp_path>/model/."""
    rng = np.random.default_rng(0)
    X = rng.random((40, _N_FEATURES))
    y = (X[:, 0] > 0.5).astype(int)
    clf = RandomForestClassifier(n_estimators=5, random_state=0)
    clf.fit(X, y)
    scaler = StandardScaler()
    scaler.fit(X)
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    with open(model_dir / "model.sav", "wb") as fh:
        pickle.dump(clf, fh)
    with open(model_dir / "scaler.pkl", "wb") as fh:
        pickle.dump(scaler, fh)
    return model_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunPrediction:
    # -------------------------------------------------------------- edge cases

    def test_missing_pkl_does_not_raise(self, tmp_path):
        """Non-existent pickle → function returns early without raising."""
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(tmp_path),
            str(tmp_path / "missing.pkl"),
            str(csv_out),
            descriptor=_DESCRIPTOR,
        )
        assert not csv_out.exists()

    def test_empty_dataframe_writes_na_csv(self, tmp_path):
        """Empty pickle + valid SRN CSV → output CSV with N/A predictions."""
        pkl_path = tmp_path / "empty.pkl"
        with open(pkl_path, "wb") as fh:
            pickle.dump(pd.DataFrame(), fh)

        srn_csv = tmp_path / "srn.csv"
        pd.DataFrame({"SRN": ["mol0", "mol1", "mol2"]}).to_csv(srn_csv, index=False)

        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(tmp_path),
            str(pkl_path),
            str(csv_out),
            srn_file=str(srn_csv),
            descriptor=_DESCRIPTOR,
        )
        assert csv_out.exists()
        # pandas re-reads "N/A" strings as NaN by default; check with keep_default_na=False
        result = pd.read_csv(csv_out, keep_default_na=False)
        assert "pred" in result.columns
        assert (result["pred"] == "N/A").all()

    def test_empty_df_na_prob_written(self, tmp_path):
        pkl_path = tmp_path / "empty.pkl"
        with open(pkl_path, "wb") as fh:
            pickle.dump(pd.DataFrame(), fh)
        srn_csv = tmp_path / "srn.csv"
        pd.DataFrame({"SRN": ["mol0"]}).to_csv(srn_csv, index=False)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(tmp_path), str(pkl_path), str(csv_out),
            srn_file=str(srn_csv), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out, keep_default_na=False)
        assert (result["prob"] == "N/A").all()

    def test_empty_df_no_srn_file_does_not_raise(self, tmp_path):
        """Empty pickle + missing SRN file → returns early without raising."""
        pkl_path = tmp_path / "empty.pkl"
        with open(pkl_path, "wb") as fh:
            pickle.dump(pd.DataFrame(), fh)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(tmp_path), str(pkl_path), str(csv_out),
            srn_file=str(tmp_path / "no_such_srn.csv"),
            descriptor=_DESCRIPTOR,
        )
        assert not csv_out.exists()

    def test_missing_descriptor_column_does_not_raise(self, tmp_path):
        """Pickle without the descriptor column → returns early, no CSV created."""
        pkl_path = _make_test_pkl(tmp_path, with_descriptor=False)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(tmp_path), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        assert not csv_out.exists()

    def test_missing_model_files_does_not_raise(self, tmp_path):
        """Pickle with descriptor but no model in model_dir → returns early."""
        pkl_path = _make_test_pkl(tmp_path)
        empty_model_dir = tmp_path / "empty_model"
        empty_model_dir.mkdir()
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(empty_model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        assert not csv_out.exists()

    # ----------------------------------------------------------- happy path

    def test_full_run_creates_csv(self, tmp_path):
        """End-to-end: valid pickle + model/scaler → CSV written."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        assert csv_out.exists()

    def test_full_run_pred_binary_values(self, tmp_path):
        """Prediction column must contain only 0 or 1."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out)
        assert set(result["pred"].unique()).issubset({0, 1})

    def test_full_run_prob_in_unit_interval(self, tmp_path):
        """Probability values must lie in [0, 1]."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out)
        assert result["prob"].between(0.0, 1.0).all()

    def test_full_run_prob_at_least_half(self, tmp_path):
        """Probabilities are normalised so that prob >= 0.5 always."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out)
        assert (result["prob"] >= 0.5).all()

    def test_full_run_descriptor_label_in_csv(self, tmp_path):
        """Descriptor label column must match the descriptor argument."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out)
        assert (result["Descriptors"] == _DESCRIPTOR).all()

    def test_full_run_method_label_in_csv(self, tmp_path):
        """ML_Method column must match the method argument."""
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out),
            descriptor=_DESCRIPTOR, method="SVM",
        )
        result = pd.read_csv(csv_out)
        assert (result["ML_Method"] == "SVM").all()

    def test_full_run_row_count_matches_input(self, tmp_path):
        """Output CSV must have one row per compound in the test pickle."""
        n = 15
        model_dir = _make_model_dir(tmp_path)
        pkl_path = _make_test_pkl(tmp_path, n=n)
        csv_out = tmp_path / "out.csv"
        run_prediction(
            str(model_dir), str(pkl_path), str(csv_out), descriptor=_DESCRIPTOR,
        )
        result = pd.read_csv(csv_out)
        assert len(result) == n
