# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""RDKit-based molecular feature computation: SMILES standardisation and fingerprints.

The functions used by the Snakemake workflow are:

* :func:`standardize` — canonical SMILES standardisation (fragment removal,
  clean-up).
* :func:`finger_print_gen` — Morgan or MACCS fingerprint generation.
* :func:`calc_descr` — RDKit 2-D descriptor calculation.
"""

import copy

import numpy as np
import pandas as pd
import rdkit
from rdkit import Chem
from rdkit.Chem import Descriptors, MACCSkeys, MolStandardize, SaltRemover
from rdkit.Chem.AllChem import GetMorganFingerprintAsBitVect
from rdkit.ML.Descriptors import MoleculeDescriptors


def standardize(df, smiles_col):
    """Standardise SMILES strings using RDKit MolStandardize.

    Applies salt stripping, normalisation, and fragment-parent selection
    following the workflow described by Greg Landrum (RSC OpenScience 2021).
    No neutralisation or tautomer canonicalisation is performed — the aim is
    a consistent single representation suitable for ML.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame with a SMILES column.
    smiles_col : str
        Name of the SMILES column.

    Returns
    -------
    pandas.DataFrame
        Copy of the input with a ``"SMILES_CLEAN"`` column added.
    """
    df2 = copy.deepcopy(df)
    clean_smiles_all = []

    for i in df[smiles_col]:
        mol = Chem.MolFromSmiles(str(i))
        clean_mol = rdkit.Chem.MolStandardize.rdMolStandardize.Cleanup(mol)
        parent_clean_mol = rdkit.Chem.MolStandardize.rdMolStandardize.FragmentParent(clean_mol)
        clean_smiles = Chem.MolToSmiles(parent_clean_mol, canonical=True, doRandom=False)
        clean_smiles_all.append(clean_smiles)

    df2["SMILES_CLEAN"] = clean_smiles_all
    return df2


def finger_print_gen(mol, load_DF, smiles, method, fp_name, bits=1024, radius=3):
    """Generate molecular fingerprints and add them as a new DataFrame column.

    Supported fingerprint types are ``"MACCS"`` (167-bit MACCS keys),
    ``"Morgan"`` (configurable bit count and radius), and ``"E-state"``
    (RDKit path fingerprint used as a proxy).  An unknown ``method`` falls back
    to MACCS with a warning.

    Parameters
    ----------
    mol : str or pandas.DataFrame
        CSV file path (when ``load_DF="NO"``) or a DataFrame (when
        ``load_DF="YES"``).
    load_DF : {"YES", "NO"}
        Whether ``mol`` is already a DataFrame (``"YES"``) or a file path
        (``"NO"``).
    smiles : str
        Name of the SMILES column in the DataFrame.
    method : {"MACCS", "Morgan", "E-state"}
        Fingerprint type.
    fp_name : str
        Name of the output column holding the fingerprint arrays.
    bits : int, optional
        Number of bits for the Morgan fingerprint.  Default ``1024``.
    radius : int, optional
        Radius for the Morgan fingerprint.  Default ``3``.

    Returns
    -------
    pandas.DataFrame
        Copy of the input DataFrame with ``fp_name`` column added.
    """
    if load_DF == "NO":
        dataframe = pd.read_csv(mol, index_col=0)
        dataframe.dropna(inplace=True)
    else:
        dataframe = mol.copy()

    mol_smi = [Chem.MolFromSmiles(smi) for smi in dataframe[str(smiles)]]

    if method == "MACCS":
        fp = [np.array(MACCSkeys.GenMACCSKeys(m)) for m in mol_smi]
    elif method == "Morgan":
        fp = [np.array(GetMorganFingerprintAsBitVect(m, radius, nBits=bits)) for m in mol_smi]
    elif method == "E-state":
        fp = [np.array(Chem.RDKFingerprint(m)) for m in mol_smi]
    else:
        print(f"Warning: Wrong method specified: {method}. The default MACCS will be used instead.")
        fp = [np.array(MACCSkeys.GenMACCSKeys(m)) for m in mol_smi]

    dataframe2 = dataframe.copy()
    dataframe2[fp_name] = fp
    return dataframe2


def smi_to_descriptors(smiles):
    """Calculate all RDKit 2-D descriptors for a single SMILES string.

    Sodium radicals are stripped from the SMILES before descriptor calculation
    to avoid erroneous ion entries.

    Parameters
    ----------
    smiles : str
        Input SMILES string.

    Returns
    -------
    numpy.ndarray
        Array of RDKit 2-D descriptor values, or an empty list if the
        molecule could not be parsed.
    """
    calc = MoleculeDescriptors.MolecularDescriptorCalculator(
        [x[0] for x in Descriptors._descList]
    )
    remover = SaltRemover.SaltRemover(defnData="[Na]")
    mol = remover.StripMol(Chem.MolFromSmiles(smiles), dontRemoveEverything=True)

    descriptors = []
    if mol:
        descriptors = np.array(calc.CalcDescriptors(mol))
    return descriptors


def calc_descr(df, smiles):
    """Calculate RDKit 2-D descriptors for all compounds in a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a SMILES column.
    smiles : str
        SMILES column name.

    Returns
    -------
    pandas.DataFrame
        Copy of the input with a new ``"descriptors_{smiles}"`` column
        containing the descriptor arrays.
    """
    col_new = "descriptors_" + smiles
    df_descr = df.copy()
    df_descr[col_new] = df[smiles].apply(smi_to_descriptors)
    return df_descr
