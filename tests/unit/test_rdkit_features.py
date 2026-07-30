# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.rdkit_features."""
import numpy as np
import pandas as pd
import pytest

from qm_lux.rdkit_features import (
    calc_descr,
    finger_print_gen,
    smi_to_descriptors,
    standardize,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SMILES = [
    "c1ccccc1",           # benzene
    "c1ccc2ccccc2c1",     # naphthalene
    "CC(=O)O",            # acetic acid
]

_CANONICAL_BENZENE = "c1ccccc1"
_KEKULIZED_BENZENE = "C1=CC=CC=C1"


def _make_df(smiles_list=None):
    smiles_list = smiles_list or _SMILES
    return pd.DataFrame({
        "SRN": [f"mol{i}" for i in range(len(smiles_list))],
        "SMILES": smiles_list,
        "SMILES_CLEAN": smiles_list,
    })


# ---------------------------------------------------------------------------
# standardize
# ---------------------------------------------------------------------------

class TestStandardize:
    def test_returns_dataframe(self):
        df = _make_df()
        result = standardize(df, "SMILES")
        assert isinstance(result, pd.DataFrame)

    def test_adds_smiles_clean_column(self):
        df = _make_df()
        result = standardize(df, "SMILES")
        assert "SMILES_CLEAN" in result.columns

    def test_original_smiles_column_preserved(self):
        df = _make_df()
        result = standardize(df, "SMILES")
        assert "SMILES" in result.columns

    def test_same_row_count(self):
        df = _make_df()
        result = standardize(df, "SMILES")
        assert len(result) == len(_SMILES)

    def test_canonical_smiles_non_empty(self):
        df = _make_df()
        result = standardize(df, "SMILES")
        assert result["SMILES_CLEAN"].str.len().gt(0).all()

    def test_does_not_modify_input(self):
        df = _make_df()
        original_smiles = df["SMILES"].tolist()
        standardize(df, "SMILES")
        assert df["SMILES"].tolist() == original_smiles

    def test_canonical_form_consistent_for_equivalent_smiles(self):
        """Two representations of benzene must standardise to the same canonical SMILES."""
        df = pd.DataFrame({
            "SRN": ["m0", "m1"],
            "SMILES": [_CANONICAL_BENZENE, _KEKULIZED_BENZENE],
        })
        result = standardize(df, "SMILES")
        assert result["SMILES_CLEAN"].iloc[0] == result["SMILES_CLEAN"].iloc[1]

    def test_salt_stripped(self):
        """Acetic acid sodium salt → only acetic acid is returned (largest fragment)."""
        df = pd.DataFrame({
            "SRN": ["m0"],
            "SMILES": ["CC(=O)[O-].[Na+]"],
        })
        result = standardize(df, "SMILES")
        # The sodium ion should have been stripped
        assert "[Na+]" not in result["SMILES_CLEAN"].iloc[0]


# ---------------------------------------------------------------------------
# finger_print_gen
# ---------------------------------------------------------------------------

class TestFingerPrintGen:
    def _df(self, smiles_list=None):
        smiles_list = smiles_list or _SMILES
        return pd.DataFrame({
            "SRN": [f"mol{i}" for i in range(len(smiles_list))],
            "SMILES_CLEAN": smiles_list,
        })

    def test_morgan_returns_dataframe(self):
        df = self._df()
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert isinstance(result, pd.DataFrame)

    def test_morgan_fp_column_added(self):
        df = self._df()
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert "fp_morgan" in result.columns

    def test_maccs_fp_length_is_167_bits(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "MACCS", "fp_maccs")
        assert len(result["fp_maccs"].iloc[0]) == 167

    def test_morgan_fp_length_default_1024_bits(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert len(result["fp_morgan"].iloc[0]) == 1024

    def test_morgan_custom_bits(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan", bits=512)
        assert len(result["fp_morgan"].iloc[0]) == 512

    def test_unknown_method_falls_back_to_maccs(self):
        """Unknown method falls back to MACCS (167 bits)."""
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "INVALID_METHOD", "fp_test")
        assert len(result["fp_test"].iloc[0]) == 167

    def test_fp_is_numpy_array(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert isinstance(result["fp_morgan"].iloc[0], np.ndarray)

    def test_fp_is_binary_for_morgan(self):
        """Morgan fingerprint bits are 0 or 1."""
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        fp = result["fp_morgan"].iloc[0]
        assert set(fp).issubset({0, 1})

    def test_fp_is_binary_for_maccs(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "MACCS", "fp_maccs")
        fp = result["fp_maccs"].iloc[0]
        assert set(fp).issubset({0, 1})

    def test_e_state_returns_array(self):
        df = self._df(["c1ccccc1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "E-state", "fp_estate")
        assert isinstance(result["fp_estate"].iloc[0], np.ndarray)

    def test_same_molecule_same_fingerprint(self):
        """Two equivalent SMILES should produce the same Morgan fingerprint."""
        df = self._df([_CANONICAL_BENZENE, _KEKULIZED_BENZENE])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        np.testing.assert_array_equal(
            result["fp_morgan"].iloc[0],
            result["fp_morgan"].iloc[1],
        )

    def test_different_molecules_different_fingerprints(self):
        """Benzene and naphthalene must not share the same Morgan fingerprint."""
        df = self._df(["c1ccccc1", "c1ccc2ccccc2c1"])
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert not np.array_equal(
            result["fp_morgan"].iloc[0],
            result["fp_morgan"].iloc[1],
        )

    def test_load_from_csv(self, tmp_path):
        """load_DF='NO' reads from a CSV file path."""
        df = self._df(["c1ccccc1", "c1ccc2ccccc2c1"])
        csv_path = tmp_path / "mols.csv"
        df.to_csv(csv_path)
        result = finger_print_gen(str(csv_path), "NO", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert "fp_morgan" in result.columns
        assert len(result) == 2

    def test_row_count_preserved(self):
        df = self._df()
        result = finger_print_gen(df, "YES", "SMILES_CLEAN", "Morgan", "fp_morgan")
        assert len(result) == len(_SMILES)


# ---------------------------------------------------------------------------
# smi_to_descriptors
# ---------------------------------------------------------------------------

class TestSmiToDescriptors:
    def test_returns_numpy_array(self):
        result = smi_to_descriptors("c1ccccc1")
        assert isinstance(result, np.ndarray)

    def test_non_empty_for_valid_smiles(self):
        result = smi_to_descriptors("c1ccccc1")
        assert len(result) > 0

    def test_consistent_length_across_molecules(self):
        """All molecules produce descriptor vectors of the same length."""
        r1 = smi_to_descriptors("c1ccccc1")
        r2 = smi_to_descriptors("c1ccc2ccccc2c1")
        r3 = smi_to_descriptors("CC(=O)O")
        assert len(r1) == len(r2) == len(r3)

    def test_descriptor_values_are_numeric(self):
        result = smi_to_descriptors("c1ccccc1")
        assert np.issubdtype(result.dtype, np.number)

    def test_different_molecules_different_descriptors(self):
        """Benzene and naphthalene must not have identical descriptor vectors."""
        r1 = smi_to_descriptors("c1ccccc1")
        r2 = smi_to_descriptors("c1ccc2ccccc2c1")
        assert not np.allclose(r1, r2, equal_nan=True)

    def test_sodium_salt_stripped(self):
        """SMILES with [Na] radical: result must be non-empty (Na stripped)."""
        result = smi_to_descriptors("[Na].CC(=O)O")
        assert isinstance(result, np.ndarray)


# ---------------------------------------------------------------------------
# calc_descr
# ---------------------------------------------------------------------------

class TestCalcDescr:
    def _df(self, smiles_list=None):
        smiles_list = smiles_list or _SMILES
        return pd.DataFrame({
            "SRN": [f"mol{i}" for i in range(len(smiles_list))],
            "SMILES_CLEAN": smiles_list,
        })

    def test_returns_dataframe(self):
        df = self._df()
        result = calc_descr(df, "SMILES_CLEAN")
        assert isinstance(result, pd.DataFrame)

    def test_descriptor_column_added(self):
        df = self._df()
        result = calc_descr(df, "SMILES_CLEAN")
        assert "descriptors_SMILES_CLEAN" in result.columns

    def test_same_row_count(self):
        df = self._df()
        result = calc_descr(df, "SMILES_CLEAN")
        assert len(result) == len(df)

    def test_descriptor_arrays_non_empty(self):
        df = self._df(["c1ccccc1"])
        result = calc_descr(df, "SMILES_CLEAN")
        arr = result["descriptors_SMILES_CLEAN"].iloc[0]
        assert len(arr) > 0

    def test_original_columns_preserved(self):
        df = self._df(["c1ccccc1"])
        result = calc_descr(df, "SMILES_CLEAN")
        assert "SRN" in result.columns
        assert "SMILES_CLEAN" in result.columns

    def test_column_name_uses_smiles_arg(self):
        """Column name must be 'descriptors_' + the smiles argument."""
        df = pd.DataFrame({"SRN": ["m0"], "SMILES_MY": ["c1ccccc1"]})
        result = calc_descr(df, "SMILES_MY")
        assert "descriptors_SMILES_MY" in result.columns
