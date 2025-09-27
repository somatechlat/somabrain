#!/bin/sh
# Entrypoint for SomaBrain container

set -e

# Allow overriding host, port, workers, and extra args
HOST="${SOMABRAIN_HOST:-0.0.0.0}"
PORT="${SOMABRAIN_PORT:-9696}"
WORKERS="${SOMABRAIN_WORKERS:-1}"
EXTRA_ARGS="${SOMABRAIN_EXTRA_ARGS}"

# Print config for debugging
echo "Starting SomaBrain API on $HOST:$PORT with $WORKERS worker(s)"
echo "SOMABRAIN container starting on host: ${SOMABRAIN_HOST}, port: ${SOMABRAIN_PORT}"

# Wait for critical dependencies (Kafka broker and OPA) to be reachable before starting
echo "Checking dependencies: Kafka and OPA"
KAFKA_OK=0
OPA_OK=0

# Use the real Kafka smoke test for health check
KAFKA_BROKER="${SOMABRAIN_KAFKA_HOST:-kafka}:${SOMABRAIN_KAFKA_PORT:-9092}"
for i in 1 2 3 4 5 6; do
  echo "Attempt $i: checking Kafka broker..."
  python3 scripts/kafka_smoke_test.py --bootstrap-server "$KAFKA_BROKER" --timeout 5 && KAFKA_OK=1 && break || true
  sleep 2
done

for i in 1 2 3 4 5 6; do
  echo "Attempt $i: checking OPA readiness..."
  if curl -fsS "${SOMABRAIN_OPA_URL:-http://opa:8181}/health" >/dev/null 2>&1; then
    OPA_OK=1
    break
  fi
  sleep 2
done

if [ "$KAFKA_OK" -ne 1 ]; then
  echo "Warning: Kafka bootstrap not reachable; the app will still start but audit may fallback to journal"
fi
if [ "$OPA_OK" -ne 1 ]; then
  echo "Warning: OPA not reachable; the app will still start but policy checks may fail closed"
fi

# Optional demo seed: when SOMABRAIN_DEMO_SEED=true, seed a few memories after startup.
# Runs in background to avoid blocking the server.
if [ "${SOMABRAIN_DEMO_SEED:-}" = "true" ] || [ "${SOMABRAIN_DEMO_SEED:-}" = "1" ]; then
  (
    sleep 2
    SEED_HOST="${HOST}"
    SEED_PORT="${PORT}"
    sh scripts/docker_demo_seed.sh "$SEED_HOST" "$SEED_PORT" || true
  ) &
fi

# Execute uvicorn with graceful shutdown and lifespan support
exec uvicorn somabrain.app:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS" \
  --timeout-keep-alive 5 \
  --proxy-headers \
  $EXTRA_ARGS
