#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Default local port/backends (prod-like but constrained)
: "${REDIS_HOST_PORT:=30100}"
: "${REDIS_CONTAINER_PORT:=6379}"
: "${POSTGRES_HOST_PORT:=30106}"
: "${POSTGRES_CONTAINER_PORT:=5432}"
: "${POSTGRES_USER:=somabrain}"
: "${POSTGRES_PASSWORD:=somabrain}"
: "${POSTGRES_DB:=somabrain}"
: "${KAFKA_BROKER_HOST_PORT:=30102}"
: "${KAFKA_BROKER_CONTAINER_PORT:=9092}"
: "${KAFKA_EXPORTER_HOST_PORT:=30103}"
: "${KAFKA_EXPORTER_CONTAINER_PORT:=9308}"
: "${OPA_HOST_PORT:=30104}"
: "${OPA_CONTAINER_PORT:=8181}"
: "${PROMETHEUS_HOST_PORT:=30105}"
: "${PROMETHEUS_CONTAINER_PORT:=9090}"
: "${POSTGRES_EXPORTER_HOST_PORT:=30107}"
: "${POSTGRES_EXPORTER_CONTAINER_PORT:=9187}"
: "${SOMABRAIN_PORT:=9696}"
: "${SOMABRAIN_HOST_PORT:=9696}"
: "${INTEGRATOR_HEALTH_HOST_PORT:=30115}"
: "${SOMABRAIN_INTEGRATOR_HEALTH_PORT:=9015}"
: "${SEGMENTATION_HEALTH_HOST_PORT:=30116}"
: "${SOMABRAIN_SEGMENTATION_HEALTH_PORT:=9016}"

export REDIS_HOST_PORT REDIS_CONTAINER_PORT \
  POSTGRES_HOST_PORT POSTGRES_CONTAINER_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB \
  KAFKA_BROKER_HOST_PORT KAFKA_BROKER_CONTAINER_PORT KAFKA_EXPORTER_HOST_PORT KAFKA_EXPORTER_CONTAINER_PORT \
  OPA_HOST_PORT OPA_CONTAINER_PORT PROMETHEUS_HOST_PORT PROMETHEUS_CONTAINER_PORT \
  POSTGRES_EXPORTER_HOST_PORT POSTGRES_EXPORTER_CONTAINER_PORT \
  SOMABRAIN_PORT SOMABRAIN_HOST_PORT INTEGRATOR_HEALTH_HOST_PORT SOMABRAIN_INTEGRATOR_HEALTH_PORT \
  SEGMENTATION_HEALTH_HOST_PORT SOMABRAIN_SEGMENTATION_HEALTH_PORT

# Ensure required binaries
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
command -v docker-compose >/dev/null || { echo "docker-compose not found"; exit 1; }

echo "[preflight] checking required environment variables"
required_vars=(
  SOMABRAIN_KAFKA_URL
  SOMABRAIN_POSTGRES_DSN
  SOMABRAIN_REDIS_URL
  SOMABRAIN_MEMORY_HTTP_ENDPOINT
)
missing=0
for v in "${required_vars[@]}"; do
  if [ -z "${!v:-}" ]; then
    echo "  missing: $v"
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "[preflight] set the required variables (see config/env.example)"; exit 1;
fi

echo "[preflight] checking memory backend at ${SOMABRAIN_MEMORY_HTTP_ENDPOINT}"
mem_auth=()
if [ -n "${SOMABRAIN_MEMORY_HTTP_TOKEN:-}" ]; then
  mem_auth=(-H "Authorization: Bearer ${SOMABRAIN_MEMORY_HTTP_TOKEN}")
fi
if ! curl -fsS "${mem_auth[@]}" "${SOMABRAIN_MEMORY_HTTP_ENDPOINT%/}/health" >/dev/null 2>&1; then
  echo "[preflight] memory backend not reachable; update SOMABRAIN_MEMORY_HTTP_ENDPOINT/TOKEN"
  exit 1
fi

echo "[preflight] bringing up Kafka"
docker compose up -d somabrain_kafka

echo "[preflight] creating topics"
BOOTSTRAP_INTERNAL="somabrain_kafka:9092"
topics=(
  "${SOMABRAIN_TOPIC_NEXT_EVENT:-cog.next_event}"
  "${SOMABRAIN_TOPIC_CONFIG_UPDATES:-cog.config.updates}"
  "${SOMABRAIN_TOPIC_STATE_UPDATES:-cog.state.updates}"
  "${SOMABRAIN_TOPIC_AGENT_UPDATES:-cog.agent.updates}"
  "${SOMABRAIN_TOPIC_ACTION_UPDATES:-cog.action.updates}"
  "${SOMABRAIN_TOPIC_GLOBAL_FRAME:-cog.global.frame}"
  "${SOMABRAIN_TOPIC_SEGMENTS:-cog.segments}"
  "soma.audit"
)
for t in "${topics[@]}"; do
  docker compose exec -T somabrain_kafka \
    /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic "$t" --bootstrap-server "$BOOTSTRAP_INTERNAL" --replication-factor 1 --partitions 2
done

echo "[preflight] waiting for Kafka to settle"
sleep 5
for t in "${topics[@]}"; do
  docker compose exec -T somabrain_kafka \
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_INTERNAL" --describe --topic "$t" \
    || { echo "[preflight] topic check failed for $t"; exit 1; }
done

echo "[preflight] starting remaining services"
docker compose up -d

echo "[preflight] waiting for health endpoints"
HOST=${SOMABRAIN_HOST:-localhost}
PORT=${SOMABRAIN_PORT:-9696}
INTEGRATOR_PORT=${INTEGRATOR_HEALTH_HOST_PORT:-30115}
SEGMENT_PORT=${SEGMENTATION_HEALTH_HOST_PORT:-30116}

for i in {1..30}; do
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    if curl -fsS "http://localhost:${INTEGRATOR_PORT}/health" >/dev/null 2>&1 && \
       curl -fsS "http://localhost:${SEGMENT_PORT}/health" >/dev/null 2>&1; then
      echo "[preflight] health checks passed"
      exit 0
    fi
  fi
  sleep 2
done

echo "[preflight] health checks did not pass in time"
docker compose logs --tail=200
exit 1
