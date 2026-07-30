# QM-LUX — Quantum Molecular Learning with predicted UV-Vis for Xenotoxicity

[![Tests](https://github.com/bedapub/QM-LUX/actions/workflows/test.yml/badge.svg)](https://github.com/bedapub/QM-LUX/actions/workflows/test.yml)
[![Docker](https://github.com/bedapub/QM-LUX/actions/workflows/docker.yml/badge.svg)](https://github.com/bedapub/QM-LUX/actions/workflows/docker.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/bedapub/QM-LUX/releases/tag/v1.0.0)

QM-LUX predicts the phototoxicity of small molecules using UV-Vis spectra computed with quantum mechanics. The workflow combines 3D conformer generation (RDKit MMFF94s), conformational sampling with CREST/XTB, excited-state TD-DFT calculations with Gaussian, and an ML classifier trained on UV-Vis AUC descriptors, Morgan fingerprints, and RDKit physicochemical properties.

---

## Quick start

1. **Pull the image**

```bash
# Singularity (required for the Snakemake workflow)
singularity pull qm-lux.sif docker://ghcr.io/bedapub/qm-lux:1.0.0

# Docker (alternative for interactive use)
docker pull ghcr.io/bedapub/qm-lux:1.0.0
```

2. **Prepare input** — a CSV with `SRN` and `SMILES` columns (see [Configuration](#configuration))

3. **Phase 1** — conformer generation with CREST/XTB (runs inside the container)

```bash
cd workflow
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml xtb_conf <N_cores>
```

4. **Run Gaussian 16** on the generated `.gjf` input files — external step; see [Gaussian setup](#gaussian-setup)

5. **Phase 2** — UV-Vis descriptors, ML prediction, HTML report

```bash
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml all <N_cores>
```

Results appear in `<results_directory>/summary.csv` and a per-compound HTML report.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
  - [As a Python package](#as-a-python-package)
  - [Container image (Singularity / Docker)](#container-image-singularity--docker)
  - [Development install](#development-install)
- [Running with Snakemake (recommended)](#running-with-snakemake-recommended)
  - [Configuration](#configuration)
  - [Running locally (multi-core)](#running-locally-multi-core)
  - [Running on a SLURM cluster](#running-on-a-slurm-cluster)
  - [Two-phase execution and Gaussian](#two-phase-execution-and-gaussian)
  - [Workflow DAG](#workflow-dag)
- [Running with the CLI](#running-with-the-cli)
- [Python API](#python-api)
- [Providing a pre-trained model](#providing-a-pre-trained-model)
- [Output](#output)
  - [Snakemake HTML report](#snakemake-html-report)
- [Running tests](#running-tests)
- [Gaussian setup](#gaussian-setup)
- [Important notes](#important-notes)
- [Troubleshooting](#troubleshooting)
- [Contributors](#contributors)
- [Citation](#citation)
- [License](#license)

---

## Requirements

- **Singularity** ≥ 3.x (or Apptainer) **or Docker** — to run the pre-built image; Singularity is required for the Snakemake workflow, Docker can be used for interactive CLI use
- **Snakemake** ≥ 8 — workflow manager (on the host)
- **Gaussian 16** — commercial; required for the UV-Vis excitation step; runs on the host, not inside the image (see [Gaussian setup](#gaussian-setup))
- **Python 3.11** + [Poetry](https://python-poetry.org/) ≥ 1.8 — for installing `qm_lux` as a library or for development

---

## Installation

### As a Python package

`qm_lux` is distributed as a pre-built wheel attached to each [GitHub Release](https://github.com/bedapub/QM-LUX/releases).
No registry credentials are required once the repository is public.

> **Private repository:** If the repository has not yet been made public, the release asset URL
> requires a GitHub personal access token (PAT) with `repo` scope. Download the wheel via the
> GitHub API first, then install from the local file:
> ```bash
> curl -sL -H "Authorization: token $GITHUB_TOKEN" \
>      -H "Accept: application/octet-stream" \
>      "https://api.github.com/repos/bedapub/QM-LUX/releases/assets/<asset-id>" \
>      -o /tmp/qm_lux-1.0.0-py3-none-any.whl
> pip install /tmp/qm_lux-1.0.0-py3-none-any.whl
> ```

#### pip — direct wheel URL

```bash
pip install https://github.com/bedapub/QM-LUX/releases/download/v1.0.0/qm_lux-1.0.0-py3-none-any.whl
```

#### Poetry — URL dependency (pinned release)

```toml
# pyproject.toml
[tool.poetry.dependencies]
qm-lux = {url = "https://github.com/bedapub/QM-LUX/releases/download/v1.0.0/qm_lux-1.0.0-py3-none-any.whl"}
```

#### Poetry — git dependency (latest tag)

```toml
# pyproject.toml
[tool.poetry.dependencies]
qm-lux = {git = "https://github.com/bedapub/QM-LUX.git", tag = "v1.0.0"}
```

#### Verify the install

```python
import qm_lux
print(qm_lux.__version__)   # 1.0.0
print(qm_lux.__all__)       # list of public symbols
```

> **Note:** XTB, CREST, and Gaussian are not Python packages and are **not** installed by pip/Poetry.
> They are available inside the container image (XTB, CREST) or must be installed separately on the host (Gaussian).
> Use the container image (Singularity for Snakemake, Docker for interactive use) for the full end-to-end workflow.

---

### Container image (Singularity / Docker)

The image is a standard Docker image published to the GitHub Container Registry (GHCR) and rebuilt automatically on every push to `main`. It can be used with either Singularity or Docker.

**Singularity** is required for the Snakemake workflow (used via the `container:` directive). Singularity pulls the Docker image directly from GHCR and converts it to a `.sif` file.

**Docker** can be used for interactive CLI use on any system where Docker is available.

#### Singularity

```bash
# Authenticate — requires a GitHub personal access token (PAT) with read:packages scope
export SINGULARITY_DOCKER_USERNAME=<your-github-username>
export SINGULARITY_DOCKER_PASSWORD=<your-github-pat>

# Pull latest
singularity pull qm-lux.sif docker://ghcr.io/bedapub/qm-lux:latest

# Pin to a specific release tag for reproducibility
singularity pull qm-lux.sif docker://ghcr.io/bedapub/qm-lux:1.0.0
```

Verify the image:

```bash
singularity exec qm-lux.sif python -m qm_lux.cli --help
singularity exec qm-lux.sif snakemake --version
singularity exec qm-lux.sif xtb --version
singularity exec qm-lux.sif crest --version
```

Store the `.sif` file in a shared location and export its directory as `QM_LUX_SIF_DIR` before running `run.sh`:

```bash
export QM_LUX_SIF_DIR=/path/to/sif/dir
```

#### Docker

```bash
# Authenticate — requires a GitHub personal access token (PAT) with read:packages scope
echo <your-github-pat> | docker login ghcr.io -u <your-github-username> --password-stdin

# Pull latest
docker pull ghcr.io/bedapub/qm-lux:latest

# Pin to a specific release tag for reproducibility
docker pull ghcr.io/bedapub/qm-lux:1.0.0
```

Verify the image:

```bash
docker run --rm ghcr.io/bedapub/qm-lux:1.0.0 python -m qm_lux.cli --help
docker run --rm ghcr.io/bedapub/qm-lux:1.0.0 xtb --version
docker run --rm ghcr.io/bedapub/qm-lux:1.0.0 crest --version
```

---

### Development install

Use Poetry when you need to work on the package source code itself.
XTB and CREST are not available in the Poetry environment.

```bash
git clone https://github.com/bedapub/QM-LUX.git
cd QM-LUX
poetry env use 3.11
poetry install --with dev
poetry shell

# Run unit tests
pytest tests/unit/ -q
```

---

## Running with Snakemake (recommended)

The Snakemake workflow is the primary execution method. It handles job submission, checkpointing, and parallelism automatically. The `run.sh` script wraps both phases and passes Singularity arguments from the config file.

Ensure `snakemake` is in your `PATH` before calling `run.sh` — activate your conda environment or virtual environment first if needed.

### Configuration

Copy and adapt the example config from `workflow/config/config.yaml`:

```yaml
# workflow/config/my_run.yaml

input_file: resources/my_molecules.csv   # CSV with SRN and SMILES columns
results_directory: results_my_run

crest_threads: 8      # CPUs per CREST job
gaussian_threads: 24  # CPUs per Gaussian job (host-side)

qmlux_image: /path/to/qm-lux.sif   # absolute path to the local .sif file

# ML model — required keys (always set these)
model_method: RF
# Feature set identifier — must match the bundled model; do not change unless you retrain
model_descriptor: fp_Morganclean__descriptors_SMILES_CLEAN__100-1000

# ML model — sourcing (choose ONE of the three options below)
#
# Option 1: local directory — use if you already have model.sav + scaler.pkl on disk
#model_local_folder: /path/to/my/model_dir
#
# Option 2: GitHub release download — fetches the public model (internet access required)
model_github_url: https://github.com/bedapub/QM-LUX/releases/download/v1.0.0
#
# Option 3: Arvados Keep-web — set ARVADOS_API_TOKEN in your shell before running
#model_arv_uuid: <collection-uuid>
#model_arv_keepweb_url: https://collections.example.com
#model_arv_folder_name:   # leave empty if model files are at collection root

# Singularity bind mounts — REQUIRED for non-home paths
# Singularity does not auto-mount filesystems outside $HOME.
# List every top-level path the workflow reads from or writes to:
singularity_args_param: "--cleanenv --bind /tmp --bind /path/to/workdir"
```

The input CSV must have two columns (`SRN`, `SMILES`). Example:

```
SRN,SMILES
CPD-001,c1ccccc1
CPD-002,CC(=O)Oc1ccccc1C(=O)O
```

### Running locally (multi-core)

```bash
cd workflow

# Phase 1: conformer generation and CREST/XTB
QM_LUX_SIF_DIR=/path/to/sif/dir \
  ./scripts/run.sh config/my_run.yaml xtb_conf <N_cores>

# --- Gaussian runs externally here (see Two-phase section) ---

# Phase 2: UV-Vis descriptors, ML prediction, HTML report
QM_LUX_SIF_DIR=/path/to/sif/dir \
  ./scripts/run.sh config/my_run.yaml all <N_cores>
```

`run.sh` passes `singularity_args_param` from the config automatically. If `QM_LUX_SIF_DIR` is not set, it defaults to the repository root (two levels above `run.sh`), which is where `singularity pull` places `qm-lux.sif` by default.

### Running on a SLURM cluster

Omit the rule and cores arguments — `run.sh` detects this and switches to the SLURM profile:

```bash
cd workflow

# Phase 1 (submits CREST jobs via SLURM)
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml xtb_conf

# Phase 2 (after Gaussian finishes)
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml all
```

Adapt the per-rule SLURM resources in `workflow/profiles/slurm/config.yaml` to match your cluster:

```yaml
default-resources:
  qos: '15d'        # replace with your cluster QoS name
  mem_mb: 10000

set-resources:
  crest:
    qos: '15d'
    mem_mb: 20000
  gaussian_runner:
    qos: '15d'
    mem_mb: 100000
```

### Two-phase execution and Gaussian

The workflow splits into two Snakemake invocations because Gaussian (the TD-DFT engine) is commercial and cannot be bundled in the open-source image. The `gaussian_runner` rule has **no** `container:` directive and runs on the host.

```
Phase 1:  preparation → xtb_conf → [CREST/XTB inside container]
                                              ↓
                                  gaussian_preparation
                                              ↓
Gaussian: gaussian_runner  ← host Gaussian 16 required
                                              ↓
Phase 2:  uvvis → model → prediction → get_results → summarize_results
```

### Workflow DAG

| Rule | Container | Description |
|---|:---:|---|
| `preparation` | yes | Parse SMILES input; generate 3D conformers with RDKit MMFF94s |
| `xtb_conf` | yes | Prepare conformer SDF files for CREST input |
| `crest` | yes | Conformational sampling in implicit water; produces `crest_best.xyz` |
| `xtb` | yes | Single-point XTB energy on best conformer |
| `gaussian_preparation` | yes | Generate Gaussian `.gjf` input files |
| `gaussian_runner` | **no** | Run Gaussian TD-DFT (requires host Gaussian license) |
| `uvvis` | yes | Parse Gaussian output; compute AUC descriptors over four wavelength ranges |
| `model` | yes | Download pre-trained model |
| `prediction` | yes | Load model and scaler; output phototoxicity predictions |
| `get_results` | yes | Aggregate results into CSV + HTML report with molecular images |
| `summarize_results` | no | Write final `summary.csv` |

---

## Running with the CLI

The `qm-lux` CLI is the single entry point for all workflow steps. Run it inside the container using `singularity exec` (on HPC) or `docker run` (on workstations/cloud):

```bash
# Singularity
SIF=/path/to/qm-lux.sif
singularity exec $SIF python -m qm_lux.cli --help
singularity exec $SIF python -m qm_lux.cli data_preparation --help

# Docker (mount the current directory into /workdir)
IMG=ghcr.io/bedapub/qm-lux:1.0.0
docker run --rm -v "$(pwd)":/workdir -w /workdir $IMG python -m qm_lux.cli --help
docker run --rm -v "$(pwd)":/workdir -w /workdir $IMG python -m qm_lux.cli data_preparation --help
```

### Available subcommands

| Subcommand | Used by | Description |
|---|:---:|---|
| `data_preparation` | Snakemake + interactive | Parse SMILES input; generate 3D conformers |
| `xtb_conf` | Snakemake | Prepare conformer SDF files for CREST input |
| `xtb_runner` | interactive | Run xtb/CREST conformer search manually |
| `gaussian_preparation` | Snakemake + interactive | Generate Gaussian `.gjf` TD-DFT input files from XYZ geometry |
| `validate` | Snakemake | Validate CREST output file format (`crest_best.xyz` or `crest.out`) |
| `get_pred_UVvis` | Snakemake + interactive | Process Gaussian output; compute AUC descriptors |
| `prediction` | Snakemake + interactive | ML prediction (Snakemake mode: pass `--pkl`/`--csv`/`--srn`; interactive: auto-discovered) |
| `get_results` | Snakemake + interactive | Aggregate results into CSV + HTML (Snakemake mode: pass `--output`; interactive: auto-discovered) |

### Step-by-step manual run

Complete interactive prediction sequence with Singularity:

```bash
SIF=/path/to/qm-lux.sif

singularity exec $SIF python -m qm_lux.cli data_preparation -i molecules.csv
singularity exec $SIF python -m qm_lux.cli xtb_runner
singularity exec $SIF python -m qm_lux.cli gaussian_preparation
# --- Run Gaussian 16 on the generated .gjf files (host step) ---
singularity exec $SIF python -m qm_lux.cli get_pred_UVvis
singularity exec $SIF python -m qm_lux.cli prediction -i training_results/
singularity exec $SIF python -m qm_lux.cli get_results -t PRED
```

Or with Docker (bind-mounting the working directory):

```bash
IMG=ghcr.io/bedapub/qm-lux:1.0.0
RUN="docker run --rm -v $(pwd):/workdir -w /workdir $IMG"

$RUN python -m qm_lux.cli data_preparation -i molecules.csv
$RUN python -m qm_lux.cli xtb_runner
$RUN python -m qm_lux.cli gaussian_preparation
# --- Run Gaussian 16 on the generated .gjf files (host step) ---
$RUN python -m qm_lux.cli get_pred_UVvis
$RUN python -m qm_lux.cli prediction -i training_results/
$RUN python -m qm_lux.cli get_results -t PRED
```

---

## Python API

The `qm_lux` package exposes a stable public API for programmatic use:

```python
from qm_lux import (
    get_UV_vis_from_gaussian_output,
    extract_UV_gaussian_output,
    run_AUCs_spectra,
    ML_preparation_test_set,
)

# Parse Gaussian TD-DFT logs and write per-molecule .xy UV-Vis spectra
get_UV_vis_from_gaussian_output(base_dir)

# Read .xy files into a DataFrame (wavelength, epsilon, SRN columns)
df_uv = extract_UV_gaussian_output(base_dir)

# Compute AUC descriptors over four wavelength ranges
df_auc = run_AUCs_spectra(base_dir)

# Assemble the ML feature matrix (AUC descriptors + fingerprints + RDKit properties)
X = ML_preparation_test_set(df_auc, fp_df)
```

See `print(qm_lux.__all__)` for the full list of exported symbols.

---

## Providing a pre-trained model

The workflow requires two model files: `model.sav` (a pickled scikit-learn Random Forest) and `scaler.pkl` (a pickled `StandardScaler`). Three ways to provide them:

### Option 1 — Local directory (recommended for users with files on disk)

Point `model_local_folder` in your config to a directory containing both files:

```yaml
model_local_folder: /path/to/my/model_dir
```

### Option 2 — GitHub release download

A public model is distributed as a GitHub release asset. Set `model_github_url` to the base URL of the release (the workflow appends `/model.sav` and `/scaler.pkl`):

```yaml
model_github_url: https://github.com/bedapub/QM-LUX/releases/download/v1.0.0
```

Requires internet access from the node running the `model` rule.

### Option 3 — Arvados Keep-web

For Arvados users, set `ARVADOS_API_TOKEN` in your shell and point the config to your collection:

```yaml
model_arv_uuid: <collection-uuid>
model_arv_keepweb_url: https://collections.example.com
model_arv_folder_name:   # leave empty if model files are at collection root
```

### About the bundled model

The bundled model (v1.0.0) is a Random Forest classifier trained on an internal Roche phototoxicity reference dataset.

**Model file formats**

`model.sav` and `scaler.pkl` are plain Python `pickle` files. They do **not** store the descriptor name or the method label — those are config-only metadata.

| File | Object type | Key attributes |
|---|---|---|
| `model.sav` | `sklearn.ensemble.RandomForestClassifier` | `n_estimators=1200`, `max_depth=13`, `criterion="entropy"`, `class_weight="balanced"`, `min_samples_leaf=3`, `random_state=22`; `n_features_in_=1324`; `classes_=[0,1]` |
| `scaler.pkl` | `sklearn.preprocessing.StandardScaler` | `n_features_in_=1324` |

Both objects were serialised with scikit-learn 1.5.1. The container ships scikit-learn 1.5.0, which triggers a minor `InconsistentVersionWarning` on load; predictions are not affected in practice.

**Feature vector (1324 dimensions)**

`model_descriptor` in the config selects a column from the intermediate `test_set_with_fP_rdkit_prop_UVvis.pkl` file. The bundled value `fp_Morganclean__descriptors_SMILES_CLEAN__100-1000` names a column whose arrays have exactly 1324 elements — the concatenation of:

| Component | Dim | Details |
|---|:---:|---|
| `fp_Morganclean` | 1024 | Morgan circular fingerprint, radius 3, 1024 bits (RDKit `GetMorganFingerprintAsBitVect`) |
| `descriptors_SMILES_CLEAN` | 210 | Full RDKit 2D descriptor set (`rdkit.Chem.Descriptors._descList`) |
| `100-1000` | 90 | UV-Vis AUC integrals over 90 × 10 nm segments from 100 to 1000 nm (trapezoidal rule) |

**Compatibility rules for custom models**

- `model.sav` must be a scikit-learn estimator with `predict()` and `predict_proba()` methods; it must accept a 2D array with `n_features_in_` columns.
- `scaler.pkl` must be a scikit-learn transformer with `transform()`; it must expect the same number of features.
- `model_descriptor` must be a column name present in `test_set_with_fP_rdkit_prop_UVvis.pkl`; its array length must equal `model.n_features_in_`. A mismatch silently produces wrong results — the code does not validate this.
- `model_method` is a documentation label only; it is written as-is to the `ML_Method` column of the predictions CSV and is never validated against `model.sav`.
- Do not change `model_descriptor` unless you supply a retrained model trained on a matching feature set.

Performance metrics and training set details are reported in the accompanying manuscript (in preparation; see [Citation](#citation)).

---

## Output

The workflow produces two main outputs in `<results_directory>/`:

- **`summary.csv`** — one row per compound:
  - `SRN` — molecule identifier from the input CSV
  - `phototoxicity_label` — predicted class (`phototoxic` / `non-phototoxic`)
  - `probability` — ML classifier score (0–1; higher = more likely phototoxic)

- **HTML report** — interactive per-compound table with:
  - 2D structure images
  - UV-Vis absorption spectrum plots
  - Predicted label and probability score

Intermediate files (conformers, Gaussian output, AUC descriptor pickles) are preserved under `<results_directory>/` for inspection and re-use.

### Snakemake HTML report

`run.sh` automatically generates a self-contained HTML report after a successful full run (both phases). The report is written to `<results_directory>.html` in the `workflow/` directory.

To regenerate or produce a report with a custom filename:

```bash
cd workflow
bash scripts/run_report.sh config/my_run.yaml                    # writes report.html
bash scripts/run_report.sh config/my_run.yaml results_run1.html  # custom filename
```

The report is a single self-contained HTML file and includes:

| Section | Content |
|---|---|
| **Results** | Summary table (`summary.html`), per-compound prediction table with UV-Vis spectra (`results_ML_with_mol_UV.html`), UV-Vis AUC descriptor table (`UVvis.html`), failed-molecule list |
| **Workflow** | Interactive rule graph for both phases |
| **Home** | Workflow description, numbered pipeline steps, full references |

> The report requires the full workflow to have completed (including the Gaussian UV-Vis step). It will fail if Phase 2 outputs are missing.

---

## Running tests

### Unit tests

```bash
# With Poetry (preferred for development — no container required)
poetry run pytest tests/unit/ -q

# Inside the Singularity image — useful on HPC where the Poetry env is not available.
# PYTHONPATH puts your local checkout ahead of the copy installed in the image,
# so code changes are picked up without rebuilding.
cd /path/to/qm-lux          # repo root
singularity exec --cleanenv \
    --env PYTHONPATH=/src \
    --bind /path/to/qm-lux/src:/src \
    /path/to/qm-lux.sif \
    python -m pytest tests/unit/ -q

# Inside Docker — equivalent approach
cd /path/to/qm-lux          # repo root
docker run --rm \
    -e PYTHONPATH=/src \
    -v /path/to/qm-lux/src:/src \
    -v /path/to/qm-lux/tests:/app/tests \
    ghcr.io/bedapub/qm-lux:1.0.0 \
    python -m pytest tests/unit/ -q
```

All 294 tests must pass on a clean checkout.

### Integration test (full workflow)

End-to-end test using methane and ethane. Requires the Singularity image, Snakemake, and Gaussian 16 on the host.

```bash
bash tests/integration/run_full_test.sh /path/to/qm-lux.sif 24 /path/to/models/v1.0.0
```

The script runs both workflow phases and validates ML predictions against reference outputs (8 checks).

### Integration test (phase-1 only, no Gaussian)

```bash
cd workflow
bash ../tests/integration/run_phase1_test.sh /path/to/qm-lux.sif
```

Validates conformer generation for methane and ethane without Gaussian.

---

## Gaussian setup

Gaussian 16 is **not bundled in the container** (commercial license). It must be installed and accessible on the host running the `gaussian_runner` Snakemake rule.

### Activating Gaussian

The script `workflow/scripts/calculate_uvvis.sh` calls `g16` directly and requires it to be in `PATH`:

```bash
# Lmod / module system:
module load Gaussian/16.B.01

# Manual installation:
source /path/to/g16/bsd/g16.profile
```

Then run the workflow normally. For SLURM, load the module once before calling `run.sh` — Snakemake exports `PATH` to batch jobs.

The `gaussian_threads` config key (default `12`) controls the number of cores requested per Gaussian job.

### Scratch space

Gaussian writes large temporary files. Point `GAUSS_SCRDIR` to a fast scratch location:

```bash
export GAUSS_SCRDIR=/scratch/$USER
```

### Running without Gaussian

If you already have a `test_set_with_fP_rdkit_prop_UVvis.pkl` descriptor file, place it at `<results_directory>/data_ml/` and run phase 2 directly:

```bash
cd workflow
QM_LUX_SIF_DIR=/path/to/sif/dir \
  ./scripts/run.sh config/my_run.yaml all <N_cores>
```

Snakemake will skip any already-completed rules (including `gaussian_runner`) and proceed from the descriptor file.

---

## Important notes

**Singularity bind mounts**: Singularity only auto-mounts `$HOME`. Directories outside `$HOME` must be listed explicitly in `singularity_args_param`:

```yaml
singularity_args_param: "--cleanenv --bind /tmp --bind /scratch/myproject --bind /projects/shared"
```

**`PYTHONSAFEPATH=1`**: The container sets this env var to prevent the host working directory from shadowing the installed `qm_lux` package inside the container. For older images without this setting, pass `--env PYTHONSAFEPATH=1` in `singularity_args_param`.

**`PYTHONNOUSERSITE=1`**: The container also sets this. Singularity auto-mounts `$HOME`, so a stale `qm_lux` install in the caller's user site-packages (`~/.local`, or wherever `PYTHONUSERBASE` points) would otherwise be picked up and make `qm_lux.__version__` report the *host's* version rather than the image's. For older images without this setting, add `--env PYTHONNOUSERSITE=1` or use `--cleanenv`.

**Gaussian is a commercial dependency.** Users without Gaussian can skip to phase 2 if a pre-computed descriptor pickle is available.

**XTB / CREST** are open source and bundled in the container image (XTB 6.4.1, CREST 2.11.2). They are not installed in the Poetry development environment.

---

## Troubleshooting

**`FileNotFoundError` or directory not accessible inside the container**
Add the missing path to `singularity_args_param` in your config. Singularity only auto-mounts `$HOME`:

```yaml
singularity_args_param: "--cleanenv --bind /tmp --bind /path/to/missing/dir"
```

**`snakemake: command not found` when calling `run.sh`**
`run.sh` expects `snakemake` in your `PATH`. Activate your conda environment or virtual environment before calling the script.

**`g16: command not found` — `gaussian_runner` rule fails**
Gaussian 16 must be loaded on the host before running the workflow. See [Gaussian setup](#gaussian-setup).

**Container imports wrong version of `qm_lux`**
The container sets `PYTHONSAFEPATH=1` to prevent the host working directory from shadowing the installed package. If you are using an older image without this setting, add `--env PYTHONSAFEPATH=1` to `singularity_args_param`.

**`qm_lux.__version__` reports an unexpected version (e.g. `0.1.0`) or `unknown`**
Singularity auto-mounts `$HOME`, so a stale `qm_lux` install in your user site-packages can hijack the version metadata even though the *code* correctly comes from the image. Check with:

```bash
singularity exec --cleanenv qm-lux.sif python -c \
  "import qm_lux, importlib.metadata as m; \
   print(qm_lux.__version__, qm_lux.__file__, m.distribution('qm-lux')._path)"
```

If the reported metadata path is under your home directory, the image is fine and your environment is leaking in — run with `--cleanenv` (or `--env PYTHONNOUSERSITE=1`), and consider removing the stale install with `pip uninstall qm-lux`. A report of `unknown` means the image predates the in-image `pip install` fix; the code still works, only the version string is unavailable.

**SLURM jobs fail with memory errors**
Increase `mem_mb` for the failing rule in `workflow/profiles/slurm/config.yaml`. CREST typically needs 20 GB; Gaussian can require 100 GB or more depending on molecule size.

---

## Contributors

- Nicolò Milani (development, validation, data analysis), PMDA, PS
- Andrea Anelli (UV-Vis prediction), pCMC, TMo
- Michael Reutlinger (technical and scientific support), MedChem CADD, TMo
- Roland Schmucki (Snakemake implementation), PMDA, PS

For bug reports and feature requests, please open an issue on [GitHub](https://github.com/bedapub/QM-LUX/issues).

---

## Citation

Manuscript in preparation. If you use QM-LUX in your research, please cite this repository:

```
QM-LUX: Quantum Molecular Learning with predicted UV-Vis for Xenotoxicity.
https://github.com/bedapub/QM-LUX
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
