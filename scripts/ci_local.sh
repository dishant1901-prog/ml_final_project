#!/bin/bash
# Reproducible free local gate; no cloud service is required.
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PWD/data/cache/matplotlib}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/himaroad-uv-cache}"
mkdir -p "$MPLCONFIGDIR"

uv lock --check
uv sync --locked
uv pip check --python .venv/bin/python
.venv/bin/python -m compileall -q backend src web scripts tests
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_offline.py
git diff --check
uvx ruff check backend/app/api.py backend/app/settings.py backend/app/operations.py \
  backend/app/copilot/tools.py scripts/local_worker.py scripts/local_backup.py \
  scripts/configure_local_auth.py tests/test_operations.py tests/test_worker.py
uvx bandit -q -r backend/app scripts/local_worker.py scripts/local_backup.py \
  scripts/configure_local_auth.py web/server.py -x backend/app/reports

audit_requirements="$(mktemp /tmp/himaroad-audit.XXXXXX.txt)"
trap 'rm -f "$audit_requirements"' EXIT
uv export --frozen --no-dev --no-hashes --no-emit-project --format requirements-txt --output-file "$audit_requirements"
uvx pip-audit --strict --no-deps --disable-pip -r "$audit_requirements"
