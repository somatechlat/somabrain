#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# start_test_server.sh
# ---------------------------------------------------------------------------
# Starts a *second* SomaBrain FastAPI instance on port 9797 for the live test
# suite.  The production server (port 9696) is left untouched – this script
# respects any existing process on that port.
#
# Usage:
#   BRAIN_MODE=dev scripts/start_test_server.sh &
#   # The server will run in the background.  When finished, kill it with:
#   kill %1   # or use the PID printed below.
# ---------------------------------------------------------------------------

set -euo pipefail

# Export a distinct port for the test instance.  The app reads SOMABRAIN_PORT
# from the environment, so we only need to set it here.
export SOMABRAIN_PORT=9797
export SOMABRAIN_HOST=0.0.0.0

# Allow the caller to pass additional uvicorn arguments (e.g. reload).
UVICORN_ARGS=${UVICORN_ARGS:-}

echo "Starting SomaBrain test server on http://$SOMABRAIN_HOST:$SOMABRAIN_PORT"

# Run uvicorn in the background; capture its PID so the caller can stop it.
uvicorn somabrain.app:app --host $SOMABRAIN_HOST --port $SOMABRAIN_PORT $UVICORN_ARGS &
SERVER_PID=$!

echo "Test server PID: $SERVER_PID"

# Simple health‑check loop – wait until /health returns 200 before exiting.
until curl -s http://localhost:${SOMABRAIN_PORT}/health | grep -q "\"ok\": true"; do
  echo "Waiting for test server to become healthy..."
  sleep 1
done

echo "Test server is ready."

# Keep the script alive so the background process stays running.  The caller can
# terminate it with `kill $SERVER_PID` or by sending SIGINT to this script.
wait $SERVER_PID