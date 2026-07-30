# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for unit tests."""
import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Molecules
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_smiles():
    """Four simple public molecules covering diverse chemistry."""
    return [
        "c1ccccc1",                    # benzene
        "c1ccc2ccccc2c1",              # naphthalene
        "CC(=O)Oc1ccccc1C(=O)O",      # aspirin
        "Fc1ccc(F)cc1",                # 1,4-difluorobenzene
    ]


# ---------------------------------------------------------------------------
# UV-vis spectrum fixtures
# ---------------------------------------------------------------------------

def _make_uvvis_df(srn="test_mol_uvvis"):
    """Synthetic UV-vis spectrum: Gaussian absorption peak at 300 nm."""
    wavelengths = np.linspace(100.0, 1000.0, 901)
    intensities = 50000.0 * np.exp(-((wavelengths - 300.0) ** 2) / (2 * 20.0 ** 2))
    return pd.DataFrame({
        "lambda (nm)": wavelengths.astype(str),
        "Epsilon (mL/cm/mol)": intensities.astype(str),
        "SRN": srn,
    })


@pytest.fixture
def uvvis_df():
    """DataFrame in the format produced by extract_UV_gaussian_output.

    Single synthetic molecule with a Gaussian absorption peak at 300 nm,
    wavelength range 100–1000 nm (901 points, 1 nm steps).
    """
    return _make_uvvis_df()


@pytest.fixture
def uvvis_xy_dir(tmp_path):
    """Temp directory tree with a synthetic _uvvis.xy file.

    Directory layout mirrors what extract_UV_gaussian_output expects:
      <base_dir>/0/<subdir>/<srn>_uvvis.xy
    """
    subdir = tmp_path / "0" / "mol0"
    subdir.mkdir(parents=True)
    xy_file = subdir / "mol0_uvvis.xy"

    wavelengths = np.linspace(100.0, 1000.0, 901)
    intensities = 50000.0 * np.exp(-((wavelengths - 300.0) ** 2) / (2 * 20.0 ** 2))

    lines = ["#lambda Intensity\n"]
    for w, e in zip(wavelengths, intensities):
        lines.append(f"{w:.18e} {e:.18e}\n")
    xy_file.write_text("".join(lines))

    return tmp_path


# ---------------------------------------------------------------------------
# Gaussian log fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def gaussian_log_path(tmp_path):
    """Temp directory with a minimal synthetic Gaussian log file.

    Contains three excited-state lines in the format parse_output() expects:
      Excited State   N:      Singlet-A  <eV> eV  <nm> nm  f=<osc>
    """
    log_dir = tmp_path / "gauss_out"
    log_dir.mkdir()
    log_file = log_dir / "mol.log"

    content = (
        " Entering Gaussian System\n"
        " Excitation energies and oscillator strengths:\n"
        "\n"
        " Excited State   1:      Singlet-A      4.4762 eV  276.99 nm  f=0.0557  <S**2>=0.000\n"
        " Excited State   2:      Singlet-A      4.6148 eV  268.67 nm  f=0.4482  <S**2>=0.000\n"
        " Excited State   3:      Singlet-A      4.8791 eV  254.11 nm  f=0.0070  <S**2>=0.000\n"
        " Normal termination of Gaussian 16.\n"
    )
    log_file.write_text(content)

    return log_dir, "mol.log"
