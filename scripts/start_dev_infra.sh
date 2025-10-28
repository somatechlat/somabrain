#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose.yml"
ENV_FILE="${1:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file '$ENV_FILE' not found. Please create it (see .env template)." >&2
  exit 1
fi

echo "Bringing up SomaBrain dev infra via docker compose..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build somabrain_app

echo "Waiting for services to be healthy..."

# Wait for Redis container health
for i in {1..40}; do
  REDIS_ID=$(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps -q somabrain_redis || true)
  if [[ -n "$REDIS_ID" ]] && docker inspect --format='{{.State.Health.Status}}' "$REDIS_ID" 2>/dev/null | grep -q "healthy"; then
    echo "Redis is up"
    break
  fi
  sleep 1
done

# Determine host port for health probes
HOST_PORT=$(grep '^SOMABRAIN_HOST_PORT=' "$ENV_FILE" | tail -n1 | cut -d= -f2)
HOST_PORT=${HOST_PORT:-9696}

# Wait for SomaBrain API health endpoint
for i in {1..60}; do
  if curl -sSf "http://127.0.0.1:${HOST_PORT}/health" >/dev/null 2>&1; then
    echo "SomaBrain API is up"
    break
  fi
  sleep 2
done

echo "Dev infra started. Key environment values:"
echo "  SOMABRAIN_HOST_PORT=${HOST_PORT}"
echo "  SOMABRAIN_MEMORY_HTTP_ENDPOINT=$(grep '^SOMABRAIN_MEMORY_HTTP_ENDPOINT=' "$ENV_FILE" | tail -n1 | cut -d= -f2)"
echo "  SOMABRAIN_REDIS_URL=$(grep '^SOMABRAIN_REDIS_URL=' "$ENV_FILE" | tail -n1 | cut -d= -f2)"

echo "To run tests with backend enforcement:"
echo "  SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1 .cleanup-venv/bin/python -m pytest"

echo "Done."
