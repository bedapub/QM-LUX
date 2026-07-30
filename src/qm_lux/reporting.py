# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""HTML report generation: merge ML predictions, structures, and UV-Vis plots.

:func:`get_mol_ML_results` is re-exported from :mod:`qm_lux.utils.io` for
backward compatibility.
"""

import base64
import os
import pickle

import pandas as pd

from qm_lux.utils.plotting import create_molecule_images


def get_mol_ML_results(base_dir):
    """Merge ML predictions with structures and UV-Vis plots into an HTML report.

    Reads ``test_set_with_fP_rdkit_prop_UVvis.pkl`` and the ML result CSVs from
    ``<base_dir>/ML_results/``, generates molecule structure images, then writes
    a self-contained HTML report at ``<base_dir>/results_ML_with_mol_UV.html``.
    Also writes ``<base_dir>/Failed_molecules.txt`` listing compounds without ML
    results (likely due to failed QM steps).

    Parameters
    ----------
    base_dir : str
        Working directory containing the pickle, ML results, UV plots, and
        molecule images.
    """
    base_dir = os.path.abspath(base_dir)
    create_molecule_images(base_dir, output_dir="molecule_images")
    print(base_dir)

    dir_res = os.path.join(base_dir, "ML_results")
    dir_uv = os.path.join(base_dir, "UV_plots")
    dir_structures = os.path.join(base_dir, "molecule_images")

    with open(os.path.join(base_dir, "test_set_with_fP_rdkit_prop_UVvis.pkl"), "rb") as f:
        df = pickle.load(f)
    print("\nDATASET")
    print(df)

    df_res = pd.DataFrame()
    for file in os.listdir(dir_res):
        if file.startswith("results_ML") and file.endswith(".csv"):
            print(f"Concatenate ML results: Read file: {file}")
            df_ML = pd.read_csv(os.path.join(dir_res, file))
            df_res = pd.concat([df_res, df_ML])

    df_res = df_res.drop(columns=["Unnamed: 0"], errors="ignore")
    merged_df = pd.merge(df[["SRN", "SMILES_CLEAN"]], df_res, left_index=True, right_index=True)
    print("\nDataset with the ML prediction")
    print(merged_df)

    merged_df = merged_df.sort_values(by="SRN").reset_index(drop=True)
    merged_df["prob"] = merged_df["prob"].round(2)

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phototoxicity Results HTML</title>
        <!-- DataTables CSS -->
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
        <!-- jQuery and DataTables JS -->
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <style>
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                text-align: center;
                padding: 8px;
                border: 1px solid black;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            img {{
                height: auto;
            }}
            .gradient {{
                display: inline-block;
                padding: 6px 10px; /* Increased padding to make the area around the text larger */
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Phototoxicity Results</h1>
        <table id="resultsTable" class="display">
            <thead>
                <tr>
                    <th>SRN</th>
                    <th>SMILES_CLEAN</th>
                    <th>Structure</th>
                    <th>UV-Vis Spectra</th>
                    <th>Prediction</th>
                    <th>Probability</th>
                    <th>Descriptors</th>
                    <th>ML Method</th>
                </tr>
            </thead>
            <tbody>
    """

    for index, row in merged_df.iterrows():
        srn = row["SRN"]
        prob = row["prob"]
        pred = row["pred"]
        descriptors = row["Descriptors"]
        ml_method = row["ML_Method"]
        smiles = row["SMILES_CLEAN"]

        text_color = "green" if pred == 0.0 else "red"
        background_color = f"rgba(0, 128, 0, {prob})" if pred == 0.0 else f"rgba(255, 0, 0, {prob})"

        uv_spectra_html = ""
        srn_clean = srn.split(".")[0]
        for file in os.listdir(dir_uv):
            file_clean = file.split(".")[0]
            if srn_clean == file_clean:
                with open(os.path.join(dir_uv, file), "rb") as uv_file:
                    uv_base64 = base64.b64encode(uv_file.read()).decode("utf-8")
                uv_spectra_html = f'<img src="data:image/png;base64,{uv_base64}" alt="UV-Vis Spectra" style="width:350px;">'
                break

        structure_html = ""
        for file in os.listdir(dir_structures):
            if file.startswith(srn):
                with open(os.path.join(dir_structures, file), "rb") as struct_file:
                    struct_base64 = base64.b64encode(struct_file.read()).decode("utf-8")
                structure_html = f'<img src="data:image/png;base64,{struct_base64}" alt="Molecule Structure" style="width:260px;">'
                break

        html_content += f"""
            <tr>
                <td style="color:{text_color};">{srn}</td>
                <td style="color:{text_color};">{smiles}</td>
                <td>{structure_html}</td>
                <td>{uv_spectra_html}</td>
                <td style="color:{text_color};">{pred}</td>
                <td><span class="gradient" style="background-color:{background_color};">{prob}</span></td>
                <td style="color:{text_color};">{descriptors}</td>
                <td style="color:{text_color};">{ml_method}</td>
            </tr>
        """

    html_content += """
            </tbody>
        </table>
        <!-- Initialize DataTables -->
        <script>
            $(document).ready(function() {{
                $('#resultsTable').DataTable();
            }});
        </script>
    </body>
    </html>
    """

    output_html_path = os.path.join(base_dir, "results_ML_with_mol_UV.html")
    with open(output_html_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    print(f"HTML file with enhanced gradient around 'Prob' has been saved as: {output_html_path}")

    df_ini = pd.read_csv(os.path.join(base_dir, "input.csv"))
    list_ini_srn = list(df_ini["SRN"])
    merged_df[["SRN", "diast_numb"]] = (
        merged_df["SRN"]
        .str.split("_", n=1, expand=True)
        .reindex(columns=[0, 1], fill_value="")
    )
    final_srn = list(merged_df["SRN"])
    failed_mol = set(list_ini_srn) - set(final_srn)

    print("")
    print("")
    if failed_mol:
        print("###################################################")
        print("Failed molecules are:", failed_mol)
        print("###################################################")
    else:
        print("###################################################")
        print("No crash during molecules processing:")
        print("All input molecules provided have ML results!!!")
        print("###################################################")

    with open(os.path.join(base_dir, "Failed_molecules.txt"), "w") as file:
        for item in failed_mol:
            file.write(f"{item}\n")

    print("")
    print("")
    print("##############################################################################################################################################")
    print("####### Final HTML 'results_ML_with_mol_UV' file with the ML results + pred. UV-vis and Molecular structure is successfully generated! #######")
    print("#################### Minimized molecules from CREST used for the TD-DFT  are in the subfolder 'Minimized_mol' as xyz files ###################")
    print("##############################################################################################################################################")
    print("")
