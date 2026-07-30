# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Backward-compatibility shim — use :mod:`qm_lux.utils.gaussian` directly.

All public functions in that module:
:func:`~qm_lux.utils.gaussian.get_UV_vis_from_gaussian_output`,
:func:`~qm_lux.utils.gaussian.extract_UV_gaussian_output`,
:func:`~qm_lux.utils.gaussian.create_input_with_charge`,
:func:`~qm_lux.utils.gaussian.sum_gauss`,
:func:`~qm_lux.utils.gaussian.parse_output`.
"""

from qm_lux.utils.gaussian import get_UV_vis_from_gaussian_output  # noqa: F401
