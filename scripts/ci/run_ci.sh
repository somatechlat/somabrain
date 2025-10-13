#!/usr/bin/env bash
set -euo pipefail

# SomaBrain CI entrypoint: run lint, type-check, unit tests, and integration smoke.
# This mirrors the commands developers must execute locally before pushing changes.

UV="${UV:-uv}"
PYTEST_FLAGS=${PYTEST_FLAGS:-""}

${UV} run ruff check .
${UV} run mypy somabrain
${UV} run pytest ${PYTEST_FLAGS}
${UV} run pytest tests/smoke_test.py
