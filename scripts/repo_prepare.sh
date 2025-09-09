#!/usr/bin/env bash
set -euo pipefail

# repo_prepare.sh — install dev deps, run tests, run benchmark, build docs
# Usage: ./scripts/repo_prepare.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ART=artifacts
mkdir -p "$ART"

PYBIN=""
# prefer project venv if exists
if [ -x "$ROOT/venv/bin/python" ]; then
  PYBIN="$ROOT/venv/bin/python"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYBIN="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYBIN=$(command -v python3)
else
  echo "No python available" >&2
  exit 2
fi

echo "Using python: $PYBIN"

echo "Installing dev deps (editable)"
"$PYBIN" -m pip install -U pip setuptools wheel
if [ -f pyproject.toml ]; then
  "$PYBIN" -m pip install -e .[dev]
fi

echo "Running tests"
"$PYBIN" -m pytest -q | tee pytest_output.txt
cp pytest_output.txt "$ART/"

echo "Running cognition benchmark"
"$PYBIN" benchmarks/run_cognition_bench.py
cp benchmarks/*.csv benchmarks/*.png "$ART/" || true

echo "Building Sphinx docs"
if [ -x "$ROOT/venv/bin/python" ]; then
  VENVPY="$ROOT/venv/bin/python"
else
  VENVPY="$PYBIN"
fi
if [ -d docs ]; then
  "$VENVPY" -m sphinx -M html docs/source docs/build | tee docs_build_output.txt || true
  cp -r docs/build/html "$ART/" || true
fi

echo "Artifacts collected in $ART"
ls -la "$ART"
