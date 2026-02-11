# SomaBrain Docker Deployment Guide

> **Document Version**: 2.0.0  
> **Last Updated**: 2026-01-09  
> **Status**: ✅ Verified 100% Healthy

This guide provides step-by-step instructions for deploying SomaBrain with the Rust Core enabled.

---

## Quick Start

```bash
# 1. Clone and navigate
cd /path/to/somabrain

# 2. Start all services
docker compose -f infra/standalone/docker-compose.yml up -d

# 3. Verify health (all 16 services should be healthy)
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| RAM | 8GB | 12GB |
| Disk | 10GB | 20GB |

---

## Step-by-Step Deployment

### Step 1: Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables (optional)
# Key variables:
#   SOMABRAIN_POSTGRES_DSN - PostgreSQL connection string
#   SOMABRAIN_HRR_DIM - Hyperdimensional vector dimension (default: 8192)
#   SOMABRAIN_GLOBAL_SEED - Reproducibility seed (default: 42)
```

### Step 2: Start Core Services

```bash
# Start standalone stack
docker compose -f infra/standalone/docker-compose.yml up -d

# Wait for services to initialize (30-60 seconds)
sleep 30
```

### Step 3: Verify Health

```bash
# Check all containers are healthy
docker compose ps

# Expected output: 16 services, all (healthy)
```

### Step 4: Run Database Migrations

```bash
# Apply Django migrations
docker exec somabrain_standalone_app python manage.py migrate
```

### Step 5: Verify Rust Core

```bash
# Check Rust core is loaded
docker exec somabrain_standalone_app python -c \
  "from somabrain.core.rust_bridge import is_rust_available; print('Rust:', is_rust_available())"

# Expected: Rust: True
```

### Step 6: Test API

```bash
# Health check
curl -s http://localhost:30101/health | python3 -m json.tool

# Check Rust modules
curl -s http://localhost:30101/api/health/diagnostics | python3 -m json.tool
```

---

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| somabrain_standalone_app | 30101 | Main API + Rust Core |
| somabrain_standalone_postgres | 5432 | PostgreSQL database |
| somabrain_standalone_redis | 6379 | Cache + KV store |
| somabrain_standalone_milvus | 19530 | Vector store |
| somabrain_standalone_kafka | 9092 | Event streaming |
| somabrain_standalone_opa | 8181 | Policy engine |

---

## Rust Core Modules

When properly deployed, 20 Rust modules are available:

```
Amygdala, BHDCEncoder, BatchNorm, BudgetedPredictor, Consolidation,
Dropout, FNOM, HebbianConsolidation, LLMPredictor, MahalanobisPredictor,
MatrixOps, MultiConsolidation, Neuromodulators, QuantumModule, QuantumState,
SlowPredictor, batch_norm_inference, norm_l2, softmax
```

Verify with:
```bash
docker exec somabrain_standalone_app python -c \
  "import somabrain_rs; print([m for m in dir(somabrain_rs) if not m.startswith('_')])"
```

---

## Running Tests

### Integration Tests
```bash
# From host machine
cd /path/to/somabrain
source .venv/bin/activate
DJANGO_SETTINGS_MODULE=somabrain.settings \
  python -m pytest tests/integration/test_cognition_workbench.py \
                   tests/integration/test_memory_workbench.py -v
```

### Expected Results
- Cognition workbench: 3/3 passed
- Memory workbench: 1/1 passed
- Property/unit tests: 103/108 passed

---

## Troubleshooting

### Container Restarting
```bash
# Check logs
docker logs somabrain_standalone_app --tail 50

# Common fix: Extend health check timing
docker compose down && docker compose up -d
```

### Rust Core Not Loading
```bash
# Verify wheel is installed
docker exec somabrain_standalone_app pip list | grep somabrain

# Rebuild if needed
cd rust_core && ./scripts/build_rust.sh
```

### Database Connection Issues
```bash
# Use correct DSN format
export SOMABRAIN_POSTGRES_DSN=postgresql://somabrain:somabrain@somabrain_standalone_postgres:5432/somabrain
```

---

## Production Deployment

For production, use Kubernetes. See:
- `infra/k8s/README.md` - Kubernetes deployment guide
- `infra/k8s/base/` - Base manifests
- `infra/k8s/overlays/` - Environment-specific configs

---

## Related Documentation

- [SomaFractalMemory Deployment](../../somafractalmemory/infra/standalone/DEPLOYMENT_GUIDE.md)
- [Kubernetes Guide](../k8s/README.md)
- [API Reference](../../docs/api.md)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-09 | Rust Core integration, 16-service verification |
| 1.0.0 | 2026-01-08 | Initial deployment guide |
