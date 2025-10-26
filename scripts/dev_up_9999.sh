#!/usr/bin/env bash
set -euo pipefail
# dev_up_9999.sh - bring up the secondary stack (API on 9999) alongside the default

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

ENVFILE=.env.9999.local

# Sanitize environment so host-level overrides from other stacks don't leak
unset SOMABRAIN_KAFKA_URL || true
unset SOMABRAIN_POSTGRES_DSN || true
unset SOMABRAIN_REDIS_URL || true
unset POSTGRES_USER || true
unset POSTGRES_PASSWORD || true
unset POSTGRES_DB || true
unset KAFKA_CFG_NODE_ID || true
unset KAFKA_CFG_PROCESS_ROLES || true
unset KAFKA_CFG_CONTROLLER_QUORUM_VOTERS || true
unset KAFKA_CFG_LISTENERS || true
unset KAFKA_CFG_ADVERTISED_LISTENERS || true
unset KAFKA_CFG_CONTROLLER_LISTENER_NAMES || true
unset KAFKA_CFG_INTER_BROKER_LISTENER_NAME || true
unset KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP || true
unset KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE || true
unset KAFKA_CFG_NUM_PARTITIONS || true
unset KAFKA_CFG_DEFAULT_REPLICATION_FACTOR || true
unset KAFKA_CFG_OFFSETS_TOPIC_REPLICATION_FACTOR || true
unset KAFKA_CFG_TRANSACTION_STATE_LOG_REPLICATION_FACTOR || true
unset KAFKA_CFG_TRANSACTION_STATE_LOG_MIN_ISR || true
unset KAFKA_CFG_LOG_DIRS || true
unset KAFKA_CFG_LOG_RETENTION_MS || true
unset KAFKA_CFG_LOG_SEGMENT_BYTES || true
unset KAFKA_CFG_LOG_RETENTION_BYTES || true
unset KAFKA_CFG_COMPRESSION_TYPE || true
unset KAFKA_HEAP_OPTS || true
unset KAFKA_CLUSTER_ID || true
unset REDIS_HOST_PORT || true
unset KAFKA_BROKER_HOST_PORT || true
unset KAFKA_EXPORTER_HOST_PORT || true
unset OPA_HOST_PORT || true
unset PROMETHEUS_HOST_PORT || true
unset POSTGRES_HOST_PORT || true
unset POSTGRES_EXPORTER_HOST_PORT || true
unset SOMABRAIN_HOST_PORT || true

if [ ! -f "$ENVFILE" ]; then
  echo "Generating $ENVFILE with fixed host ports for 9999 stack"
  cp .env.9999.local "$ENVFILE"
fi

echo "Using compose project name from docker-compose.9999.yml (somabrain-9999)"

echo "Bringing up the 9999 stack (API on :9999) without touching other projects"
docker compose -p somabrain-9999 -f docker-compose.yml -f docker-compose.9999.yml --env-file "$ENVFILE" up -d --build somabrain_app somabrain_outbox_publisher

# Wait for somabrain health
API_HOST_PORT=9999
echo "Waiting for somabrain (secondary) on http://localhost:${API_HOST_PORT}/health"
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:${API_HOST_PORT}/health" >/dev/null 2>&1; then
    echo "somabrain (9999) healthy"
    break
  fi
  sleep 2
done

echo "Writing ports.9999.json"
python3 - <<'PY'
import json,subprocess
ports={}
services=['somabrain_app','somabrain_redis','somabrain_kafka','somabrain_prometheus','somabrain_postgres','somabrain_kafka_exporter','somabrain_postgres_exporter','somabrain_opa','somabrain_schema_registry']
port_map={'somabrain_app':'9696','somabrain_redis':'6379','somabrain_kafka':'9092','somabrain_prometheus':'9090','somabrain_postgres':'5432','somabrain_kafka_exporter':'9308','somabrain_postgres_exporter':'9187','somabrain_opa':'8181','somabrain_schema_registry':'8081'}
for s in services:
    try:
    out=subprocess.check_output(['docker','compose','-p','somabrain-9999','-f','docker-compose.yml','-f','docker-compose.9999.yml','port',s,port_map[s]], text=True).strip()
        ports[s+'_host_mapping']=out
    except Exception:
        ports[s+'_host_mapping']=''
open('ports.9999.json','w').write(json.dumps(ports,indent=2))
print('wrote ports.9999.json')
PY

echo "Done. Secondary stack is available at http://localhost:9999"
