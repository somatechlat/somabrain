# SomaBrain Standalone Deployment Guide

> **Document Version**: 3.0.0
> **Last Updated**: 2026-02-19
> **Status**: ✅ Vault-First Architecture (Port 30200)

This guide provides step-by-step instructions for deploying the **SomaBrain Cognitive Core** (Layer 3) in standalone mode.

**Key Architecture Features:**
- **Vault-First Secrets**: All credentials (DB, Redis, JWT) injected via HashiCorp Vault.
- **Strict Port Authority**: All host ports confined to **30xxx** range.
- **AAAS Sovereignty**: Multi-tenant logic strictly stripped from standalone runtime.

---

## ⚡ Quick Start

```bash
# 1. Clone and navigate
cd /path/to/somabrain

# 2. Configure Environment
    Use the provided example file to create your local configuration.

    ```bash
    cd infra/standalone
    cp .env.example .env
    ```

    Edit `.env` to set your secrets:
    *   `SOMABRAIN_VAULT_TOKEN`: (Required) A secure token for Vault initialization.
    *   `POSTGRES_PASSWORD`: (Required) Password for the database.
    *   `SOMABRAIN_MEMORY_HTTP_TOKEN`: Token to authenticate with SFM.

    > **Note on Connectivity**:
    > Standalone mode automatically configures service URLs (Kafka, OPA, Redis) using internal Docker DNS names.
    > You do **not** need to manually set `SOMABRAIN_KAFKA_URL` or `SOMABRAIN_OPA_URL` unless overriding defaults.

# 3. Start Stack (With Vault Injection)
docker compose -f infra/standalone/docker-compose.yml --env-file infra/standalone/.env up -d

# 4. Verify Health (Wait ~30s for Vault Init)
docker compose -f infra/standalone/docker-compose.yml ps
```

---

## 🏛️ Port Authority (30xxx Range)

All SomaBrain services are strictly mapped to the **30xxx** range to avoid conflicts with SFM (10xxx) or Agent (20xxx).

| Service | Host Port | Internal Port | Purpose |
|:---|:---|:---|:---|
| **API** | `30101` | `30101` | Main Cognitive API |
| **Vault** | `30200` | `8200` | Secrets Management |
| **Kafka** | `30102` | `9094` | Event Bus |
| **Redis** | `30100` | `6379` | Working Memory Cache |
| **Postgres** | `30106` | `5432` | State Store |
| **OPA** | `30104` | `8181` | Policy Engine |
| **Prometheus** | `30105` | `9090` | Metrics |
| **DB Exporter** | `30107` | `9187` | Postgres Metrics |
| **Schema Reg** | `30108` | `8081` | Kafka Schema Registry |
| **MinIO** | `30109` | `9000` | S3-compatible Storage |
| **MinIO UI** | `30110` | `9001` | Storage Console |
| **Jaeger** | `30111` | `16686` | Distributed Tracing |
| **Integrator** | `30115` | `9015` | Health & Metrics |
| **Segmentation** | `30116` | `9016` | Health & Metrics |
| **Milvus** | `30119` | `19530` | Vector Store (Internal Oak) |

---

## 🔐 Secrets Architecture (Vault)

SomaBrain uses **HashiCorp Vault** as the single source of truth for secrets.
Services do **NOT** receive raw secrets (like `POSTGRES_PASSWORD`) via environment variables.

### Bootstrapping Flow
1.  **Vault Service (`somabrain_standalone_vault`)** starts on port `30200`.
2.  **Vault Init (`somabrain_standalone_vault_init`)** waits for Vault to be healthy.
3.  **Seeding**: `vault_init` uses `SOMABRAIN_VAULT_TOKEN` to seed:
    - `somabrain/database` (User/Pass/Host/Port)
    - `somabrain/redis` (URL)
    - `somabrain/auth` (JWT Secret)
4.  **Application Bootstrap**: Services (`app`, `cog`, `outbox`, `integrator`) start with:
    - `VAULT_ADDR=http://somabrain_standalone_vault:8200`
    - `VAULT_TOKEN=<token>`
5.  **Runtime Fetch**: On startup, `vault_client.py` connects to Vault and fetches the actual credentials to configure Django settings.

---

## 🧪 Verification

### 1. Check Vault Status
```bash
curl -s http://localhost:30200/v1/sys/health | jq
# Expect: "initialized": true, "sealed": false
```

### 2. Check API Health
```bash
curl -s http://localhost:30101/health | jq
# Expect: "status": "ok", "database": "connected", "redis": "connected"
```

### 3. Verify Rust Core
```bash
docker exec somabrain_standalone_app python -c \
  "from somabrain.core.rust_bridge import is_rust_available; print(f'Rust Available: {is_rust_available()}')"
```

---

## 🛠️ Troubleshooting

### "VaultNotConfigured" Error
- **Cause**: The `vault_init` container failed or hasn't finished.
- **Fix**: Check logs: `docker logs somabrain_standalone_vault_init`. Ensure `SOMABRAIN_VAULT_TOKEN` matches in `.env`.

### Database Connection Failed
- **Cause**: App cannot fetch credentials from Vault.
- **Fix**: Verify Vault is unsealed (Step 1). Verify `somabrain/database` secret exists:
  ```bash
  docker exec somabrain_standalone_vault vault kv get somabrain/database
  ```

---

## Document History

| Version | Date | Changes |
|:---|:---|:---|
| 3.0.0 | 2026-02-19 | **Vault-First Architecture Upgrade** (Port 30200). Enforced 30xxx Port Authority. |
| 2.0.0 | 2026-01-09 | Rust Core integration. |
| 1.0.0 | 2026-01-08 | Initial deployment guide. |

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
