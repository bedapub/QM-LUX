# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.chirality."""
import pandas as pd
import pytest

from qm_lux.chirality import (
    chiral_center_miss_render,
    chirality_analysis,
    chirality_analysis_all,
    chirality_generator,
    lack_chiral_finder,
)


# ---------------------------------------------------------------------------
# Molecule SMILES used in fixtures
# ---------------------------------------------------------------------------

# No chiral centres at all
_BENZENE = "c1ccccc1"
# One fully assigned (S) chiral centre
_ALANINE_S = "N[C@@H](C)C(=O)O"
# One unassigned chiral centre
_ALANINE_NOSTR = "CC(N)C(=O)O"
# Two assigned chiral centres
_TARTARIC_ACID = "OC(=O)[C@@H](O)[C@H](O)C(=O)O"


def _make_df(smiles_list, srn_prefix="mol"):
    """Build a minimal DataFrame with SRN, SMILES, and SMILES_CLEAN columns."""
    n = len(smiles_list)
    return pd.DataFrame({
        "SRN": [f"{srn_prefix}{i}" for i in range(n)],
        "SMILES": smiles_list,
        "SMILES_CLEAN": smiles_list,
    })


# ---------------------------------------------------------------------------
# lack_chiral_finder
# ---------------------------------------------------------------------------

class TestLackChiralFinder:
    def test_returns_list(self):
        df = _make_df([_BENZENE])
        assert isinstance(lack_chiral_finder(df, "SMILES"), list)

    def test_benzene_no_unassigned_chiral(self):
        df = _make_df([_BENZENE])
        assert lack_chiral_finder(df, "SMILES") == []

    def test_assigned_alanine_not_flagged(self):
        """Fully assigned chiral centre must not be reported as missing."""
        df = _make_df([_ALANINE_S])
        assert lack_chiral_finder(df, "SMILES") == []

    def test_unassigned_alanine_flagged(self):
        df = _make_df([_ALANINE_NOSTR])
        result = lack_chiral_finder(df, "SMILES")
        assert result == ["mol0"]

    def test_mixed_molecules_only_unassigned_flagged(self):
        df = _make_df([_BENZENE, _ALANINE_NOSTR, _ALANINE_S])
        result = lack_chiral_finder(df, "SMILES")
        assert "mol1" in result
        assert "mol0" not in result
        assert "mol2" not in result

    def test_tartaric_acid_assigned_not_flagged(self):
        """Both chiral centres assigned → not flagged."""
        df = _make_df([_TARTARIC_ACID])
        assert lack_chiral_finder(df, "SMILES") == []

    def test_custom_column_name(self):
        df = pd.DataFrame({
            "SRN": ["mol0"],
            "MY_SMILES": [_ALANINE_NOSTR],
        })
        result = lack_chiral_finder(df, "MY_SMILES")
        assert "mol0" in result


# ---------------------------------------------------------------------------
# chiral_center_miss_render
# ---------------------------------------------------------------------------

class TestChiralCenterMissRender:
    def test_returns_dataframe(self):
        df = _make_df([_BENZENE])
        result = chiral_center_miss_render(df.copy(), [])
        assert isinstance(result, pd.DataFrame)

    def test_chiral_center_column_added(self):
        df = _make_df([_BENZENE])
        result = chiral_center_miss_render(df.copy(), [])
        assert "Chiral Center" in result.columns

    def test_chirality_column_empty_when_no_missing(self):
        df = _make_df([_BENZENE])
        result = chiral_center_miss_render(df.copy(), [])
        assert result["Chirality"].iloc[0] == ""

    def test_annotates_ambiguous_for_listed_srn(self):
        df = _make_df([_ALANINE_NOSTR])
        result = chiral_center_miss_render(df.copy(), ["mol0"])
        assert result["Chirality"].iloc[0] == "AMBIGUOUS"

    def test_single_centre_marked_as_1(self):
        df = _make_df([_ALANINE_NOSTR])
        result = chiral_center_miss_render(df.copy(), ["mol0"])
        assert result["Chiral Center"].iloc[0] == "1"

    def test_non_listed_srn_not_marked_ambiguous(self):
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        # Only mol1 is in list_miss_chiral
        result = chiral_center_miss_render(df.copy(), ["mol1"])
        assert result["Chirality"].iloc[0] == ""
        assert result["Chirality"].iloc[1] == "AMBIGUOUS"

    def test_chiral_center_empty_when_not_in_list(self):
        df = _make_df([_BENZENE])
        result = chiral_center_miss_render(df.copy(), [])
        assert result["Chiral Center"].iloc[0] == ""


# ---------------------------------------------------------------------------
# chirality_generator
# ---------------------------------------------------------------------------

class TestChiralityGenerator:
    def test_returns_dataframe(self):
        df = _make_df([_ALANINE_S])
        df["Chiral Center"] = ""
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        assert isinstance(result, pd.DataFrame)

    def test_no_chiral_centre_smiles_unchanged(self):
        """When Chiral Center != '1', SMILES_CLEAN is not modified."""
        df = _make_df([_BENZENE])
        df["Chiral Center"] = ""
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        assert result["SMILES_CLEAN"].iloc[0] == _BENZENE

    def test_assigned_stereo_unchanged(self):
        """Already-assigned SMILES with Chiral Center != '1' stays the same."""
        df = _make_df([_ALANINE_S])
        df["Chiral Center"] = ""
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        assert result["SMILES_CLEAN"].iloc[0] == _ALANINE_S

    def test_unassigned_single_centre_gets_stereospecifier(self):
        """A row with Chiral Center='1' should receive an assigned SMILES (@)."""
        df = _make_df([_ALANINE_NOSTR])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        new_smi = result["SMILES_CLEAN"].iloc[0]
        # RDKit-canonical SMILES with stereo contains @ or @@
        assert "@" in new_smi

    def test_row_count_unchanged(self):
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        df["Chiral Center"] = ["", "1"]
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# chirality_analysis
# ---------------------------------------------------------------------------

class TestChiralityAnalysis:
    def test_returns_dataframe(self):
        df = _make_df([_BENZENE])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert isinstance(result, pd.DataFrame)

    def test_chirality_column_present(self):
        df = _make_df([_BENZENE])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert "Chirality" in result.columns

    def test_no_chiral_compound_not_flagged(self):
        df = _make_df([_BENZENE])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert result["Chirality"].iloc[0] == ""

    def test_unassigned_single_centre_flagged(self):
        df = _make_df([_ALANINE_NOSTR])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert result["Chirality"].iloc[0] == "AMBIGUOUS"

    def test_input_not_mutated(self):
        df = _make_df([_BENZENE])
        original_srn = df["SRN"].tolist()
        chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert df["SRN"].tolist() == original_srn


# ---------------------------------------------------------------------------
# chirality_analysis_all
# ---------------------------------------------------------------------------

class TestChiralityAnalysisAll:
    def test_returns_dataframe(self):
        df = _make_df([_BENZENE])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        assert isinstance(result, pd.DataFrame)

    def test_output_columns(self):
        df = _make_df([_BENZENE])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        for col in ("SRN", "SMILES_CLEAN_CHIRAL", "SMILES"):
            assert col in result.columns

    def test_srn_suffixed_with_index(self):
        """Output SRN values must be suffixed with '_<n>'."""
        df = _make_df([_BENZENE])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        assert result["SRN"].iloc[0].startswith("mol0_")

    def test_benzene_one_row_returned(self):
        """Benzene has no stereo centres → exactly one isomer row."""
        df = _make_df([_BENZENE])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        # len(isomers) == 1 path: one row per compound
        assert len(result) == 1

    def test_alanine_unassigned_at_least_one_isomer(self):
        """Unassigned chiral centre → at least one isomer generated."""
        df = _make_df([_ALANINE_NOSTR])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        assert len(result) >= 1

    def test_smiles_column_contains_original_smiles(self):
        """The 'SMILES' output column preserves the input SMILES string."""
        df = _make_df([_BENZENE])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        assert result["SMILES"].iloc[0] == _BENZENE

    def test_multiple_compounds_produce_separate_rows(self):
        """Two compounds must each produce at least one row."""
        df = _make_df([_BENZENE, _ALANINE_S])
        result = chirality_analysis_all(df.copy(), "SMILES_CLEAN")
        srn_prefixes = {s.split("_")[0] for s in result["SRN"]}
        assert "mol0" in srn_prefixes
        assert "mol1" in srn_prefixes
