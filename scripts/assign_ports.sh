#!/bin/bash
#
# Dynamically find and assign free ports for all services.
#
# This script checks for port availability starting from a base port (50000)
# and generates a .env file with the assigned ports for docker-compose.
#

set -e

# Base port for service assignments
BASE_PORT=50000

# Function to find the next available port
find_free_port() {
    local port=$1
    while nc -z localhost $port; do
        port=$((port + 1))
    done
    echo $port
}

# Assign ports for all services
REDIS_PORT=$(find_free_port $BASE_PORT)
KAFKA_PORT=$(find_free_port $((REDIS_PORT + 1)))
POSTGRES_PORT=$(find_free_port $((KAFKA_PORT + 1)))
PROMETHEUS_PORT=$(find_free_port $((POSTGRES_PORT + 1)))
SOMABRAIN_PORT=9696
OPA_PORT=$(find_free_port $((PROMETHEUS_PORT + 2)))
KAFKA_EXPORTER_PORT=$(find_free_port $((OPA_PORT + 1)))
POSTGRES_EXPORTER_PORT=$(find_free_port $((KAFKA_EXPORTER_PORT + 1)))

# Create .env file
cat > .env <<EOF
REDIS_HOST_PORT=$REDIS_PORT
KAFKA_HOST_PORT=$KAFKA_PORT
POSTGRES_HOST_PORT=$POSTGRES_PORT
PROMETHEUS_HOST_PORT=$PROMETHEUS_PORT
SOMABRAIN_HOST_PORT=$SOMABRAIN_PORT
OPA_HOST_PORT=$OPA_PORT
KAFKA_EXPORTER_HOST_PORT=$KAFKA_EXPORTER_PORT
POSTGRES_EXPORTER_HOST_PORT=$POSTGRES_EXPORTER_PORT
EOF

echo "Successfully assigned ports and created .env file."
