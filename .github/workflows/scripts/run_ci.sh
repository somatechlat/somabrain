#!/usr/bin/env bash
set -euo pipefail

# SomaBrain CI entrypoint: run lint, type-check, unit tests, and integration smoke.
# This mirrors the commands developers must execute locally before pushing changes.

UV="${UV:-uv}"
PYTEST_FLAGS=${PYTEST_FLAGS:-""}

# Capture dependency install timing before running the remainder of CI tasks.
${UV} run python scripts/ci/record_dependency_install_metrics.py

${UV} run ruff check .
${UV} run mypy somabrain
${UV} run pytest ${PYTEST_FLAGS}
${UV} run pytest tests/smoke_test.py
