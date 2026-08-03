# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""ML engine wrappers: prediction inference and cross-validation dispatch.

:func:`run_prediction` is the entry point used by the Snakemake workflow for
scoring new compounds with a pre-trained Random Forest model.
"""

import os
import pickle

import numpy as np
import pandas as pd

from qm_lux.metrics import model_performance_ext


def run_prediction(
    path_input_model,
    pkl_file,
    csv_file,
    srn_file=None,
    attribute="SRN",
    method="RF",
    descriptor="fp_Morganclean__descriptors_SMILES_CLEAN__250-700",
):
    """Score test compounds with a pre-trained classifier.

    Loads a pickled model and scaler from ``path_input_model``, applies them to
    the descriptor column in the test pickle, and writes prediction results to
    a CSV file with columns ``SRN``, ``pred``, ``prob``, ``ML_Method`` and
    ``Descriptors``.  ``prob`` is the model's confidence in the class it
    predicted, normalised to ``[0.5, 1.0]`` — *not* the probability of the
    positive class.

    Every failure mode is a silent early return that writes no CSV: a missing
    or unreadable pickle, a pickle lacking the ``descriptor`` column, or a
    missing model/scaler.  The one exception is an empty pickle together with
    ``srn_file``, which writes a CSV of ``"N/A"`` placeholders.

    Parameters
    ----------
    path_input_model : str
        Directory containing ``model.sav`` and ``scaler.pkl``.
    pkl_file : str
        Path to the input pickle file holding the test-set feature matrix.
    csv_file : str
        Path where the output predictions CSV is written.
    srn_file : str, optional
        CSV file with SRN identifiers, used as a fallback when ``pkl_file``
        loads an empty DataFrame.
    attribute : str, optional
        Name of a column that must exist in the test pickle.  Default
        ``"SRN"``.  It is read and handed to
        :func:`~qm_lux.metrics.model_performance_ext` as ``test_y``, which
        ignores it — in prediction mode there are no true labels to score
        against.  The only effect of changing it is which column a missing-key
        failure is reported on.
    method : str, optional
        ML method label recorded in the output.  Default ``"RF"``.
    descriptor : str, optional
        Descriptor column to use for prediction.
    """
    try:
        with open(pkl_file, "rb") as f:
            test = pickle.load(f)

        if test.empty:
            print("Loaded DataFrame is empty. Writing N/A results using SRN numbers.")
            try:
                srn_df = pd.read_csv(srn_file)
                srn_numbers = srn_df.index.tolist()
            except (FileNotFoundError, IOError) as e:
                print(f"Error reading SRN file {srn_file}: {e}")
                return
            empty_df = pd.DataFrame({
                "": srn_numbers,
                "pred": ["N/A"] * len(srn_numbers),
                "prob": ["N/A"] * len(srn_numbers),
                "Descriptors": [descriptor] * len(srn_numbers),
                "ML_Method": [method] * len(srn_numbers),
            })
            empty_df.to_csv(csv_file, index=False)
            return

    except (FileNotFoundError, IOError) as e:
        print(f"Error reading pickle file {pkl_file}: {e}")
        return

    if descriptor not in test.columns:
        print(f"Descriptor column '{descriptor}' not found in DataFrame.")
        return

    try:
        with open(os.path.join(path_input_model, "model.sav"), "rb") as model_file:
            loaded_model = pickle.load(model_file)
        with open(os.path.join(path_input_model, "scaler.pkl"), "rb") as scaler_file:
            loaded_scaler = pickle.load(scaler_file)
    except (FileNotFoundError, IOError) as e:
        print(f"Error loading model or scaler from {path_input_model}: {e}")
        return

    try:
        X_raw = test[descriptor].apply(lambda x: np.array(x)).tolist()
        X = np.array(X_raw)
        X = loaded_scaler.transform(X)
    except ValueError as e:
        print(f"Error transforming descriptor data: {e}")
        return

    y = np.array(test[attribute].to_list())

    df = pd.DataFrame()
    accuracy, sens, spec, auc, test_prob, test_pred, cm, mcc, acc, prec = (
        model_performance_ext(loaded_model, X, y)
    )

    df["pred"] = test_pred
    df["prob"] = [value if value >= 0.5 else 1 - value for value in test_prob]
    df["Descriptors"] = descriptor
    df["ML_Method"] = method

    try:
        df.to_csv(csv_file, index=True)
    except IOError as e:
        print(f"Error writing to CSV file {csv_file}: {e}")


