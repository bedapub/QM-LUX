# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Input preparation: structure standardisation, SDF generation, and feature computation.

:func:`data_preparation` is the entry point used by the Snakemake workflow for
the ``preparation`` rule.  It standardises input SMILES, enumerates chiral
isomers, generates Morgan fingerprints and RDKit physicochemical descriptors,
and writes the result as a pickle file for downstream XTB and ML steps.
"""

import os
import pickle

import pandas as pd

from qm_lux.chirality import chirality_analysis, chirality_analysis_all
from qm_lux.rdkit_features import calc_descr, finger_print_gen, standardize


def data_preparation(path, folder, stereo_check, current_df=None):
    """Standardise input compounds and compute structural features.

    Reads a CSV of SMILES, standardises structures, optionally enumerates
    chiral isomers, generates Morgan fingerprints and RDKit physicochemical
    descriptors, and serialises the result to ``<folder>/xtb_input.pkl``.

    Parameters
    ----------
    path : str
        Path to the input CSV file (must contain ``SMILES`` and ``SRN``
        columns).
    folder : str
        Output directory where ``input.csv`` and ``xtb_input.pkl`` are
        written.
    stereo_check : {"YES", "NO"}
        ``"NO"`` — enumerate all possible stereo isomers (training mode).
        ``"YES"`` — use the existing stereo assignment and filter compounds
        with more than one unassigned chiral centre.
    current_df : str or None, default None
        Path to an existing pickle file; compounds already present (by SRN)
        are excluded from the new run.  Required when ``stereo_check="YES"``
        and ignored when ``stereo_check="NO"``.

    Returns
    -------
    pandas.DataFrame
        Feature matrix with columns ``SRN``, ``SMILES_CLEAN``,
        ``fp_Morganclean``, and RDKit descriptor columns.

    Raises
    ------
    ValueError
        If ``stereo_check`` is neither ``"YES"`` nor ``"NO"``, or if it is
        ``"YES"`` and no ``current_df`` was supplied.
    """
    data = pd.read_csv(path)
    data.to_csv(os.path.join(folder, "input.csv"))

    data = standardize(data, "SMILES")

    if stereo_check == "NO":
        data_chir = chirality_analysis_all(data, "SMILES_CLEAN")
        print(data_chir)
    elif stereo_check == "YES":
        # Match on the mode alone. Folding "and current_df" into this condition
        # sent a YES call with no exclusion list to the else branch, which left
        # data_chir unassigned and raised UnboundLocalError two lines below
        # instead of naming the real problem.
        if not current_df:
            raise ValueError(
                "stereo_check='YES' requires current_df: the path to the pickle "
                "of already-processed compounds whose SRNs are excluded from "
                "this run (data_preparation -d). Pass stereo_check='NO' to "
                "enumerate all isomers of every compound instead."
            )

        with open(current_df, "rb") as f:
            df2 = pickle.load(f)

        # Prior-run SRNs carry a per-isomer suffix — "_0" from the line below,
        # "_0".."_n" from chirality_generator_all — while the incoming SRNs are
        # raw. Comparing them directly matches nothing, so the exclusion
        # silently becomes a no-op; strip the suffix before comparing.
        prior_srns = set(df2["SRN"].astype(str).str.replace(r"_\d+$", "", regex=True))
        data = data[~data["SRN"].astype(str).isin(prior_srns)]
        data_chir = chirality_analysis(data, "SMILES_CLEAN")
        diast_to_remove = data_chir[data_chir["Chiral Center"] == ">1"]
        print("List of compounds to remove with more than 1 unassigned chiral centers:")
        print(diast_to_remove["SRN"])
        data_chir = data_chir[~data_chir["SRN"].isin(list(diast_to_remove["SRN"]))]
        data_chir.reset_index(inplace=True, drop=True)
        data_chir["SRN"] = data_chir["SRN"] + "_0"
    else:
        raise ValueError(
            f"stereo_check must be 'YES' or 'NO', got {stereo_check!r}"
        )

    data_chir = data_chir.rename(columns={"SMILES_CLEAN_CHIRAL": "SMILES_CLEAN"})
    data_chir_fp = finger_print_gen(data_chir, "YES", "SMILES_CLEAN", "Morgan", "fp_Morganclean")
    data_chir_fp = data_chir_fp.reset_index(drop=True)
    data_chir_fp_descr = calc_descr(data_chir_fp, "SMILES_CLEAN")
    print(data_chir_fp_descr)

    pkl_path = os.path.join(folder, "xtb_input.pkl")
    print("Input file in pkl in:", pkl_path)
    with open(pkl_path, "wb") as f:
        pickle.dump(data_chir_fp_descr, f)

    return data_chir_fp_descr
