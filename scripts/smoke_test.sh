#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test for a running SomaBrain instance. Checks /health and /metrics.
# Usage: ./scripts/smoke_test.sh [BASE_URL]
# Example: ./scripts/smoke_test.sh http://127.0.0.1:9696

BASE_URL=${1:-http://127.0.0.1:9696}
MAX_RETRIES=10
SLEEP=2

echo "Smoke test: $BASE_URL/health and $BASE_URL/metrics"

for i in $(seq 1 "$MAX_RETRIES"); do
  if curl -fsS "$BASE_URL/health" >/dev/null; then
    echo "health OK"
    break
  else
    echo "health not ready (attempt $i/$MAX_RETRIES)"
    sleep "$SLEEP"
  fi
  if [ "$i" -eq "$MAX_RETRIES" ]; then
    echo "health endpoint did not become ready after $MAX_RETRIES attempts" >&2
    exit 1
  fi
done

if ! curl -fsS "$BASE_URL/metrics" >/dev/null; then
  echo "metrics endpoint failed" >&2
  exit 2
fi

echo "Smoke test passed"
