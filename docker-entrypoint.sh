#!/bin/sh
# Entrypoint for SomaBrain container

set -e

# If a command is provided, delegate to it immediately (service/worker mode)
if [ "$#" -gt 0 ]; then
  echo "docker-entrypoint: delegating to provided command: $*"
  exec "$@"
fi

# Allow overriding host, port, workers, and extra args
HOST="${SOMABRAIN_HOST:-0.0.0.0}"
PORT="${SOMABRAIN_PORT:-9999}"
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
# Single canonical env: SOMABRAIN_KAFKA_URL (optionally prefixed with kafka://)
KAFKA_BROKER="${SOMABRAIN_KAFKA_URL:-}"
if [ -n "$KAFKA_BROKER" ]; then
  KAFKA_BROKER="${KAFKA_BROKER#kafka://}"
fi
if [ -n "$KAFKA_BROKER" ]; then
  for i in 1 2 3 4 5 6; do
    echo "Attempt $i: checking Kafka broker..."
    python3 scripts/kafka_smoke_test.py --bootstrap-server "$KAFKA_BROKER" --timeout 5 && KAFKA_OK=1 && break || true
    sleep 2
  done
else
  echo "Warning: SOMABRAIN_KAFKA_URL is not set; skipping Kafka smoke test"
fi

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

# Optional: run database migrations (disabled by default). Enable by setting
# SOMABRAIN_AUTO_MIGRATE=1 to execute Alembic upgrade on startup.
if [ "${SOMABRAIN_AUTO_MIGRATE:-}" = "1" ] || [ "${SOMABRAIN_AUTO_MIGRATE:-}" = "true" ]; then
  if command -v alembic >/dev/null 2>&1; then
    echo "Running database migrations (alembic upgrade heads)..."
    (cd /app && alembic -c /app/alembic.ini upgrade heads) || echo "alembic migration failed; continuing"
  else
    echo "Alembic not found on PATH; skipping auto-migrate"
  fi
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

# Initialize runtime singletons (idempotent). Important when backend enforcement is enabled.
# Only run for API mode (no custom command provided).
if [ -x "/app/scripts/initialize_runtime.py" ] || [ -f "/app/scripts/initialize_runtime.py" ]; then
  echo "Running initialize_runtime.py to prepare runtime singletons"
  python3 /app/scripts/initialize_runtime.py || echo "initialize_runtime.py exited with non-zero status"
fi

# Execute uvicorn with graceful shutdown and lifespan support
exec python3 /app/scripts/start_server.py
