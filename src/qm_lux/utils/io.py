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


def get_results(path):
    """Aggregate cross-validation ML result CSVs and write a summary file.

    Scans subdirectories of ``path`` for ``results_ML*.csv`` files, concatenates
    them sorted by MCC, writes ``database_results.csv``, and logs any
    sub-directories with missing results.

    Parameters
    ----------
    path : str
        Directory containing model-specific result sub-directories.
    """
    df_all_iter = pd.DataFrame()
    list_opt_no_ava = ["NO CVs FOR:"]

    for directory in os.listdir(path):
        if os.path.isdir(os.path.join(path, directory)):
            found = 0
            for df in os.listdir(os.path.join(path, directory)):
                if df.startswith("results_ML"):
                    file_path = os.path.join(path, directory)
                    df_read = pd.read_csv(os.path.join(file_path, df))
                    df_all_iter = pd.concat([df_all_iter, df_read])
                    found = 1

            if found == 0:
                if directory != ".ipynb_checkpoints":
                    list_opt_no_ava.append(directory)

    df_all_iter.sort_values(by=["MCC"], inplace=True, ascending=False)
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
