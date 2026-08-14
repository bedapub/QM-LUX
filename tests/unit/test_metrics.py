# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.metrics."""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from qm_lux.metrics import (
    model_performance,
    model_performance_ext,
    table_stat_cal,
    table_stat_cal_iter,
    table_stat_cal_std,
    TP_TN_FN_FP,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fitted_model():
    rng = np.random.default_rng(0)
    X = rng.random((40, 5))
    y = (X[:, 0] > 0.5).astype(int)
    clf = RandomForestClassifier(n_estimators=5, random_state=0)
    clf.fit(X, y)
    return clf, X, y


# ---------------------------------------------------------------------------
# model_performance_ext
# ---------------------------------------------------------------------------

class TestModelPerformanceExt:
    def test_returns_ten_elements(self, fitted_model):
        clf, X, y = fitted_model
        result = model_performance_ext(clf, X, y)
        assert len(result) == 10

    def test_first_eight_are_nan(self, fitted_model):
        clf, X, y = fitted_model
        result = model_performance_ext(clf, X, y)
        for v in result[:4]:
            assert np.isnan(v)
        for v in result[6:]:
            assert np.isnan(v)

    def test_prob_and_pred_shapes(self, fitted_model):
        clf, X, y = fitted_model
        _, _, _, _, prob, pred, _, _, _, _ = model_performance_ext(clf, X, y)
        assert len(prob) == len(y)
        assert len(pred) == len(y)
        assert set(pred).issubset({0, 1})

    def test_importable_from_ml_plots(self, fitted_model):
        from qm_lux.ml_plots import model_performance_ext as mpe
        clf, X, y = fitted_model
        assert len(mpe(clf, X, y)) == 10


# ---------------------------------------------------------------------------
# model_performance
# ---------------------------------------------------------------------------

class TestModelPerformance:
    def test_returns_ten_elements(self, fitted_model):
        clf, X, y = fitted_model
        result = model_performance(clf, X, y, verbose=False)
        assert len(result) == 10

    def test_metrics_in_range(self, fitted_model):
        clf, X, y = fitted_model
        bacc, sens, spec, auc, prob, pred, cm, mcc, acc, prec = model_performance(
            clf, X, y, verbose=False
        )
        for v in (bacc, sens, spec, auc, acc, prec):
            assert 0.0 <= v <= 1.0
        assert -1.0 <= mcc <= 1.0
        assert cm.shape == (2, 2)

    def test_prob_sums_correct(self, fitted_model):
        clf, X, y = fitted_model
        _, _, _, _, prob, pred, _, _, _, _ = model_performance(clf, X, y, verbose=False)
        assert np.all((prob >= 0) & (prob <= 1))


# ---------------------------------------------------------------------------
# TP_TN_FN_FP
# ---------------------------------------------------------------------------

class TestTPTNFNFP:
    def _call(self):
        index = np.array([0, 1, 2, 3])
        exp   = np.array([1, 0, 1, 0])
        pred  = np.array([1, 0, 0, 1])
        prob  = np.array([0.9, 0.1, 0.4, 0.6])
        return TP_TN_FN_FP(index, exp, pred, 1, "desc", "RF", "roc_auc",
                           prob, "external", "NO", "cal")

    def test_returns_dataframe(self):
        df = self._call()
        assert isinstance(df, pd.DataFrame)

    def test_expected_columns(self):
        df = self._call()
        for col in ("INDEX", "EXP", "PRED", "TP", "TN", "FP", "FN", "PROB", "ITER"):
            assert col in df.columns

    def test_tp_tn_fp_fn_correct(self):
        df = self._call()
        assert df["TP"].tolist() == [1, 0, 0, 0]
        assert df["TN"].tolist() == [0, 1, 0, 0]
        assert df["FN"].tolist() == [0, 0, 1, 0]
        assert df["FP"].tolist() == [0, 0, 0, 1]

    def test_row_count(self):
        df = self._call()
        assert len(df) == 4


# ---------------------------------------------------------------------------
# table_stat_cal_std
# ---------------------------------------------------------------------------

class TestTableStatCalStd:
    def _call(self, oversampling="NO"):
        return table_stat_cal_std(
            "RF", "desc", oversampling, "external", "roc_auc", "cal",
            0.8, 0.05, 0.75, 0.04, 0.7, 0.03, 0.8, 0.02,
            0.6, 0.01, 0.78, 0.03, 0.72, 0.02,
        )

    def test_returns_single_row_dataframe(self):
        df = self._call()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_oversampling_label_no(self):
        df = self._call("NO")
        assert df["Method Training"].iloc[0] == "NO Oversampling"

    def test_oversampling_label_yes(self):
        df = self._call("YES")
        assert df["Method Training"].iloc[0] == "YES Oversampling"

    def test_oversampling_label_smote(self):
        df = self._call("SMOTE")
        assert df["Method Training"].iloc[0] == "SMOTE"

    def test_auc_value(self):
        df = self._call()
        assert df["AUC"].iloc[0] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# table_stat_cal
# ---------------------------------------------------------------------------

class TestTableStatCal:
    def _call(self, oversampling="NO"):
        return table_stat_cal(
            "RF", "desc", oversampling, "external", "roc_auc", "cal",
            0.8, 0.05, 0.75, 0.04, 0.7, 0.03, 0.8, 0.02, 0.6, 0.01,
        )

    def test_returns_single_row(self):
        assert len(self._call()) == 1

    def test_oversampling_no(self):
        df = self._call("NO")
        assert df["Method Training"].iloc[0] == "NO Oversampling"

    def test_oversampling_yes(self):
        df = self._call("YES")
        assert df["Method Training"].iloc[0] == "YES Oversampling"


# ---------------------------------------------------------------------------
# table_stat_cal_iter
# ---------------------------------------------------------------------------

class TestTableStatCalIter:
    def _call(self, oversampling="NO"):
        return table_stat_cal_iter(
            "RF", "desc", oversampling, "external", "roc_auc", "cal",
            0.8, 0.75, 0.7, 0.8, 0.6, 0.78, 0.72, 3,
        )

    def test_returns_single_row(self):
        assert len(self._call()) == 1

    def test_iter_value(self):
        df = self._call()
        assert df["iter"].iloc[0] == 3

    def test_oversampling_no(self):
        df = self._call("NO")
        assert df["Method Training"].iloc[0] == "NO Oversampling"


# ---------------------------------------------------------------------------
# The three builders agree on how oversampling is spelled
# ---------------------------------------------------------------------------

class TestOversamplingLabelIsShared:
    """One mapping, three tables.

    ``table_stat_cal`` and ``table_stat_cal_iter`` used to fold everything that
    was not "NO" into the literal "YES Oversampling", while
    ``table_stat_cal_std`` had a real SMOTE branch. A SMOTE run was therefore
    labelled "SMOTE" or "YES Oversampling" depending only on which builder ran,
    and the fold-level table could not be joined to the aggregate one on
    Method Training.
    """

    BUILDERS = {
        "std": lambda ov: table_stat_cal_std(
            "RF", "desc", ov, "external", "roc_auc", "cal",
            0.8, 0.05, 0.75, 0.04, 0.7, 0.03, 0.8, 0.02,
            0.6, 0.01, 0.78, 0.03, 0.72, 0.02,
        ),
        "cal": lambda ov: table_stat_cal(
            "RF", "desc", ov, "external", "roc_auc", "cal",
            0.8, 0.05, 0.75, 0.04, 0.7, 0.03, 0.8, 0.02, 0.6, 0.01,
        ),
        "iter": lambda ov: table_stat_cal_iter(
            "RF", "desc", ov, "external", "roc_auc", "cal",
            0.8, 0.75, 0.7, 0.8, 0.6, 0.78, 0.72, 3,
        ),
    }

    @pytest.mark.parametrize("raw,expected", [
        ("NO", "NO Oversampling"),
        ("YES", "YES Oversampling"),
        ("SMOTE", "SMOTE"),
    ])
    def test_every_builder_spells_it_the_same_way(self, raw, expected):
        labels = {name: b(raw)["Method Training"].iloc[0]
                  for name, b in self.BUILDERS.items()}
        assert set(labels.values()) == {expected}, labels

    def test_smote_survives_in_all_three(self):
        """The specific collapse this fix removes."""
        for name, build in self.BUILDERS.items():
            assert build("SMOTE")["Method Training"].iloc[0] == "SMOTE", name

    @pytest.mark.parametrize("raw", ["smote", "Yes", "", "BorderlineSMOTE"])
    def test_an_unrecognised_mode_is_recorded_verbatim_not_relabelled(self, raw):
        """Deliberately not a raise, and deliberately not "YES Oversampling".

        These builders run after training, so the honest record is what was
        actually requested; folding an unknown mode into a known label is what
        made the old bare `else` misreport. Rejecting a bad value belongs at
        the point the run is configured, not here.
        """
        for name, build in self.BUILDERS.items():
            assert build(raw)["Method Training"].iloc[0] == raw, name
