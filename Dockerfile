FROM condaforge/miniforge3:latest

# tini for proper signal handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Layer 1: QM-LUX tools, conda env qmlux (pinned Python 3.11.11, rdkit, xtb, crest, ...) ---
# Installed in a separate named env so its solver doesn't fight snakemake's deps.
COPY environment.yml .
RUN mamba env create -f environment.yml && \
    mamba clean --all --yes

# --- Layer 2: Snakemake (separate env, no version conflicts with qmlux) ---
# snakemake 8.x requires Python >=3.11; installed in its own env to avoid
# clashing with the tightly-pinned packages in qmlux.
RUN mamba create -n snakemake -c conda-forge -c bioconda "snakemake>=8,<10" -y && \
    mamba clean --all --yes

# Both envs on PATH: qmlux supplies python/rdkit/xtb/crest; snakemake env supplies snakemake
ENV PATH=/opt/conda/envs/qmlux/bin:/opt/conda/envs/snakemake/bin:/opt/conda/bin:/app:$PATH
ENV CONDA_DEFAULT_ENV=qmlux
# Prevent host CWD from shadowing the installed qm_lux package when run via Singularity
ENV PYTHONSAFEPATH=1
# Ignore host user site-packages. Singularity auto-mounts $HOME, so without this a
# stale qm_lux dist-info in the caller's ~/.local can hijack importlib.metadata and
# make qm_lux.__version__ report the host's version instead of the image's.
ENV PYTHONNOUSERSITE=1

# Copy ONLY what the image needs, explicitly. Never `COPY . .` — a deny-list
# .dockerignore fails open, so anything new and untracked (agent notes, logs,
# credentials, build artefacts) would silently land in a published image.
# Needed here: pyproject.toml + README.md (poetry-core reads both at build time)
# and the package source. The Snakemake workflow itself runs on the HOST and
# bind-mounts the working directory, so workflow/ is deliberately NOT copied.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install qm_lux so importlib.metadata can resolve its version from inside the image.
# Without an in-image dist-info, qm_lux.__version__ falls back to whatever metadata
# leaks in from the host (or "unknown" under --cleanenv).
# --no-deps: all dependencies are already provided by the conda env.
RUN /opt/conda/envs/qmlux/bin/pip install --no-deps .

ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["python", "-m", "qm_lux.cli", "--help"]
