#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations via Docker Compose one-shot job
# Usage:
#   scripts/migrate_db.sh [--build]
#
# Options:
#   --build   Build the application image before running migrations

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
repo_root="${here%/scripts}"
cd "$repo_root"

if [[ "${1:-}" == "--build" ]]; then
  echo "[migrate] Building somabrain image..."
  docker compose -f docker-compose.yml build somabrain_app somabrain_cog somabrain_outbox_publisher
fi

# Ensure Postgres is up first
echo "[migrate] Starting Postgres (if not already running)..."
docker compose -f docker-compose.yml up -d somabrain_postgres

# Run the one-shot migration job (scoped under the dev profile)
echo "[migrate] Running Alembic upgrade head..."
docker compose -f docker-compose.yml --profile dev run --rm somabrain_db_migrate

echo "[migrate] Done."
