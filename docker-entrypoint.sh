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
PORT="${SOMABRAIN_PORT:-9696}"
WORKERS="${SOMABRAIN_WORKERS:-1}"
EXTRA_ARGS="${SOMABRAIN_EXTRA_ARGS}"

# Print config for debugging
echo "Starting SomaBrain API on $HOST:$PORT with $WORKERS worker(s)"
echo "SOMABRAIN container starting on host: ${SOMABRAIN_HOST}, port: ${SOMABRAIN_PORT}"

# Wait for critical dependencies (Kafka broker and OPA) to be reachable before starting.
# In development mode we allow Kafka to be optional. Set SOMABRAIN_REQUIRE_KAFKA=0
# to skip the Kafka check. OPA is still required because the auth layer depends on it.
echo "Checking dependencies: Kafka and OPA (fail-fast)"
KAFKA_OK=0
OPA_OK=0

# Determine whether we should enforce Kafka reachability.
REQUIRE_KAFKA="${SOMABRAIN_REQUIRE_KAFKA:-1}"

# Use the real Kafka smoke test for health check when required.
KAFKA_BROKER="${SOMABRAIN_KAFKA_URL:-}"
if [ -n "$KAFKA_BROKER" ]; then
  KAFKA_BROKER="${KAFKA_BROKER#kafka://}"
fi
if [ "$REQUIRE_KAFKA" = "1" ] && [ -n "$KAFKA_BROKER" ]; then
  for i in 1 2 3 4 5 6; do
    echo "Attempt $i: checking Kafka broker..."
    python3 scripts/kafka_smoke_test.py --bootstrap-server "$KAFKA_BROKER" --timeout 5 && KAFKA_OK=1 && break || true
    sleep 2
  done
else
  echo "Skipping Kafka check (SOMABRAIN_REQUIRE_KAFKA=$REQUIRE_KAFKA)"
  KAFKA_OK=1
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
  echo "ERROR: Kafka bootstrap not reachable; refusing to start (no fallbacks)." >&2
  exit 1
fi
if [ "$OPA_OK" -ne 1 ]; then
  echo "ERROR: OPA not reachable; refusing to start (no fallbacks)." >&2
  exit 1
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

# Note: demo seeding via scripts/docker_demo_seed.sh has been removed to avoid referencing
# non-existent scripts. If needed in the future, reintroduce a seeded data helper explicitly.

# Initialize runtime singletons (idempotent). Important when backend enforcement is enabled.
# Only run for API mode (no custom command provided).
if [ -x "/app/scripts/initialize_runtime.py" ] || [ -f "/app/scripts/initialize_runtime.py" ]; then
  echo "Running initialize_runtime.py to prepare runtime singletons"
  python3 /app/scripts/initialize_runtime.py || echo "initialize_runtime.py exited with non-zero status"
fi

# Execute uvicorn with graceful shutdown and lifespan support
exec python3 /app/scripts/start_server.py
