#!/bin/bash
# Temporary fix: Comment out storage.db imports until these files are refactored to Django ORM
# These files use SQLAlchemy session.query() patterns that need full conversion

set -e

echo "=== Commenting out storage.db imports (temporary workaround) ==="

# List of files with storage.db imports
files=(
  "somabrain/services/outbox_sync.py"
  "somabrain/services/cognitive_loop_service.py"
  "somabrain/cognitive/thread_router.py"
  "somabrain/sleep/policy_sleep_router.py"
  "somabrain/sleep/brain_sleep_router.py"
  "somabrain/sleep/util_sleep_router.py"
  "somabrain/routers/health.py"
  "somabrain/oak/planner.py"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "Processing: $file"
    # Comment out the import line
    sed -i '' 's/^from somabrain\.storage\.db import/# FIXME: Django migration - from somabrain.storage.db import/' "$file"
    sed -i '' 's/^        from somabrain\.storage\.db import/#         FIXME: Django migration - from somabrain.storage.db import/' "$file"
  else
    echo "Warning: $file not found"
  fi
done

echo "=== Done - 8 files marked for Django ORM refactoring ==="
echo "NOTE: These files still use SQLAlchemy patterns and need full conversion"
