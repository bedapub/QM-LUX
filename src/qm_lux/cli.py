# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for the QM-LUX phototoxicity prediction workflow.

Entry point: ``python -m qm_lux.cli <subcommand> [options]``

Subcommands
-----------
data_preparation
    Standardise SMILES, enumerate chiral isomers, compute fingerprints and
    descriptors, and write ``xtb_input.pkl``.
xtb_conf
    Embed MMFF94s conformers and write SDF files for XTB/CREST.
xtb_runner
    Run XTB/CREST conformer search interactively.
gaussian_preparation
    Write a Gaussian TD-DFT input ``.gjf`` file from an XTB-optimised XYZ
    geometry.
validate
    Validate a CREST or XTB output file (``crest_best.xyz`` or ``crest.out``).
get_pred_UVvis
    Parse Gaussian TD-DFT output, compute UV-Vis AUCs, and assemble the ML
    feature matrix.
prediction
    Score compounds with the pre-trained Random Forest model.
get_results
    Collect ML prediction results and write a summary CSV and HTML report.
"""

import os
import random
import sys
import warnings
import argparse

from ase.io import read as ase_read

from qm_lux.preparation import data_preparation
from qm_lux.xtb import generate_conf_xtb
from qm_lux.ml_engines import run_prediction
from qm_lux.utils.io import check_directory_exists, get_results, remove_chk_files, xy_files
from qm_lux.utils.xtb_parser import get_QM
from qm_lux.utils.plotting import plot_UV
from qm_lux.reporting import get_mol_ML_results
from qm_lux.utils.validation import validate_crest_best_xyz, validate_crest_out
from qm_lux.descriptors import ML_preparation_test_set
from qm_lux.utils.gaussian import (
    create_input_with_charge,
    extract_UV_gaussian_output,
    get_UV_vis_from_gaussian_output,
)
from qm_lux.utils.uvvis import run_AUCs_spectra

warnings.simplefilter("ignore")


def main():
    """Parse command-line arguments and dispatch to the requested workflow step."""
    parser = argparse.ArgumentParser(description='Wrapper script for calling different functions')
    subparsers = parser.add_subparsers(title='Functions', dest='function')

    # data_preparation
    parser_data_preparation = subparsers.add_parser('data_preparation', help='Call data_preparation')
    parser_data_preparation.add_argument("-i", "--input", type=str, help='Name of the test set')
    parser_data_preparation.add_argument("-o", "--outdir", type=str, required=False,
                                         help='Output directory name (optional; auto-generated when omitted)')
    parser_data_preparation.add_argument("-c", "--chirality_check", type=str, default="NO",
                                         help='NO: generate all diastereoisomers from unassigned chiral centers; '
                                              'YES: generate only enantiomers, and skip compounds already listed '
                                              'in --current_df. Case-insensitive. Default=NO.')
    parser_data_preparation.add_argument("-d", "--current_df", type=str, required=False,
                                         help='Path to the pickle of already-processed compounds, whose SRNs are '
                                              'excluded from this run. Required when --chirality_check=YES.')

    # xtb_conf — Snakemake: prepare conformer inputs for xtb/CREST
    parser_xtb_conf = subparsers.add_parser('xtb_conf', help='Prepare conformer inputs for xtb/CREST')
    parser_xtb_conf.add_argument("-i", "--input", type=str, help='Input pkl file')

    # xtb_runner — interactive: run xtb/CREST directly
    parser_xtb_runner = subparsers.add_parser('xtb_runner', help='Run xtb/CREST conformer search')
    parser_xtb_runner.add_argument("-i", "--input", type=str, help='Path of dataframe .pkl as input to run xtb-crest')

    # gaussian_preparation — write Gaussian TD-DFT input from XYZ geometry
    parser_gaussian_prep = subparsers.add_parser(
        'gaussian_preparation',
        help='Write a Gaussian TD-DFT input .gjf from an XTB-optimised XYZ geometry',
    )
    parser_gaussian_prep.add_argument("-i", "--infile", required=True, help="Input .xyz file, e.g., crest_best.xyz")
    parser_gaussian_prep.add_argument("-n", "--name", required=True, help="Molecule name (used for job title and checkpoint basename)")
    parser_gaussian_prep.add_argument("-c", "--charge", type=int, default=0, help="Formal charge of the molecule. Default 0")
    parser_gaussian_prep.add_argument("-d", "--directory", required=True, help="Output directory for the .gjf file")
    # These become the %mem and %nprocshared lines of the .gjf, which Gaussian
    # honours over GAUSS_MDEF/GAUSS_PDEF and over `g16 -m=`/`-p=` — so they must
    # match what the scheduler allocates to the gaussian_runner rule.
    parser_gaussian_prep.add_argument("-m", "--mem-gb", type=int, default=20,
                                      help="Memory for the %%mem line, in GB. Default 20")
    parser_gaussian_prep.add_argument("-p", "--nproc", type=int, default=24,
                                      help="Shared processors for the %%nprocshared line. Default 24")

    # validate — check CREST/XTB output file format
    parser_validate = subparsers.add_parser(
        'validate',
        help='Validate a CREST or XTB output file format',
    )
    parser_validate.add_argument("file_type", choices=["crest_best.xyz", "crest.out"],
                                 help='File type to validate')
    parser_validate.add_argument("file_path", help='Path to the file to validate')

    # get_pred_UVvis — process Gaussian UV-vis output
    parser_results_UV = subparsers.add_parser('get_pred_UVvis',
                                              help='Process Gaussian UV-vis output, compute AUCs, and build ML descriptors')
    parser_results_UV.add_argument("-i", "--input", type=str,
                                   help='Path of the folder where .log files from Gaussian are stored.')

    # get_results — collect ML results (Snakemake: --output provided; interactive: --type CV/PRED)
    parser_results = subparsers.add_parser('get_results',
                                           help='Collect ML results and generate summary report')
    parser_results.add_argument("-i", "--input", type=str,
                                 help='Results root directory (Snakemake) or data_ml folder (interactive)')
    parser_results.add_argument("-o", "--output", type=str,
                                 help='Output directory (Snakemake mode; omit for interactive)')
    parser_results.add_argument("-t", "--type", type=str, default="PRED",
                                 help='CV (cross-validation) or PRED (prediction). Default=PRED (interactive only)')

    # prediction — run ML prediction (Snakemake: --pkl/--csv/--srn provided; interactive: auto-discovered)
    parser_prediction = subparsers.add_parser('prediction', help='Run ML prediction on test compounds')
    parser_prediction.add_argument("-i", "--input", type=str, help='Path to the model folder')
    parser_prediction.add_argument("-p", "--pkl", type=str,
                                   help='Path to the input pkl file (auto-discovered from --dataframe if omitted)')
    parser_prediction.add_argument("-c", "--csv", type=str, help='Path to the output CSV file')
    parser_prediction.add_argument("-s", "--srn", type=str, help='Path to the input SRN/molecule CSV file')
    parser_prediction.add_argument("-df", "--dataframe", type=str,
                                   help='Path to the data_ml folder (for auto-discovery when --pkl is omitted)')
    parser_prediction.add_argument("-a", "--attribute", type=str, default="SRN",
                                   help='Target column name. Default=SRN')
    parser_prediction.add_argument("-m", "--method", type=str, default="RF",
                                   help='ML method name, e.g. RF. Default=RF')
    parser_prediction.add_argument("-d", "--descriptor", type=str,
                                   help='Descriptor column name in the pkl file')
    parser_prediction.add_argument("-e", "--ext_val", type=str, default="NO",
                                   help='YES if actual labels are available (external validation). Default=NO')

    args = parser.parse_args()

    work_dir = os.getcwd()

    if args.function == 'data_preparation':
        print("Current folder:", work_dir)
        file_name = args.input
        # Normalise the same way workflow/Snakefile does, so `-c yes` and a
        # config `chirality_check: yes` reach data_preparation identically.
        # data_preparation itself rejects anything that is not YES or NO.
        diast_check = args.chirality_check.strip().upper()
        current_df = args.current_df if diast_check == "YES" else None

        if args.outdir:
            full_path = os.path.join(work_dir, args.outdir)
        else:
            full_path = os.path.join(work_dir, "data_ml" + ''.join(random.choices('0123456789', k=10)))

        os.makedirs(full_path, exist_ok=True)
        print("Folder created successfully:", full_path)
        data_preparation(os.path.abspath(file_name), full_path, diast_check, current_df)

    elif args.function == 'xtb_conf':
        generate_conf_xtb(args.input)

    elif args.function == 'xtb_runner':
        path_xtb = args.input

        if not path_xtb:
            path_xtb = work_dir
            subdirectories = [name for name in os.listdir(path_xtb)
                              if os.path.isdir(os.path.join(path_xtb, name)) and name.startswith("data_ml")]
            if len(subdirectories) == 1:
                path_xtb = os.path.join(work_dir, subdirectories[0])
                generate_conf_xtb(path_xtb)
            else:
                print(f"More than 1 subfolder in {work_dir}, specify the input folder with --input")
        else:
            generate_conf_xtb(path_xtb)

    elif args.function == 'gaussian_preparation':
        if os.path.getsize(args.infile) == 0:
            print(f"Error: The input file '{args.infile}' is empty.")
        else:
            molecule = ase_read(args.infile)
            create_input_with_charge(molecule, args.name, args.charge, args.directory,
                                     mem_gb=args.mem_gb, n_processes=args.nproc)

    elif args.function == 'validate':
        if args.file_type == "crest_best.xyz":
            validate_crest_best_xyz(args.file_path)
        else:
            validate_crest_out(args.file_path)

    elif args.function == 'get_pred_UVvis':
        path_input_results = args.input

        if not path_input_results:
            subdirectories = [name for name in os.listdir(work_dir)
                              if os.path.isdir(os.path.join(work_dir, name)) and name.startswith("data_ml")]
            if len(subdirectories) == 1:
                path_input_results = os.path.join(work_dir, subdirectories[0])
            else:
                print(f"More than 1 subfolder in {work_dir}, specify the input folder with --input")
                sys.exit(1)

        if not check_directory_exists(path_input_results):
            sys.exit(f"The input directory {path_input_results} does not exist. Abort!")

        try:
            remove_chk_files(path_input_results)
            get_UV_vis_from_gaussian_output(path_input_results)
            df_xy_files = xy_files(path_input_results)
            if df_xy_files is None:
                raise FileNotFoundError("No .xy UV spectra files found in the specified directory.")
            df_UV = extract_UV_gaussian_output(path_input_results)
            print("UV-vis binning methods:")
            data_UV_AUC = run_AUCs_spectra(df_UV)
            plot_UV(path_input_results, df_UV)
            get_QM(path_input_results, "no_SRN")
            ML_preparation_test_set(path_input_results, data_UV_AUC)
        except Exception as e:
            print(f"Error processing UV-vis data: {e}")

    elif args.function == 'get_results':
        if args.output:
            # Snakemake mode: --input is the results root, derive data_ml subdir
            base_dir = os.path.join(args.input, "data_ml")
            os.makedirs(args.output, exist_ok=True)
            get_mol_ML_results(base_dir)
        else:
            # Interactive mode: --input is the data_ml folder (or auto-discovered)
            path_input_results = args.input
            if not path_input_results:
                path_input_results = work_dir
                subdirectories = [name for name in os.listdir(path_input_results)
                                  if os.path.isdir(os.path.join(path_input_results, name))
                                  and name.startswith("data_ml")]
                if len(subdirectories) == 1:
                    path_input_results = os.path.join(work_dir, subdirectories[0])

            if path_input_results:
                if args.type == "CV":
                    get_results(path_input_results)
                elif args.type == "PRED":
                    get_mol_ML_results(path_input_results)
                else:
                    print("Wrong type of analysis, provide PRED (prediction) or CV (cross-validation)")

    elif args.function == 'prediction':
        pkl_file = args.pkl
        csv_file = args.csv
        srn_file = args.srn

        if not pkl_file:
            # Auto-discover data_ml folder
            data_ml_dir = args.dataframe
            if not data_ml_dir:
                subdirs = [name for name in os.listdir(work_dir)
                           if os.path.isdir(os.path.join(work_dir, name)) and name.startswith("data_ml")]
                if len(subdirs) == 1:
                    data_ml_dir = os.path.join(work_dir, subdirs[0])
                else:
                    print(f"More than 1 subfolder in {work_dir}, specify the data_ml folder with --dataframe")
                    sys.exit(1)
            pkl_file = os.path.join(data_ml_dir, "test_set_with_fP_rdkit_prop_UVvis.pkl")
            csv_file = csv_file or os.path.join(data_ml_dir, "ML_results", "results_ML.csv")
            srn_file = srn_file or os.path.join(data_ml_dir, "input.csv")
            print(f"test set: {data_ml_dir}")

        try:
            run_prediction(
                path_input_model=args.input,
                pkl_file=pkl_file,
                csv_file=csv_file,
                srn_file=srn_file,
                attribute=args.attribute,
                method=args.method,
                descriptor=args.descriptor,
            )
        except Exception as e:
            print(f"Error in prediction: {e}")

    else:
        print('Invalid function specified')


if __name__ == "__main__":
    main()
