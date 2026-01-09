# SomaBrain Docker Deployment Guide

**Document ID**: SOMA-DEPLOY-DOCKER-001  
**Version**: 1.0.0  
**Last Updated**: 2026-01-09  
**Status**: Verified ✅

---

## 1. Overview

This guide provides step-by-step instructions for deploying SomaBrain using Docker Compose. The deployment includes 16 containerized services providing a complete cognitive architecture platform.

### 1.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | 25.0+ |
| Docker Compose | v2.20+ | v2.24+ |
| RAM | 8GB | 16GB |
| Disk | 20GB | 50GB |
| CPU | 4 cores | 8 cores |

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SomaBrain Cluster                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  App (API)  │  │    Cog      │  │  Outbox Publisher   │  │
│  │   :30101    │  │  (Async)    │  │    (Kafka)          │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│  ┌──────▼────────────────▼─────────────────────▼──────────┐ │
│  │                Infrastructure Layer                     │ │
│  │  PostgreSQL │ Redis │ Kafka │ Milvus │ OPA │ MinIO     │ │
│  │   :30106    │       │:30102 │        │     │           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Quick Start (5 Minutes)

### Step 1: Navigate to Infrastructure Directory

```bash
cd /path/to/somabrain/infra/docker
```

### Step 2: Start All Services

```bash
docker compose -p somabrain up -d
```

### Step 3: Verify Deployment

```bash
# Check container status
docker compose -p somabrain ps

# Verify health endpoint
curl http://localhost:30101/healthz
# Expected: {"status": "healthy", "timestamp": "..."}

# Verify comprehensive health
curl http://localhost:30101/health
# Expected: {"status": "ok", "healthy_count": 10, ...}
```

---

## 3. Detailed Deployment Steps

### 3.1 Pre-Deployment Verification

```bash
# Verify Docker version
docker --version  # Should be 24.0+

# Verify Docker Compose version
docker compose version  # Should be v2.20+

# Check available resources
docker system info | grep -E "(CPUs|Total Memory)"
```

### 3.2 Clone Repository

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
git checkout somabrain-rust
```

### 3.3 Build and Start Services

```bash
cd infra/docker

# Build images (first time or after code changes)
docker compose -p somabrain build

# Start all services
docker compose -p somabrain up -d

# View logs
docker compose -p somabrain logs -f somabrain_app
```

### 3.4 Wait for Health Checks

```bash
# Wait for all services to be healthy (approx. 60-90 seconds)
watch -n 5 'docker compose -p somabrain ps'
```

---

## 4. Service Reference

### 4.1 Port Mapping

| Service | Host Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| somabrain_app | 30101 | 9696 | Main API |
| kafka | 30102 | 9094 | Message broker |
| prometheus | 30105 | 9090 | Metrics |
| postgres | 30106 | 5432 | Database |
| postgres_exporter | 30107 | 9187 | DB metrics |
| kafka_exporter | 30108 | 9308 | Kafka metrics |
| jaeger | 30109 | 16686 | Tracing UI |

### 4.2 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| PostgreSQL | somabrain | somabrain |
| Supervisor | admin | soma |

### 4.3 Environment Variables

All environment variables have sensible defaults for local development:

```yaml
POSTGRES_USER: somabrain
POSTGRES_PASSWORD: somabrain
POSTGRES_DB: somabrain
SOMABRAIN_POSTGRES_DSN: postgresql://somabrain:somabrain@somabrain_postgres:5432/somabrain
SOMABRAIN_REDIS_URL: redis://somabrain_redis:6379/0
SOMABRAIN_OPA_URL: http://somabrain_opa:8181
KAFKA_BROKER_CONTAINER_PORT: 9092
```

---

## 5. Verification Commands

### 5.1 Health Checks

```bash
# Basic health (Kubernetes liveness probe)
curl http://localhost:30101/healthz

# Comprehensive health (all backends)
curl http://localhost:30101/health | jq

# API documentation
open http://localhost:30101/api/docs
```

### 5.2 Service-Specific Verification

```bash
# PostgreSQL
docker exec somabrain-somabrain_postgres-1 pg_isready -U somabrain

# Redis
docker exec somabrain-somabrain_redis-1 redis-cli ping

# Kafka (list topics)
docker exec somabrain-somabrain_kafka-1 kafka-topics --bootstrap-server localhost:9092 --list

# Milvus (check collections)
curl http://localhost:19530/v1/vector/collections
```

---

## 6. Operations

### 6.1 Stopping Services

```bash
# Stop all services (preserve data)
docker compose -p somabrain down

# Stop and remove volumes (DESTRUCTIVE)
docker compose -p somabrain down -v
```

### 6.2 Restarting Services

```bash
# Restart a specific service
docker compose -p somabrain restart somabrain_app

# Rebuild and restart
docker compose -p somabrain up -d --build somabrain_app
```

### 6.3 Viewing Logs

```bash
# All services
docker compose -p somabrain logs -f

# Specific service
docker compose -p somabrain logs -f somabrain_app

# Last 100 lines
docker compose -p somabrain logs --tail 100 somabrain_app
```

### 6.4 Scaling (Development Only)

```bash
# Scale cog workers
docker compose -p somabrain up -d --scale somabrain_cog=3
```

---

## 7. Troubleshooting

### 7.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Port already allocated | Previous deployment running | `docker compose -p somabrain down --remove-orphans` |
| Container restarting | Missing env vars | Check logs: `docker logs <container>` |
| Postgres unhealthy | Password not set | Verify `POSTGRES_PASSWORD` default is set |
| Kafka not connecting | Wrong port | Ensure `KAFKA_BROKER_CONTAINER_PORT: 9092` |
| OPA unreachable | URL not set | Verify `SOMABRAIN_OPA_URL` default |

### 7.2 Reset Everything

```bash
# Nuclear option - removes ALL data
docker compose -p somabrain down -v --remove-orphans
docker system prune -f
docker compose -p somabrain up -d --build
```

---

## 8. Production Considerations

> [!WARNING]
> This docker-compose is designed for **development and testing**. For production:

1. **Use external databases**: PostgreSQL, Redis should be managed services
2. **Configure secrets**: Use Docker secrets or external vault
3. **Enable TLS**: Configure SSL certificates for all endpoints
4. **Set resource limits**: Configure memory/CPU limits per service
5. **Use Kubernetes**: See `infra/k8s/DEPLOYMENT_GUIDE.md`

---

## Appendix A: File Structure

```
infra/docker/
├── docker-compose.yml      # Main orchestration file
├── Dockerfile              # Multi-stage build for Python app
├── docker-entrypoint.sh    # Container startup script
├── .dockerignore           # Build context exclusions
├── README.md               # Quick reference
└── DEPLOYMENT_GUIDE.md     # This file
```

---

## Appendix B: Verified Health Output

```json
{
  "status": "ok",
  "healthy_count": 10,
  "degraded_count": 0,
  "unhealthy_count": 2,
  "infrastructure": {
    "postgresql": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "kafka": {"status": "healthy"},
    "milvus": {"status": "healthy"},
    "opa": {"status": "healthy"},
    "minio": {"status": "healthy"}
  },
  "internal_services": {
    "cognitive": {"status": "healthy"},
    "embedder": {"status": "healthy"}
  }
}
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-09 | Vibe Collective | Initial verified deployment |
