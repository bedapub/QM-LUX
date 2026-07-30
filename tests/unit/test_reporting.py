# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.reporting.

get_mol_ML_results is deeply file-system-driven (PKL, CSVs, image directories,
an input.csv, and an HTML output).  Tests construct a minimal valid directory
tree in tmp_path and mock only create_molecule_images to avoid RDKit drawing.

SRN format used throughout: "<BASE>_<DIAST>" (e.g. "MOL001_0"), which matches
the real workflow convention.  The function splits on "_" to recover the base
SRN for the failed-molecule comparison against input.csv.
"""
import pickle
from unittest.mock import patch

import pandas as pd
import pytest

from qm_lux.reporting import get_mol_ML_results


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

# Minimal valid PNG header bytes (not a real image, but enough for base64 encoding)
_TINY_PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def report_dir(tmp_path):
    """Build the full directory structure expected by get_mol_ML_results.

    Layout:
      <tmp>/test_set_with_fP_rdkit_prop_UVvis.pkl  — 2-compound test set
      <tmp>/ML_results/results_ML_RF.csv            — RF predictions
      <tmp>/UV_plots/MOL001_0.png                   — UV-vis image for mol 0
      <tmp>/molecule_images/MOL001_0.png             — structure image for mol 0
      <tmp>/molecule_images/MOL002_0.png             — structure image for mol 1
      <tmp>/input.csv                               — original input (base SRNs)
    """
    # Test-set pickle: SRN in "<BASE>_<DIAST>" format, integer index 0, 1
    df_pkl = pd.DataFrame(
        {
            "SRN": ["MOL001_0", "MOL002_0"],
            "SMILES_CLEAN": ["c1ccccc1", "c1ccc2ccccc2c1"],
        },
        index=[0, 1],
    )
    with open(tmp_path / "test_set_with_fP_rdkit_prop_UVvis.pkl", "wb") as fh:
        pickle.dump(df_pkl, fh)

    # ML results: index 0, 1 must match the pkl index for the merge
    ml_dir = tmp_path / "ML_results"
    ml_dir.mkdir()
    df_ml = pd.DataFrame(
        {
            "pred": [0.0, 1.0],
            "prob": [0.2, 0.8],
            "Descriptors": ["fp_morgan", "fp_morgan"],
            "ML_Method": ["RF", "RF"],
        },
        index=[0, 1],
    )
    df_ml.to_csv(ml_dir / "results_ML_RF.csv")

    # UV plots directory with one sample image
    uv_dir = tmp_path / "UV_plots"
    uv_dir.mkdir()
    (uv_dir / "MOL001_0.png").write_bytes(_TINY_PNG)

    # Molecule images (normally created by create_molecule_images, which we mock)
    mol_dir = tmp_path / "molecule_images"
    mol_dir.mkdir()
    (mol_dir / "MOL001_0.png").write_bytes(_TINY_PNG)
    (mol_dir / "MOL002_0.png").write_bytes(_TINY_PNG)

    # Input CSV: base SRNs (no "_DIAST" suffix)
    df_input = pd.DataFrame(
        {"SRN": ["MOL001", "MOL002"], "SMILES": ["c1ccccc1", "c1ccc2ccccc2c1"]}
    )
    df_input.to_csv(tmp_path / "input.csv", index=False)

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetMolMLResults:
    def _run(self, report_dir):
        """Run get_mol_ML_results with create_molecule_images mocked out."""
        with patch("qm_lux.reporting.create_molecule_images"):
            get_mol_ML_results(str(report_dir))

    # -------------------------------------------------- output files created

    def test_html_file_created(self, report_dir):
        self._run(report_dir)
        assert (report_dir / "results_ML_with_mol_UV.html").exists()

    def test_failed_molecules_file_created(self, report_dir):
        self._run(report_dir)
        assert (report_dir / "Failed_molecules.txt").exists()

    # -------------------------------------------------- HTML content

    def test_html_contains_phototoxicity_title(self, report_dir):
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        assert "Phototoxicity" in html

    def test_html_contains_table_structure(self, report_dir):
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        assert "<table" in html
        assert "</table>" in html

    def test_html_contains_srn_values(self, report_dir):
        """Both compound SRNs must appear somewhere in the HTML."""
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        # At least one SRN should be in the output
        assert "MOL001_0" in html or "MOL002_0" in html

    def test_html_contains_prediction_column_header(self, report_dir):
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        assert "Prediction" in html

    def test_html_contains_probability_column_header(self, report_dir):
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        assert "Probability" in html

    def test_html_contains_uv_image_for_mol1(self, report_dir):
        """MOL001_0 has a UV image; HTML must embed it as base64."""
        self._run(report_dir)
        html = (report_dir / "results_ML_with_mol_UV.html").read_text()
        assert 'data:image/png;base64,' in html

    # -------------------------------------------------- failed molecules logic

    def test_no_failed_molecules_when_all_have_results(self, report_dir):
        """With matching SRNs in pkl and input.csv, Failed_molecules.txt is empty."""
        self._run(report_dir)
        content = (report_dir / "Failed_molecules.txt").read_text().strip()
        assert content == ""

    def test_failed_molecule_written_when_missing_from_results(self, tmp_path):
        """A compound in input.csv but absent from the ML results ends up in Failed_molecules.txt."""
        # PKL has only MOL001_0; input.csv has MOL001 and MOL003
        df_pkl = pd.DataFrame(
            {"SRN": ["MOL001_0"], "SMILES_CLEAN": ["c1ccccc1"]}, index=[0]
        )
        with open(tmp_path / "test_set_with_fP_rdkit_prop_UVvis.pkl", "wb") as fh:
            pickle.dump(df_pkl, fh)

        ml_dir = tmp_path / "ML_results"
        ml_dir.mkdir()
        df_ml = pd.DataFrame(
            {"pred": [0.0], "prob": [0.2], "Descriptors": ["fp"], "ML_Method": ["RF"]},
            index=[0],
        )
        df_ml.to_csv(ml_dir / "results_ML_RF.csv")

        (tmp_path / "UV_plots").mkdir()
        mol_dir = tmp_path / "molecule_images"
        mol_dir.mkdir()
        (mol_dir / "MOL001_0.png").write_bytes(_TINY_PNG)

        # Input CSV has an extra compound (MOL003) that has no results
        df_input = pd.DataFrame({"SRN": ["MOL001", "MOL003"], "SMILES": ["c1ccccc1", "C"]})
        df_input.to_csv(tmp_path / "input.csv", index=False)

        with patch("qm_lux.reporting.create_molecule_images"):
            get_mol_ML_results(str(tmp_path))

        content = (tmp_path / "Failed_molecules.txt").read_text()
        assert "MOL003" in content

    # -------------------------------------------------- create_molecule_images called

    def test_create_molecule_images_called(self, report_dir):
        """get_mol_ML_results must delegate image creation to create_molecule_images."""
        with patch("qm_lux.reporting.create_molecule_images") as mock_cmi:
            get_mol_ML_results(str(report_dir))
        mock_cmi.assert_called_once()
