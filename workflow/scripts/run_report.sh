#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
# Generate a Snakemake HTML report for a completed QM-LUX run.
#
# Usage (from the workflow/ directory):
#   bash scripts/run_report.sh <config.yaml> [output.html]
#
# <config.yaml>  — the same config file passed to run.sh
# [output.html]  — report filename (default: report.html)
#
# Requires that the workflow has already completed successfully.
# The report embeds all registered outputs (failed_molecules.txt) and the
# global description from report/description.rst.

set -euo pipefail

function usage() {
    echo ""
    echo "Usage: $0 <config.yaml> [output.html]"
    echo ""
    echo "  config.yaml   — config file used for the completed run"
    echo "  output.html   — report output file (default: report.html)"
    echo ""
}

if [[ $# -lt 1 ]]; then usage && exit 1; fi

config_file=$1
report_file="${2:-report.html}"

if [ ! -e "$config_file" ]; then
    echo "Error: config file '$config_file' not found."
    exit 1
fi

echo "Generating Snakemake report -> $report_file"
snakemake --snakefile Snakefile \
          --configfile "$config_file" \
          --report "$report_file"

# Reorder navigation: Results first, then Workflow / Statistics / About.
# Snakemake 9 hardcodes Workflow→Statistics→About→[categories] in menu.js;
# we patch the embedded JS in the self-contained HTML.
python3 - "$report_file" << 'PYEOF'
import sys, pathlib

p = pathlib.Path(sys.argv[1])
html = p.read_text()

OLD = (
    'this.getMenuItem("Workflow", "share", this.showWorkflow),\n'
    '            this.getMenuItem("Statistics", "chart", this.showStatistics),\n'
    '            this.getMenuItem("About", "information-circle", this.props.app.showReportInfo),\n'
    '            this.getCategoryMenumitems()'
)
NEW = (
    'this.getCategoryMenumitems(),\n'
    '            this.getMenuItem("Workflow", "share", this.showWorkflow),\n'
    '            this.getMenuItem("Statistics", "chart", this.showStatistics),\n'
    '            this.getMenuItem("About", "information-circle", this.props.app.showReportInfo)'
)

if OLD in html:
    p.write_text(html.replace(OLD, NEW, 1))
    print("Nav reordered: Results → Workflow → Statistics → About")
else:
    print("Warning: nav patch not applied (template may have changed)")
PYEOF

# Reorder files within the Results section.
# Snakemake sorts entries lexicographically by path in abstract_results.js;
# we replace that sort with one that uses an explicit basename priority list.
python3 - "$report_file" << 'PYEOF'
import sys, pathlib

p = pathlib.Path(sys.argv[1])
html = p.read_text()

OLD_SORT = (
    'entryLabelValues = entryLabelValues.sort(function (aLabels, bLabels) {\n'
    '            // sort labels lexicographically, first element is the most important\n'
    '            for (let i = 0; i < aLabels.length; i++) {\n'
    '                let comparison = aLabels[i].localeCompare(bLabels[i]);\n'
    '                if (comparison !== 0) {\n'
    '                    return comparison;\n'
    '                }\n'
    '            }\n'
    '            return 0;\n'
    '        })'
)
NEW_SORT = (
    'entryLabelValues = entryLabelValues.sort(function (aLabels, bLabels) {\n'
    '            var _ORD = ["summary.html","results_ML_with_mol_UV.html","UVvis.html","failed_molecules.html"];\n'
    '            function _key(ls) { var n = ls[0].split("/").pop(); var i = _ORD.indexOf(n); return i === -1 ? _ORD.length : i; }\n'
    '            var _d = _key(aLabels) - _key(bLabels); if (_d !== 0) return _d;\n'
    '            // sort labels lexicographically, first element is the most important\n'
    '            for (let i = 0; i < aLabels.length; i++) {\n'
    '                let comparison = aLabels[i].localeCompare(bLabels[i]);\n'
    '                if (comparison !== 0) {\n'
    '                    return comparison;\n'
    '                }\n'
    '            }\n'
    '            return 0;\n'
    '        })'
)

if OLD_SORT in html:
    p.write_text(html.replace(OLD_SORT, NEW_SORT, 1))
    print("Results order: summary → results_ML_with_mol_UV → UVvis → failed_molecules")
else:
    print("Warning: sort patch not applied (template may have changed)")
PYEOF

# Show only file basenames in the Results left panel.
# When a result has no explicit labels Snakemake falls back to the full output
# path; we replace [path] with [path.split("/").pop()] so the panel shows
# "summary.html" instead of "/projects/.../summary.html".
python3 - "$report_file" << 'PYEOF'
import sys, pathlib

p = pathlib.Path(sys.argv[1])
html = p.read_text()

OLD = '} else {\n                entryLabels = [path];\n            }'
NEW = '} else {\n                entryLabels = [path.split("/").pop().replace(/\\.html$/, "")];\n            }'

if OLD in html:
    p.write_text(html.replace(OLD, NEW, 1))
    print("Results labels: full paths replaced with basenames (no .html extension)")
else:
    print("Warning: basename patch not applied (template may have changed)")
PYEOF

echo "Done. Report written to: $report_file"
