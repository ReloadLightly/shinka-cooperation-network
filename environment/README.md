# Scientific R environment

The local runtime uses the authors' exact **R 4.2.1** and **RSiena 1.3.10**.
**PRROC 1.3.1** is this project's fixed metric implementation. The installed
environment is entirely inside the repository; it does not replace system R.

Run R scripts with `environment/run-r path/to/script.R [arguments]`.
Reconstruct the environment with `bash scripts/bootstrap_environment.sh`.
The bootstrap downloads public packages and needs internet access. On a fresh
checkout, `conda-linux-64.explicit.txt` supplies exact conda artifacts and MD5
checksums; `environment.yml` documents the human-readable dependency intent.
The bootstrap verifies SHA256 for micromamba and the RSiena release archive.

RSiena comes from upstream tag `v1.3.10`, commit
`c13ddd4af204cdcfb743ebab6217a68fad333f5a`. Its source archive is retained in
`downloads/RSiena-v1.3.10.tar.gz` and extracted to `../vendor/RSiena`. All 795
archived source files were byte-compared after compilation; none changed.
Compilation creates additional generated files in that source directory.
`provenance.json` records checksums, licensing declarations, and source identity.
RSiena declares `GPL-2 | GPL-3 | file LICENSE`; PRROC declares `GPL-3`.

`verify.R` checks exact versions and executes PRROC metric fixtures. For positive
scores `(0.8, 0.4)` and negative scores `(0.6, 0.2)`, the pinned integral is
`0.79726744594591781`. `scores.class0` represents positive observations.
`prroc-verification.json` preserves the executable check. It does not establish
forecast validity or provide a scientific model score.

The environment differs from the reported original Ubuntu 14.4 LTS setup:
this host is Ubuntu 22.04.5 on WSL2, uses conda-forge R binaries, GCC/G++ 15.3.0
with GNU++14 compilation, and OpenBLAS 0.3.34. Other package versions were not
specified by the authors; this project's complete versions are in
`r-packages.tsv`, `versions.json`, and `session-info.txt`. Numerical or package
behavior differences remain possible despite matching R and RSiena. The R
wrapper defaults OpenBLAS and OpenMP to one thread unless explicitly set.
Most conda R packages were built under R 4.2.3 and emit that warning when loaded
under the retained R 4.2.1 runtime; every original import nevertheless loaded.

All packages imported by the three original entry scripts were installed and
load-checked in `logs/author-imports.log`. Single-threaded RSiena compilation
took 150.73 seconds and used 219,508 KB peak RSS. Installation, compiler output,
and resource measurements are retained under `logs/`. An initial micromamba
cache-permission failure is retained separately; the bootstrap now puts its
cache inside the project. Scientific runs are managed outside this environment
directory and are not implied by successful installation.
The conda hydroTSM package omitted its `classInt` dependency; that import failure
is retained, and `r-classint` is explicitly included in the final lock.
