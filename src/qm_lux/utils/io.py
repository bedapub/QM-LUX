# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Filesystem I/O utilities for result collection and workflow helpers.

Functions moved to specialised modules are re-exported here so that existing
``from qm_lux.utils.io import ...`` call sites continue to work unchanged:

* :func:`get_QM` — now in :mod:`qm_lux.utils.xtb_parser`
* :func:`plot_UV` — now in :mod:`qm_lux.utils.plotting`
* :func:`create_molecule_images` — now in :mod:`qm_lux.utils.plotting`
* :func:`get_mol_ML_results` — now in :mod:`qm_lux.reporting`
"""

import os

import numpy as np
import pandas as pd

from qm_lux.utils.xtb_parser import get_QM  # noqa: F401
from qm_lux.utils.plotting import create_molecule_images, plot_UV  # noqa: F401
from qm_lux.reporting import get_mol_ML_results  # noqa: F401


#: The column :func:`get_results` sorts by. Its presence is also what tells a
#: cross-validation stats file apart from a prediction file, because the two are
#: named alike -- see :func:`get_results`.
CV_METRIC_COLUMN = "MCC"


def get_results(path):
    """Aggregate cross-validation ML result CSVs and write a summary file.

    Scans subdirectories of ``path`` for ``results_ML*.csv`` files, concatenates
    those that carry cross-validation metrics sorted by MCC, writes
    ``database_results.csv``, and logs any sub-directories with missing results.

    A ``results_ML*`` name is **not** enough on its own to identify a
    cross-validation file: the prediction step writes
    ``<data_ml*>/ML_results/results_ML<descriptors><model>.csv``, whose columns
    are ``pred``/``prob``/``Descriptors``/``ML_Method`` and which has no metrics
    at all. Both matched the old glob, with two consequences:

    * pointed at a ``data_ml*`` tree, this found only prediction files,
      concatenated them, and then died on ``sort_values(by=["MCC"])`` with a
      bare ``KeyError: 'MCC'`` -- naming a column, never the directory or the
      mistake;
    * pointed at a real ``training_results/`` tree it *worked*, and quietly
      folded the prediction rows in beside the metrics. A measured run produced
      12 rows of which only 1 was a cross-validation row; the other 11 were
      predictions carrying ``NaN`` for every metric column.

    Selection is therefore by content -- the presence of ``MCC`` -- rather than
    by filename, which stays robust if either naming scheme changes. Files that
    match the prefix but are skipped are named on stdout rather than dropped
    silently.

    Whether a sub-directory is reported as missing results is deliberately
    *unchanged*: any ``results_ML*`` file still counts, so a directory holding
    only predictions is not newly listed under ``NO CVs FOR:``. That keeps
    ``CVs_error_cal_folds.txt`` byte-identical for existing trees.

    Parameters
    ----------
    path : str
        Directory containing model-specific result sub-directories.

    Raises
    ------
    ValueError
        When no file under ``path`` carries cross-validation metrics. This
        replaces the ``KeyError: 'MCC'`` described above.
    """
    df_all_iter = pd.DataFrame()
    list_opt_no_ava = ["NO CVs FOR:"]
    skipped = []

    for directory in os.listdir(path):
        if os.path.isdir(os.path.join(path, directory)):
            found = 0
            for df in os.listdir(os.path.join(path, directory)):
                if df.startswith("results_ML"):
                    # Counted before the content checks below, on purpose: this
                    # flag answers "did this directory produce any results at
                    # all", which is a different question from "are they CV
                    # results" and feeds a different output file.
                    found = 1
                    file_path = os.path.join(path, directory)
                    candidate = os.path.join(file_path, df)
                    if not df.endswith(".csv"):
                        # results_ML_with_mol_UV.html matches the same prefix.
                        skipped.append((candidate, "not a .csv"))
                        continue
                    try:
                        df_read = pd.read_csv(candidate)
                    except Exception as exc:  # unreadable/corrupt CSV
                        skipped.append((candidate, f"unreadable as CSV: {exc}"))
                        continue
                    if CV_METRIC_COLUMN not in df_read.columns:
                        skipped.append(
                            (candidate,
                             f"no {CV_METRIC_COLUMN} column - looks like a "
                             "prediction file, not cross-validation results"))
                        continue
                    df_all_iter = pd.concat([df_all_iter, df_read])

            if found == 0:
                if directory != ".ipynb_checkpoints":
                    list_opt_no_ava.append(directory)

    for candidate, why in skipped:
        print(f"Skipped {candidate}: {why}")

    if df_all_iter.empty:
        message = [
            f"No cross-validation results under {path}: no results_ML*.csv "
            f"there has a {CV_METRIC_COLUMN} column."
        ]
        predictions = [c for c, why in skipped if "prediction file" in why]
        if predictions:
            message.append(
                f"Found {len(predictions)} prediction file(s) instead, e.g. "
                f"{predictions[0]} - those are the prediction step's output, "
                "collected with type PRED.")
        message.append(
            "This function expects the training results directory holding one "
            "sub-directory per model/descriptor combination, not a data_ml* "
            "directory.")
        raise ValueError(" ".join(message))

    df_all_iter.sort_values(by=[CV_METRIC_COLUMN], inplace=True, ascending=False)
    df_all_iter.to_csv(os.path.join(path, "database_results.csv"))
    print("")
    print("Database_results file created in:" + path)
    print("")
    np.savetxt(os.path.join(path, "CVs_error_cal_folds.txt"), np.array(list_opt_no_ava), fmt="%s")
    print("Check uncompleted CVs in:" + os.path.join(path, "CVs_error_cal_folds.txt"))
    print("")


def remove_chk_files(main_folder):
    """Recursively remove all Gaussian checkpoint (``.chk``) files.

    Parameters
    ----------
    main_folder : str
        Root directory to search.
    """
    main_folder = os.path.abspath(main_folder)
    for root, dirs, files in os.walk(main_folder):
        for file in files:
            if file.endswith(".chk"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")


def check_directory_exists(path):
    """Check that a path exists and is a directory.

    Parameters
    ----------
    path : str
        The filesystem path to check.

    Returns
    -------
    bool
        True if the path exists and is a directory.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    NotADirectoryError
        If the path is not a directory.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"The path '{path}' does not exist.")
    if not os.path.isdir(path):
        raise NotADirectoryError(f"The path '{path}' is not a directory.")
    return True


def xy_files(base_dir):
    """Collect all ``.xy`` UV-Vis spectrum files under ``base_dir/0/``.

    Parameters
    ----------
    base_dir : str
        Root results directory containing a ``0/`` subdirectory with
        per-molecule folders, each holding one ``.xy`` file.

    Returns
    -------
    pandas.DataFrame or None
        Single-column DataFrame (``file_path``) of absolute paths to all
        ``.xy`` files found, or ``None`` if no files are present.
    """
    base_dir = os.path.abspath(base_dir)
    directory_uv = os.path.join(base_dir, "0")

    file_paths = []

    for dire in os.listdir(directory_uv):
        for fname in os.listdir(os.path.join(directory_uv, dire)):
            if fname.endswith(".xy"):
                file_paths.append(os.path.join(directory_uv, dire, fname))

    return pd.DataFrame(file_paths, columns=["file_path"]) if file_paths else None
