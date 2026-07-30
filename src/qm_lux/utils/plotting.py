# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Visualisation helpers: UV-Vis spectrum plots and RDKit molecule images.

Both functions are re-exported from :mod:`qm_lux.utils.io` for backward
compatibility.
"""

import os
import pickle

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rdkit import Chem


def plot_UV(base_dir, df_uv):
    """Generate UV-Vis spectrum PNG plots for each compound.

    For each compound, plots the predicted absorption spectrum between 250 and
    700 nm and saves the figure as ``<base_dir>/UV_plots/<SRN>.png``.

    Parameters
    ----------
    base_dir : str
        Working directory containing ``xtb_input.pkl``; UV plots are saved to
        ``<base_dir>/UV_plots/``.
    df_uv : pandas.DataFrame
        UV-Vis data with columns ``SRN``, ``lambda (nm)``,
        ``Epsilon (mL/cm/mol)``.
    """
    base_dir = os.path.abspath(base_dir)
    with open(os.path.join(base_dir, "xtb_input.pkl"), "rb") as f:
        df_srn = pickle.load(f)

    print("DF")
    print(df_uv)
    df_uv = df_uv.sort_values(["SRN", "lambda (nm)"], ascending=True)
    df_srn["INDEX_MERGE"] = df_srn.index
    df_uv[["INDEX_MERGE", "UV"]] = df_uv["SRN"].str.split("_", n=1, expand=True)
    df_uv["INDEX_MERGE"] = df_uv["INDEX_MERGE"].astype(int)
    df = pd.merge(df_srn, df_uv.loc[:, ~df_uv.columns.isin(["SRN"])], on="INDEX_MERGE")

    x = np.array(list(df["SRN"]))
    list_cmp = np.unique(x)
    print(list_cmp)

    directory = os.path.join(base_dir, "UV_plots")
    if not os.path.exists(directory):
        os.makedirs(directory)

    for i in list_cmp:
        df_i = df[df["SRN"] == i]
        df_i = df_i[df_i["lambda (nm)"] > 250]
        df_i = df_i[df_i["lambda (nm)"] <= 700]

        list_x = list(df_i["lambda (nm)"])
        list_y = list(df_i["Epsilon (mL/cm/mol)"])

        index_MAC_lambda = list_y.index(max(list_y))

        fig, ax = plt.subplots()
        ax.plot([float(x) for x in list_x], [float(x) for x in list_y], linewidth=2.0, color="blue")
        ax.set_xlabel("lambda (nm)", fontsize=14, color="blue")
        ax.set_ylabel("PRED ABS (L/mol/cm)", color="blue", fontsize=14)
        plt.grid(which="major", axis="both")
        plt.title(i)
        plt.savefig(os.path.join(directory, f"{i}.png"))
        plt.show()

        print("############", i, "############")
        print("******* PREDICTED SPECTRA *******")
        print("Abs.: ", int(list_y[index_MAC_lambda]), "L/mol/cm")
        print("lambda max Abs.: ", int(list_x[index_MAC_lambda]), "nm")


def create_molecule_images(path, output_dir="molecule_images"):
    """Generate RDKit 2-D structure PNG images for each compound.

    Reads ``<path>/test_set_with_fP_rdkit_prop_UVvis.pkl`` and saves one
    300×300 px PNG per compound to ``<path>/<output_dir>/``.

    Parameters
    ----------
    path : str
        Directory containing the test-set pickle file.
    output_dir : str, optional
        Sub-directory name for PNG output.  Default ``"molecule_images"``.
    """
    from rdkit.Chem import Draw

    file_path = os.path.join(path, "test_set_with_fP_rdkit_prop_UVvis.pkl")

    if os.path.exists(file_path):
        df = pd.read_pickle(file_path)
        print("Dataset successfully loaded.")
    else:
        print(f"The file '{file_path}' does not exist. Check the path and try again.")
        return

    os.makedirs(os.path.join(path, output_dir), exist_ok=True)

    for index, row in df.iterrows():
        smiles = row["SMILES_CLEAN"]
        srn = row["SRN"]
        molecule = Chem.MolFromSmiles(smiles)

        if molecule:
            img_path = os.path.join(path, output_dir, f"{srn}.png")
            Draw.MolToFile(molecule, img_path, size=(300, 300))
            print(f"Saved molecule image: {img_path}")
        else:
            print(f"Invalid SMILES string for SRN: {srn}")
