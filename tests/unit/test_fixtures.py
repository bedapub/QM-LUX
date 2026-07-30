# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests that verify the shared fixtures are well-formed."""
import numpy as np
import pandas as pd


def test_sample_smiles_length(sample_smiles):
    assert len(sample_smiles) >= 4


def test_uvvis_df_columns(uvvis_df):
    assert set(["lambda (nm)", "Epsilon (mL/cm/mol)", "SRN"]).issubset(uvvis_df.columns)


def test_uvvis_df_wavelength_range(uvvis_df):
    lam = pd.to_numeric(uvvis_df["lambda (nm)"])
    assert lam.min() <= 100.0
    assert lam.max() >= 1000.0


def test_uvvis_df_single_molecule(uvvis_df):
    assert uvvis_df["SRN"].nunique() == 1


def test_uvvis_xy_dir_structure(uvvis_xy_dir):
    xy_files = list((uvvis_xy_dir / "0").rglob("*_uvvis.xy"))
    assert len(xy_files) == 1
    lines = xy_files[0].read_text().splitlines()
    assert lines[0].startswith("#")
    assert len(lines) > 10


def test_gaussian_log_path(gaussian_log_path):
    log_dir, log_name = gaussian_log_path
    log_file = log_dir / log_name
    assert log_file.exists()
    content = log_file.read_text()
    assert "Excited State" in content
    assert content.count("Excited State") == 3
