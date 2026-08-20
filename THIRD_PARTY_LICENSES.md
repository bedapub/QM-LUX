# Third-party components redistributed in the QM-LUX container image

**Generated file — do not edit by hand.** Regenerate with `tools/gen_third_party_licenses.py`; see that file's docstring for the exact command. Re-run it after any change to `environment.yml` or the `Dockerfile`.

QM-LUX's own source is Apache-2.0 (see [LICENSE](LICENSE)). The published image
`ghcr.io/bedapub/qm-lux` additionally **redistributes** the components below.
Attribution notices required by their licences are in [NOTICE](NOTICE).

Gaussian 16 is **not** listed: it is commercial, is not in the image, and runs
against the user's own licensed installation on the host.

Components: **246** total, of which **43** carry a copyleft or
non-OSI licence and are listed separately first.

## Components with copyleft or non-OSI licences

| Component | Version | Declared licence | Packaged as |
|---|---|---|---|
| `alsa-lib` | 1.2.16.1 | LGPL-2.1-or-later | conda |
| `ase` | 3.23.0 | LGPL-2.1-or-later | conda |
| `cairo` | 1.18.4 | LGPL-2.1-only or MPL-1.1 | conda |
| `certifi` | 2026.7.22 | MPL-2.0 | pip |
| `crest` | 2.11.2 | LGPL-3.0-or-later | conda |
| `dbus` | 1.13.6 | GPL-2.0-or-later | conda |
| `font-ttf-ubuntu` | 0.83 | LicenseRef-Ubuntu-Font-Licence-Version-1.0 | conda |
| `freetype` | 2.14.3 | GPL-2.0-only OR FTL | conda |
| `graphite2` | 1.3.15 | LGPL-2.0-or-later | conda |
| `keyutils` | 1.6.3 | LGPL-2.1-or-later | conda |
| `ld_impl_linux-64` | 2.46.1 | GPL-3.0-only | conda |
| `libegl` | 1.7.0 | LicenseRef-libglvnd | conda |
| `libev` | 4.33 | BSD-2-Clause OR GPL-2.0-or-later | conda |
| `libfreetype` | 2.14.3 | GPL-2.0-only OR FTL | conda |
| `libfreetype6` | 2.14.3 | GPL-2.0-only OR FTL | conda |
| `libgcc` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libgcc-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libgfortran` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libgfortran-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libgfortran5` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libgl` | 1.7.0 | LicenseRef-libglvnd | conda |
| `libglib` | 2.84.0 | LGPL-2.1-or-later | conda |
| `libglvnd` | 1.7.0 | LicenseRef-libglvnd | conda |
| `libglx` | 1.7.0 | LicenseRef-libglvnd | conda |
| `libgomp` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libiconv` | 1.18 | LGPL-2.1-only | conda |
| `libnsl` | 2.0.1 | LGPL-2.1-only | conda |
| `libntlm` | 1.8 | LGPL-2.1-or-later | conda |
| `libopengl` | 1.7.0 | LicenseRef-libglvnd | conda |
| `libstdcxx` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libstdcxx-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | conda |
| `libxcrypt` | 4.4.38 | LGPL-2.1-or-later | conda |
| `mkl` | 2024.2.2 | LicenseRef-IntelSimplifiedSoftwareOct2022 | conda |
| `mysql-common` | 9.0.1 | GPL-2.0-or-later | conda |
| `mysql-libs` | 9.0.1 | GPL-2.0-or-later | conda |
| `pycairo` | 1.29.0 | LGPL-2.1-only OR MPL-1.1 | conda |
| `pyside6` | 6.9.0 | LGPL-3.0-only | conda |
| `qhull` | 2020.2 | LicenseRef-Qhull | conda |
| `qt6-main` | 6.9.0 | LGPL-3.0-only | conda |
| `readline` | 8.3 | GPL-3.0-only | conda |
| `tzdata` | 2026c | LicenseRef-Public-Domain | conda |
| `xtb` | 6.4.1 | LGPL-3.0-or-later | conda |
| `zeromq` | 4.3.5 | MPL-2.0 | conda |

## Full inventory

| Component | Version | Declared licence |
|---|---|---|
| `_openmp_mutex` | 4.5 | BSD-3-Clause |
| `alsa-lib` | 1.2.16.1 | LGPL-2.1-or-later |
| `arvados-python-client` | 3.2.1 | UNSPECIFIED |
| `ase` | 3.23.0 | LGPL-2.1-or-later |
| `asttokens` | 3.0.2 | Apache-2.0 |
| `blinker` | 1.9.0 | MIT |
| `boto3` | 1.43.64 | Apache-2.0 |
| `botocore` | 1.43.64 | Apache-2.0 |
| `brotli` | 1.2.0 | MIT |
| `brotli-bin` | 1.2.0 | MIT |
| `bzip2` | 1.0.8 | bzip2-1.0.6 |
| `c-ares` | 1.34.8 | MIT |
| `ca-certificates` | 2026.7.22 | ISC |
| `cairo` | 1.18.4 | LGPL-2.1-only or MPL-1.1 |
| `certifi` | 2026.7.22 | MPL-2.0 |
| `cffi` | 2.1.1 | UNSPECIFIED |
| `charset-normalizer` | 3.4.9 | MIT |
| `ciso8601` | 2.3.3 | MIT |
| `click` | 8.4.2 | BSD-3-Clause |
| `colorama` | 0.4.6 | BSD-3-Clause |
| `comm` | 0.2.3 | BSD-3-Clause |
| `contourpy` | 1.3.3 | BSD-3-Clause |
| `crest` | 2.11.2 | LGPL-3.0-or-later |
| `cryptography` | 50.0.0 | UNSPECIFIED |
| `curl` | 8.18.0 | curl |
| `cycler` | 0.12.1 | BSD-3-Clause |
| `cyrus-sasl` | 2.1.28 | BSD-3-Clause-Attribution |
| `dbus` | 1.13.6 | GPL-2.0-or-later |
| `debugpy` | 1.8.21 | MIT |
| `double-conversion` | 3.3.1 | BSD-3-Clause |
| `et_xmlfile` | 2.0.0 | MIT |
| `exceptiongroup` | 1.3.1 | MIT and PSF-2.0 |
| `executing` | 2.2.1 | MIT |
| `expat` | 2.8.1 | MIT |
| `flask` | 3.1.3 | BSD-3-Clause |
| `font-ttf-dejavu-sans-mono` | 2.37 | BSD-3-Clause |
| `font-ttf-inconsolata` | 3.000 | OFL-1.1 |
| `font-ttf-source-code-pro` | 2.038 | OFL-1.1 |
| `font-ttf-ubuntu` | 0.83 | LicenseRef-Ubuntu-Font-Licence-Version-1.0 |
| `fontconfig` | 2.18.2 | MIT |
| `fonts-conda-ecosystem` | 1 | BSD-3-Clause |
| `fonts-conda-forge` | 1 | BSD-3-Clause |
| `fonttools` | 4.63.0 | MIT |
| `freetype` | 2.14.3 | GPL-2.0-only OR FTL |
| `freetype-py` | 2.3.0 | BSD-3-Clause |
| `google-api-core` | 2.33.0 | Apache 2.0 |
| `google-api-python-client` | 2.198.0 | Apache 2.0 |
| `google-auth` | 2.56.2 | Apache 2.0 |
| `google-auth-httplib2` | 0.4.0 | Apache 2.0 |
| `googleapis-common-protos` | 1.75.0 | Apache 2.0 |
| `graphite2` | 1.3.15 | LGPL-2.0-or-later |
| `greenlet` | 3.5.4 | MIT |
| `harfbuzz` | 11.0.0 | MIT |
| `httplib2` | 0.32.0 | MIT |
| `icu` | 75.1 | MIT |
| `idna` | 3.18 | UNSPECIFIED |
| `imbalanced-learn` | 0.13.0 | MIT |
| `iniconfig` | 2.3.0 | MIT |
| `ipykernel` | 6.29.4 | BSD-3-Clause |
| `ipython` | 9.16.1 | BSD-3-Clause |
| `ipython_pygments_lexers` | 1.1.1 | BSD-3-Clause |
| `itsdangerous` | 2.2.0 | BSD-3-Clause |
| `jedi` | 0.20.0 | Apache-2.0 AND MIT |
| `jinja2` | 3.1.6 | BSD-3-Clause |
| `jmespath` | 1.1.0 | MIT |
| `joblib` | 1.5.3 | BSD-3-Clause |
| `jupyter_client` | 8.9.1 | BSD-3-Clause |
| `jupyter_core` | 5.9.1 | BSD-3-Clause |
| `keyutils` | 1.6.3 | LGPL-2.1-or-later |
| `kiwisolver` | 1.5.0 | BSD-3-Clause |
| `krb5` | 1.21.3 | MIT |
| `lcms2` | 2.19.1 | MIT |
| `ld_impl_linux-64` | 2.46.1 | GPL-3.0-only |
| `lerc` | 4.2.0 | Apache-2.0 |
| `libblas` | 3.9.0 | BSD-3-Clause |
| `libboost` | 1.84.0 | BSL-1.0 |
| `libboost-python` | 1.84.0 | BSL-1.0 |
| `libbrotlicommon` | 1.2.0 | MIT |
| `libbrotlidec` | 1.2.0 | MIT |
| `libbrotlienc` | 1.2.0 | MIT |
| `libcblas` | 3.9.0 | BSD-3-Clause |
| `libclang-cpp20.1` | 20.1.8 | Apache-2.0 WITH LLVM-exception |
| `libclang13` | 21.1.0 | Apache-2.0 WITH LLVM-exception |
| `libcups` | 2.3.3 | Apache-2.0 |
| `libcurl` | 8.18.0 | curl |
| `libdeflate` | 1.25 | MIT |
| `libdrm` | 2.4.127 | MIT |
| `libedit` | 3.1.20250104 | BSD-2-Clause |
| `libegl` | 1.7.0 | LicenseRef-libglvnd |
| `libev` | 4.33 | BSD-2-Clause OR GPL-2.0-or-later |
| `libexpat` | 2.8.1 | MIT |
| `libffi` | 3.7.0 | MIT |
| `libfreetype` | 2.14.3 | GPL-2.0-only OR FTL |
| `libfreetype6` | 2.14.3 | GPL-2.0-only OR FTL |
| `libgcc` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libgcc-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libgfortran` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libgfortran-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libgfortran5` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libgl` | 1.7.0 | LicenseRef-libglvnd |
| `libglib` | 2.84.0 | LGPL-2.1-or-later |
| `libglvnd` | 1.7.0 | LicenseRef-libglvnd |
| `libglx` | 1.7.0 | LicenseRef-libglvnd |
| `libgomp` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libhwloc` | 2.12.1 | BSD-3-Clause |
| `libiconv` | 1.18 | LGPL-2.1-only |
| `libjpeg-turbo` | 3.2.0 | IJG AND BSD-3-Clause AND Zlib |
| `liblapack` | 3.9.0 | BSD-3-Clause |
| `libllvm20` | 20.1.8 | Apache-2.0 WITH LLVM-exception |
| `libllvm21` | 21.1.0 | Apache-2.0 WITH LLVM-exception |
| `liblzma` | 5.8.3 | 0BSD |
| `libnghttp2` | 1.68.1 | MIT |
| `libnsl` | 2.0.1 | LGPL-2.1-only |
| `libntlm` | 1.8 | LGPL-2.1-or-later |
| `libopenblas` | 0.3.28 | BSD-3-Clause |
| `libopengl` | 1.7.0 | LicenseRef-libglvnd |
| `libpciaccess` | 0.19 | MIT |
| `libpng` | 1.6.58 | zlib-acknowledgement |
| `libpq` | 17.7 | PostgreSQL |
| `libsodium` | 1.0.20 | ISC |
| `libsqlite` | 3.53.4 | blessing |
| `libssh2` | 1.11.1 | BSD-3-Clause |
| `libstdcxx` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libstdcxx-ng` | 14.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `libtiff` | 4.7.2 | HPND |
| `libuuid` | 2.42.2 | BSD-3-Clause |
| `libwebp-base` | 1.6.0 | BSD-3-Clause |
| `libxcb` | 1.17.0 | MIT |
| `libxcrypt` | 4.4.38 | LGPL-2.1-or-later |
| `libxkbcommon` | 1.11.0 | MIT/X11 Derivative |
| `libxml2` | 2.13.9 | MIT |
| `libxslt` | 1.1.43 | MIT |
| `libzlib` | 1.3.2 | Zlib |
| `llvm-openmp` | 22.1.8 | Apache-2.0 WITH LLVM-exception |
| `markupsafe` | 3.0.3 | BSD-3-Clause |
| `matplotlib` | 3.10.0 | PSF-2.0 |
| `matplotlib-base` | 3.10.0 | PSF-2.0 |
| `matplotlib-inline` | 0.2.2 | BSD-3-Clause |
| `mkl` | 2024.2.2 | LicenseRef-IntelSimplifiedSoftwareOct2022 |
| `munkres` | 1.1.4 | Apache-2.0 |
| `mysql-common` | 9.0.1 | GPL-2.0-or-later |
| `mysql-libs` | 9.0.1 | GPL-2.0-or-later |
| `ncurses` | 6.6 | X11 AND BSD-3-Clause |
| `nest-asyncio` | 1.6.0 | BSD-2-Clause |
| `numpy` | 1.26.4 | BSD-3-Clause |
| `openjpeg` | 2.5.4 | BSD-2-Clause |
| `openldap` | 2.6.10 | OLDAP-2.8 |
| `openpyxl` | 3.1.5 | MIT |
| `openssl` | 3.6.3 | Apache-2.0 |
| `packaging` | 26.3 | Apache-2.0 |
| `pandas` | 2.1.4 | BSD-3-Clause |
| `parso` | 0.8.7 | MIT |
| `patsy` | 1.0.2 | BSD-2-Clause AND PSF-2.0 |
| `pcre2` | 10.44 | BSD-3-Clause |
| `pexpect` | 4.9.0 | ISC |
| `pillow` | 12.3.0 | HPND |
| `pip` | 26.2.1 | MIT |
| `pixman` | 0.46.4 | MIT |
| `platformdirs` | 4.11.0 | MIT |
| `pluggy` | 1.6.0 | MIT |
| `prompt-toolkit` | 3.0.53 | BSD-3-Clause |
| `proto-plus` | 1.28.2 | Apache 2.0 |
| `protobuf` | 7.35.1 | 3-Clause BSD License |
| `psutil` | 7.2.2 | BSD-3-Clause |
| `pthread-stubs` | 0.4 | MIT |
| `ptyprocess` | 0.7.0 | ISC |
| `pure_eval` | 0.2.3 | MIT |
| `pyasn1` | 0.6.4 | BSD-2-Clause |
| `pyasn1_modules` | 0.4.2 | BSD |
| `pycairo` | 1.29.0 | LGPL-2.1-only OR MPL-1.1 |
| `pycparser` | 3.0 | UNSPECIFIED |
| `pycurl` | 7.47.0 | UNSPECIFIED |
| `pygments` | 2.20.0 | BSD-2-Clause |
| `pyparsing` | 3.3.2 | MIT |
| `pyside6` | 6.9.0 | LGPL-3.0-only |
| `pytest` | 8.4.2 | MIT |
| `python` | 3.11.11 | Python-2.0 |
| `python-dateutil` | 2.9.0.post0 | Apache-2.0 |
| `python-tzdata` | 2026.3 | Apache-2.0 |
| `python_abi` | 3.11 | BSD-3-Clause |
| `pytz` | 2026.3.post1 | MIT |
| `pyzmq` | 27.1.0 | BSD-3-Clause |
| `qhull` | 2020.2 | LicenseRef-Qhull |
| `qm-lux` | 1.0.0 | Apache-2.0 |
| `qt6-main` | 6.9.0 | LGPL-3.0-only |
| `rdkit` | 2023.09.6 | BSD-3-Clause |
| `readline` | 8.3 | GPL-3.0-only |
| `reportlab` | 5.0.0 | BSD-3-Clause |
| `requests` | 2.34.2 | Apache-2.0 |
| `rlpycairo` | 0.4.0 | BSD-3-Clause |
| `s3transfer` | 0.19.2 | Apache License 2.0 |
| `scikit-learn` | 1.5.0 | BSD-3-Clause |
| `scipy` | 1.13.1 | BSD-3-Clause |
| `seaborn` | 0.13.2 | BSD-3-Clause |
| `seaborn-base` | 0.13.2 | BSD-3-Clause |
| `setuptools` | 83.0.0 | MIT |
| `shiboken6` | 6.9.0 | UNSPECIFIED |
| `six` | 1.17.0 | MIT |
| `sklearn-compat` | 0.1.6 | BSD-3-Clause |
| `sqlalchemy` | 2.0.51 | MIT |
| `stack_data` | 0.6.3 | MIT |
| `statsmodels` | 0.14.6 | BSD-3-Clause |
| `tbb` | 2021.13.0 | Apache-2.0 |
| `threadpoolctl` | 3.6.0 | BSD-3-Clause |
| `tk` | 8.6.13 | TCL |
| `tomli` | 2.4.1 | MIT |
| `tornado` | 6.5.7 | Apache-2.0 |
| `traitlets` | 5.16.1 | BSD-3-Clause |
| `typing-extensions` | 4.16.0 | PSF-2.0 |
| `typing_extensions` | 4.16.0 | PSF-2.0 |
| `tzdata` | 2026c | LicenseRef-Public-Domain |
| `unicodedata2` | 17.0.1 | Apache-2.0 |
| `uritemplate` | 4.2.0 | BSD 3-Clause OR Apache-2.0 |
| `urllib3` | 2.7.0 | UNSPECIFIED |
| `wayland` | 1.23.1 | MIT |
| `wcwidth` | 0.8.2 | MIT |
| `websockets` | 17.0.1 | UNSPECIFIED |
| `werkzeug` | 3.1.8 | BSD-3-Clause |
| `wheel` | 0.47.0 | MIT |
| `xcb-util` | 0.4.1 | MIT |
| `xcb-util-cursor` | 0.1.6 | MIT |
| `xcb-util-image` | 0.4.0 | MIT |
| `xcb-util-keysyms` | 0.4.1 | MIT |
| `xcb-util-renderutil` | 0.3.10 | MIT |
| `xcb-util-wm` | 0.4.2 | MIT |
| `xkeyboard-config` | 2.48 | MIT |
| `xlsxwriter` | 3.2.0 | BSD-2-Clause |
| `xorg-libice` | 1.1.2 | MIT |
| `xorg-libsm` | 1.2.6 | MIT |
| `xorg-libx11` | 1.8.13 | MIT |
| `xorg-libxau` | 1.0.12 | MIT |
| `xorg-libxcomposite` | 0.4.7 | MIT |
| `xorg-libxcursor` | 1.2.3 | MIT |
| `xorg-libxdamage` | 1.1.6 | MIT |
| `xorg-libxdmcp` | 1.1.5 | MIT |
| `xorg-libxext` | 1.3.7 | MIT |
| `xorg-libxfixes` | 6.0.2 | MIT |
| `xorg-libxi` | 1.8.3 | MIT |
| `xorg-libxrandr` | 1.5.5 | MIT |
| `xorg-libxrender` | 0.9.12 | MIT |
| `xorg-libxtst` | 1.2.5 | MIT |
| `xorg-libxxf86vm` | 1.1.7 | MIT |
| `xtb` | 6.4.1 | LGPL-3.0-or-later |
| `zeromq` | 4.3.5 | MPL-2.0 |
| `zlib-ng` | 2.3.3 | Zlib |
| `zstd` | 1.5.7 | BSD-3-Clause |
