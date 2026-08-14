# QM-LUX — Quantum Molecular Learning with predicted UV-Vis for Xenotoxicity

[![Tests](https://github.com/bedapub/QM-LUX/actions/workflows/test.yml/badge.svg)](https://github.com/bedapub/QM-LUX/actions/workflows/test.yml)
[![Docker](https://github.com/bedapub/QM-LUX/actions/workflows/docker.yml/badge.svg)](https://github.com/bedapub/QM-LUX/actions/workflows/docker.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/bedapub/QM-LUX/releases/tag/v1.0.0)

QM-LUX predicts the phototoxicity of small molecules using UV-Vis spectra computed with quantum mechanics. The workflow combines 3D conformer generation (RDKit MMFF94s), conformational sampling with CREST/XTB, excited-state TD-DFT calculations with Gaussian, and an ML classifier trained on UV-Vis AUC descriptors, Morgan fingerprints, and RDKit physicochemical properties.

---

## Quick start

1. **Clone the repository**

```bash
git clone https://github.com/bedapub/QM-LUX.git
cd QM-LUX
```

The image ships the `qm_lux` Python package only — it does **not** contain the Snakemake workflow. `run.sh`, the `Snakefile` and the example configs come from this repository, and Snakemake runs on the host and bind-mounts your working directory into the container. You need both the clone and the image.

2. **Pull the image**

```bash
# Singularity (required for the Snakemake workflow)
singularity pull qm-lux.sif docker://ghcr.io/bedapub/qm-lux:1.0.0

# Docker (alternative for interactive use)
docker pull ghcr.io/bedapub/qm-lux:1.0.0
```

3. **Prepare input** — a CSV with `SRN` and `SMILES` columns (see [Configuration](#configuration))

4. **Run the workflow** — one command runs everything: conformer generation, CREST/XTB, Gaussian TD-DFT, UV-Vis descriptors, ML prediction and the HTML report.

```bash
cd workflow

# on a SLURM cluster
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml

# or locally, on N cores
QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml --cores <N>
```

Results appear in `<results_directory>/summary.csv` and a per-compound HTML report.

> Gaussian 16 must be installed and on your `PATH` — it is commercial and cannot be shipped in the image. You do **not** run it yourself: `run.sh` invokes it as part of the workflow. See [Gaussian setup](#gaussian-setup).

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
    - [Other schedulers](#other-schedulers)
  - [How the DAG is built](#how-the-dag-is-built)
  - [Workflow DAG](#workflow-dag)
- [Running with the CLI](#running-with-the-cli)
- [Providing a pre-trained model](#providing-a-pre-trained-model)
- [Output](#output)
  - [Snakemake HTML report](#snakemake-html-report)
- [Running tests](#running-tests)
- [Gaussian setup](#gaussian-setup)
- [Important notes](#important-notes)
- [Troubleshooting](#troubleshooting)
- [Support](#support)
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

Ensure `snakemake` is in your `PATH` before calling `run.sh` — activate your conda environment or virtual environment first if needed. `run.sh` checks for it and exits with a clear message if it is missing.

#### `run.sh` arguments

```
./scripts/run.sh <config.yaml> [--cores N] [--target RULE]
```

| Option | Effect |
|---|---|
| *(none)* | Run the complete pipeline, submitted through the SLURM profile |
| `--cores N` | Run **locally** on `N` cores instead of submitting to SLURM |
| `--target RULE` | Stop after `RULE` instead of running everything (debugging) |
| `-h`, `--help` | Show usage and exit |

The two forms you normally need — both run the **complete** pipeline, Gaussian included:

```bash
./scripts/run.sh config/my_run.yaml              # cluster
./scripts/run.sh config/my_run.yaml --cores 8    # local, 8 cores
```

**`--cores` is what selects a local run**; without it the run goes through the SLURM profile. `--target all` means the full pipeline and is identical to omitting `--target`.

Stopping early is a debugging affordance, not part of normal use:

```bash
./scripts/run.sh config/my_run.yaml --target xtb_conf             # cluster
./scripts/run.sh config/my_run.yaml --target xtb_conf --cores 8   # local
```

Options may be given in any order. `--cores=8` and `--target=xtb_conf` are also accepted.

Three environment variables adjust behaviour:

| Variable | Effect |
|---|---|
| `QM_LUX_SIF_DIR` | Directory containing `qm-lux.sif` (default: repository root) |
| `QM_LUX_CLUSTER_PROFILE` | Snakemake workflow profile for a cluster run (default: `profiles/slurm`) — see [Other schedulers](#other-schedulers) |
| `QM_LUX_NO_AUTO_BIND` | Set to `1` to disable deriving Singularity `--bind` mounts from the config — see [Automatic bind mounts](#automatic-bind-mounts) |

The HTML report is generated for a complete run only; a run that stops at an intermediate rule has no predictions to report on, and the report step is skipped.

> **Positional arguments still work.** The older `run.sh <config.yaml> [target] [cores]` form is unchanged, so existing scripts and cluster job files keep working: `./scripts/run.sh config/my_run.yaml xtb_conf 8` is the same as `--target xtb_conf --cores 8`, and a lone number is read as the core count (`./scripts/run.sh config/my_run.yaml 8`). Mixing the two forms for the *same* value is rejected rather than silently resolved.

### Configuration

Copy and adapt the example config from `workflow/config/config.yaml`:

```yaml
# workflow/config/my_run.yaml

input_file: resources/my_molecules.csv   # CSV with SRN and SMILES columns
results_directory: results_my_run

crest_threads: 8      # CPUs per CREST job
gaussian_threads: 24  # CPUs per Gaussian job (host-side)
gaussian_mem_gb: 20   # memory per Gaussian job, in GB (optional; default 20)

qmlux_image: /path/to/qm-lux.sif   # absolute path to the local .sif file

# Stereochemistry — NO (default) enumerates all diastereoisomers of unassigned
# chiral centres. YES is the exceptional case: it keeps the stereo assignment
# given in the input, drops compounds with more than one unassigned chiral
# centre, and skips compounds already listed in chirality_current_df (required
# with YES, ignored with NO).
# Quote the value — unquoted YAML NO/YES are booleans, not strings.
chirality_check: "NO"
#chirality_current_df: /path/to/already_processed.pkl

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

# Singularity bind mounts
# run.sh derives mounts for the paths named above (input_file, results_directory,
# model_local_folder, qmlux_image), so you normally only need extra entries here.
# Anything you do list is kept as given and is never overridden:
singularity_args_param: "--cleanenv --bind /tmp"
```

The input CSV must have two columns (`SRN`, `SMILES`). Example:

```
SRN,SMILES
CPD-001,c1ccccc1
CPD-002,CC(=O)Oc1ccccc1C(=O)O
```

### Running locally (multi-core)

Pass the number of cores. That single command runs the whole pipeline — conformer generation, CREST/XTB, Gaussian, UV-Vis descriptors, prediction and the HTML report:

```bash
cd workflow

QM_LUX_SIF_DIR=/path/to/sif/dir \
  ./scripts/run.sh config/my_run.yaml --cores <N>
```

Gaussian must be on your `PATH` (see [Gaussian setup](#gaussian-setup)); `run.sh` calls it for you.

`run.sh` passes `singularity_args_param` from the config automatically. If `QM_LUX_SIF_DIR` is not set, it defaults to the repository root (two levels above `run.sh`), which is where `singularity pull` places `qm-lux.sif` by default.

#### Automatic bind mounts

A container sees only what is bound into it, so a configured path outside your working directory is invisible to the workflow unless it is mounted. `run.sh` therefore derives bind mounts from the paths the config already names — `input_file`, `results_directory`, `model_local_folder`, `chirality_current_df` and `qmlux_image` — and appends them to `singularity_args_param`. It prints what it added:

```
Auto-bound from config/my_run.yaml: /data/projects/qmlux
```

Details worth knowing:

- **Your `singularity_args_param` is authoritative.** It is only ever appended to, never rewritten, and a derived path already covered by one of your `--bind` entries (or by the working directory, which Snakemake mounts as the container home) is skipped rather than repeated. Both `--bind a,b` and `--bind=a` are recognised.
- **File-valued keys contribute their directory**, directory-valued keys contribute themselves. Paths sharing a parent collapse to a single mount.
- **Paths are resolved before binding**, so a checkout reached through a symlink still mounts correctly.
- **A path that does not exist yet** — `results_directory` before the first run — is walked up to its nearest existing ancestor. This matters: Singularity treats a missing bind source as fatal (`container creation failed: ... mount source ... doesn't exist`), not as something to skip.
- **URL-valued keys are ignored** (`model_github_url`, `model_arv_keepweb_url`), as is anything that is not a path.
- Set `QM_LUX_NO_AUTO_BIND=1` to disable the derivation and rely solely on `singularity_args_param`.

> Some sites mount shared filesystems for every container via `bind path` entries in `singularity.conf`, which hides missing mounts until someone runs the same config elsewhere. The derivation makes a config work regardless of that site configuration. Paths containing spaces are not supported.

### Running on a SLURM cluster

Omit the **cores** argument — `run.sh` detects this and switches to the SLURM profile. Everything else is identical; it is still one command for the whole pipeline:

```bash
cd workflow

QM_LUX_SIF_DIR=/path/to/sif/dir ./scripts/run.sh config/my_run.yaml
```

Snakemake submits each rule as its own SLURM job, including `gaussian_runner`, so Gaussian must be available on the **compute** nodes rather than on the submit node.

This requires [`snakemake-executor-plugin-slurm`](https://github.com/snakemake/snakemake-executor-plugin-slurm). Without it the run stops immediately with `--executor/-e: invalid choice: 'slurm'`; `run.sh` prints a warning naming the plugin before that happens.

Adapt the per-rule SLURM resources in `workflow/profiles/slurm/config.yaml` to match your cluster:

```yaml
executor: slurm     # keep — this is what sends jobs to the scheduler

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

#### Other schedulers

The bundled profile targets SLURM, but cluster mode is not limited to it. Install the executor plugin for your scheduler, copy `workflow/profiles/slurm` , change `executor:` to match, and point `QM_LUX_CLUSTER_PROFILE` at the copy:

```bash
QM_LUX_CLUSTER_PROFILE=/path/to/my/profile ./scripts/run.sh config/my_run.yaml
```

`run.sh` checks the directory contains a `config.yaml` and exits with an actionable message if not.

> **A site-wide profile does not decide local vs. cluster.** Some clusters ship a Snakemake module that sets `SNAKEMAKE_PROFILE` globally with `executor: slurm` in it, which would otherwise apply to *every* invocation on that host — including one you asked to run locally. `run.sh` passes `--executor local` in local mode so `--cores N` always means what it says.

### How the DAG is built

**You do not need this section to use QM-LUX** — one `run.sh` call makes one Snakemake invocation that runs everything. It documents an implementation detail that matters only if you invoke `snakemake` directly instead of through `run.sh`, or if you edit the Snakefile.

```
preparation → xtb_conf ⇢ crest → … per-molecule rules … → uvvis → … → all
                        ↑
                 the checkpoint
```

(`⇢` is the checkpoint boundary; the [Workflow DAG](#workflow-dag) below has the complete graph.)

**Gaussian is not a manual step.** `gaussian_runner` is an ordinary rule, scheduled by Snakemake like any other. What is special about it is only that it has **no** `container:` directive — Gaussian is commercial and cannot be bundled in the open-source image, so the rule executes against your own licensed installation on the host. That is a packaging constraint, nothing more.

**Why `xtb_conf` is a checkpoint** — the `⇢` above. `rule uvvis` does not name its inputs; it discovers them by listing the per-molecule directories under `<results_directory>/data_ml/0/`, which `xtb_conf` creates, one per molecule:

```python
checkpoints.xtb_conf.get(**wildcards)          # wait for xtb_conf, then re-plan
return list_directories(os.path.join(outdir, "data_ml", "0"))
```

Snakemake normally evaluates a rule's inputs while **building the DAG**, before anything has run. On a cold run those directories do not exist yet, so the listing would return nothing and the DAG would come out with `crest`, `xtb`, `gaussian_preparation` and `gaussian_runner` **missing entirely** and `uvvis` holding no inputs — failing at `uvvis`.

Declaring `xtb_conf` a [checkpoint](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#data-dependent-conditional-execution) is what fixes this: Snakemake pauses after it completes and **re-plans the rest of the DAG** against the directories that now exist. That is why the listing lives in an input function rather than inline in the rule body.

> **Do not downgrade `xtb_conf` to a plain `rule`.** Earlier versions did, and `run.sh` had to compensate by making *two* Snakemake invocations back to back — the second process re-read the directory listing that the first had populated. Reverting the keyword silently reintroduces the truncated DAG.

**`data_ml/` is a `params`, not an `output`.** `rule preparation` creates `<results_directory>/data_ml/` and declares the two files it writes there (`xtb_input.pkl`, `input.csv`) as outputs — but not the directory itself. It must not: that directory is also where every later per-molecule rule writes, so declaring `directory(data_ml)` would make `preparation` the declared owner of `crest`'s temporary `crest/` directory and `uvvis`'s `UV_plots/` as well, and Snakemake rejects such a DAG with `ChildIOException`. Under the old two-invocation split `preparation` and `uvvis` never appeared in the same DAG, so the clash never surfaced; with a single invocation it does. Nothing changes on disk — the directory is still created and its real products are still tracked.

### Workflow DAG

![Rule graph: preparation and xtb_conf, then a dashed checkpoint edge to crest, which branches into xtb and gaussian_preparation, through gaussian_runner into uvvis, joined by model into prediction, get_results, summarize_results and report_tables, ending at all](docs/dag.png)

The dashed edge is the `xtb_conf` checkpoint (see [How the DAG is built](#how-the-dag-is-built)). It is drawn differently because it is not an ordinary file dependency: `xtb_conf` writes the per-molecule `.sdf` files that `crest` consumes but does not declare them as outputs, so the link only comes into existence when Snakemake re-plans the DAG after the checkpoint completes.

That is also why `snakemake --rulegraph` cannot draw this graph in one piece. `--rulegraph` is static — it plans without executing, so it cannot expand the checkpoint, and it shows either the pre-checkpoint half or the post-checkpoint half depending on what is already on disk:

```bash
cd workflow
# cold directory -> preparation, xtb_conf, and the post-uvvis tail
snakemake --rulegraph | dot -Tpng -Grankdir=LR > /tmp/dag_pre.png
# directory where xtb_conf has completed but the per-molecule rules have not
# -> crest, xtb, gaussian_preparation, gaussian_runner, uvvis and the tail
snakemake --rulegraph | dot -Tpng -Grankdir=LR > /tmp/dag_post.png
```

`docs/dag.png` is the union of the two, with the checkpoint edge added.

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
| `report_tables` | no | Render `summary.csv`, `UVvis.csv` and the failed-molecule list as HTML for the Snakemake report |

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

> The `model` rule runs **inside** the container, and the recommended `singularity_args_param` includes `--cleanenv`, which strips the host environment — so a plain exported variable does not reach the rule. `run.sh` handles this by re-exporting the token as `SINGULARITYENV_ARVADOS_API_TOKEN`, which Singularity forwards even under `--cleanenv`. If you invoke `snakemake` directly instead of through `run.sh`, export that prefixed name yourself (or drop `--cleanenv`), otherwise the rule fails on an unset variable.

### About the bundled model

The bundled model (v1.0.0) is a Random Forest classifier trained on an internal phototoxicity reference dataset that is not distributed with this repository.

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

> The report requires the full workflow to have completed (including the Gaussian UV-Vis step). It will fail if the prediction outputs are missing.

---

## Running tests

### Unit tests

Unit tests can be run either in the Poetry development environment or inside the
container image, which ships `pytest`. The `tests/` tree itself is not copied
into the image — bind-mount a checkout instead, as shown below.

```bash
# Set up the development environment once (see Development install)
poetry install --with dev

# Run the unit tests
poetry run pytest tests/unit/ -q
```

Inside the Singularity image — useful on HPC where the Poetry environment is not
available. Singularity bind-mounts the current working directory by default, so
running from the repository root is enough:

```bash
cd /path/to/qm-lux          # repo root
singularity exec /path/to/qm-lux.sif python -m pytest tests/unit/ -q
```

This exercises the copy of `qm_lux` installed *in the image*, not the checkout —
which is usually what you want when validating an image. To test local source
changes without rebuilding, put your checkout ahead of the installed copy:

```bash
singularity exec --env PYTHONPATH=/src --bind "$PWD/src:/src" \
    /path/to/qm-lux.sif python -m pytest tests/unit/ -q
```

Inside Docker the working directory is not mounted automatically, so both the
tests and (optionally) the source must be passed explicitly:

```bash
cd /path/to/qm-lux          # repo root
docker run --rm -v "$PWD/tests:/app/tests" -w /app \
    ghcr.io/bedapub/qm-lux:1.0.0 python -m pytest tests/unit/ -q
```

All 344 tests must pass on a clean checkout.

### Command-line tests for `run.sh`

`run.sh` is shell, so the Python unit tests do not cover it. This suite drives it
directly against a stub `snakemake` placed on `PATH`, checking every argument
path, both run modes, the derived Singularity bind mounts and the environment
forwarding — without running a single real job. It needs only Bash, `python3`
and coreutils: no Snakemake, no Singularity, no Gaussian, and it finishes in
seconds, so it runs in CI on every push.

```bash
bash tests/cli/test_run_sh.sh
```

### Integration test (full workflow)

End-to-end test using methane and ethane. Requires the Singularity image, Snakemake, and Gaussian 16 on the host.

```bash
bash tests/integration/run_full_test.sh /path/to/qm-lux.sif 24 /path/to/models/v1.0.0
```

The script runs both workflow phases and validates ML predictions against reference outputs (8 checks).

### Integration test (stage 1 only, no Gaussian)

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
# Environment-module system (Lmod / Environment Modules) — the module name is
# site-specific; ask your administrator or check `module avail gaussian`:
module load <your-site-gaussian-module>

# Manual installation:
source /path/to/g16/bsd/g16.profile
```

Then run the workflow normally. For SLURM, load the module once before calling `run.sh` — Snakemake exports `PATH` to batch jobs.

`run.sh` warns if `g16` is not in `PATH` when the requested target could reach `gaussian_runner`. The warning is **not** fatal: on a cluster the rule executes on a compute node, which may provide `g16` even when the submit node does not. Targets that never reach `gaussian_runner` (such as `xtb_conf`) do not trigger it.

#### Gaussian resources

Two config keys control what a Gaussian job gets:

| Key | Default | Sets |
|---|---|---|
| `gaussian_threads` | `24` | `%nprocshared` in the `.gjf` **and** the scheduler's CPU request |
| `gaussian_mem_gb` | `20` | `%mem` in the `.gjf`; the scheduler is asked for 25% more (4 GB minimum) |

Both numbers reach Gaussian through the `.gjf` header written by `gaussian_preparation`, because Gaussian reads `%mem`/`%nprocshared` in preference to `GAUSS_MDEF`/`GAUSS_PDEF` and to the `g16 -m=`/`-p=` flags. Setting either key therefore changes the request *and* what the job actually uses; they cannot drift apart.

The scheduler reservation is deliberately larger than `%mem` — Gaussian's resident set is the `%mem` pool plus executable, basis-set and per-link overhead, so an allocation of exactly `%mem` risks an OOM kill. Set `gaussian_mem_gb` to the largest `%mem` your nodes can host with that headroom.

One case the config keys cannot cover on their own: Snakemake lowers a rule's `threads` to fit `--cores`, so a local run with `--cores 4` and `gaussian_threads: 24` allocates 4 cores while the `.gjf` — written earlier by `gaussian_preparation` — asks for 24. `calculate_uvvis.sh` therefore caps `%nprocshared` to the cores actually allocated, on a copy, leaving the `.gjf` on disk untouched. It reports the cap on stdout, so it shows up in the rule's log. A `%mem` mismatch is warned about but not changed, since nothing lowers the memory reservation the way `--cores` lowers threads.

### Scratch space

Gaussian writes large temporary files. Point `GAUSS_SCRDIR` to a fast scratch location:

```bash
export GAUSS_SCRDIR=/scratch/$USER
```

### Running without Gaussian

If you already have a `test_set_with_fP_rdkit_prop_UVvis.pkl` descriptor file, place it at `<results_directory>/data_ml/` and run the downstream rules directly:

```bash
cd workflow
QM_LUX_SIF_DIR=/path/to/sif/dir \
  ./scripts/run.sh config/my_run.yaml --cores <N>
```

Snakemake will skip any already-completed rules (including `gaussian_runner`) and proceed from the descriptor file.

---

## Important notes

**Singularity bind mounts**: Singularity only auto-mounts `$HOME`. `run.sh` derives mounts for the paths the config names (see [Automatic bind mounts](#automatic-bind-mounts)); any *other* directory the workflow touches must still be listed explicitly:

```yaml
singularity_args_param: "--cleanenv --bind /tmp --bind /scratch/myproject --bind /projects/shared"
```

**`PYTHONSAFEPATH=1`**: The container sets this env var to prevent the host working directory from shadowing the installed `qm_lux` package inside the container. For older images without this setting, pass `--env PYTHONSAFEPATH=1` in `singularity_args_param`.

**`PYTHONNOUSERSITE=1`**: The container also sets this. Singularity auto-mounts `$HOME`, so a stale `qm_lux` install in the caller's user site-packages (`~/.local`, or wherever `PYTHONUSERBASE` points) would otherwise be picked up and make `qm_lux.__version__` report the *host's* version rather than the image's. For older images without this setting, add `--env PYTHONNOUSERSITE=1` or use `--cleanenv`.

**Gaussian is a commercial dependency.** Users without Gaussian can skip the QM steps if a pre-computed descriptor pickle is available.

**XTB / CREST** are open source and bundled in the container image (XTB 6.4.1, CREST 2.11.2). They are not installed in the Poetry development environment.

---

## Troubleshooting

**`FileNotFoundError` or directory not accessible inside the container**
`run.sh` binds the paths your config names automatically and prints them as `Auto-bound from …`; if the missing directory is not in that line, add it to `singularity_args_param` yourself:

```yaml
singularity_args_param: "--cleanenv --bind /tmp --bind /path/to/missing/dir"
```

If a path *is* listed as auto-bound yet still appears empty inside the container, check whether you reached the workflow directory through a symlink — `run.sh` resolves this, but a directly invoked `snakemake` does not.

**`container creation failed: … mount source … doesn't exist`**
A `--bind` entry in `singularity_args_param` points at a path that does not exist. Singularity treats this as fatal rather than skipping it. Create the directory or remove the entry; the paths `run.sh` derives are already walked up to an existing ancestor.

**`argument --executor/-e: invalid choice: 'slurm'`**
Cluster mode needs `snakemake-executor-plugin-slurm`, which is not part of Snakemake core. Install it, or run locally with `--cores N`, or set `QM_LUX_CLUSTER_PROFILE` to a profile for your own scheduler. `run.sh` warns about this before the run starts.

**Jobs go to SLURM even though `--cores N` was given**
Fixed in current versions — `run.sh` now passes `--executor local`. If you invoke `snakemake` directly rather than through `run.sh`, a site-wide profile in `$SNAKEMAKE_PROFILE` can still impose `executor: slurm` on every call; override it with `--executor local` or `--profile none`.

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

**`Error: segmentation violation` after `Normal termination of Gaussian 16`**
Harmless — the calculation already finished successfully. Some Gaussian 16 builds segfault in thread teardown *after* writing their results, so the trace appears immediately below the `Normal termination` line and shows a libc backtrace (`__clone` → `__libc_free`). Measured on the bundled test input: `g16` still exits `0`, and the excited states and SCF energy are byte-identical to a single-threaded run that produces no such trace. The workflow checks for `Normal termination`, so these runs are correctly treated as successful. It only appears with `gaussian_threads` greater than 1; there is no reason to lower it, as the results are unaffected.

**SLURM jobs fail with memory errors**
Memory is declared by each rule in `workflow/Snakefile`, not in the SLURM profile — the profile deliberately sets only `qos`, because a `mem_mb` under its `set-resources:` would silently override the rule. For Gaussian, raise `gaussian_mem_gb` in your config file: it sets the `%mem` written into the Gaussian input *and* the SLURM reservation together, so the two cannot drift apart. For CREST and XTB (20 GB each by default), edit `resources: mem_mb=` on the rule in the `Snakefile`.

---

## Support

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
