# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""qm_lux — Phototoxicity prediction combining QM UV-Vis descriptors with ML.

Public API
----------
Import directly from ``qm_lux`` rather than from internal sub-modules:

    from qm_lux import data_preparation, run_AUCs_spectra, ML_preparation_test_set

Internal module paths may change between versions; the names below are stable.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("qm-lux")
except PackageNotFoundError:
    __version__ = "unknown"

# ── Data preparation ────────────────────────────────────────────────────────
from qm_lux.preparation import data_preparation

# ── Chirality utilities ─────────────────────────────────────────────────────
from qm_lux.chirality import (
    chirality_analysis,
    chirality_generator,
    lack_chiral_finder,
)

# ── RDKit fingerprints / descriptors ────────────────────────────────────────
from qm_lux.rdkit_features import calc_descr, finger_print_gen, standardize

# ── Conformer generation (XTB/CREST input) ──────────────────────────────────
from qm_lux.xtb import generate_conf_xtb

# ── UV-Vis AUC descriptors ──────────────────────────────────────────────────
from qm_lux.utils.uvvis import run_AUCs_spectra

# ── Gaussian output parsing ─────────────────────────────────────────────────
from qm_lux.utils.gaussian import (
    extract_UV_gaussian_output,
    get_UV_vis_from_gaussian_output,
)

# ── ML feature assembly ─────────────────────────────────────────────────────
from qm_lux.descriptors import ML_preparation_test_set

# ── Results / reporting ─────────────────────────────────────────────────────
from qm_lux.reporting import get_mol_ML_results
from qm_lux.utils.io import get_results

__all__ = [
    "__version__",
    # preparation
    "data_preparation",
    # chirality
    "chirality_analysis",
    "chirality_generator",
    "lack_chiral_finder",
    # RDKit features
    "calc_descr",
    "finger_print_gen",
    "standardize",
    # conformer generation
    "generate_conf_xtb",
    # UV-Vis
    "run_AUCs_spectra",
    "extract_UV_gaussian_output",
    "get_UV_vis_from_gaussian_output",
    # ML
    "ML_preparation_test_set",
    # results
    "get_mol_ML_results",
    "get_results",
]
