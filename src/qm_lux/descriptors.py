# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Descriptor scaling, merging, and test-set preparation for ML prediction.

The primary entry point used by the Snakemake workflow is
:func:`ML_preparation_test_set`, which assembles the full feature matrix from
pre-computed structural fingerprints, RDKit physico-chemical descriptors,
HOMO-LUMO gap data, and predicted UV-Vis AUC values, then serialises it as a
pickle file for downstream ML scoring.
"""

import copy
import os
import pickle

import numpy as np
import pandas as pd


def descr_merge(df, descr_to_merge):
    """Concatenate descriptor arrays from multiple columns into a new column.

    Supports merging two or three descriptor columns.  The new column is named
    by joining the *other* column names with ``"__"`` (for three-way merges,
    one merged column is created per left-out descriptor).

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing at least the columns named in ``descr_to_merge``.
    descr_to_merge : list of str
        Two or three column names whose array values should be concatenated.

    Returns
    -------
    pandas.DataFrame
        Input DataFrame with one (two-way) or three (three-way) new columns
        appended.
    """
    if len(descr_to_merge) == 3:
        for i in descr_to_merge:
            d = copy.deepcopy(descr_to_merge)
            d.remove(i)
            name_col = "__".join(d)
            print("NAME NEW COLUMN:", name_col)

            all_descr_temp = []
            for index, row in df.iterrows():
                descr_temp = np.concatenate((row[d[0]], row[d[1]]))
                all_descr_temp.append(descr_temp)

            df[name_col] = all_descr_temp

    elif len(descr_to_merge) == 2:
        all_descr_temp = []
        name_col = "__".join(descr_to_merge)
        print("NAME NEW COLUMN:", name_col)

        for index, row in df.iterrows():
            descr_temp = np.concatenate((row[descr_to_merge[0]], row[descr_to_merge[1]]))
            all_descr_temp.append(descr_temp)

        df[name_col] = all_descr_temp

    print("row in the dataframe", len(df))
    print("row of descriptors", len(all_descr_temp))

    return df


def ML_preparation_test_set(base_dir, df_AUCs):
    """Assemble the full feature matrix for ML prediction and write it to disk.

    Combines structural fingerprints and physico-chemical descriptors from a
    pre-computed pickle, HOMO-LUMO gap data from a CSV, and predicted UV-Vis
    AUC values into a set of merged descriptor columns.  The result is saved
    as ``<base_dir>/test_set_with_fP_rdkit_prop_UVvis.pkl``.

    Parameters
    ----------
    base_dir : str
        Results directory containing ``xtb_input.pkl`` and
        ``dataframe_all_res_QM_xtb.csv``.
    df_AUCs : pandas.DataFrame
        Predicted UV-Vis AUC data with columns ``SRN``, ``100-1000``,
        ``from250``, and ``to700`` (as produced by
        :func:`qm_lux.utils.uvvis.run_AUCs_spectra`).
    """
    base_dir = os.path.abspath(base_dir)

    with open(os.path.join(base_dir, "xtb_input.pkl"), "rb") as f:
        df_ini = pickle.load(f)

    df_ini["INDEX_MERGE"] = df_ini.index

    df_AUCs = df_AUCs.reset_index(drop=True)
    df_AUCs[["INDEX_MERGE", "UV"]] = df_AUCs["SRN"].str.split("_", n=1, expand=True)
    df_AUCs["INDEX_MERGE"] = df_AUCs["INDEX_MERGE"].astype(int)
    df_fp_phys_chem_chiral2 = pd.merge(df_ini, df_AUCs, on="INDEX_MERGE")

    df_fp_phys_chem_chiral2["SRN"] = df_fp_phys_chem_chiral2["SRN_x"]

    HLg = pd.read_csv(os.path.join(base_dir, "dataframe_all_res_QM_xtb.csv"))
    df_fp_phys_chem_chiral2 = pd.merge(
        df_fp_phys_chem_chiral2, HLg[["SRN", "HOMO-LUMO GAP (eV)"]], on="SRN"
    )

    df_fp_phys_chem_chiral2["HLg_list"] = df_fp_phys_chem_chiral2[
        "HOMO-LUMO GAP (eV)"
    ].apply(lambda x: [x])
    df_fp_phys_chem_chiral2["SET_VAL"] = "TEST"

    df_fp_phys_chem_chiral2["SRN"] = df_fp_phys_chem_chiral2["SRN_x"]
    all_data = copy.deepcopy(df_fp_phys_chem_chiral2)
    all_data = all_data.reset_index(drop=True)
    _descr_250_700 = [
        "250-260pred", "260-270pred", "270-280pred", "280-290pred",
        "290-300pred", "300-310pred", "310-320pred", "320-330pred",
        "330-340pred", "340-350pred", "350-360pred", "360-370pred",
        "370-380pred", "380-390pred", "390-400pred", "400-410pred",
        "410-420pred", "420-430pred", "430-440pred", "440-450pred",
        "450-460pred", "460-470pred", "470-480pred", "480-490pred",
        "490-500pred", "500-510pred", "510-520pred", "520-530pred",
        "530-540pred", "540-550pred", "550-560pred", "560-570pred",
        "570-580pred", "580-590pred", "590-600pred", "600-610pred",
        "610-620pred", "620-630pred", "630-640pred", "640-650pred",
        "650-660pred", "660-670pred", "670-680pred", "680-690pred",
        "690-700pred",
    ]
    all_data["250-700"] = all_data[_descr_250_700].values.tolist()
    all_data = descr_merge(all_data, ["fp_Morganclean", "descriptors_SMILES_CLEAN"])

    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN", "HLg_list"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN", "to700"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN", "from250"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN", "100-1000"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN", "250-700"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list", "to700"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list", "from250"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list", "100-1000"]
    )
    all_data = descr_merge(
        all_data, ["fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list", "250-700"]
    )

    list_col = [
        "SRN",
        "SMILES_CLEAN",
        "fp_Morganclean__descriptors_SMILES_CLEAN",
        "fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list",
        "fp_Morganclean__descriptors_SMILES_CLEAN__100-1000",
        "fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list__100-1000",
        "fp_Morganclean__descriptors_SMILES_CLEAN__from250",
        "fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list__from250",
        "fp_Morganclean__descriptors_SMILES_CLEAN__to700",
        "fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list__to700",
        "fp_Morganclean__descriptors_SMILES_CLEAN__250-700",
        "fp_Morganclean__descriptors_SMILES_CLEAN__HLg_list__250-700",
        "100-1000",
    ]

    with open(os.path.join(base_dir, "test_set_with_fP_rdkit_prop_UVvis.pkl"), "wb") as f:
        pickle.dump(all_data[list_col], f)

    print("Pickle file with the test set successfully created.")
