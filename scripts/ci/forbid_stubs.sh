#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[forbid_stubs] Scanning repository for forbidden stub artifacts..."

# Note: Some environments cannot delete empty directories via automation.
# We rely on content-based checks below to forbid any functional stub code.

forbidden_patterns=(
  "somabrain/memory_stub"
  "from somabrain\.memory_stub"
  "StubPredictor"
  "memory stub (host access)"
)

failed=0
for pat in "${forbidden_patterns[@]}"; do
  if grep -RInE "$pat" \
    --exclude-dir=.git --exclude-dir=.mypy_cache --exclude-dir=.pytest_cache --exclude-dir=.venv \
    --exclude=forbid_stubs.sh \
    . >/dev/null 2>&1; then
    echo "[forbid_stubs] Found forbidden pattern: $pat"
    grep -RInE "$pat" \
      --exclude-dir=.git --exclude-dir=.mypy_cache --exclude-dir=.pytest_cache --exclude-dir=.venv \
      --exclude=forbid_stubs.sh \
      . | sed 's/^/  /'
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "[forbid_stubs] ERROR: Stub artifacts detected. Please remove them before merging."
  exit 2
fi

echo "[forbid_stubs] OK: No stub artifacts detected."