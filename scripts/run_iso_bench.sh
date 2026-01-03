#!/bin/bash

# ISO Workbench Runner
# Organizes and runs the Certified Verification Suite

# 1. Load Environment & Defaults
export DJANGO_SETTINGS_MODULE=somabrain.settings
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:10101
export SOMA_MILVUS_PORT=20530
export MILVUS_PORT=20530
export SOMA_REDIS_PORT=20379

echo "🚀 Launching ISO 25010 Verification Workbench..."
echo "📂 Configuration: tests/integration/infra_config.py"
echo "---------------------------------------------------"

# 2. Execute ISO Infrastructure Suite
echo ">> Domain 1: Real Infrastructure (ISO Reliability/Security)"
.venv/bin/pytest tests/integration/test_infrastructure_iso.py -v -W ignore
INFRA_EXIT=$?

# 3. Execute End-to-End Memory Flow
echo "---------------------------------------------------"
echo ">> Domain 2: Business Logic Interoperability (E2E Memory)"
# Note: Using -k to select specific e2e test to avoid workbench noise
.venv/bin/pytest tests/integration/test_memory_e2e.py -v -W ignore
E2E_EXIT=$?

echo "---------------------------------------------------"
if [ $INFRA_EXIT -eq 0 ] && [ $E2E_EXIT -eq 0 ]; then
    echo "✅ WORKBENCH STATUS: GREEN (Passed All Domains)"
    exit 0
else
    echo "❌ WORKBENCH STATUS: RED (Failures Detected)"
    exit 1
fi
