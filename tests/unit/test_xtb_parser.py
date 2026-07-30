# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.utils.xtb_parser (get_QM)."""

import os
import pickle

import pandas as pd
import pytest

from qm_lux.utils.xtb_parser import get_QM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Exact spacing must match the startswith checks in get_QM — do NOT use
# textwrap.dedent here as it strips leading spaces based on the minimum
# indented line (" * finished run on" has only 1 space).
_XTB_OUT = (
    "          | TOTAL ENERGY              -4.174075866738 Eh   |\n"
    "          | HOMO-LUMO GAP              9.631384157988 eV   |\n"
    "             Fermi-level            -8.1743 Eh\n"
    " * finished run on 2026/07/29 at 12:00:00\n"
)

_SDF_HEADER = "CPD-001_0\n\n\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n"


def _build_xtb_dir(tmp_path, srn="CPD-001", conf_idx=0):
    """Write a minimal XTB result directory structure."""
    data_ml = tmp_path / "data_ml"
    base_0 = data_ml / "0"
    mol_dir = base_0 / str(conf_idx)
    mol_dir.mkdir(parents=True)

    # SDF file (first line encodes SRN)
    (mol_dir / f"{conf_idx}.sdf").write_text(f"{srn}_0\n\n\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n")

    # XTB .out file
    (mol_dir / f"{conf_idx}.out").write_text(_XTB_OUT)

    # crest_best.xyz (empty but present)
    (mol_dir / "crest_best.xyz").write_text("1\ntest\nC  0.0 0.0 0.0\n")

    # xtb_input.pkl
    df_srn = pd.DataFrame({"SRN": [srn]})
    with open(data_ml / "xtb_input.pkl", "wb") as f:
        pickle.dump(df_srn, f)

    return str(data_ml)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetQM:
    def test_returns_dataframe(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM(base_dir, srn_mode="no_SRN")
        assert isinstance(result, pd.DataFrame)

    def test_expected_columns(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM(base_dir, srn_mode="no_SRN")
        for col in ("SRN", "ENERGY (Eh)", "HOMO-LUMO GAP (eV)", "Fermi-Level (eV)",
                    "Expected lambda Absmax (nm)"):
            assert col in result.columns

    def test_energy_parsed_correctly(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM(base_dir, srn_mode="no_SRN")
        assert result["ENERGY (Eh)"].iloc[0] == pytest.approx(-4.174075866738)

    def test_homo_lumo_parsed_correctly(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM(base_dir, srn_mode="no_SRN")
        assert result["HOMO-LUMO GAP (eV)"].iloc[0] == pytest.approx(9.631384157988)

    def test_lambda_absmax_computed(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM(base_dir, srn_mode="no_SRN")
        # E = hc/lambda => lambda = hc/E; value must be a positive float in nm
        assert result["Expected lambda Absmax (nm)"].iloc[0] > 0

    def test_writes_csv(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        get_QM(base_dir, srn_mode="no_SRN")
        assert os.path.exists(os.path.join(base_dir, "dataframe_all_res_QM_xtb.csv"))

    def test_copies_crest_xyz(self, tmp_path):
        base_dir = _build_xtb_dir(tmp_path)
        get_QM(base_dir, srn_mode="no_SRN")
        minimized = os.path.join(base_dir, "Minimized_mol")
        assert os.path.isdir(minimized)
        assert any(f.endswith("_crest_best.xyz") for f in os.listdir(minimized))

    def test_importable_from_utils_io(self, tmp_path):
        from qm_lux.utils.io import get_QM as get_QM_io
        base_dir = _build_xtb_dir(tmp_path)
        result = get_QM_io(base_dir, srn_mode="no_SRN")
        assert isinstance(result, pd.DataFrame)
