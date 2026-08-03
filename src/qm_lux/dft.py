# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Backward-compatibility shim — use :mod:`qm_lux.utils.gaussian` directly.

Only :func:`~qm_lux.utils.gaussian.get_UV_vis_from_gaussian_output` is
re-exported here, for the historical ``from qm_lux.dft import ...`` spelling.
The rest of the module's public API — ``extract_UV_gaussian_output``,
``create_input_with_charge``, ``sum_gauss``, ``parse_output`` — is reachable
only from :mod:`qm_lux.utils.gaussian` or the :mod:`qm_lux` top-level package.
"""

from qm_lux.utils.gaussian import get_UV_vis_from_gaussian_output  # noqa: F401
