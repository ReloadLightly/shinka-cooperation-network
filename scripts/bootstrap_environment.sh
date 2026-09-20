#!/usr/bin/env bash
# The explicit lock is authoritative after the first successful solve.
set -euo pipefail
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_ROOT"
mkdir -p environment/{bin,downloads,logs,R-library,conda-pkgs} vendor
export MAMBA_ROOT_PREFIX="$PROJECT_ROOT/environment/conda-pkgs"
export XDG_CACHE_HOME="$PROJECT_ROOT/environment/cache"
if [[ ! -x environment/bin/micromamba ]]; then
  curl --fail --location --retry 3 https://micro.mamba.pm/api/micromamba/linux-64/2.9.0 -o environment/downloads/micromamba.tar.bz2
  echo '8761c382127e6363bd9e0a2451aa3ef90d071a79133f736e2f759a3bf13040dd  environment/downloads/micromamba.tar.bz2' | sha256sum -c -
  tar -xjf environment/downloads/micromamba.tar.bz2 -C environment bin/micromamba
fi
if [[ ! -x environment/runtime/bin/Rscript ]]; then
  if [[ -f environment/conda-linux-64.explicit.txt ]]; then
    /usr/bin/time -v environment/bin/micromamba create --yes --prefix "$PROJECT_ROOT/environment/runtime" --file environment/conda-linux-64.explicit.txt 2>&1 | tee environment/logs/bootstrap-conda.log
  else
    /usr/bin/time -v environment/bin/micromamba create --yes --prefix "$PROJECT_ROOT/environment/runtime" --file environment/environment.yml 2>&1 | tee environment/logs/bootstrap-conda.log
  fi
fi
if [[ ! -f environment/downloads/RSiena-v1.3.10.tar.gz ]]; then
  curl --fail --location --retry 3 https://github.com/stocnet/rsiena/archive/refs/tags/v1.3.10.tar.gz -o environment/downloads/RSiena-v1.3.10.tar.gz
fi
echo 'c7e0fc358f064e6b5d753ceb675a2eb00ea08cd6d58934ebabef31055302a1d5  environment/downloads/RSiena-v1.3.10.tar.gz' | sha256sum -c -
if [[ ! -d vendor/RSiena ]]; then
  tar -xzf environment/downloads/RSiena-v1.3.10.tar.gz -C vendor
  mv vendor/rsiena-1.3.10 vendor/RSiena
fi
export R_LIBS_USER="$PROJECT_ROOT/environment/R-library"
export MAKEFLAGS=-j1
/usr/bin/time -v environment/bin/micromamba run --prefix "$PROJECT_ROOT/environment/runtime" R CMD INSTALL --library="$R_LIBS_USER" vendor/RSiena 2>&1 | tee environment/logs/bootstrap-rsiena.log
environment/bin/micromamba env export --prefix "$PROJECT_ROOT/environment/runtime" --explicit > environment/conda-linux-64.explicit.txt
environment/run-r environment/verify.R 2>&1 | tee environment/logs/verify.log
environment/run-r environment/verify_imports.R 2>&1 | tee environment/logs/author-imports.log
