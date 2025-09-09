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
