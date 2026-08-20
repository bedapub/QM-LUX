#!/usr/bin/env python3
"""Regenerate THIRD_PARTY_LICENSES.md from a built QM-LUX container image.

The inventory is read out of the image rather than out of ``environment.yml``
because the two are not the same list: conda resolves a long transitive tree,
and some of what it pulls in carries obligations the direct pins do not imply
(Qt via matplotlib, MySQL client libraries via Qt, Intel MKL via the OpenBLAS
build of libblas). Hand-maintaining the list is how components go unrecorded.

Run it inside the image, from the repository root::

    singularity exec --cleanenv qm-lux.sif python tools/gen_third_party_licenses.py \
        > THIRD_PARTY_LICENSES.md

    # or, with Docker
    docker run --rm -v "$PWD:/w" -w /w ghcr.io/bedapub/qm-lux:1.0.0 \
        python tools/gen_third_party_licenses.py > THIRD_PARTY_LICENSES.md

``--cleanenv`` matters: without it a host ``PYTHONPATH``/``PYTHONUSERBASE`` can
leak host site-packages into the scan and record distributions the image does
not actually ship.

Licence strings are reported verbatim as the packager declared them. They are
an index for a legal review, not a substitute for one.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from importlib import metadata as md

ENV = "/opt/conda/envs/qmlux"

# Licences that impose an obligation beyond simple attribution, or that are not
# OSI-approved at all. Matched against the declared licence string.
COPYLEFT = re.compile(r"\b(A?GPL|LGPL|MPL|EPL|CDDL|OSL|EUPL)", re.I)
NON_OSI = re.compile(r"LicenseRef|Proprietary", re.I)


def collect() -> dict[str, tuple[str, str, str]]:
    """Return {name: (version, licence, source)} for everything in the image."""
    rows: dict[str, tuple[str, str, str]] = {}

    for path in glob.glob(f"{ENV}/conda-meta/*.json"):
        try:
            d = json.load(open(path))
        except (OSError, ValueError):
            continue
        rows[d["name"]] = (d["version"], (d.get("license") or "UNSPECIFIED").strip(), "conda")

    # pip-installed distributions (arvados-python-client and its dependencies)
    seen = {r.lower().replace("-", "_") for r in rows}
    for dist in md.distributions():
        try:
            name, ver = dist.metadata["Name"], dist.version
        except Exception:  # noqa: BLE001 - a broken dist-info must not abort the scan
            continue
        if not name or name.lower().replace("-", "_") in seen:
            continue
        lic = dist.metadata.get("License") or ""
        # Some wheels dump the entire licence text into the License field.
        if not lic or len(lic) > 60 or "\n" in lic:
            classifiers = [
                c for c in (dist.metadata.get_all("Classifier") or []) if c.startswith("License ::")
            ]
            if classifiers:
                lic = classifiers[-1].split(" :: ")[-1]
            elif lic:
                lic = lic.splitlines()[0][:60]
            else:
                lic = "UNSPECIFIED"
        rows[name] = (ver, lic.strip(), "pip")

    return rows


def main() -> int:
    rows = collect()
    if not rows:
        print(f"error: no packages found under {ENV} — run this inside the image", file=sys.stderr)
        return 1

    notable = {
        n: v for n, v in rows.items() if COPYLEFT.search(v[1]) or NON_OSI.search(v[1])
    }

    out = sys.stdout
    w = out.write

    w("# Third-party components redistributed in the QM-LUX container image\n\n")
    w(
        "**Generated file — do not edit by hand.** Regenerate with "
        "`tools/gen_third_party_licenses.py`; see that file's docstring for the exact "
        "command. Re-run it after any change to `environment.yml` or the `Dockerfile`.\n\n"
    )
    w(
        "QM-LUX's own source is Apache-2.0 (see [LICENSE](LICENSE)). The published image\n"
        "`ghcr.io/bedapub/qm-lux` additionally **redistributes** the components below.\n"
        "Attribution notices required by their licences are in [NOTICE](NOTICE).\n\n"
    )
    w(
        "Gaussian 16 is **not** listed: it is commercial, is not in the image, and runs\n"
        "against the user's own licensed installation on the host.\n\n"
    )
    w(f"Components: **{len(rows)}** total, of which **{len(notable)}** carry a copyleft or\n")
    w("non-OSI licence and are listed separately first.\n\n")

    w("## Components with copyleft or non-OSI licences\n\n")
    w("| Component | Version | Declared licence | Packaged as |\n")
    w("|---|---|---|---|\n")
    for n in sorted(notable, key=str.lower):
        ver, lic, src = notable[n]
        w(f"| `{n}` | {ver} | {lic} | {src} |\n")

    w("\n## Full inventory\n\n")
    w("| Component | Version | Declared licence |\n")
    w("|---|---|---|\n")
    for n in sorted(rows, key=str.lower):
        ver, lic, _ = rows[n]
        w(f"| `{n}` | {ver} | {lic} |\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
