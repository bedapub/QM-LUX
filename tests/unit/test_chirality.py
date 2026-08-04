# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.chirality."""
import pandas as pd
import pytest

import qm_lux.chirality as chirality_mod
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

    def test_default_adds_no_enantiomer_columns(self):
        """two_enantiomers defaults to False: no extra columns appear."""
        df = _make_df([_ALANINE_NOSTR])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN")
        assert "SMILES_CLEAN_0" not in result.columns
        assert "SMILES_CLEAN_1" not in result.columns


class TestChiralityGeneratorTwoEnantiomers:
    """Tests for two_enantiomers=True — keep both enantiomers side by side."""

    def test_both_enantiomer_columns_added(self):
        df = _make_df([_ALANINE_NOSTR])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert "SMILES_CLEAN_0" in result.columns
        assert "SMILES_CLEAN_1" in result.columns

    def test_the_two_enantiomers_differ(self):
        df = _make_df([_ALANINE_NOSTR])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert result["SMILES_CLEAN_0"].iloc[0] != result["SMILES_CLEAN_1"].iloc[0]
        assert "@" in result["SMILES_CLEAN_0"].iloc[0]
        assert "@" in result["SMILES_CLEAN_1"].iloc[0]

    def test_smiles_clean_left_untouched(self):
        """Unlike the False branch, SMILES_CLEAN must not be overwritten."""
        df = _make_df([_ALANINE_NOSTR])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert result["SMILES_CLEAN"].iloc[0] == _ALANINE_NOSTR

    def test_rows_without_single_centre_are_nan(self):
        """Compounds not carrying exactly one centre get no enantiomers."""
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        df["Chiral Center"] = ["", "1"]
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert pd.isna(result["SMILES_CLEAN_0"].iloc[0])
        assert not pd.isna(result["SMILES_CLEAN_0"].iloc[1])

    def test_row_count_unchanged(self):
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        df["Chiral Center"] = ["", "1"]
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert len(result) == 2

    def test_unfilled_rows_are_a_real_nan_not_the_string(self):
        """Regression: the skipped rows must hold NaN, never a "nan" string.

        The enantiomer columns used to be created implicitly by the first
        ``.at`` write inside the loop, which on pandas < 2.2 produced a
        fixed-width numpy string array whose unwritten rows held ``str(nan)``
        truncated to that width. Those are ordinary strings, so ``pd.isna`` was
        False and a caller's ``dropna`` kept rows carrying no isomer at all.
        Assert the value is not string-like rather than only that ``isna`` holds,
        so a future regression to any truncation of "nan" is caught too.
        """
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        df["Chiral Center"] = ["", "1"]
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        for column in ("SMILES_CLEAN_0", "SMILES_CLEAN_1"):
            skipped = result[column].iloc[0]
            assert not isinstance(skipped, str), f"{column} holds the string {skipped!r}"
            assert pd.isna(skipped)

    def test_dropna_removes_exactly_the_skipped_rows(self):
        """The downstream consequence: dropna must drop the isomer-less rows."""
        df = _make_df([_BENZENE, _ALANINE_NOSTR])
        df["Chiral Center"] = ["", "1"]
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        kept = result.dropna(subset=["SMILES_CLEAN_0"])
        assert len(kept) == 1
        assert kept["SMILES_CLEAN"].iloc[0] == _ALANINE_NOSTR

    def test_centre_yielding_too_few_isomers_is_also_nan(self):
        """The other skip path: flagged as one centre, but <2 isomers enumerated.

        ``test_rows_without_single_centre_are_nan`` only covers rows filtered out
        by ``Chiral Center``; this covers a row that reaches the enumeration and
        is skipped by the ``len(isomers) >= 2`` guard, which is the branch that
        leaves the column untouched for an *already created* column.
        """
        # Benzene has no chiral centre, so enumeration yields fewer than two
        # isomers even though the column claims one centre.
        df = _make_df([_BENZENE])
        df["Chiral Center"] = "1"
        result = chirality_generator(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert not isinstance(result["SMILES_CLEAN_0"].iloc[0], str)
        assert pd.isna(result["SMILES_CLEAN_0"].iloc[0])
        assert pd.isna(result["SMILES_CLEAN_1"].iloc[0])


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

    def test_two_enantiomers_reaches_the_generator(self):
        """chirality_analysis must forward two_enantiomers, not swallow it.

        The keyword form is what the curation caller uses, so it is tested as
        a keyword rather than positionally.
        """
        df = _make_df([_ALANINE_NOSTR])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN", two_enantiomers=True)
        assert "SMILES_CLEAN_0" in result.columns
        assert result["SMILES_CLEAN_0"].iloc[0] != result["SMILES_CLEAN_1"].iloc[0]

    def test_default_keeps_one_enantiomer(self):
        """Omitting the argument keeps the single-enantiomer behaviour."""
        df = _make_df([_ALANINE_NOSTR])
        result = chirality_analysis(df.copy(), "SMILES_CLEAN")
        assert "SMILES_CLEAN_0" not in result.columns
        assert "@" in result["SMILES_CLEAN"].iloc[0]


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

    @pytest.mark.parametrize("try_embedding", [True, False])
    def test_try_embedding_reaches_rdkit(self, monkeypatch, try_embedding):
        """The tryEmbedding argument must reach StereoEnumerationOptions.

        It was previously declared on both functions but hardcoded to ``True``
        at the call site, so passing ``False`` did nothing.  Every current
        caller uses the default, which is why the dead parameter went unseen.
        """
        seen = []
        real_opts = chirality_mod.StereoEnumerationOptions

        def _spy(**kwargs):
            seen.append(kwargs.get("tryEmbedding"))
            return real_opts(**kwargs)

        monkeypatch.setattr(chirality_mod, "StereoEnumerationOptions", _spy)
        chirality_analysis_all(_make_df([_ALANINE_NOSTR]), "SMILES_CLEAN", try_embedding)
        assert seen == [try_embedding]


class TestChiralityGeneratorAllZeroIsomers:
    """A compound RDKit enumerates no isomers for must be dropped, not faked.

    RDKit returns at least one isomer for every molecule these tests could
    reasonably build, so the empty result is injected by patching
    ``EnumerateStereoisomers``.  That is the only way to reach the branch, and
    the branch is worth reaching: before the fix, a zero-isomer compound
    appended the *previous* compound's rows a second time, so the output
    silently gained a duplicate and lost a compound.
    """

    @staticmethod
    def _patch_empty_for(monkeypatch, empty_indices):
        """Make the nth call to EnumerateStereoisomers return no isomers.

        ``empty_indices`` holds 0-based call numbers; every other call is
        delegated to the real RDKit implementation so the rest of the
        function behaves normally.
        """
        real = chirality_mod.EnumerateStereoisomers
        calls = {"n": 0}

        def _fake(mol, options=None):
            i = calls["n"]
            calls["n"] += 1
            if i in empty_indices:
                return iter(())
            return real(mol, options=options)

        monkeypatch.setattr(chirality_mod, "EnumerateStereoisomers", _fake)

    def test_zero_isomer_compound_does_not_duplicate_its_predecessor(self, monkeypatch):
        """The surviving compound must appear once, not twice."""
        self._patch_empty_for(monkeypatch, {1})
        result = chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert list(result["SRN"]) == ["mol0_0"]

    def test_zero_isomer_compound_is_absent_from_the_output(self, monkeypatch):
        """The dropped compound must not be represented by another's rows."""
        self._patch_empty_for(monkeypatch, {1})
        result = chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert "mol1" not in {s.split("_")[0] for s in result["SRN"]}

    def test_smiles_column_is_not_attributed_to_the_wrong_compound(self, monkeypatch):
        """The duplicated row also carried the wrong SMILES; check the values."""
        self._patch_empty_for(monkeypatch, {1})
        result = chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert list(result["SMILES"]) == [_BENZENE]

    def test_zero_isomer_first_compound_does_not_raise(self, monkeypatch):
        """A zero-isomer compound in first position used to be an UnboundLocalError."""
        self._patch_empty_for(monkeypatch, {0})
        result = chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert list(result["SRN"]) == ["mol1_0"]

    def test_all_compounds_zero_isomers_returns_empty(self, monkeypatch):
        """No isomers anywhere → an empty frame, not a crash."""
        self._patch_empty_for(monkeypatch, {0, 1})
        result = chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert result.empty

    def test_dropped_srns_are_reported(self, monkeypatch, capsys):
        """Dropping a compound silently is what made this hard to notice.

        The function prints every SRN as it iterates, so asserting that
        ``"mol1"`` appears somewhere in stdout would pass even with no
        reporting at all.  The named SRN must follow the report marker.
        """
        self._patch_empty_for(monkeypatch, {1})
        chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        out = capsys.readouterr().out
        marker = "no stereoisomers could be enumerated, compounds dropped:"
        assert marker in out
        assert "mol1" in out.split(marker, 1)[1]

    def test_nothing_is_reported_when_every_compound_succeeds(self, monkeypatch, capsys):
        """The report must not fire on a clean run."""
        chirality_analysis_all(_make_df([_BENZENE, _ALANINE_S]), "SMILES_CLEAN")
        assert "compounds dropped:" not in capsys.readouterr().out
