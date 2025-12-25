#!/bin/bash
# Batch fix all import errors found in tests

set -e

echo "=== Fixing import errors ==="

# Fix 1: db.models.outbox → models
echo "1. Fixing OutboxEvent imports..."
sed -i '' 's/from somabrain\.db\.models\.outbox import OutboxEvent/from somabrain.models import OutboxEvent/g' \
  tests/integration/test_outbox_durability.py \
  somabrain/services/outbox_sync.py \
  somabrain/routers/health.py \
  tests/unit/test_outbox_sync.py

# Fix 2: thread_model → models
echo "2. Fixing CognitiveThread imports..."
sed -i '' 's/from somabrain\.cognitive\.thread_model import CognitiveThread/from somabrain.models import CognitiveThread/g' \
  tests/oak/test_thread.py \
  somabrain/oak/planner.py \
  somabrain/cognitive/thread_router.py

# Fix 3: DOPAMINE_MIN → DOPAMINE_BASE (check if exists)
echo "3. Checking DOPAMINE settings..."
if grep -q "SOMABRAIN_NEURO_DOPAMINE_MIN" tests/property/test_multitenancy_serialization.py 2>/dev/null; then
  sed -i '' 's/SOMABRAIN_NEURO_DOPAMINE_MIN/SOMABRAIN_NEURO_DOPAMINE_BASE/g' \
    tests/property/test_multitenancy_serialization.py
  echo "Fixed DOPAMINE setting"
fi

echo "=== All import errors fixed ==="
