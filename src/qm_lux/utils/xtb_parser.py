# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""XTB output parsing: extract QM properties from XTB run directories."""

import os
import re
import shutil

import pandas as pd


def get_QM(base_dir, srn_mode):
    """Parse XTB output files and assemble a CSV of QM properties.

    For each compound, reads the XTB ``.out`` file to extract total energy,
    HOMO-LUMO gap, and Fermi level, copies the CREST-minimised geometry to
    ``<base_dir>/Minimized_mol/``, and writes the results to
    ``<base_dir>/dataframe_all_res_QM_xtb.csv``.

    Parameters
    ----------
    base_dir : str
        Working directory containing ``xtb_input.pkl`` and the ``0/``
        sub-directory with per-compound XTB output folders.
    srn_mode : {"SRN", "no_SRN"}
        ``"SRN"`` — use the compound identifier as the folder name;
        ``"no_SRN"`` — use the integer index as the folder name.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``SRN``, ``ENERGY (Eh)``,
        ``HOMO-LUMO GAP (eV)``, ``Fermi-Level (eV)``, and
        ``Expected lambda Absmax (nm)``.
    """
    import pickle

    base_dir = os.path.abspath(base_dir)
    os.makedirs(os.path.join(base_dir, "Minimized_mol"), exist_ok=True)

    with open(os.path.join(base_dir, "xtb_input.pkl"), "rb") as f:
        df = pickle.load(f)

    base_dir_0 = os.path.abspath(os.path.join(base_dir, "0"))
    list_comp = list(df["SRN"])

    no_xtb = []
    all_sdf = []
    df_final = pd.DataFrame()
    c = 0
    df = pd.DataFrame()

    for conf in range(len(list_comp)):
        if srn_mode == "SRN":
            file_mol = str(list_comp[conf])
        elif srn_mode == "no_SRN":
            file_mol = str(conf)

        print(list_comp[conf])
        out_path = os.path.join(base_dir_0, str(file_mol), file_mol + ".out")
        print(out_path)
        file_exists = os.path.exists(out_path)
        print(file_exists)

        if not file_exists:
            no_xtb.append(list_comp[conf])
            continue

        with open(os.path.join(base_dir_0, str(file_mol), str(file_mol) + ".sdf")) as f:
            lines = f.read()
            first = lines.split("\n", 1)[0]
            s_SRN = first.split("_", 2)
            s_SRN = "_".join(s_SRN[:2])
            print("SRN")
            print(s_SRN)

        with open(os.path.join(base_dir_0, str(file_mol), file_mol + ".out")) as f:
            c = c + 1
            count_dup = 0
            for line in f:
                if line.startswith("          | TOTAL ENERGY"):
                    l_E = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(line))
                if line.startswith("          | HOMO-LUMO GAP"):
                    l_HL = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(line))
                if line.startswith("             Fermi-level"):
                    if count_dup == 0:
                        l_Fermi = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(line))
                        count_dup += 1
                if line.startswith(" * finished run on"):
                    temp_df = pd.DataFrame({
                        "SRN": s_SRN,
                        "ENERGY (Eh)": float(l_E[0]),
                        "HOMO-LUMO GAP (eV)": float(l_HL[0]),
                        "Fermi-Level (eV)": float(l_Fermi[0]),
                    }, index=[0])
                    df = pd.concat([df, temp_df])
                    break
                else:
                    continue

        all_sdf.append(s_SRN)

        file_path = os.path.join(base_dir_0, str(file_mol), "crest_best.xyz")
        if os.path.exists(file_path):
            destination_dir = os.path.join(base_dir, "Minimized_mol")
            os.makedirs(destination_dir, exist_ok=True)
            destination_file_path = os.path.join(destination_dir, f"{s_SRN}_crest_best.xyz")
            shutil.copy(file_path, destination_file_path)
        else:
            print(f"The file {file_path} does not exist.")

    df_final = pd.concat([df_final, df])
    df_final["Expected lambda Absmax (nm)"] = (
        (2.99e8 * 6.62e-34) / (df_final["HOMO-LUMO GAP (eV)"] * 1.60e-19) * 1e9
    )
    df_final.reset_index(drop=True, inplace=True)
    df_final.to_csv(os.path.join(base_dir, "dataframe_all_res_QM_xtb.csv"))
    print("NO xTB FILES IN", no_xtb, "xTB with .out but without QM values", set(all_sdf) - set(list(df_final["SRN"])))

    return df_final
