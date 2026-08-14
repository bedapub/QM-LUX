# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
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
