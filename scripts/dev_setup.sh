#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
echo "Repo root: $ROOT_DIR"

if [ ! -d "$ROOT_DIR/.venv" ]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$ROOT_DIR/requirements.txt"
python -m pip install pre-commit

echo "Installing pre-commit hooks..."
pre-commit install || true
pre-commit install --hook-type commit-msg || true

echo "Running test suite..."
pytest -q

echo "Dev setup complete. Activate the venv with: source .venv/bin/activate"
