#!/usr/bin/env bash
set -euo pipefail

PY=${1:-python3}
VENV_DIR=${2:-.venv}

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python interpreter '$PY' not found. Please install Python 3.9+ and retry." >&2
  exit 1
fi

echo "Creating virtual environment at $VENV_DIR..."
"$PY" -m venv "$VENV_DIR"
source "$VENV_DIR"/bin/activate
python -m pip install --upgrade pip

echo "Installing requirements..."
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
else
  # Minimal deps for running the API
  pip install fastapi uvicorn prometheus-client httpx numpy
fi

echo "Virtual environment ready. Activate with: source $VENV_DIR/bin/activate"
