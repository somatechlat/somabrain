# SomaBrain Docker Deployment

## Overview
This directory contains the Docker Compose configuration for local development and E2E testing. Configuration mirrors the Kubernetes manifests in `../k8s/` exactly.

## Prerequisites
- Docker Engine 24+
- Docker Compose v2+
- 12GB+ available RAM

## Quick Start
```bash
# From project root
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d

# Verify health
curl http://localhost:20020/health

# View logs
docker logs somabrain-somabrain-api-1 -f
```

## Services

| Service | Image | Port (Host) | Port (Container) | Memory |
|---------|-------|-------------|------------------|--------|
| somabrain-api | Built from Dockerfile | 20020 | 20020 | 2Gi |
| postgres | postgres:15-alpine | 30106 | 5432 | 2Gi |
| redis | redis:7-alpine | 30100 | 6379 | 1Gi |
| kafka | apache/kafka:3.7.0 | 30102 | 9092 | 2Gi |
| milvus | milvusdb/milvus:v2.3.9 | 30119 | 19530 | 4Gi |

## Environment Variables
| Variable | Value | Description |
|----------|-------|-------------|
| `SOMABRAIN_POSTGRES_DSN` | `postgresql://soma:soma_pass@postgres:5432/somabrain` | PostgreSQL connection |
| `SOMABRAIN_REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `SOMABRAIN_KAFKA_URL` | `kafka:9092` | Kafka bootstrap servers |
| `SOMABRAIN_MILVUS_HOST` | `milvus` | Milvus host |
| `SOMABRAIN_MILVUS_PORT` | `19530` | Milvus port |

## Commands

```bash
# Start stack
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d

# Stop stack
docker compose -f infra/docker/docker-compose.yml -p somabrain down

# Rebuild API only
docker compose -f infra/docker/docker-compose.yml -p somabrain up -d --build somabrain-api

# View all logs
docker compose -f infra/docker/docker-compose.yml -p somabrain logs -f

# Clean up (including volumes)
docker compose -f infra/docker/docker-compose.yml -p somabrain down -v
```

## Troubleshooting

### PostgreSQL connection failed
Verify password matches in both `docker-compose.yml`:
- `POSTGRES_PASSWORD: soma_pass` (postgres service)
- `SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma_pass@...` (somabrain-api service)

### Port conflicts
Change host ports in `docker-compose.yml` if 30xxx range is occupied.

### Build cache issues
```bash
docker compose -f infra/docker/docker-compose.yml -p somabrain build --no-cache
```
