#!/usr/bin/env bash
set -e

# Start a simple mock memory service in the background on an alternative port
# to avoid conflicts with any existing service on 9595.
MOCK_PORT=9596
export SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:${MOCK_PORT}"
uvicorn scripts.mock_memory:app --host 0.0.0.0 --port $MOCK_PORT &
MEM_PID=$!
# Wait for the mock service to be ready
sleep 2

# Run the end‑to‑end smoke test against the running SomaBrain API
# Ensure the API container is up (e.g., `docker compose up -d somabrain_app`)
python3 scripts/devprod_smoke.py --url http://localhost:9696

# Clean up the mock memory process
kill $MEM_PID || true
