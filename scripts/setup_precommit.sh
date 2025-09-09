#!/usr/bin/env bash
set -euo pipefail

# Install pre-commit and install hooks
python -m pip install --upgrade pip
python -m pip install --upgrade pre-commit
pre-commit install
pre-commit install --hook-type commit-msg

# Set commit template
git config commit.template .gitmessage

echo "Pre-commit hooks installed and commit template set."
