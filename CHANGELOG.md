# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
