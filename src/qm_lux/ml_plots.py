# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Confusion-matrix and cross-validation plot helpers.

Metrics and performance-summary functions live in :mod:`qm_lux.metrics` and
are re-exported here so that existing ``from qm_lux.ml_plots import ...``
call sites continue to work unchanged.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from qm_lux.metrics import (  # noqa: F401
    model_performance,
    model_performance_ext,
    TP_TN_FN_FP,
    table_stat_cal,
    table_stat_cal_std,
    table_stat_cal_iter,
)


def conf_matrix_plot(cf_matrix):
    """Plot a labelled confusion matrix heatmap.

    Parameters
    ----------
    cf_matrix : numpy.ndarray
        2×2 confusion matrix (from :func:`sklearn.metrics.confusion_matrix`).
    """
    ax = plt.subplots(1, 1, figsize=(5, 5))

    group_names = ["True Neg", "False Pos", "False Neg", "True Pos"]
    group_counts = ["{0:0.0f}".format(value) for value in cf_matrix.flatten()]
    total = np.sum(cf_matrix)
    fractions = cf_matrix.flatten() / total if total > 0 else np.zeros(cf_matrix.size)
    group_percentages = ["{0:.2%}".format(v) for v in fractions]
    labels = [
        f"{v1}\n{v2}\n{v3}"
        for v1, v2, v3 in zip(group_names, group_counts, group_percentages)
    ]
    labels = np.asarray(labels).reshape(2, 2)

    ax = sns.heatmap(cf_matrix, annot=labels, fmt="", cmap="Blues")
    ax.set_title("Confusion Matrix \n\n")
    ax.set_xlabel("\nPredicted Values")
    ax.set_ylabel("Actual Values ")
    ax.xaxis.set_ticklabels(["False", "True"])
    ax.yaxis.set_ticklabels(["False", "True"])
    plt.show()


def plot_roc_curves_for_models(df, label, attributes):
    """Plot ROC curves for multiple cross-validation iterations.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ``false_pos_rate``, ``true_pos_rate``,
        ``inter`` (iteration), and ``auc``.
    label : str
        Model label used in the plot title.
    attributes : str
        Descriptor name used in the plot title.
    """
    fig, axs = plt.subplots(1, 1, figsize=(5, 5))
    df["inter"] = df["inter"].map(str)
    df["auc"] = df["auc"].map(str)
    df["Iter-AUC"] = df["inter"].str.cat(df["auc"].values, sep=" -AUC = ")

    g = sns.lineplot(x="false_pos_rate", y="true_pos_rate", data=df, hue="Iter-AUC", estimator=None)
    g.set_title("ROC-" + label + "-" + attributes, fontsize=15)
    g.set_xlabel("False Positive Rate", fontsize=15)
    g.set_ylabel("True Positive Rate", fontsize=15)
    plt.setp(g.get_legend().get_texts(), fontsize="10")
    plt.setp(g.get_legend().get_title(), fontsize="15")
    axs.plot([0, 1], [0, 1], "r--")
