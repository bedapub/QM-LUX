# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for rdkit_fp_phys_chem.py and Chirality_evaluation.py (public subset)."""
import numpy as np
import pandas as pd
import pytest
from rdkit import Chem

from qm_lux.rdkit_features import (
    calc_descr,
    finger_print_gen,
    smi_to_descriptors,
    standardize,
)
from qm_lux.chirality import (
    lack_chiral_finder,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _smiles_df(smiles_list, col="SMILES"):
    return pd.DataFrame({col: smiles_list})


def _srn_df(records):
    """records: list of (SRN, SMILES) tuples."""
    return pd.DataFrame(records, columns=["SRN", "SMILES_CLEAN"])


# ---------------------------------------------------------------------------
# standardize
# ---------------------------------------------------------------------------

class TestStandardize:
    def test_adds_smiles_clean_column(self):
        df = _smiles_df(["c1ccccc1"])
        result = standardize(df, "SMILES")
        assert "SMILES_CLEAN" in result.columns

    def test_input_unchanged(self):
        df = _smiles_df(["c1ccccc1"])
        _ = standardize(df, "SMILES")
        assert "SMILES_CLEAN" not in df.columns

    def test_canonical_smiles_produced(self):
        df = _smiles_df(["C1=CC=CC=C1"])  # non-canonical benzene
        result = standardize(df, "SMILES")
        mol = Chem.MolFromSmiles(result["SMILES_CLEAN"].iloc[0])
        assert mol is not None

    def test_fragment_parent_kept(self):
        df = _smiles_df(["c1ccccc1.O"])   # benzene + water
        result = standardize(df, "SMILES")
        clean = result["SMILES_CLEAN"].iloc[0]
        assert "." not in clean

    def test_row_count_preserved(self, sample_smiles):
        df = _smiles_df(sample_smiles)
        result = standardize(df, "SMILES")
        assert len(result) == len(sample_smiles)

    def test_benzene_roundtrip(self):
        df = _smiles_df(["c1ccccc1"])
        result = standardize(df, "SMILES")
        assert Chem.MolToSmiles(Chem.MolFromSmiles("c1ccccc1")) == \
               result["SMILES_CLEAN"].iloc[0]


# ---------------------------------------------------------------------------
# finger_print_gen — Morgan
# ---------------------------------------------------------------------------

class TestFingerPrintGenMorgan:
    def _df(self, smiles_list):
        return pd.DataFrame({"SMILES": smiles_list})

    def test_returns_dataframe(self, sample_smiles):
        df = self._df(sample_smiles)
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        assert isinstance(result, pd.DataFrame)

    def test_fp_column_added(self, sample_smiles):
        df = self._df(sample_smiles)
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        assert "fp_Morgan" in result.columns

    def test_fp_length_1024(self, sample_smiles):
        df = self._df(sample_smiles)
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        for fp in result["fp_Morgan"]:
            assert len(fp) == 1024

    def test_fp_bits_are_binary(self, sample_smiles):
        df = self._df(sample_smiles)
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        for fp in result["fp_Morgan"]:
            assert set(fp).issubset({0.0, 1.0})

    def test_different_molecules_differ(self):
        df = self._df(["c1ccccc1", "c1ccc2ccccc2c1"])
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        fp0 = result["fp_Morgan"].iloc[0]
        fp1 = result["fp_Morgan"].iloc[1]
        assert not np.array_equal(fp0, fp1)

    def test_same_molecule_same_fp(self):
        df = self._df(["c1ccccc1", "c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan")
        assert np.array_equal(result["fp_Morgan"].iloc[0],
                              result["fp_Morgan"].iloc[1])

    def test_custom_bits(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES", "Morgan", "fp_Morgan",
                                  bits=512, radius=2)
        assert len(result["fp_Morgan"].iloc[0]) == 512


# ---------------------------------------------------------------------------
# finger_print_gen — MACCS
# ---------------------------------------------------------------------------

class TestFingerPrintGenMACCS:
    def test_maccs_length_167(self, sample_smiles):
        df = pd.DataFrame({"SMILES": sample_smiles})
        result = finger_print_gen(df, "YES", "SMILES", "MACCS", "fp_MACCS")
        for fp in result["fp_MACCS"]:
            assert len(fp) == 167

    def test_maccs_bits_binary(self, sample_smiles):
        df = pd.DataFrame({"SMILES": sample_smiles})
        result = finger_print_gen(df, "YES", "SMILES", "MACCS", "fp_MACCS")
        for fp in result["fp_MACCS"]:
            assert set(fp).issubset({0.0, 1.0})


# ---------------------------------------------------------------------------
# finger_print_gen — RDKIT method bug
# ---------------------------------------------------------------------------

class TestFingerPrintGenRDKITBug:
    def test_rdkit_method_falls_back_to_maccs(self):
        """Unknown method falls back to MACCS with a printed warning."""
        df = pd.DataFrame({"SMILES": ["c1ccccc1"]})
        result = finger_print_gen(df, "YES", "SMILES", "RDKIT", "fp_RDKIT")
        assert "fp_RDKIT" in result.columns
        assert result["fp_RDKIT"].iloc[0].shape == (167,)


# ---------------------------------------------------------------------------
# smi_to_descriptors
# ---------------------------------------------------------------------------

class TestSmiToDescriptors:
    def test_returns_numpy_array(self):
        result = smi_to_descriptors("c1ccccc1")
        assert isinstance(result, np.ndarray)

    def test_same_smiles_same_result(self):
        r1 = smi_to_descriptors("c1ccccc1")
        r2 = smi_to_descriptors("c1ccccc1")
        assert np.array_equal(r1, r2)

    def test_different_smiles_differ(self):
        r_benz = smi_to_descriptors("c1ccccc1")
        r_naph = smi_to_descriptors("c1ccc2ccccc2c1")
        assert not np.array_equal(r_benz, r_naph)

    def test_benzene_molecular_weight(self):
        from rdkit.Chem import Descriptors
        desc_names = [x[0] for x in Descriptors._descList]
        mw_idx = desc_names.index("MolWt")
        result = smi_to_descriptors("c1ccccc1")
        assert result[mw_idx] == pytest.approx(78.11, abs=0.1)

    def test_salt_removed_before_descriptors(self):
        r_clean = smi_to_descriptors("c1ccccc1")
        r_salt = smi_to_descriptors("c1ccccc1.[Na]")
        assert np.array_equal(r_clean, r_salt)


# ---------------------------------------------------------------------------
# calc_descr
# ---------------------------------------------------------------------------

class TestCalcDescr:
    def test_adds_descriptor_column(self, sample_smiles):
        df = pd.DataFrame({"SMILES": sample_smiles})
        result = calc_descr(df, "SMILES")
        assert "descriptors_SMILES" in result.columns

    def test_row_count_preserved(self, sample_smiles):
        df = pd.DataFrame({"SMILES": sample_smiles})
        result = calc_descr(df, "SMILES")
        assert len(result) == len(sample_smiles)

    def test_each_row_is_array(self, sample_smiles):
        df = pd.DataFrame({"SMILES": sample_smiles})
        result = calc_descr(df, "SMILES")
        for arr in result["descriptors_SMILES"]:
            assert isinstance(arr, np.ndarray)


# ---------------------------------------------------------------------------
# lack_chiral_finder
# ---------------------------------------------------------------------------

class TestLackChiralFinder:
    def test_no_chiral_center_returns_empty(self):
        df = _srn_df([("mol1", "c1ccccc1")])
        result = lack_chiral_finder(df, "SMILES_CLEAN")
        assert result == []

    def test_defined_chirality_returns_empty(self):
        df = _srn_df([("ala", "N[C@@H](C)C(=O)O")])
        result = lack_chiral_finder(df, "SMILES_CLEAN")
        assert result == []

    def test_unassigned_chirality_returns_srn(self):
        df = _srn_df([("ala_ambig", "NC(C)C(=O)O")])
        result = lack_chiral_finder(df, "SMILES_CLEAN")
        assert "ala_ambig" in result

    def test_mixed_returns_only_unassigned(self):
        df = _srn_df([
            ("defined", "N[C@@H](C)C(=O)O"),
            ("ambig",   "NC(C)C(=O)O"),
            ("achiral",  "c1ccccc1"),
        ])
        result = lack_chiral_finder(df, "SMILES_CLEAN")
        assert result == ["ambig"]

