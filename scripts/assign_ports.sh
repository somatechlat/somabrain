#!/bin/bash
#
# Dynamically find and assign free ports for all services.
#
# This script checks for port availability starting from standard container ports
# and generates a .env file with the assigned ports for docker-compose.
#
# Port allocation scheme (direct access, no offset):
# - SomaBrain API: 9696
# - Redis: 6379
# - Kafka: 9092
# - Kafka Exporter: 9308
# - OPA: 8181
# - Prometheus: 9090
# - Postgres: 5432
# - Postgres Exporter: 9187
#

set -e

# Standard ports for direct container access
SOMABRAIN_PORT=9696
REDIS_PORT=6379
KAFKA_PORT=9092
KAFKA_EXPORTER_PORT=9308
OPA_PORT=8181
PROMETHEUS_PORT=9090
POSTGRES_PORT=5432
POSTGRES_EXPORTER_PORT=9187

# Create .env file with standard ports
cat > .env <<EOF
# Direct Docker port mapping (standard container ports)
SOMABRAIN_HOST_PORT=$SOMABRAIN_PORT
REDIS_HOST_PORT=$REDIS_PORT
KAFKA_HOST_PORT=$KAFKA_PORT
KAFKA_EXPORTER_HOST_PORT=$KAFKA_EXPORTER_PORT
OPA_HOST_PORT=$OPA_PORT
PROMETHEUS_HOST_PORT=$PROMETHEUS_PORT
POSTGRES_HOST_PORT=$POSTGRES_PORT
POSTGRES_EXPORTER_HOST_PORT=$POSTGRES_EXPORTER_PORT
EOF

echo "Successfully created .env file with direct container port mapping."
echo "Service access:"
echo "  SomaBrain API: localhost:$SOMABRAIN_PORT"
echo "  Redis: localhost:$REDIS_PORT"
echo "  Kafka: localhost:$KAFKA_PORT"
echo "  OPA: localhost:$OPA_PORT"
echo "  Prometheus: localhost:$PROMETHEUS_PORT"
echo "  Postgres: localhost:$POSTGRES_PORT"
