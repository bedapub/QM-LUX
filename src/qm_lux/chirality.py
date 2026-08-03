# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Chirality analysis and stereo-isomer enumeration using RDKit.

The two main entry points used by the Snakemake workflow are:

* :func:`chirality_analysis_all` — enumerate all possible stereo isomers from
  unassigned chiral centres (used when ``stereo_check="NO"``).
* :func:`chirality_analysis` — assign known stereo centres and flag compounds
  with more than one ambiguous chiral centre (used when ``stereo_check="YES"``).
"""

import copy

import pandas as pd
from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions


def lack_chiral_finder(df, col):
    """Find SRN identifiers of compounds with at least one unassigned chiral centre.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ``SRN`` and the SMILES column named by ``col``.
    col : str
        Column name containing SMILES strings.

    Returns
    -------
    list of str
        SRN values for which at least one chiral centre has unknown
        configuration (``"?"``).
    """
    list_remove = []
    for index, row in df.iterrows():
        m = Chem.MolFromSmiles(row[col])
        chiral_centers = Chem.FindMolChiralCenters(
            m, force=True, includeUnassigned=True, useLegacyImplementation=True
        )
        for chiral_center in chiral_centers:
            if chiral_center[1] == "?":
                list_remove.append(row["SRN"])
                break
    return list_remove


def chiral_center_miss_render(df, list_miss_chiral):
    """Annotate compounds with unassigned chiral centres in a DataFrame.

    Adds a ``"Chiral Center"`` column (``"1"`` or ``">1"``) and a
    ``"Chirality"`` column (``"AMBIGUOUS"`` or ``""``) to the DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing ``SRN`` and ``SMILES_CLEAN`` columns.
    list_miss_chiral : list of str
        SRN values of compounds with unassigned chiral centres (as returned
        by :func:`lack_chiral_finder`).

    Returns
    -------
    pandas.DataFrame
        Annotated DataFrame with ``"Chiral Center"`` and ``"Chirality"``
        columns added.
    """
    df["Chiral Center"] = ""
    for index, cmp in df.iterrows():
        check = 0
        for srn in list_miss_chiral:
            if cmp["SRN"] == srn:
                m = Chem.MolFromSmiles(cmp["SMILES_CLEAN"])
                chiral_centers = Chem.FindMolChiralCenters(
                    m, force=True, includeUnassigned=True, useLegacyImplementation=True
                )
                print(cmp["SMILES_CLEAN"], "INDEX:", index)
                print(chiral_centers)
                df.at[index, "Chirality"] = "AMBIGUOUS"
                check = 1
                if len(chiral_centers) == 1:
                    df.at[index, "Chiral Center"] = "1"
                else:
                    df.at[index, "Chiral Center"] = ">1"
                break
            else:
                continue
        if check == 0:
            df.at[index, "Chirality"] = ""

    return df


def chirality_generator(df, col, two_enantiomers=False):
    """Enumerate stereo isomers for compounds with exactly one chiral centre.

    For each compound in ``df`` where ``"Chiral Center"`` is ``"1"``,
    enumerates possible stereo isomers.  ``two_enantiomers`` selects what is
    done with them:

    * ``False`` (default, the training path) — keep a single enantiomer and
      overwrite ``"SMILES_CLEAN"`` in place with the first unique isomer.
    * ``True`` (the curation path) — keep both enantiomers side by side in new
      ``"SMILES_CLEAN_0"`` and ``"SMILES_CLEAN_1"`` columns, leaving
      ``"SMILES_CLEAN"`` untouched.  Compounds yielding fewer than two isomers
      are skipped and get ``NaN`` in both columns.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ``SRN``, ``col``, and ``"Chiral Center"``.
    col : str
        SMILES column to enumerate from.
    two_enantiomers : bool, optional
        Keep both enantiomers in separate columns instead of collapsing to
        one.  Default ``False``.

    Returns
    -------
    pandas.DataFrame
        Copy of the input.  With ``two_enantiomers=False``, ``"SMILES_CLEAN"``
        is updated for applicable rows; with ``True``, ``"SMILES_CLEAN_0"``
        and ``"SMILES_CLEAN_1"`` are added.
    """
    df2 = copy.deepcopy(df)
    message_list = []
    for index, cmp in df.iterrows():
        if cmp["Chiral Center"] == "1":
            print(cmp["SRN"])
            m = Chem.MolFromSmiles(cmp[col])
            opts = StereoEnumerationOptions(unique=True, onlyUnassigned=True, tryEmbedding=True)
            isomers = tuple(EnumerateStereoisomers(m, options=opts))
            print(isomers)
            if not two_enantiomers:
                if len(isomers) != 0:
                    smi = Chem.MolToSmiles(isomers[0])
                    print(smi)
                    df2.at[index, "SMILES_CLEAN"] = smi
                else:
                    message_list.append(cmp["SRN"])
            # Two enantiomers requires two isomers to put in the two columns;
            # one isomer is not half an answer here, so the row is skipped
            # rather than half-filled.
            elif len(isomers) >= 2:
                smi1 = Chem.MolToSmiles(isomers[0])
                smi2 = Chem.MolToSmiles(isomers[1])
                print(f"Stereoisomer 1: {smi1}")
                print(f"Stereoisomer 2: {smi2}")
                df2.at[index, "SMILES_CLEAN_0"] = smi1
                df2.at[index, "SMILES_CLEAN_1"] = smi2
            else:
                message_list.append(cmp["SRN"])

    print("compounds without ambiguous chirality generated (only for one chiral center)")
    return df2


def chirality_generator_all(df, col, tryEmbedding=True):
    """Enumerate all stereo isomers for every compound in the DataFrame.

    For each compound, enumerates possible stereo isomers and creates one row
    per isomer with a suffixed SRN (e.g. ``"CPD-001_0"``, ``"CPD-001_1"``).
    When the number of enumerated isomers equals 2^N (with N chiral centres),
    only half are retained to avoid enantiomeric pairs.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ``SRN`` and the SMILES column named by ``col``.
    col : str
        SMILES column to enumerate from.
    tryEmbedding : bool, optional
        Passed through to :class:`StereoEnumerationOptions`.  Default ``True``.

    Returns
    -------
    pandas.DataFrame
        Expanded DataFrame with one row per enumerated isomer; columns
        ``SRN``, ``SMILES_CLEAN_CHIRAL``, and ``SMILES``.
    """
    df_final = pd.DataFrame()
    message_list = []
    for index, cmp in df.iterrows():
        print(cmp["SRN"])
        m = Chem.MolFromSmiles(cmp[col])
        opts = StereoEnumerationOptions(
            unique=True, onlyUnassigned=True, tryEmbedding=tryEmbedding
        )
        isomers = tuple(EnumerateStereoisomers(m, options=opts))
        chiral_centers = Chem.FindMolChiralCenters(
            m, force=True, includeUnassigned=True, useLegacyImplementation=True
        )
        print(2 ** len(chiral_centers))
        print(len(isomers))
        if len(isomers) != 0:
            smi_chiral = []
            smi_srn = []
            if len(isomers) == 1:
                smi = Chem.MolToSmiles(isomers[0])
                smi_chiral.append(smi)
                smi_srn.append(cmp["SRN"] + "_" + str(0))
                df_chiral = pd.DataFrame({
                    "SRN": smi_srn,
                    "SMILES_CLEAN_CHIRAL": smi_chiral,
                    "SMILES": cmp[col],
                })
            elif 2 ** len(chiral_centers) != len(isomers):
                for chiral in range(len(isomers)):
                    smi = Chem.MolToSmiles(isomers[chiral])
                    print(smi)
                    smi_chiral.append(smi)
                    smi_srn.append(cmp["SRN"] + "_" + str(chiral))
                    df_chiral = pd.DataFrame({
                        "SRN": smi_srn,
                        "SMILES_CLEAN_CHIRAL": smi_chiral,
                        "SMILES": cmp[col],
                    })
            else:
                for chiral in range(int(2 ** len(chiral_centers) / 2)):
                    print(chiral_centers)
                    smi = Chem.MolToSmiles(isomers[chiral])
                    print(smi)
                    smi_chiral.append(smi)
                    smi_srn.append(cmp["SRN"] + "_" + str(chiral))
                    df_chiral = pd.DataFrame({
                        "SRN": smi_srn,
                        "SMILES_CLEAN_CHIRAL": smi_chiral,
                        "SMILES": cmp[col],
                    })
        else:
            message_list.append(cmp["SRN"])

        df_final = pd.concat([df_final, df_chiral])

    return df_final


def chirality_analysis(df, col, two_enantiomers=False):
    """Assign stereochemistry and flag ambiguous compounds.

    Combines :func:`lack_chiral_finder`, :func:`chiral_center_miss_render`,
    and :func:`chirality_generator` to produce a DataFrame with all one-centre
    ambiguities resolved and multi-centre ambiguities flagged.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame with SMILES in column ``col`` and ``SRN`` identifiers.
    col : str
        SMILES column name.
    two_enantiomers : bool, optional
        Passed through to :func:`chirality_generator`.  ``False`` (default)
        collapses each single-centre compound to one enantiomer in
        ``"SMILES_CLEAN"``; ``True`` keeps both in ``"SMILES_CLEAN_0"`` and
        ``"SMILES_CLEAN_1"``.

    Returns
    -------
    pandas.DataFrame
        Annotated DataFrame with ``"Chiral Center"`` and ``"Chirality"``
        columns and resolved single-centre stereo SMILES.
    """
    df2 = copy.deepcopy(df)
    list_remove = lack_chiral_finder(df2, col)
    df2 = chiral_center_miss_render(df2, list_remove)
    df2 = chirality_generator(df2, col, two_enantiomers)
    return df2


def chirality_analysis_all(df, col, tryEmbedding=True):
    """Enumerate all stereo isomers for all compounds.

    Thin wrapper around :func:`chirality_generator_all`.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame with SMILES in column ``col`` and ``SRN`` identifiers.
    col : str
        SMILES column name.
    tryEmbedding : bool, optional
        Passed through to :func:`chirality_generator_all`.  Default ``True``.

    Returns
    -------
    pandas.DataFrame
        Expanded DataFrame with one row per enumerated stereo isomer.
    """
    return chirality_generator_all(df, col, tryEmbedding)



