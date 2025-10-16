#!/bin/bash
#
# Dynamically find and assign free ports for all services.
#
# This script checks for port availability starting from the Docker range (30000+)
# and generates a .env file with the assigned ports for docker-compose.
#
# Port allocation scheme:
# - SomaBrain API: 30000
# - Redis: 30001
# - Kafka: 30002
# - Kafka Exporter: 30003
# - OPA: 30004
# - Prometheus: 30005
# - Postgres: 30006
# - Postgres Exporter: 30007
#

set -e

# Base port for Docker service assignments (30000+ range)
BASE_PORT=30000

# Function to find the next available port
find_free_port() {
    local port=$1
    while nc -z localhost $port 2>/dev/null; do
        port=$((port + 1))
    done
    echo $port
}

# Assign ports for all services
SOMABRAIN_PORT=$(find_free_port $BASE_PORT)
REDIS_PORT=$(find_free_port $((SOMABRAIN_PORT + 1)))
KAFKA_PORT=$(find_free_port $((REDIS_PORT + 1)))
KAFKA_EXPORTER_PORT=$(find_free_port $((KAFKA_PORT + 1)))
OPA_PORT=$(find_free_port $((KAFKA_EXPORTER_PORT + 1)))
PROMETHEUS_PORT=$(find_free_port $((OPA_PORT + 1)))
POSTGRES_PORT=$(find_free_port $((PROMETHEUS_PORT + 1)))
POSTGRES_EXPORTER_PORT=$(find_free_port $((POSTGRES_PORT + 1)))

# Create .env file
cat > .env <<EOF
# Docker host port mapping (30000+ range)
SOMABRAIN_HOST_PORT=$SOMABRAIN_PORT
REDIS_HOST_PORT=$REDIS_PORT
KAFKA_HOST_PORT=$KAFKA_PORT
KAFKA_EXPORTER_HOST_PORT=$KAFKA_EXPORTER_PORT
OPA_HOST_PORT=$OPA_PORT
PROMETHEUS_HOST_PORT=$PROMETHEUS_PORT
POSTGRES_HOST_PORT=$POSTGRES_PORT
POSTGRES_EXPORTER_HOST_PORT=$POSTGRES_EXPORTER_PORT
EOF

echo "Successfully assigned Docker ports and created .env file."
echo "Service port mapping:"
echo "  SomaBrain API: localhost:$SOMABRAIN_PORT"
echo "  Redis: localhost:$REDIS_PORT"
echo "  Kafka: localhost:$KAFKA_PORT"
echo "  OPA: localhost:$OPA_PORT"
echo "  Prometheus: localhost:$PROMETHEUS_PORT"
echo "  Postgres: localhost:$POSTGRES_PORT"
