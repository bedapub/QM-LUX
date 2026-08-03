# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Binary classification metrics and CV performance summary builders.

These functions have no matplotlib dependency and are safe to import in
headless / batch contexts.  :mod:`qm_lux.ml_plots` re-exports all symbols
defined here so that existing ``from qm_lux.ml_plots import ...`` call sites
continue to work unchanged.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def model_performance(ml_model, test_x, test_y, verbose=True):
    """Calculate and optionally print classification performance metrics.

    Parameters
    ----------
    ml_model : sklearn estimator
        Fitted model with ``predict_proba`` and ``predict`` methods.
    test_x : array-like
        Feature matrix for the test set.
    test_y : array-like
        True binary labels for the test set.
    verbose : bool, optional
        Print performance metrics.  Default ``True``.

    Returns
    -------
    tuple
        ``(balanced_accuracy, sensitivity, specificity, roc_auc, test_prob,
        test_pred, confusion_matrix, mcc, accuracy, precision)``
    """
    test_prob = ml_model.predict_proba(test_x)[:, 1]
    test_pred = ml_model.predict(test_x)

    accuracy = balanced_accuracy_score(test_y, test_pred)
    sens = recall_score(test_y, test_pred)
    spec = recall_score(test_y, test_pred, pos_label=0)
    auc = roc_auc_score(test_y, test_prob)
    cm = confusion_matrix(test_y, test_pred)
    mcc = matthews_corrcoef(test_y, test_pred)
    acc = accuracy_score(test_y, test_pred)
    prec = precision_score(test_y, test_pred)

    if verbose:
        print("")
        print("PERFORMANCE IN EXTERNAL VALIDATION")
        print(f"B. Accuracy: {accuracy:.2}")
        print(f"Sensitivity: {sens:.2f}")
        print(f"Specificity: {spec:.2f}")
        print(f"AUC: {auc:.2f}")
        print(f"MCC: {mcc:.2f}")
        print(f"Accuracy: {acc:.2f}")
        print(f"Precision: {prec:.2f}")

    return accuracy, sens, spec, auc, test_prob, test_pred, cm, mcc, acc, prec


def model_performance_ext(ml_model, test_x, test_y):
    """Return predictions without computing performance metrics.

    Used when true labels are unavailable (external prediction mode).

    Parameters
    ----------
    ml_model : sklearn estimator
        Fitted model with ``predict_proba`` and ``predict`` methods.
    test_x : array-like
        Feature matrix for the test set.
    test_y : array-like
        Placeholder; not used but kept for API compatibility with
        :func:`model_performance`.

    Returns
    -------
    tuple
        Ten-element tuple matching the shape of :func:`model_performance`'s
        return value, so the two can be unpacked identically.  Elements 5 and
        6 (0-based indices 4 and 5) are ``test_prob`` and ``test_pred``; the
        remaining eight are ``float("nan")``.
    """
    test_prob = ml_model.predict_proba(test_x)[:, 1]
    test_pred = ml_model.predict(test_x)

    return (
        float("nan"), float("nan"), float("nan"), float("nan"),
        test_prob, test_pred,
        float("nan"), float("nan"), float("nan"), float("nan"),
    )


def TP_TN_FN_FP(index, exp, pred, iteration, descriptors, ml_label, scoring, prob, val, oversampling, score_cal):
    """Compute per-compound TP/TN/FP/FN membership for a single CV iteration.

    Parameters
    ----------
    index : array-like of int
        Compound indices in the test set.
    exp : array-like
        Experimental (true) binary labels.
    pred : array-like
        Predicted binary labels.
    iteration : int
        Cross-validation iteration number.
    descriptors : str
        Descriptor set name.
    ml_label : str
        ML method label.
    scoring : str
        Scoring metric used during optimisation.
    prob : array-like
        Predicted probabilities for the positive class.
    val : str
        Validation type label.
    oversampling : str
        Oversampling strategy label.
    score_cal : str
        Calibration score label.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``INDEX``, ``EXP``, ``PRED``, ``TN``, ``TP``,
        ``FN``, ``FP``, ``PROB``, ``ITER``, ``Descriptors``, ``Validation``,
        ``Oversampling``, ``Score Calib``, ``ML Method``, ``Scoring``.
    """
    li = [index, np.array(exp), pred]
    df = pd.DataFrame(li)
    df = df.T
    df = df.set_axis(["INDEX", "EXP", "PRED"], axis=1)
    df["INDEX"] = df["INDEX"].astype("int")

    res_exp = np.array(exp)
    index_loop = 0
    TP = []
    FP = []
    TN = []
    FN = []

    for i in res_exp:
        TN.append(1 if pred[index_loop] == 0 and i == 0 else 0)
        TP.append(1 if pred[index_loop] == 1 and i == 1 else 0)
        FN.append(1 if pred[index_loop] == 0 and i == 1 else 0)
        FP.append(1 if pred[index_loop] == 1 and i == 0 else 0)
        index_loop += 1

    df = pd.concat([
        df,
        pd.DataFrame({"TN": TN}),
        pd.DataFrame({"TP": TP}),
        pd.DataFrame({"FN": FN}),
        pd.DataFrame({"FP": FP}),
        pd.DataFrame({"PROB": prob}),
    ], axis=1)

    df["ITER"] = iteration
    df["ITER"] = df["ITER"].astype("int")
    df["Descriptors"] = descriptors
    df["Validation"] = val
    df["Oversampling"] = oversampling
    df["Score Calib"] = score_cal
    df["ML Method"] = ml_label
    df["Scoring"] = scoring

    return df


def table_stat_cal_std(label, attributes, oversampling, validation, scoring, cal_scoring,
                       auc, auc_std, baccuracy, baccuracy_std,
                       sensitivity, sensitivity_std, specificity, specificity_std,
                       mcc, mcc_std, acc, acc_std, prec, prec_std):
    """Build a performance summary DataFrame with mean and standard deviation.

    Parameters
    ----------
    label : str
        ML method name.
    attributes : str
        Descriptor set name.
    oversampling : {"NO", "YES", "SMOTE"}
        Oversampling strategy.
    validation : str
        Validation type.
    scoring : str
        Optimisation scoring metric.
    cal_scoring : str
        Calibration score label.
    auc, auc_std : float
        ROC-AUC mean and standard deviation.
    baccuracy, baccuracy_std : float
        Balanced accuracy mean and standard deviation.
    sensitivity, sensitivity_std : float
        Sensitivity mean and standard deviation.
    specificity, specificity_std : float
        Specificity mean and standard deviation.
    mcc, mcc_std : float
        Matthews correlation coefficient mean and standard deviation.
    acc, acc_std : float
        Overall accuracy mean and standard deviation.
    prec, prec_std : float
        Precision mean and standard deviation.

    Returns
    -------
    pandas.DataFrame
        Single-row DataFrame with all metrics and their standard deviations.
    """
    if oversampling == "NO":
        oversampling = "NO Oversampling"
    elif oversampling == "YES":
        oversampling = "YES Oversampling"
    elif oversampling == "SMOTE":
        oversampling = "SMOTE"

    df = pd.DataFrame({
        "ML Method": label, "Descriptors": attributes, "Method Training": oversampling,
        "Validation": validation, "Opt Scoring": scoring, "Cal Score": cal_scoring,
        "AUC": auc, "AUC_std": auc_std,
        "B.Accuracy": baccuracy, "B.Accuracy_std": baccuracy_std,
        "Sensitivity": sensitivity, "Sensitivity_std": sensitivity_std,
        "Specificity": specificity, "Specificity_std": specificity_std,
        "MCC": mcc, "MCC_std": mcc_std,
        "Accuracy": acc, "Accuracy_std": acc_std,
        "Precision": prec, "Precision_std": prec_std,
    }, index=[0])

    return df


def table_stat_cal(label, attributes, oversampling, validation, scoring, cal_scoring,
                   auc, auc_std, accuracy, accuracy_std,
                   sensitivity, sensitivity_std, specificity, specificity_std,
                   mcc, mcc_std):
    """Build a performance summary DataFrame (legacy, fewer metrics than table_stat_cal_std).

    Parameters
    ----------
    label : str
        ML method name.
    attributes : str
        Descriptor set name.
    oversampling : {"NO", "YES"}
        Oversampling strategy.
    validation : str
        Validation type.
    scoring : str
        Optimisation scoring metric.
    cal_scoring : str
        Calibration score label.
    auc, auc_std : float
        ROC-AUC mean and standard deviation.
    accuracy, accuracy_std : float
        Balanced accuracy mean and standard deviation.
    sensitivity, sensitivity_std : float
        Sensitivity mean and standard deviation.
    specificity, specificity_std : float
        Specificity mean and standard deviation.
    mcc, mcc_std : float
        MCC mean and standard deviation (stored under ``Precision``).

    Returns
    -------
    pandas.DataFrame
        Single-row DataFrame.  Note that the column labels do not all mean
        what they say: this legacy function takes fewer metrics than it has
        output columns, so ``specificity`` is written to both ``Specificity``
        and ``Accuracy`` and ``mcc`` is written to ``Precision`` (likewise for
        the ``_std`` columns).  Prefer :func:`table_stat_cal_std`, which takes
        every metric explicitly.
    """
    if oversampling == "NO":
        oversampling = "NO Oversampling"
    else:
        oversampling = "YES Oversampling"

    df = pd.DataFrame({
        "ML Method": label, "Descriptors": attributes, "Method Training": oversampling,
        "Validation": validation, "Opt Scoring": scoring, "Cal Score": cal_scoring,
        "AUC": auc, "AUC_std": auc_std,
        "B.Accuracy": accuracy, "B.Accuracy_std": accuracy_std,
        "Sensitivity": sensitivity, "Sensitivity_std": sensitivity_std,
        "Specificity": specificity, "Specificity_std": specificity_std,
        "Accuracy": specificity, "Accuracy_std": specificity_std,
        "Precision": mcc, "Precision_std": mcc_std,
    }, index=[0])

    return df


def table_stat_cal_iter(label, attributes, oversampling, validation, scoring, cal_scoring,
                        auc, baccuracy, sensitivity, specificity, mcc, acc, pres, iter_):
    """Build a per-iteration performance summary DataFrame.

    Parameters
    ----------
    label : str
        ML method name.
    attributes : str
        Descriptor set name.
    oversampling : {"NO", "YES"}
        Oversampling strategy.
    validation : str
        Validation type.
    scoring : str
        Optimisation scoring metric.
    cal_scoring : str
        Calibration score label.
    auc : float
        ROC-AUC.
    baccuracy : float
        Balanced accuracy.
    sensitivity : float
        Sensitivity.
    specificity : float
        Specificity.
    mcc : float
        Matthews correlation coefficient.
    acc : float
        Overall accuracy.
    pres : float
        Precision.
    iter_ : int
        Iteration index.

    Returns
    -------
    pandas.DataFrame
        Single-row DataFrame for this iteration.
    """
    if oversampling == "NO":
        oversampling = "NO Oversampling"
    else:
        oversampling = "YES Oversampling"

    df = pd.DataFrame({
        "ML Method": label, "Descriptors": attributes, "Method Training": oversampling,
        "Validation": validation, "Opt Scoring": scoring, "Cal Score": cal_scoring,
        "AUC": auc, "B.Accuracy": baccuracy,
        "Sensitivity": sensitivity, "Specificity": specificity,
        "MCC": mcc, "Accuracy": acc, "Precision": pres, "iter": iter_,
    }, index=[0])

    return df
