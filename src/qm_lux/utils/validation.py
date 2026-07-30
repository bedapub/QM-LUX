# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Validators for CREST and XTB geometry optimisation output files."""

import sys


def validate_crest_best_xyz(file_path):
    """Validate the structure and format of a ``crest_best.xyz`` file.

    The file must have:

    * A first header line containing an integer (number of coordinate rows).
    * A second header line containing a single float (energy).
    * Subsequent lines with exactly 4 columns: element symbol (string) followed
      by three Cartesian coordinates (floats).

    Parameters
    ----------
    file_path : str
        Path to the ``crest_best.xyz`` file.

    Returns
    -------
    bool
        ``True`` if the file structure and format are correct, ``False``
        otherwise.
    """
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()

        if len(lines) < 2:
            print("Error: The file does not contain the required header lines.")
            return False

        try:
            num_rows = int(lines[0].strip())
        except ValueError:
            print("Error: The first header line must be an integer representing the number of rows.")
            return False

        try:
            float(lines[1].strip())
        except ValueError:
            print("Error: The second header line must be a float.")
            return False

        for i, line in enumerate(lines[2:], start=3):
            parts = line.split()
            if len(parts) != 4:
                print(f"Error: Line {i} does not contain exactly 4 columns.")
                return False

            if not parts[0].isalpha():
                print(f"Error: The first column in line {i} must be a string.")
                return False

            try:
                float(parts[1])
                float(parts[2])
                float(parts[3])
            except ValueError:
                print(f"Error: Columns 2, 3, and 4 in line {i} must be floats.")
                return False

        if len(lines) - 2 != num_rows:
            print("Error: The number of data rows does not match the number specified in the header.")
            return False

        print("The file structure and format are correct.")
        return True

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        return False


def validate_crest_out(file_path):
    """Validate the header of a ``crest.out`` file.

    Checks that the CREST banner header is present and matches the expected
    format.  One or more empty lines before the first ``=`` character are
    allowed.

    Parameters
    ----------
    file_path : str
        Path to the ``crest.out`` file.

    Returns
    -------
    bool
        ``True`` if the file header is correct, ``False`` otherwise.
    """
    expected_header = [
        "       ==============================================\n",
        "       |                                            |\n",
        "       |                 C R E S T                  |\n",
        "       |                                            |\n",
        "       |  Conformer-Rotamer Ensemble Sampling Tool  |\n",
        "       |          based on the GFN methods          |\n",
        "       |             P.Pracht, S.Grimme             |\n",
        "       |          Universitaet Bonn, MCTC           |\n",
        "       ==============================================\n",
    ]

    try:
        with open(file_path, "r") as file:
            lines = file.readlines()

        header_start = -1
        for i, line in enumerate(lines):
            if line.strip() == "==============================================":
                header_start = i
                break

        if header_start == -1:
            print("Error: The file does not contain the required header.")
            return False

        for i, expected_line in enumerate(expected_header):
            if lines[header_start + i] != expected_line:
                print("Error: The file header does not match the expected format.")
                return False

        print("The file structure and format are correct.")
        return True

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        return False
