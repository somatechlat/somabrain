#!/usr/bin/env bash
# Wait for services (redis, opa, redpanda) started via docker compose to be healthy.
# Usage: scripts/wait_for_services.sh <timeout_seconds>
set -euo pipefail
TIMEOUT=${1:-60}
SLEEP_INTERVAL=2
elapsed=0
ok_redis=0
ok_opa=0
ok_rp=0
while [ $elapsed -lt $TIMEOUT ]; do
  # Redis
  if docker run --rm --network host redis:7 redis-cli -h 127.0.0.1 ping >/dev/null 2>&1; then
    ok_redis=1
  fi
  # OPA (host port defaults to 30004)
  OPA_HP="${OPA_HOST_PORT:-30004}"
  if curl -sf "http://127.0.0.1:${OPA_HP}/health" >/dev/null 2>&1; then
    ok_opa=1
  fi
  # Redpanda (kafka)
  if nc -z 127.0.0.1 9092 >/dev/null 2>&1; then
    ok_rp=1
  fi
  if [ $ok_redis -eq 1 ] && [ $ok_opa -eq 1 ] && [ $ok_rp -eq 1 ]; then
    echo "All services are healthy"
    exit 0
  fi
  sleep $SLEEP_INTERVAL
  elapsed=$((elapsed + SLEEP_INTERVAL))
done
# If we reach here, dump some diagnostic info
echo "Timeout waiting for services (elapsed=${elapsed}s)" >&2
exit 2
