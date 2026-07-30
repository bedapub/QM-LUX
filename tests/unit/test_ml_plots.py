# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.ml_plots."""
# Set non-interactive backend before any matplotlib import to avoid display issues.
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from qm_lux.ml_plots import (
    conf_matrix_plot,
    model_performance,
    model_performance_ext,
    plot_roc_curves_for_models,
    table_stat_cal,
    table_stat_cal_iter,
    table_stat_cal_std,
    TP_TN_FN_FP,
)


# ---------------------------------------------------------------------------
# Re-export smoke tests
# ---------------------------------------------------------------------------

class TestReExports:
    """Verify all symbols from qm_lux.metrics are re-exported by qm_lux.ml_plots."""

    def test_model_performance_callable(self):
        assert callable(model_performance)

    def test_model_performance_ext_callable(self):
        assert callable(model_performance_ext)

    def test_tp_tn_fn_fp_callable(self):
        assert callable(TP_TN_FN_FP)

    def test_table_stat_cal_callable(self):
        assert callable(table_stat_cal)

    def test_table_stat_cal_std_callable(self):
        assert callable(table_stat_cal_std)

    def test_table_stat_cal_iter_callable(self):
        assert callable(table_stat_cal_iter)

    def test_model_performance_ext_same_as_metrics(self):
        """Re-exported symbol must be the identical function object."""
        from qm_lux.metrics import model_performance_ext as orig
        assert model_performance_ext is orig


# ---------------------------------------------------------------------------
# conf_matrix_plot
# ---------------------------------------------------------------------------

class TestConfMatrixPlot:
    def test_runs_without_error_for_valid_matrix(self):
        cf_matrix = np.array([[10, 2], [3, 15]])
        with patch("matplotlib.pyplot.show"):
            conf_matrix_plot(cf_matrix)

    def test_perfect_classifier_matrix(self):
        cf_matrix = np.array([[50, 0], [0, 50]])
        with patch("matplotlib.pyplot.show"):
            conf_matrix_plot(cf_matrix)

    def test_all_false_positives_matrix(self):
        cf_matrix = np.array([[0, 50], [50, 0]])
        with patch("matplotlib.pyplot.show"):
            conf_matrix_plot(cf_matrix)

    def test_all_zeros_no_warning(self):
        """A zero-only confusion matrix must not emit a RuntimeWarning."""
        import warnings
        cf_matrix = np.array([[0, 0], [0, 0]])
        with patch("matplotlib.pyplot.show"):
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                conf_matrix_plot(cf_matrix)


# ---------------------------------------------------------------------------
# plot_roc_curves_for_models
# ---------------------------------------------------------------------------

def _make_roc_df(n_points=10, n_iters=2):
    """Synthetic ROC data for n_iters cross-validation iterations."""
    rng = np.random.default_rng(0)
    fpr = np.linspace(0, 1, n_points)
    tpr = np.sqrt(fpr)
    rows = {
        "false_pos_rate": np.tile(fpr, n_iters),
        "true_pos_rate": np.tile(tpr, n_iters),
        "inter": np.repeat(list(range(n_iters)), n_points),
        "auc": np.repeat([0.75 + i * 0.05 for i in range(n_iters)], n_points),
    }
    return pd.DataFrame(rows)


class TestPlotRocCurvesForModels:
    def test_runs_without_error(self):
        df = _make_roc_df()
        with patch("matplotlib.pyplot.show"):
            plot_roc_curves_for_models(df, "RF", "fp_morgan")

    def test_iter_auc_column_created(self):
        """The function must add an 'Iter-AUC' column to the DataFrame."""
        df = _make_roc_df()
        with patch("matplotlib.pyplot.show"):
            plot_roc_curves_for_models(df, "RF", "fp_morgan")
        assert "Iter-AUC" in df.columns

    def test_inter_column_becomes_string(self):
        """The function casts 'inter' to str in place."""
        df = _make_roc_df()
        with patch("matplotlib.pyplot.show"):
            plot_roc_curves_for_models(df, "RF", "fp_morgan")
        assert df["inter"].dtype == object  # str after .map(str)

    def test_single_iteration(self):
        """A single cross-validation iteration must not crash."""
        df = _make_roc_df(n_iters=1)
        with patch("matplotlib.pyplot.show"):
            plot_roc_curves_for_models(df, "SVM", "fp_maccs")

    def test_label_and_attributes_in_title(self):
        """The title string is set inside the function via g.set_title;
        the function must complete without error for any label/attribute string."""
        df = _make_roc_df()
        with patch("matplotlib.pyplot.show"):
            plot_roc_curves_for_models(df, "RandomForest", "morgan_fp_1024")
