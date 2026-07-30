# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.utils.plotting."""
# Set non-interactive backend before any matplotlib/pyplot import.
import matplotlib
matplotlib.use("Agg")

import pickle
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from qm_lux.utils.plotting import create_molecule_images, plot_UV


# ---------------------------------------------------------------------------
# Helpers / fixtures for plot_UV
# ---------------------------------------------------------------------------

def _make_xtb_pkl(tmp_path, srns=("MOL001", "MOL002")):
    """Write an xtb_input.pkl with a DataFrame indexed 0, 1, … and a SRN column."""
    df = pd.DataFrame({"SRN": list(srns)})
    pkl_path = tmp_path / "xtb_input.pkl"
    with open(pkl_path, "wb") as fh:
        pickle.dump(df, fh)
    return pkl_path


def _make_uv_df(n_wavelengths=5, srns=("MOL001", "MOL002")):
    """Build a minimal df_uv with SRN in the format '<index>_uvvis'.

    plot_UV splits SRN on '_' to get INDEX_MERGE (integer index into df_srn).
    """
    wavelengths = [300.0, 350.0, 400.0, 450.0, 500.0][:n_wavelengths]
    intensities = [1000.0, 3000.0, 5000.0, 3000.0, 1000.0][:n_wavelengths]
    rows = []
    for i, srn in enumerate(srns):
        for w, e in zip(wavelengths, intensities):
            rows.append({"SRN": f"{i}_uvvis", "lambda (nm)": w, "Epsilon (mL/cm/mol)": e})
    return pd.DataFrame(rows)


@pytest.fixture
def plot_uv_dir(tmp_path):
    """Directory with xtb_input.pkl ready for plot_UV."""
    _make_xtb_pkl(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# plot_UV
# ---------------------------------------------------------------------------

class TestPlotUV:
    def test_creates_uv_plots_directory(self, plot_uv_dir):
        df_uv = _make_uv_df()
        with patch("matplotlib.pyplot.show"):
            plot_UV(str(plot_uv_dir), df_uv)
        assert (plot_uv_dir / "UV_plots").exists()

    def test_creates_one_png_per_compound(self, plot_uv_dir):
        df_uv = _make_uv_df()
        with patch("matplotlib.pyplot.show"):
            plot_UV(str(plot_uv_dir), df_uv)
        pngs = list((plot_uv_dir / "UV_plots").glob("*.png"))
        assert len(pngs) == 2

    def test_png_names_match_srns(self, plot_uv_dir):
        df_uv = _make_uv_df()
        with patch("matplotlib.pyplot.show"):
            plot_UV(str(plot_uv_dir), df_uv)
        names = {f.stem for f in (plot_uv_dir / "UV_plots").glob("*.png")}
        assert "MOL001" in names
        assert "MOL002" in names

    def test_single_compound(self, tmp_path):
        _make_xtb_pkl(tmp_path, srns=("ONLY",))
        df_uv = _make_uv_df(srns=("ONLY",))
        with patch("matplotlib.pyplot.show"):
            plot_UV(str(tmp_path), df_uv)
        pngs = list((tmp_path / "UV_plots").glob("*.png"))
        assert len(pngs) == 1
        assert pngs[0].stem == "ONLY"

    def test_preexisting_uv_plots_dir_not_raised(self, plot_uv_dir):
        """plot_UV must not crash if UV_plots already exists."""
        (plot_uv_dir / "UV_plots").mkdir()
        df_uv = _make_uv_df()
        with patch("matplotlib.pyplot.show"):
            plot_UV(str(plot_uv_dir), df_uv)
        # Just verify completion without error


# ---------------------------------------------------------------------------
# Helpers / fixtures for create_molecule_images
# ---------------------------------------------------------------------------

@pytest.fixture
def mol_images_dir(tmp_path):
    """Directory with the required test-set pickle for create_molecule_images."""
    df = pd.DataFrame({
        "SRN": ["MOL001", "MOL002"],
        "SMILES_CLEAN": ["c1ccccc1", "c1ccc2ccccc2c1"],
    })
    df.to_pickle(str(tmp_path / "test_set_with_fP_rdkit_prop_UVvis.pkl"))
    return tmp_path


# ---------------------------------------------------------------------------
# create_molecule_images
# ---------------------------------------------------------------------------

class TestCreateMoleculeImages:
    def test_creates_output_directory(self, mol_images_dir):
        create_molecule_images(str(mol_images_dir))
        assert (mol_images_dir / "molecule_images").exists()

    def test_creates_one_png_per_compound(self, mol_images_dir):
        create_molecule_images(str(mol_images_dir))
        pngs = list((mol_images_dir / "molecule_images").glob("*.png"))
        assert len(pngs) == 2

    def test_png_names_match_srns(self, mol_images_dir):
        create_molecule_images(str(mol_images_dir))
        names = {f.stem for f in (mol_images_dir / "molecule_images").glob("*.png")}
        assert "MOL001" in names
        assert "MOL002" in names

    def test_custom_output_dir_name(self, mol_images_dir):
        create_molecule_images(str(mol_images_dir), output_dir="my_structures")
        assert (mol_images_dir / "my_structures").exists()
        pngs = list((mol_images_dir / "my_structures").glob("*.png"))
        assert len(pngs) == 2

    def test_missing_pickle_does_not_raise(self, tmp_path):
        """No pkl file present → function exits early without raising."""
        create_molecule_images(str(tmp_path))
        # No output directory created because the function returned early
        assert not (tmp_path / "molecule_images").exists()

    def test_single_compound(self, tmp_path):
        df = pd.DataFrame({"SRN": ["SOLO"], "SMILES_CLEAN": ["C"]})
        df.to_pickle(str(tmp_path / "test_set_with_fP_rdkit_prop_UVvis.pkl"))
        create_molecule_images(str(tmp_path))
        pngs = list((tmp_path / "molecule_images").glob("*.png"))
        assert len(pngs) == 1
        assert pngs[0].stem == "SOLO"

    def test_invalid_smiles_skipped_gracefully(self, tmp_path):
        """An invalid SMILES must not raise; valid ones still produce PNGs."""
        df = pd.DataFrame({
            "SRN": ["GOOD", "BAD"],
            "SMILES_CLEAN": ["c1ccccc1", "not_a_valid_smiles!!!"],
        })
        df.to_pickle(str(tmp_path / "test_set_with_fP_rdkit_prop_UVvis.pkl"))
        create_molecule_images(str(tmp_path))
        # The good molecule should still be written; the bad one is skipped.
        pngs = {f.stem for f in (tmp_path / "molecule_images").glob("*.png")}
        assert "GOOD" in pngs
