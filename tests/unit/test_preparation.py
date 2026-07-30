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
