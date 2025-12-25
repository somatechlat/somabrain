#!/usr/bin/env bash
set -e

# End-to-end memory test script
# VIBE CODING RULES: This script requires a REAL memory service to be running.
# No mocks or stubs are permitted.

# Verify the real memory service is available
MEMORY_ENDPOINT="${SOMABRAIN_MEMORY_HTTP_ENDPOINT:-http://localhost:9595}"

echo "Checking real memory service at ${MEMORY_ENDPOINT}..."
if ! curl -sf "${MEMORY_ENDPOINT}/health" > /dev/null 2>&1; then
    echo "ERROR: Real memory service not available at ${MEMORY_ENDPOINT}"
    echo "Please start the memory service before running this test."
    echo "See README.md for instructions on starting the memory backend."
    exit 1
fi

echo "Memory service health check passed."

# Run the end-to-end smoke test against the running SomaBrain API
# Ensure the API container is up (e.g., docker compose up -d somabrain_app)
python3 scripts/devprod_smoke.py --url http://localhost:9696

echo "E2E test completed successfully."
