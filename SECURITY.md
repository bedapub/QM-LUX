# Security Policy

© 2026 Roche

---

## Reporting a vulnerability

**Do not report security vulnerabilities through public GitHub Issues.**

Report them privately using one of these routes:

1. **GitHub private vulnerability reporting** — preferred.
   Go to the [Security tab](https://github.com/bedapub/QM-LUX/security/advisories/new)
   of this repository and open a draft advisory. This keeps the report private
   until a fix is available.

2. **Roche security contact** — if you cannot use GitHub, or the issue concerns
   Roche infrastructure rather than this code, report through
   <https://www.roche.com/about/governance/business-ethics> so it reaches the
   Roche security organisation.

Please include:

- The version, commit SHA, or container image digest affected
- A description of the issue and why you believe it is a security problem
- Steps to reproduce, or a proof of concept
- Any suggested mitigation

Please give us a reasonable opportunity to investigate and issue a fix before
public disclosure.

---

## Supported versions

QM-LUX is a publication-support release and is not under active feature
development. Security fixes, when made, will apply to the latest tagged release
only.

| Version | Supported |
|---|:---:|
| 1.0.x | ✅ latest release |
| < 1.0 | ❌ |

---

## Scope

### In scope

- The `qm_lux` Python package (`src/qm_lux/`)
- The Snakemake workflow and helper scripts (`workflow/`)
- The container image build (`Dockerfile`, `environment.yml`)
- The published container image `ghcr.io/bedapub/qm-lux`

### Out of scope

- **Vulnerabilities in third-party dependencies.** Report those upstream
  (RDKit, scikit-learn, XTB, CREST, Snakemake, …). If a dependency CVE requires
  a version pin change here, an Issue is the right channel, not a security
  report.
- **Gaussian 16.** Commercial software, not distributed with this project.
  Report to the vendor.
- Vulnerabilities requiring the attacker to already have shell access on the
  host running the workflow.

---

## Security considerations for users

Please be aware of the following inherent properties of this workflow. These are
documented behaviours, not vulnerabilities:

### Pickle deserialization

The workflow loads the ML model and scaler with `pickle`
(`model.sav`, `scaler.pkl`), and reads and writes intermediate `.pkl` files.
**Python's `pickle` executes arbitrary code during deserialization.**

Only load model files and intermediate pickles from sources you trust. Do not
point `model_local_folder` at an untrusted directory, and verify downloads when
using `model_github_url`.

### Model download over the network

With `model_github_url`, the `model` rule downloads `model.sav` and `scaler.pkl`
at runtime over HTTPS. Verify the integrity of these files if your threat model
requires it.

### Container privileges and bind mounts

`singularity_args_param` in the config controls host bind mounts. Bind only the
directories the workflow needs. Do not run the container as root.

### Credentials

`ARVADOS_API_TOKEN` (Arvados model sourcing, Option 3) is read from the
environment. Do not commit tokens to config files, and be aware that
environment variables may be visible to other processes on a shared host.

### SMILES input

Input SMILES strings are parsed by RDKit. Treat untrusted input files as you
would any untrusted input to a native parsing library.
