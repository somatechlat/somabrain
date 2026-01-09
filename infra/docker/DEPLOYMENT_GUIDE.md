# SomaBrain Infrastructure Deployment Guide

**Document ID**: SOMABRAIN-DEPLOY-001  
**Version**: 2.0.0  
**Last Updated**: 2026-01-09  
**Status**: Verified ✅

---

## Overview

SomaBrain provides the cognitive processing layer for the SOMA architecture. This guide covers all deployment methods.

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | 25.0+ |
| RAM | 8GB | 16GB |
| Disk | 20GB | 40GB |
| CPU | 4 cores | 8 cores |

---

## 1. Docker Compose Deployment

### Quick Start

```bash
cd somabrain

# Start all services
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d

# Verify health (wait ~60s for startup)
curl http://localhost:30101/health

# View logs
docker compose -f infra/docker/docker-compose.yml -p somabrain logs -f somabrain_app
```

### Post-Deployment Checklist

```bash
# 1. Check container status
docker ps --filter "name=somabrain" --format "table {{.Names}}\t{{.Status}}"

# 2. Verify API health
curl -s http://localhost:30101/health | jq '.healthy_count'

# 3. Test Rust core availability
docker exec somabrain-somabrain_app-1 python -c "from somabrain.core.rust_bridge import is_rust_available; print('Rust:', is_rust_available())"
```

### Service Ports

| Service | Host Port | Purpose |
|---------|-----------|---------|
| somabrain_app | 30101 | Main API |
| postgres | 30106 | Database |
| redis | 30100 | Cache |
| kafka | 30102 | Message queue |
| milvus | 30119 | Vector store |
| prometheus | 30109 | Metrics |

---

## 2. Tilt Deployment (Kubernetes)

### Prerequisites

```bash
# Install Tilt if not present
brew install tilt-dev/tap/tilt

# Start Minikube
minikube start --cpus=4 --memory=8g
```

### Deploy with Tilt

```bash
cd somabrain

# Start Tilt (opens dashboard at http://localhost:10350)
tilt up --port 10350

# View resources
tilt get resources
```

### Tiltfile Features

- **Live reload**: Code changes auto-sync to containers
- **Build acceleration**: Layer caching for Rust + Python
- **Port forwarding**: Automatic port-forward to local

---

## 3. Kubernetes (Production)

### Prerequisites

```bash
# Ensure kubectl is configured
kubectl cluster-info

# Create namespace
kubectl create namespace somabrain
```

### Deploy

```bash
cd somabrain/infra/k8s

# Apply ConfigMaps and Secrets
kubectl apply -f configmap.yaml -n somabrain
kubectl apply -f secrets.yaml -n somabrain

# Deploy infrastructure
kubectl apply -f postgres.yaml -n somabrain
kubectl apply -f redis.yaml -n somabrain
kubectl apply -f kafka.yaml -n somabrain
kubectl apply -f milvus.yaml -n somabrain

# Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=postgres -n somabrain --timeout=120s

# Deploy application
kubectl apply -f somabrain-api.yaml -n somabrain

# Verify
kubectl get pods -n somabrain
```

---

## 4. Connecting to SomaFractalMemory

SomaBrain requires SomaFractalMemory for persistent memory storage.

### Configure Connection

Set in `.env` or `docker-compose.yml`:

```bash
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:10101
SOMABRAIN_MEMORY_HTTP_TOKEN=dev-token-somastack2024
```

### Verify Connection

```bash
# Test SFM health from SomaBrain container
docker exec somabrain-somabrain_app-1 curl -s http://host.docker.internal:10101/healthz
```

---

## 5. Operations

### Start/Stop

```bash
# Docker Compose
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d
docker compose -f infra/docker/docker-compose.yml -p somabrain down

# Tilt
tilt up
tilt down
```

### Rebuild

```bash
# Rebuild single service
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d --build somabrain_app

# Rebuild with no cache
docker compose -f infra/docker/docker-compose.yml -p somabrain build --no-cache
```

### Logs

```bash
# All services
docker compose -f infra/docker/docker-compose.yml -p somabrain logs -f

# Specific service
docker compose -f infra/docker/docker-compose.yml -p somabrain logs -f somabrain_app
```

---

## 6. Troubleshooting

| Issue | Solution |
|-------|----------|
| Services restarting | Check `KAFKA_BOOTSTRAP_SERVERS` and port defaults |
| Postgres exporter unhealthy | Verify `DATA_SOURCE_NAME` has correct DSN |
| Rust core unavailable | Rebuild with `--no-cache` to recompile |
| Health check timeout | Increase `start_period` in healthcheck |

### Reset Everything

```bash
docker compose -f infra/docker/docker-compose.yml -p somabrain down -v --remove-orphans
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d --build
```

---

## Document Control

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-09 | Added Rust core, Tilt, K8s sections |
| 1.0.0 | 2025-12-01 | Initial Docker deployment |
