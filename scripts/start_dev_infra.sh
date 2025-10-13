#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Bringing up dev infra via docker-compose..."
docker-compose -f scripts/docker-compose.dev.yml up -d --build

echo "Waiting for services to be healthy..."
# Wait for Redis
for i in {1..30}; do
  if docker exec $(docker-compose -f scripts/docker-compose.dev.yml ps -q redis) redis-cli ping &>/dev/null; then
    echo "Redis is up"
    break
  fi
  sleep 1
done

# Wait for SomaBrain API
for i in {1..30}; do
  if curl -sSf http://127.0.0.1:9595/health >/dev/null 2>&1; then
    echo "SomaBrain API is up"
    break
  fi
  sleep 1
done

echo "Dev infra started. Exporting env vars for local runs:"
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
export SOMABRAIN_OPA_URL=http://127.0.0.1:8181
export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379

echo "To run tests in strict mode:"
echo "  SOMABRAIN_STRICT_REAL=1 .cleanup-venv/bin/python -m pytest"

echo "Done."
