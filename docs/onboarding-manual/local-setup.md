# Local Setup Guide

This document provides a step-by-step guide for setting up a local development environment for SomaBrain.

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- `pip` and `virtualenv`

## 1. Clone the Repository

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
```

## 2. Set Up the Environment

Create a `.env` file in the root of the repository with the following content:

```
# PostgreSQL
POSTGRES_USER=soma
POSTGRES_PASSWORD=soma
POSTGRES_DB=somabrain

# Redis
REDIS_HOST_PORT=30100
REDIS_CONTAINER_PORT=6379

# Kafka
KAFKA_BROKER_HOST_PORT=30102
KAFKA_BROKER_CONTAINER_PORT=9092

# OPA
OPA_HOST_PORT=30104
OPA_CONTAINER_PORT=8181

# Prometheus
PROMETHEUS_HOST_PORT=30105
PROMETHEUS_CONTAINER_PORT=9090

# SomaBrain API
SOMABRAIN_HOST_PORT=9696
SOMABRAIN_PORT=9696

# External Memory Service
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595
SOMABRAIN_MEMORY_HTTP_TOKEN=
```

## 3. Start the Services

Use Docker Compose to start all the required services:

```bash
docker compose up -d
```

This will start the following services:
- `somabrain_redis`
- `somabrain_kafka`
- `somabrain_opa`
- `somabrain_prometheus`
- `somabrain_postgres`
- `somabrain_app`

## 4. Verify the Setup

You can verify that all services are running correctly by checking the health endpoint:

```bash
curl -s http://localhost:9696/health | jq
```

You should see a response with `"ok": true`.

## 5. Running Tests

To run the tests, first install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Then, run the tests using `pytest`:

```bash
python -m pytest
```
