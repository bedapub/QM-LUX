# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Backward-compatibility shim — use :mod:`qm_lux.xtb` directly."""

from qm_lux.xtb import (  # noqa: F401
    generate_conf_xtb,
    get_conf_MMFF_opt,
    get_energy_conf,
    get_info_mol,
    sdf_run,
    write_SDF,
)
