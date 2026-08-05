# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.preparation."""
import pickle

import pandas as pd
import pytest

from qm_lux.preparation import data_preparation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_CSV_CONTENT = "SRN,SMILES\nmol0,c1ccccc1\nmol1,c1ccc2ccccc2c1\n"


def _write_input_csv(tmp_path, content=_SIMPLE_CSV_CONTENT):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(content)
    return csv_path


# ---------------------------------------------------------------------------
# stereo_check = "NO"
# ---------------------------------------------------------------------------

class TestDataPreparationStereoNo:
    """Tests for the stereo_check='NO' path (enumerate all isomers)."""

    def test_returns_dataframe(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert isinstance(result, pd.DataFrame)

    def test_writes_pkl_file(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        data_preparation(str(csv_path), str(out_dir), "NO")
        assert (out_dir / "xtb_input.pkl").exists()

    def test_writes_input_csv(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        data_preparation(str(csv_path), str(out_dir), "NO")
        assert (out_dir / "input.csv").exists()

    def test_pkl_is_loadable(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        data_preparation(str(csv_path), str(out_dir), "NO")
        with open(out_dir / "xtb_input.pkl", "rb") as fh:
            loaded = pickle.load(fh)
        assert isinstance(loaded, pd.DataFrame)

    def test_output_has_srn_column(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert "SRN" in result.columns

    def test_output_has_smiles_clean_column(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert "SMILES_CLEAN" in result.columns

    def test_output_has_morgan_fingerprint_column(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert "fp_Morganclean" in result.columns

    def test_output_has_descriptor_column(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert "descriptors_SMILES_CLEAN" in result.columns

    def test_output_non_empty(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert len(result) > 0

    def test_pkl_matches_returned_dataframe(self, tmp_path):
        """The pickle written to disk must contain the same data as the return value."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        with open(out_dir / "xtb_input.pkl", "rb") as fh:
            loaded = pickle.load(fh)
        assert list(result.columns) == list(loaded.columns)
        assert len(result) == len(loaded)

    def test_single_compound(self, tmp_path):
        csv_path = tmp_path / "single.csv"
        csv_path.write_text("SRN,SMILES\nsol0,c1ccccc1\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = data_preparation(str(csv_path), str(out_dir), "NO")
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# stereo_check = "YES" (with current_df)
# ---------------------------------------------------------------------------

class TestDataPreparationStereoYes:
    """Tests for the stereo_check='YES' path (use existing stereo, filter >1 centre)."""

    def _make_current_pkl(self, tmp_path, srns):
        """Write a pickle pretending some compounds are already processed."""
        df = pd.DataFrame({"SRN": srns, "SMILES_CLEAN": ["c1ccccc1"] * len(srns)})
        pkl_path = tmp_path / "current.pkl"
        with open(pkl_path, "wb") as fh:
            pickle.dump(df, fh)
        return str(pkl_path)

    def test_returns_dataframe(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, [])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        assert isinstance(result, pd.DataFrame)

    def test_already_processed_srns_excluded(self, tmp_path):
        """Compounds listed in current_df must be excluded from the output."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        # 'mol0' is already in the existing pickle → only mol1 processed
        current_pkl = self._make_current_pkl(tmp_path, ["mol0"])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        srn_bases = result["SRN"].str.split("_").str[0]
        assert "mol0" not in srn_bases.values

    def test_suffixed_srns_in_current_df_are_excluded(self, tmp_path):
        """A real prior run's pickle carries isomer-suffixed SRNs, and those must
        still exclude the matching raw SRN from the new input.

        Both code paths that write a pickle append a suffix — ``"_0"`` on the
        stereo_check='YES' path and ``"_0".."_n"`` from chirality_generator_all
        on the 'NO' path — so ``"mol0_0"``, not ``"mol0"``, is what a genuine
        current_df contains.  Comparing the raw input SRN against the suffixed
        one matched nothing and turned the exclusion into a silent no-op.
        """
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, ["mol0_0"])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        srn_bases = result["SRN"].str.split("_").str[0]
        assert "mol0" not in srn_bases.values
        assert "mol1" in srn_bases.values

    def test_multi_isomer_suffixes_are_excluded(self, tmp_path):
        """Suffixes beyond ``_0`` (multi-isomer compounds) must also match."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, ["mol0_0", "mol0_1", "mol0_2"])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        srn_bases = result["SRN"].str.split("_").str[0]
        assert "mol0" not in srn_bases.values

    def test_unrelated_srns_are_not_excluded(self, tmp_path):
        """Stripping the suffix must not over-match and drop unrelated compounds."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, ["other_0"])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        srn_bases = set(result["SRN"].str.split("_").str[0])
        assert {"mol0", "mol1"} <= srn_bases

    def test_srn_gets_zero_suffix(self, tmp_path):
        """Compounds processed via stereo_check='YES' get a '_0' SRN suffix."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, [])
        result = data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        assert result["SRN"].str.endswith("_0").all()

    def test_writes_pkl(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        current_pkl = self._make_current_pkl(tmp_path, [])
        data_preparation(str(csv_path), str(out_dir), "YES", current_pkl)
        assert (out_dir / "xtb_input.pkl").exists()


# ---------------------------------------------------------------------------
# Rejected inputs
# ---------------------------------------------------------------------------

class TestDataPreparationBadInput:
    """Every unsupported combination must raise a ValueError that names it.

    These used to fall through to a bare ``print("Error in the inputs")`` and
    then die on ``UnboundLocalError: ... 'data_chir'`` two lines later, with the
    diagnostic on stdout and the traceback on stderr.
    """

    def test_yes_without_current_df_raises(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with pytest.raises(ValueError, match="requires current_df"):
            data_preparation(str(csv_path), str(out_dir), "YES")

    def test_yes_with_empty_current_df_raises(self, tmp_path):
        """An empty string is as unusable as None, and reaches the same check."""
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with pytest.raises(ValueError, match="requires current_df"):
            data_preparation(str(csv_path), str(out_dir), "YES", "")

    @pytest.mark.parametrize("stereo_check", ["yes", "Yes", "no", "bogus", "", None])
    def test_unsupported_stereo_check_raises(self, tmp_path, stereo_check):
        """Only the exact strings 'YES' and 'NO' are accepted; callers that may
        pass other spellings normalise first (see cli.py and workflow/Snakefile).
        """
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with pytest.raises(ValueError, match="must be 'YES' or 'NO'"):
            data_preparation(str(csv_path), str(out_dir), stereo_check)

    def test_error_names_the_offending_value(self, tmp_path):
        csv_path = _write_input_csv(tmp_path)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with pytest.raises(ValueError, match="bogus"):
            data_preparation(str(csv_path), str(out_dir), "bogus")
