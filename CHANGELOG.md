# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `NOTICE` and `THIRD_PARTY_LICENSES.md` record the third-party software the
  container image redistributes. The repository previously named no licence for
  any bundled component: XTB and CREST are **LGPL-3.0-or-later** and the string
  "LGPL" did not appear anywhere in the tree. `NOTICE` covers the components
  carrying obligations beyond attribution — XTB/CREST, Qt/PySide6 (LGPL-3.0-only,
  pulled in transitively by the `matplotlib` meta-package and never loaded), ASE
  (LGPL-2.1-or-later, the one that QM-LUX code actually imports), the MySQL client
  libraries (GPL-2.0-or-later, via Qt), the GCC runtime libraries, and Intel MKL
  (proprietary; installed because the conda-forge OpenBLAS build of `libblas`
  depends on it, but not what NumPy loads — `libblas.so.3` resolves to
  `libopenblasp-r0.3.28.so`). Both files are copied into the image, since a notice
  that describes the image but lives only in git never reaches anyone who pulls it.
  The source-availability section is a **draft**: it states both the GPL-3.0 §6(b)
  written offer and the §6(d) route that fits registry distribution, and needs a
  named entity and contact before publication.
- `tools/gen_third_party_licenses.py` regenerates `THIRD_PARTY_LICENSES.md` from a
  built image. The inventory is read out of the image rather than `environment.yml`
  because the two differ: 246 components ship, 43 of them under a copyleft or
  non-OSI licence, most reached transitively.
- A `References` section in the README, with DOIs for the methods the workflow
  runs. Citations previously existed only inside the generated Snakemake report,
  so nothing was visible to anyone reading the repository.

### Fixed
- The rendered methods text stated the wrong basis set. `workflow/report/methods.rst`
  said the TD-DFT step was `B3LYP/6-31G*`; `create_input_with_charge` writes
  `B3LYP/6-311+G(d,p)` with 30 singlet states and a water PCM, as its own docstring
  says. That paragraph ships in every run's HTML report and is what a user would
  copy into a manuscript, and for excited states the difference is not cosmetic.
- The two report templates carried reference lists that disagreed. `methods.rst`
  cited CREST only through the 2024 J. Chem. Phys. paper, which describes CREST 3.0,
  while the image ships 2.11.2, whose paper is the 2020 PCCP one that appeared only
  in `description.rst`. Both files now carry the same list, verified by parsing them
  and comparing the extracted URIs. Added throughout: the xtb *program* paper
  (distinct from the GFN2 *method* paper), ALPB — passed as `--alpb water` by both
  the `crest` and `xtb` rules and previously named in prose but never cited — plus
  ASE, ETKDG and MMFF94s. Every DOI was resolved and matched to its citation.
- The Gaussian citation hardcoded "Revision C.01", which the workflow cannot know:
  it runs against whatever `g16` the host provides. It now asks the user to cite
  the revision they ran.
- `get_results` selects cross-validation files by content rather than by name.
  A `results_ML*` filename does not identify one: the prediction step writes
  `<data_ml*>/ML_results/results_ML<descriptors><model>.csv`, whose columns are
  `pred`/`prob`/`Descriptors`/`ML_Method` and which carries no metrics. Both
  matched the old glob, with two consequences. Pointed at a `data_ml*` tree it
  found only prediction files and died on `sort_values(by=["MCC"])` with a bare
  `KeyError: 'MCC'`, naming a column but neither the directory nor the mistake;
  that is now a `ValueError` saying what was found and what to run instead.
  Pointed at a genuine training-results tree it *worked*, and quietly folded
  the prediction rows in beside the metrics — a measured run produced 12 rows
  of which 1 was a cross-validation row and 11 were predictions with `NaN` for
  every metric column. Skipped files are now named on stdout.
  `CVs_error_cal_folds.txt` is deliberately unchanged: any `results_ML*` file
  still counts as "this directory produced results", so a directory holding
  only predictions is not newly listed under `NO CVs FOR:`. Verified
  byte-identical against the previous implementation on the same tree.
- `finger_print_gen` validates `load_DF`, and checks it against the type of
  `mol`. Only the exact string `"NO"` used to select the file-reading path, so
  a case typo on a CSV path died with `AttributeError: 'str' object has no
  attribute 'copy'`, and passing a DataFrame with `load_DF="NO"` died with a
  `TypeError` from inside `pandas.read_csv`. Neither message named the
  argument. Both are now `ValueError` naming `load_DF` and the value.
- The three results-table builders in `qm_lux.metrics` share one mapping for
  the `Method Training` column. `table_stat_cal` and `table_stat_cal_iter`
  folded everything that was not `"NO"` into the literal `"YES Oversampling"`,
  so a `"SMOTE"` run was recorded as a plain oversampled one — while
  `table_stat_cal_std` spelled it correctly, making the two tables from a run
  impossible to join on that column. An unrecognised mode is now recorded
  verbatim by all three rather than relabelled.
- `sdf_run` no longer raises `UnboundLocalError` when nothing is processed. An
  empty `list_comp`, a batch in which every folder already exists under
  `"NO OVERWRITE"`, and a batch in which every compound fails conformer
  embedding are all handled instead of falling off the end of the function.
- `sdf_run` no longer writes a compound into another compound's output folder.
  The output index came from a counter that only advanced on processed
  compounds, so under `"NO OVERWRITE"` one skipped compound shifted every later
  one an index too low — over the top of the file the flag was asked to
  preserve — and left the last folder empty. The index now comes from the
  compound's position in `list_comp`, which is how the folders were created.
- `sdf_run` rejects a `check` value other than `"OVERWRITE"` or
  `"NO OVERWRITE"` with `ValueError`. An unrecognised value used to leave the
  internal skip list short and surface as an `IndexError` from deep inside the
  processing loop.

### Changed
- **Breaking for callers reading the return value:** `sdf_run` returns a status
  aggregated over the whole batch — `"ERROR"` if any compound failed, otherwise
  `"OK"`. It previously returned the *last* processed compound's status, so a
  failure on any earlier compound was reported as `"OK"`. A batch in which
  nothing was processed returns `"OK"`. `generate_conf_xtb`, the only in-tree
  caller, discards the value.
- **Breaking for callers relying on the fallback:** `finger_print_gen` now
  raises `ValueError` for a `method` that is not exactly `"MACCS"`, `"Morgan"`
  or `"E-state"`. It previously printed a warning to stdout and returned 167-bit
  MACCS keys in a column named after the fingerprint that was asked for, so a
  case typo — `method="morgan"` — silently produced different descriptors than
  requested with no downstream way to tell. Case is deliberately not normalised.
  No in-tree caller is affected: `data_preparation` passes `"Morgan"` and the
  method is not configurable from the workflow.

## [1.0.0] — 2026-07-29

### Added
- `src/qm_lux/` package in src-layout, importable as `qm_lux`
- CLI entry point `qm-lux` with subcommands: `data_preparation`, `xtb_conf`,
  `xtb_runner`, `gaussian_preparation`, `validate`, `get_pred_UVvis`,
  `prediction`, `get_results`
- Snakemake workflow (8 rules) covering the full QM → ML prediction pipeline
- Singularity container (`qm-lux.sif`) built from `Dockerfile`
- Pre-trained Random Forest model published as GitHub Release asset (`v1.0.0`)
- 154 unit tests across `tests/unit/`; integration test script
  `tests/integration/run_full_test.sh` with reference validation
- Public Python API exposed via `qm_lux.__init__` (`__all__`)
- `py.typed` marker (PEP 561) for type-checker support
- GitHub Actions CI: test job on every PR/push; wheel published to GitHub
  Release on version tags

### Changed
- Refactored from monolithic `phototox_workflow` scripts into a proper
  installable Python package
- Modularised `utils/io.py` → `utils/xtb.py`, `utils/plotting.py`,
  `reporting.py`
- Moved `dft.py` body into `utils/gaussian.py`; `dft.py` is now a shim
- Renamed `sdf_generator.py` → `xtb.py`; `sdf_generator.py` is now a shim
- Extracted `metrics.py` from `ml_plots.py`
- Fixed star-import in `ml_engines.py`
- Removed unused parameters `opt_scoring` and `save_png`

### Removed
- All training-only dead code (cross-validation result plotting functions
  that were never called from the public workflow)
