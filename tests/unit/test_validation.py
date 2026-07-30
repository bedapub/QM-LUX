# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux.utils.validation."""
import pytest

from qm_lux.utils.validation import validate_crest_best_xyz, validate_crest_out


# ---------------------------------------------------------------------------
# Shared synthetic content
# ---------------------------------------------------------------------------

_VALID_XYZ_CONTENT = """\
3
-10.123456
C  1.000  0.000  0.000
H  2.000  0.000  0.000
H  0.500  0.866  0.000
"""

_VALID_CREST_OUT_HEADER = (
    "       ==============================================\n"
    "       |                                            |\n"
    "       |                 C R E S T                  |\n"
    "       |                                            |\n"
    "       |  Conformer-Rotamer Ensemble Sampling Tool  |\n"
    "       |          based on the GFN methods          |\n"
    "       |             P.Pracht, S.Grimme             |\n"
    "       |          Universitaet Bonn, MCTC           |\n"
    "       ==============================================\n"
)


# ---------------------------------------------------------------------------
# validate_crest_best_xyz
# ---------------------------------------------------------------------------

class TestValidateCrestBestXyz:
    def test_valid_file_returns_true(self, tmp_path):
        f = tmp_path / "crest_best.xyz"
        f.write_text(_VALID_XYZ_CONTENT)
        assert validate_crest_best_xyz(str(f)) is True

    def test_missing_file_returns_false(self, tmp_path):
        assert validate_crest_best_xyz(str(tmp_path / "nonexistent.xyz")) is False

    def test_empty_file_returns_false(self, tmp_path):
        f = tmp_path / "empty.xyz"
        f.write_text("")
        assert validate_crest_best_xyz(str(f)) is False

    def test_only_one_line_returns_false(self, tmp_path):
        """File with a single line (no energy header) must fail."""
        f = tmp_path / "one_line.xyz"
        f.write_text("3\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_bad_atom_count_header_returns_false(self, tmp_path):
        f = tmp_path / "bad.xyz"
        f.write_text("not_an_int\n-10.0\nC 1.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_bad_energy_line_returns_false(self, tmp_path):
        f = tmp_path / "bad.xyz"
        f.write_text("1\nnot_a_float\nC 1.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_too_few_columns_returns_false(self, tmp_path):
        """Coordinate line with only 3 columns (missing Z) must fail."""
        f = tmp_path / "bad.xyz"
        f.write_text("1\n-10.0\nC 1.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_too_many_columns_returns_false(self, tmp_path):
        """Coordinate line with 5 columns must fail."""
        f = tmp_path / "bad.xyz"
        f.write_text("1\n-10.0\nC 1.0 0.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_row_count_mismatch_returns_false(self, tmp_path):
        """Header says 2 rows but only 1 atom line present → False."""
        f = tmp_path / "bad.xyz"
        f.write_text("2\n-10.0\nC 1.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_non_alpha_element_returns_false(self, tmp_path):
        """First column of coordinate line must be alphabetic."""
        f = tmp_path / "bad.xyz"
        f.write_text("1\n-10.0\n123 1.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_non_float_coordinate_returns_false(self, tmp_path):
        """Non-numeric coordinate value must return False."""
        f = tmp_path / "bad.xyz"
        f.write_text("1\n-10.0\nC abc 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is False

    def test_single_atom_valid(self, tmp_path):
        f = tmp_path / "single.xyz"
        f.write_text("1\n-5.0\nH 0.0 0.0 0.0\n")
        assert validate_crest_best_xyz(str(f)) is True


# ---------------------------------------------------------------------------
# validate_crest_out
# ---------------------------------------------------------------------------

class TestValidateCrestOut:
    def test_valid_file_returns_true(self, tmp_path):
        f = tmp_path / "crest.out"
        f.write_text(_VALID_CREST_OUT_HEADER)
        assert validate_crest_out(str(f)) is True

    def test_valid_file_with_leading_blank_lines(self, tmp_path):
        """One or more empty lines before the banner are allowed."""
        f = tmp_path / "crest.out"
        f.write_text("\n\n" + _VALID_CREST_OUT_HEADER)
        assert validate_crest_out(str(f)) is True

    def test_valid_file_with_trailing_content(self, tmp_path):
        """Content after the header must not break validation."""
        f = tmp_path / "crest.out"
        f.write_text(_VALID_CREST_OUT_HEADER + "Some output here.\n")
        assert validate_crest_out(str(f)) is True

    def test_missing_file_returns_false(self, tmp_path):
        assert validate_crest_out(str(tmp_path / "nonexistent.out")) is False

    def test_missing_header_returns_false(self, tmp_path):
        f = tmp_path / "crest.out"
        f.write_text("Some other content\nNo CREST header here.\n")
        assert validate_crest_out(str(f)) is False

    def test_empty_file_returns_false(self, tmp_path):
        f = tmp_path / "crest.out"
        f.write_text("")
        assert validate_crest_out(str(f)) is False

    def test_wrong_program_name_returns_false(self, tmp_path):
        """Replacing 'C R E S T' with something else must fail."""
        bad = _VALID_CREST_OUT_HEADER.replace(
            "       |                 C R E S T                  |\n",
            "       |                  X T B                     |\n",
        )
        f = tmp_path / "crest.out"
        f.write_text(bad)
        assert validate_crest_out(str(f)) is False

    def test_wrong_author_line_returns_false(self, tmp_path):
        bad = _VALID_CREST_OUT_HEADER.replace(
            "       |             P.Pracht, S.Grimme             |\n",
            "       |             A.Smith, B.Jones               |\n",
        )
        f = tmp_path / "crest.out"
        f.write_text(bad)
        assert validate_crest_out(str(f)) is False
