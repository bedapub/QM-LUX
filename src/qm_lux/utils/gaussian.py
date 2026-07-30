# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Utilities for generating Gaussian input files and parsing Gaussian output."""

import os
import sys

import numpy as np
import pandas as pd
from ase.io import read  # noqa: F401 — re-exported for callers


def get_UV_vis_from_gaussian_output(base_dir):
    """Parse Gaussian TD-DFT logs and write per-molecule UV-Vis spectra.

    For each molecule folder under ``<base_dir>/0/``, reads the ``log.out``
    Gaussian output file, sums Gaussian band contributions over a wavelength
    grid of 100–1000 nm (900 points), and writes the result as a
    ``<molecule>_uvvis.xy`` file alongside the output.

    Parameters
    ----------
    base_dir : str
        Root results directory containing a ``0/`` subdirectory with
        per-molecule folders holding ``log.out`` Gaussian output files.
    """
    base_dir = os.path.abspath(base_dir)
    directory_uv = os.path.join(base_dir, "0")

    print("Work directory:")
    print(os.listdir(directory_uv))

    for dire in os.listdir(directory_uv):
        dire_UV = os.path.join(directory_uv, dire)
        for nnnn in os.listdir(dire_UV):
            if nnnn == "log.out":
                try:
                    l, v = parse_output(dire_UV, nnnn)
                    num_of_xsteps = 900
                    l_min = 100
                    l_max = 1000
                    lambda_range = np.linspace(l_min, l_max, num_of_xsteps)
                    uvvis = np.zeros(num_of_xsteps)
                    for il, jv in zip(l, v):
                        uvvis += sum_gauss(lambda_range, il, jv)
                    vec = np.column_stack((lambda_range, uvvis))
                    np.savetxt(
                        os.path.join(dire_UV, "{}_uvvis.xy".format(dire)),
                        vec,
                        header="lambda Intensity",
                        comments="#",
                    )
                    print("Done! In ", dire_UV)
                except Exception:
                    print("No predicted UV-vis in:")
                    print(nnnn)


def extract_UV_gaussian_output(base_dir):
    """Read all ``.xy`` UV-Vis files under ``base_dir/0/`` and return a DataFrame.

    Each ``.xy`` file contains two whitespace-separated columns (wavelength,
    epsilon). Comment lines starting with ``#`` are dropped.  The result is
    also written to ``base_dir/UVvis.csv``.

    Parameters
    ----------
    base_dir : str
        Root results directory containing a ``0/`` subdirectory with
        per-molecule folders.

    Returns
    -------
    pandas.DataFrame
        Columns: ``lambda (nm)``, ``Epsilon (mL/cm/mol)``, ``SRN``.
    """
    base_dir = os.path.abspath(base_dir)
    directory_uv = os.path.join(base_dir, "0")

    frames = []
    for dire in os.listdir(directory_uv):
        for fname in os.listdir(os.path.join(directory_uv, dire)):
            if not fname.endswith(".xy"):
                continue
            fpath = os.path.join(directory_uv, dire, fname)
            with open(fpath) as f:
                rows = [line.split() for line in f]
            x_vals, y_vals = zip(*rows)
            df = pd.DataFrame({
                "lambda (nm)": x_vals,
                "Epsilon (mL/cm/mol)": y_vals,
                "SRN": fname[:-3],
            })
            frames.append(df)

    df_all = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df_all = df_all[~df_all["lambda (nm)"].str.startswith("#")]
    df_all.reset_index(drop=True, inplace=True)
    print("dataframe with the UV-vis extracted")
    print(df_all)
    df_all.to_csv(os.path.join(base_dir, "UVvis.csv"))
    return df_all


def create_input_with_charge(molecule, name, charge, path):
    """Write a Gaussian TD-DFT input file (``.gjf``) for a charged molecule.

    Parameters
    ----------
    molecule : ase.Atoms
        ASE atoms object with positions and chemical symbols.
    name : str
        Molecule name; used for the checkpoint filename and job title.
    charge : int
        Formal charge of the molecule.
    path : str
        Directory where the ``.gjf`` file will be written.
    """
    mem = 20          # GB
    nstates = 30      # number of excited states
    n_processes = 24  # cores requested

    head = (
        "%chk={}_UV.chk\n%mem={}GB\n%nprocshared={}\n"
        "# td=(singlets,nstates={}) b3lyp/gen scrf=(solvent=water)\n\n"
        "{}\n\n{} 1\n"
    ).format(name, mem, n_processes, nstates, name, charge)

    positions = ""
    for sp, x, y, z in zip(
        molecule.symbols,
        molecule.positions[:, 0],
        molecule.positions[:, 1],
        molecule.positions[:, 2],
    ):
        positions += "    {}    {}    {}    {}\n".format(sp, x, y, z)
    positions += "\n"

    unique_species = np.unique(molecule.symbols)
    basis = " ".join(str(sp) for sp in unique_species)
    basis += " 0\n6-311+G(d,p)\n****\n\n"

    inputfile = head + positions + basis

    gjf_path = os.path.join(path, "{}_input.gjf".format(name))
    original_stdout = sys.stdout
    with open(gjf_path, "w") as f:
        sys.stdout = f
        print(inputfile)
        sys.stdout = original_stdout


def sum_gauss(lambda_range, lambda_i, f_i):
    """Evaluate a single Gaussian band contribution to the UV-Vis spectrum.

    Implements the formula from the Gaussian manual
    (https://gaussian.com/uvvisplot/).

    Parameters
    ----------
    lambda_range : numpy.ndarray
        Wavelength grid (nm) at which to evaluate the band.
    lambda_i : float
        Peak wavelength (nm) of this excited state.
    f_i : float
        Oscillator strength of this excited state.

    Returns
    -------
    numpy.ndarray
        Molar absorptivity contribution at each point in ``lambda_range``.
    """
    fixed_num = 1.3062974e8
    sigma = 1 / 3099.6  # ~0.4 eV half-width
    return (
        fixed_num * f_i / (1e7 * sigma)
        * np.exp(-((1 / lambda_range - 1 / lambda_i) ** 2) / sigma ** 2)
    )


def parse_output(path, molname):
    """Parse excitation energies and oscillator strengths from a Gaussian log.

    Parameters
    ----------
    path : str
        Directory containing the Gaussian output file.
    molname : str
        Filename of the Gaussian output file.

    Returns
    -------
    tuple
        ``(lambdas, fvalues)`` — lists of peak wavelengths (nm) and
        oscillator strengths, or ``(0, 0)`` if no excited states were found.
    """
    lambdas = []
    fvalues = []
    with open(os.path.join(path, molname)) as f:
        for line in f:
            tokens = line.split()
            try:
                if tokens[1] == "State":
                    lambdas.append(float(tokens[6]))
                    fvalues.append(float(tokens[8].split("=")[1]))
            except (IndexError, ValueError):
                continue
    if not fvalues:
        return 0, 0
    return lambdas, fvalues
