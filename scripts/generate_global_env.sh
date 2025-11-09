#!/usr/bin/env bash
set -euo pipefail

# Generate a .env file from .env.example if missing and print a brief summary.
# Safe to re-run; will not overwrite an existing .env unless --force is passed.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
EXAMPLE="${ROOT_DIR}/.env.example"
TARGET="${ROOT_DIR}/.env"
FORCE=${1:-}

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "ERROR: .env.example not found at ${EXAMPLE}" >&2
  exit 1
fi

if [[ -f "${TARGET}" && "${FORCE}" != "--force" ]]; then
  echo "Found existing .env; pass --force to overwrite. No changes made."
else
  cp "${EXAMPLE}" "${TARGET}"
  echo "Wrote ${TARGET} from template."
fi

# Print a compact port summary for awareness
set +e
REDIS_HOST_PORT=$(grep -E '^REDIS_HOST_PORT=' "${TARGET}" | cut -d= -f2)
KAFKA_BROKER_HOST_PORT=$(grep -E '^KAFKA_BROKER_HOST_PORT=' "${TARGET}" | cut -d= -f2)
OPA_HOST_PORT=$(grep -E '^OPA_HOST_PORT=' "${TARGET}" | cut -d= -f2)
PROMETHEUS_HOST_PORT=$(grep -E '^PROMETHEUS_HOST_PORT=' "${TARGET}" | cut -d= -f2)
POSTGRES_HOST_PORT=$(grep -E '^POSTGRES_HOST_PORT=' "${TARGET}" | cut -d= -f2)
POSTGRES_EXPORTER_HOST_PORT=$(grep -E '^POSTGRES_EXPORTER_HOST_PORT=' "${TARGET}" | cut -d= -f2)
SOMABRAIN_HOST_PORT=$(grep -E '^SOMABRAIN_HOST_PORT=' "${TARGET}" | cut -d= -f2)
set -e

cat <<EOF

Environment summary:
- Redis:        http://127.0.0.1:${REDIS_HOST_PORT}
- Kafka (port): ${KAFKA_BROKER_HOST_PORT}
- OPA:          http://127.0.0.1:${OPA_HOST_PORT}/health?plugins
- Prometheus:   http://127.0.0.1:${PROMETHEUS_HOST_PORT}
- Postgres:     localhost:${POSTGRES_HOST_PORT}
- Pg Exporter:  http://127.0.0.1:${POSTGRES_EXPORTER_HOST_PORT}
- SomaBrain:    http://127.0.0.1:${SOMABRAIN_HOST_PORT}

Next steps:
- docker compose --env-file ./.env -f docker-compose.yml up -d --build somabrain_app
- curl -fsS http://127.0.0.1:${SOMABRAIN_HOST_PORT}/healthz | jq .
EOF
