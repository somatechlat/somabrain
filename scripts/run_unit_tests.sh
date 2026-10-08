#!/usr/bin/env bash
# SomaBrain unit tests in isolation-safe groups.
set -euo pipefail
cd "$(dirname "$0")/.."
export SOMABRAIN_MEMORY_HTTP_TOKEN="${SOMABRAIN_MEMORY_HTTP_TOKEN:-test-only-token}"
PY=.venv/bin/python

collect() {
  find tests/unit -name 'test_*.py' \
    ! -path 'tests/unit/memory/test_seam_unit.py' \
    ! -name 'test_outbox_sync.py' \
    ! -name 'test_neuromod_wiring.py' \
    | sort
}

echo "== group A: django-backed unit suites =="
# shellcheck disable=SC2046
$PY -m pytest -q --tb=line $(collect)

echo "== group B: no_django neuromod suite =="
$PY -m pytest -q --tb=line tests/unit/test_neuromod_wiring.py

echo "== rust =="
(cd rust_core && cargo test -q)

echo "ALL GROUPS GREEN"
