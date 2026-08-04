# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux/utils/gaussian.py."""
import numpy as np
import pandas as pd
import pytest

from ase import Atoms

from qm_lux.utils.gaussian import (
    create_input_with_charge,
    extract_UV_gaussian_output,
    get_UV_vis_from_gaussian_output,
    parse_output,
    sum_gauss,
)


# ---------------------------------------------------------------------------
# extract_UV_gaussian_output
# ---------------------------------------------------------------------------

class TestExtractUVGaussianOutput:
    def test_returns_dataframe(self, uvvis_xy_dir):
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert isinstance(result, pd.DataFrame)

    def test_correct_columns(self, uvvis_xy_dir):
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert set(["lambda (nm)", "Epsilon (mL/cm/mol)", "SRN"]).issubset(result.columns)

    def test_header_line_filtered(self, uvvis_xy_dir):
        """Lines starting with '#' must be removed."""
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert not result["lambda (nm)"].str.startswith("#").any()

    def test_row_count(self, uvvis_xy_dir):
        """File with 901 data points (1 header + 901 values) → 901 rows after filter."""
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert len(result) == 901

    def test_srn_from_filename(self, uvvis_xy_dir):
        """SRN is the filename without the .xy extension."""
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert result["SRN"].iloc[0] == "mol0_uvvis"

    def test_wavelength_values_convertible_to_float(self, uvvis_xy_dir):
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        lam = pd.to_numeric(result["lambda (nm)"], errors="coerce")
        assert lam.notna().all()

    def test_epsilon_values_convertible_to_float(self, uvvis_xy_dir):
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        eps = pd.to_numeric(result["Epsilon (mL/cm/mol)"], errors="coerce")
        assert eps.notna().all()

    def test_wavelength_range(self, uvvis_xy_dir):
        result = extract_UV_gaussian_output(str(uvvis_xy_dir))
        lam = pd.to_numeric(result["lambda (nm)"])
        assert lam.min() == pytest.approx(100.0, rel=1e-3)
        assert lam.max() == pytest.approx(1000.0, rel=1e-3)

    def test_csv_written_to_base_dir(self, uvvis_xy_dir):
        """extract_UV_gaussian_output writes UVvis.csv alongside the 0/ dir."""
        extract_UV_gaussian_output(str(uvvis_xy_dir))
        assert (uvvis_xy_dir / "UVvis.csv").exists()

    def test_multiple_xy_files(self, tmp_path):
        """Two .xy files in different subdirs → two distinct SRN groups."""
        for mol_id in ("mol_a", "mol_b"):
            subdir = tmp_path / "0" / mol_id
            subdir.mkdir(parents=True)
            wavelengths = np.linspace(100.0, 1000.0, 901)
            intensities = np.ones(901) * 1000.0
            lines = ["#lambda Intensity\n"]
            for w, e in zip(wavelengths, intensities):
                lines.append(f"{w:.4f} {e:.4f}\n")
            (subdir / f"{mol_id}_uvvis.xy").write_text("".join(lines))

        result = extract_UV_gaussian_output(str(tmp_path))
        assert result["SRN"].nunique() == 2


# ---------------------------------------------------------------------------
# parse_output
# ---------------------------------------------------------------------------

class TestParseOutput:
    def test_returns_two_lists(self, gaussian_log_path):
        log_dir, log_name = gaussian_log_path
        lambdas, fvalues = parse_output(str(log_dir), log_name)
        assert isinstance(lambdas, list)
        assert isinstance(fvalues, list)

    def test_correct_number_of_states(self, gaussian_log_path):
        log_dir, log_name = gaussian_log_path
        lambdas, fvalues = parse_output(str(log_dir), log_name)
        assert len(lambdas) == 3
        assert len(fvalues) == 3

    def test_correct_wavelengths(self, gaussian_log_path):
        """Fixture has three excited states at 276.99, 268.67, 254.11 nm."""
        log_dir, log_name = gaussian_log_path
        lambdas, _ = parse_output(str(log_dir), log_name)
        assert lambdas == pytest.approx([276.99, 268.67, 254.11])

    def test_correct_oscillator_strengths(self, gaussian_log_path):
        """Fixture has f=0.0557, 0.4482, 0.0070."""
        log_dir, log_name = gaussian_log_path
        _, fvalues = parse_output(str(log_dir), log_name)
        assert fvalues == pytest.approx([0.0557, 0.4482, 0.0070])

    def test_returns_zero_zero_for_no_excited_states(self, tmp_path):
        """File with no excited-state lines → (0, 0)."""
        log_file = tmp_path / "empty.log"
        log_file.write_text(" Entering Gaussian System\n Normal termination.\n")
        result = parse_output(str(tmp_path), "empty.log")
        assert result == (0, 0)

    def test_wavelengths_are_floats(self, gaussian_log_path):
        log_dir, log_name = gaussian_log_path
        lambdas, _ = parse_output(str(log_dir), log_name)
        assert all(isinstance(v, float) for v in lambdas)

    def test_fvalues_are_floats(self, gaussian_log_path):
        log_dir, log_name = gaussian_log_path
        _, fvalues = parse_output(str(log_dir), log_name)
        assert all(isinstance(v, float) for v in fvalues)


# ---------------------------------------------------------------------------
# sum_gauss
# ---------------------------------------------------------------------------

class TestSumGauss:
    def test_returns_numpy_array(self):
        lam_range = np.linspace(200, 400, 201)
        result = sum_gauss(lam_range, 300.0, 0.5)
        assert isinstance(result, np.ndarray)

    def test_output_length_matches_input(self):
        lam_range = np.linspace(200, 400, 201)
        result = sum_gauss(lam_range, 300.0, 0.5)
        assert len(result) == len(lam_range)

    def test_peak_at_lambda_i(self):
        """Maximum of the broadened spectrum must be at the excitation wavelength."""
        lam_range = np.linspace(200, 400, 2001)
        lambda_i = 300.0
        result = sum_gauss(lam_range, lambda_i, 0.5)
        peak_lam = lam_range[np.argmax(result)]
        assert peak_lam == pytest.approx(lambda_i, abs=0.5)

    def test_positive_for_positive_f(self):
        """Positive oscillator strength → all positive values."""
        lam_range = np.linspace(200, 400, 201)
        result = sum_gauss(lam_range, 300.0, 0.5)
        assert np.all(result > 0)

    def test_scales_linearly_with_f_i(self):
        """Doubling f_i must double every point in the output."""
        lam_range = np.linspace(200, 400, 201)
        r1 = sum_gauss(lam_range, 300.0, 0.5)
        r2 = sum_gauss(lam_range, 300.0, 1.0)
        assert np.allclose(r2, 2 * r1)

    def test_decays_away_from_peak(self):
        """Value far from lambda_i should be much smaller than at the peak.

        sum_gauss uses a Gaussian in wavenumber (1/lambda) space with
        sigma = 1/3099.6 nm⁻¹ (~0.4 eV). At 500 nm the separation from
        a 300 nm peak is |1/500 - 1/300| ≈ 4.1 sigma → exp(-17) ≈ 4e-8,
        so the peak value is many orders of magnitude larger.
        """
        lam_range = np.array([200.0, 300.0, 500.0])
        result = sum_gauss(lam_range, 300.0, 1.0)
        assert result[1] > result[0] * 1e6   # 200 nm is ~8 sigma away
        assert result[1] > result[2] * 1e6   # 500 nm is ~4 sigma away


# ---------------------------------------------------------------------------
# get_UV_vis_from_gaussian_output
# ---------------------------------------------------------------------------

_GAUSSIAN_LOG_CONTENT = (
    " Entering Gaussian System\n"
    " Excitation energies and oscillator strengths:\n"
    "\n"
    " Excited State   1:      Singlet-A      4.4762 eV  276.99 nm  f=0.0557  <S**2>=0.000\n"
    " Excited State   2:      Singlet-A      4.6148 eV  268.67 nm  f=0.4482  <S**2>=0.000\n"
    " Excited State   3:      Singlet-A      4.8791 eV  254.11 nm  f=0.0070  <S**2>=0.000\n"
    " Normal termination of Gaussian 16.\n"
)


class TestGetUVVisFromGaussianOutput:
    @pytest.fixture
    def gaussian_log_dir(self, tmp_path):
        """Directory tree expected by get_UV_vis_from_gaussian_output.

        Layout: <base_dir>/0/mol1/log.out
        """
        mol_dir = tmp_path / "0" / "mol1"
        mol_dir.mkdir(parents=True)
        (mol_dir / "log.out").write_text(_GAUSSIAN_LOG_CONTENT)
        return tmp_path

    def test_xy_file_created(self, gaussian_log_dir):
        get_UV_vis_from_gaussian_output(str(gaussian_log_dir))
        assert (gaussian_log_dir / "0" / "mol1" / "mol1_uvvis.xy").exists()

    def test_xy_has_header_line(self, gaussian_log_dir):
        get_UV_vis_from_gaussian_output(str(gaussian_log_dir))
        first_line = (gaussian_log_dir / "0" / "mol1" / "mol1_uvvis.xy").read_text().splitlines()[0]
        assert first_line.startswith("#")

    def test_xy_has_900_data_rows(self, gaussian_log_dir):
        get_UV_vis_from_gaussian_output(str(gaussian_log_dir))
        xy_path = gaussian_log_dir / "0" / "mol1" / "mol1_uvvis.xy"
        data_lines = [
            l for l in xy_path.read_text().splitlines()
            if l.strip() and not l.startswith("#")
        ]
        assert len(data_lines) == 900

    def test_xy_wavelength_range(self, gaussian_log_dir):
        get_UV_vis_from_gaussian_output(str(gaussian_log_dir))
        xy_path = gaussian_log_dir / "0" / "mol1" / "mol1_uvvis.xy"
        data = np.loadtxt(xy_path, comments="#")
        assert data[0, 0] == pytest.approx(100.0, rel=1e-3)
        assert data[-1, 0] == pytest.approx(1000.0, rel=1e-3)

    def test_xy_intensities_non_negative(self, gaussian_log_dir):
        get_UV_vis_from_gaussian_output(str(gaussian_log_dir))
        xy_path = gaussian_log_dir / "0" / "mol1" / "mol1_uvvis.xy"
        data = np.loadtxt(xy_path, comments="#")
        assert np.all(data[:, 1] >= 0)

    def test_no_excited_states_does_not_crash(self, tmp_path):
        """A log with no excited-state lines must not raise; no .xy file is written."""
        mol_dir = tmp_path / "0" / "mol_empty"
        mol_dir.mkdir(parents=True)
        (mol_dir / "log.out").write_text(
            " Entering Gaussian System\n Normal termination.\n"
        )
        get_UV_vis_from_gaussian_output(str(tmp_path))
        assert not (mol_dir / "mol_empty_uvvis.xy").exists()


# ---------------------------------------------------------------------------
# create_input_with_charge
# ---------------------------------------------------------------------------

class TestCreateInputWithCharge:
    """The %mem / %nprocshared header lines decide what Gaussian actually uses —
    they override GAUSS_MDEF/GAUSS_PDEF and the g16 -m=/-p= flags — so they must
    follow the values the workflow passes in, not a hardcoded constant."""

    @pytest.fixture
    def molecule(self):
        return Atoms("H2", positions=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)])

    def _write(self, molecule, tmp_path, **kwargs):
        create_input_with_charge(molecule, "mol1", 0, str(tmp_path), **kwargs)
        return (tmp_path / "mol1_input.gjf").read_text()

    def test_file_written_with_expected_name(self, molecule, tmp_path):
        create_input_with_charge(molecule, "mol1", 0, str(tmp_path))
        assert (tmp_path / "mol1_input.gjf").exists()

    def test_default_resources_unchanged(self, molecule, tmp_path):
        """Defaults must reproduce the values that used to be hardcoded."""
        text = self._write(molecule, tmp_path)
        assert "%mem=20GB" in text
        assert "%nprocshared=24" in text

    def test_mem_gb_honoured(self, molecule, tmp_path):
        text = self._write(molecule, tmp_path, mem_gb=50)
        assert "%mem=50GB" in text
        assert "%mem=20GB" not in text

    def test_n_processes_honoured(self, molecule, tmp_path):
        text = self._write(molecule, tmp_path, n_processes=4)
        assert "%nprocshared=4" in text
        assert "%nprocshared=24" not in text

    def test_both_honoured_together(self, molecule, tmp_path):
        text = self._write(molecule, tmp_path, mem_gb=8, n_processes=2)
        assert "%mem=8GB" in text
        assert "%nprocshared=2" in text

    def test_theory_level_not_parameterised(self, molecule, tmp_path):
        """Only the resource lines are configurable; the method must not move."""
        text = self._write(molecule, tmp_path, mem_gb=8, n_processes=2)
        assert "td=(singlets,nstates=30)" in text
        assert "b3lyp/gen scrf=(solvent=water)" in text
        assert "6-311+G(d,p)" in text

    def test_charge_and_name_in_header(self, molecule, tmp_path):
        text = self._write(molecule, tmp_path)
        assert "%chk=mol1_UV.chk" in text
        assert "\n0 1\n" in text

    def test_negative_charge_written(self, molecule, tmp_path):
        create_input_with_charge(molecule, "anion", -1, str(tmp_path))
        text = (tmp_path / "anion_input.gjf").read_text()
        assert "\n-1 1\n" in text

    def test_resource_lines_precede_route_section(self, molecule, tmp_path):
        """Gaussian only honours Link0 (%) lines placed before the route (#) line."""
        text = self._write(molecule, tmp_path, mem_gb=8, n_processes=2)
        assert text.index("%mem=") < text.index("\n# td=")
        assert text.index("%nprocshared=") < text.index("\n# td=")

    def test_stdout_restored_after_write(self, molecule, tmp_path, capsys):
        """The function redirects sys.stdout to the file; it must put it back."""
        self._write(molecule, tmp_path)
        print("still on stdout")
        assert "still on stdout" in capsys.readouterr().out
