# SomaBrain Codebase Documentation

> **Purpose:** Comprehensive exploration and documentation of the SomaBrain codebase.  
> **Target:** Software engineers integrating with SomaBrain or extending its capabilities.  
> **Date:** April 2026

---

## 1. Overall Architecture and Structure

### 1.1 Project Overview

SomaBrain is a **Django Ninja-based cognitive runtime** that provides persistent memory capabilities for AI agents using hyperdimensional computing principles. It's designed as a callable service (not a standalone agent) that other systems (like SomaAgent01) integrate with via HTTP API.

**Key Characteristics:**
- Language: Python 3.12+
- Framework: Django 5.1+ with Django Ninja for REST API
- License: MIT/Apache 2.0
- Version: 0.2.0

### 1.2 Core Directory Structure

```
somabrain/
├── somabrain/                     # Main Django application
│   ├── api/                       # REST API endpoints (Django Ninja)
│   │   ├── endpoints/             # ~50+ endpoint modules
│   │   ├── v1.py                 # Main API router
│   │   └── schemas/              # Request/response schemas
│   ├── services/                  # Core cognitive services
│   │   ├── memory_service.py      # Memory orchestration
│   │   ├── retrieval_pipeline.py # Recall engine
│   │   ├── integrator_hub.py   # Multi-domain confidence integration
│   │   ├── segmentation_service.py
│   │   ├── calibration_service.py
│   │   ├── learner_online.py    # Online learning
│   │   ├── cognitive_loop_service.py
│   │   └── entry.py            # Service orchestrator
│   ├── admin/                    # Brain administration
│   │   ├── brain/               # Neuromodulators, focus state, FNOM
│   │   └── core/
│   ├── settings/                 # Django settings (modular)
│   │   ├── base.py
│   │   ├── cognitive.py         # Cognitive parameters
│   │   ├── neuro.py            # Neuromodulator settings
│   │   ├── infra.py            # Infrastructure config
│   │   └── standalone.py
│   ├── core/                     # Core utilities
│   │   ├── types.py             # Type definitions
│   │   ├── container.py         # DI container
│   │   ├── validation.py
│   │   ├── rust_bridge.py      # Rust extension bindings
│   │   └── exceptions.py
│   ├── infrastructure/           # Cross-cutting concerns
│   │   ├── circuit_breaker.py
│   │   ├── cb_registry.py
│   │   ├── tenant.py           # Multi-tenant support
│   │   └── degradation.py
│   ├── interface/               # Interface adapters
│   │   ├── cli/                # CLI entry point
│   │   └── memory.py           # Memory interface
│   ├── bootstrap/               # Initialization
│   │   ├── singletons.py
│   │   ├── runtime_init.py
│   │   └── opa.py
│   ├── adaptive/                 # Adaptive learning
│   ├── calibration/            # Calibration modules
│   ├── segmentation/            # HMM-based segmentation
│   ├── planning/               # Planning engine
│   ├── constituent/           # Constitution storage
│   ├── cog/                   # Kafka producer
│   ├── sleep/                 # Sleep consolidation
│   ├── monitoring/             # Observability
│   └── migrations/             # Database migrations
├── clients/                    # Client libraries
│   └── python/                 # Python client + CLI
├── infra/                      # Infrastructure as code
│   ├── k8s/                   # Kubernetes manifests
│   ├── helm/                   # Helm charts
│   └── gateway/               # API gateway configs
├── data/                       # Runtime data (JSON)
└── tests/                      # Test suites
```

---

## 2. Main Entry Points and Services

### 2.1 API Entry Point

**Primary:** Django Ninja API at `somabrain/api/v1.py`

- **Port:** 9696 (default), proxied to 30101 in Docker
- **Routes:** 50+ endpoint routers registered
- **Core Routers (Always Loaded):**
  - `/health/` - Health checks
  - `/admin/` - System administration
  - `/cognitive/` - Cognitive state
  - `/sleep/` - Sleep consolidation
  - `/neuromod/` - Neuromodulator management
  - `/memory/` - Memory store/recall
  - `/context/` - Context management
  - `/config/` - Runtime configuration

- **AAAS Routers (Loaded when `somabrain.aaas` in INSTALLED_APPS):**
  - `/auth/` - Authentication
  - `/aaas/` - Tenant/billing management
  - `/brain/` - Brain settings
  - `/roles/` - RBAC
  - `/users/` - User management
  - `/billing/` - Subscription management

### 2.2 Service Orchestrator

**Entry:** `somabrain/services/entry.py` - Main function

Starts background threads for cognitive services:

1. **IntegratorHub** (`integrator_hub.py`)
   - Multi-domain confidence integration
   - Routes observations to appropriate predictors
   - Runs continuously in background

2. **SegmentationService** (`segmentation_service.py`)
   - HMM-based session segmentation
   - Identifies cognitive boundaries

3. **DriftMonitor** (`somabrain/monitoring/drift_detector.py`)
   - Detects model drift
   - Triggers recalibration

4. **CalibrationService** (`calibration_service.py`)
   - Temperature scaling
   - Confidence calibration

5. **LearnerService** (`learner_online.py`)
   - Online learning from feedback
   - Updates predictors based on outcomes

### 2.3 Django Management

```bash
python manage.py migrate      # Database migrations
python manage.py runserver 9696 # API server
python manage.py shell        # REPL
```

---

## 3. APIs and Interfaces

### 3.1 Core Memory API

**Store Memory:**
```
POST /api/v1/memory/store
{
  "content": "string",
  "namespace": "string",
  "importance": 0.0-1.0,
  "metadata": {...}
}
→ { "id", "embedding_id", "salience", "created_at" }
```

**Recall Memory:**
```
POST /api/v1/memory/recall
{
  "query": "string",
  "top_k": int,
  "retrievers": ["vector", "wm", "graph", "lexical"],
  "namespace": "string"
}
→ { "memories": [...], "latency_ms" }
```

**Working Memory Status:**
```
GET /api/v1/memory/wm/status
→ { "capacity", "used", "items", "neuromodulators" }
```

### 3.2 Key Service APIs

| Service | Interface | Methods |
|---------|-----------|---------|
| MemoryService | `services/memory_service.py` | `store()`, `recall()`, `for_namespace()` |
| RetrievalPipeline | `services/retrieval_pipeline.py` | `retrieve()`, `rerank()` |
| IntegratorHub | `services/integrator_hub.py` | `update()`, `snapshot()`, `leader()` |
| CognitiveLoop | `services/cognitive_loop_service.py` | `process()`, `iterate()` |
| PlanEngine | `services/plan_engine.py` | `plan()`, `execute()` |

### 3.3 Client Libraries

**Python Client:** `clients/python/somabrain_client.py`

```python
from clients.python.somabrain_client import SomaBrainClient

api = SomaBrainClient(base_url="http://localhost:9696", tenant="public")
memories = api.recall("query", top_k=5)
```

**CLI:** `clients/python/cli.py`

```bash
python -m somabrain.clients.python.cli "query text"
```

---

## 4. Integration with Other Systems

### 4.1 SomaStack Ecosystem

SomaBrain is designed to integrate within the SomaStack:

```
SomaStack/
├── shared/              # Port 49000-49099 (Keycloak, etc.)
├── SomaFractalMemory/   # Port 21000-21099 (long-term storage)
├── SomaBrain/          # Port 30000-30199 ← THIS REPO
└── SomaAgent01/        # Port 20000-20199 (agent orchestration)
```

### 4.2 External Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| PostgreSQL | State storage, ORM | Yes |
| Redis | Caching, sessions, pub/sub | Yes |
| Milvus | Vector similarity (HNSW) | Yes |
| Kafka | Event streaming,cognitive events | Yes |
| OPA | Policy enforcement | No (optional) |
| Prometheus | Metrics | No (optional) |

### 4.3 Memory Backend Integration

SomaBrain delegates to external memory HTTP service:

```python
# Settings
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://soma-fractal-memory:8080
SOMABRAIN_MEMORY_HTTP_TOKEN=<token>
```

When unavailable, uses circuit breaker pattern with local degradation.

### 4.4 Deployment Modes

Two deployment modes controlled by `SOMABRAIN_MODE` (`somabrain/core/mode.py`):

1. **Standalone:** Core API only, no AAAS features
2. **AAAS (Agent As A Service):** Full multi-tenant with billing, roles, users

---

## 5. Key Configuration Files

### 5.1 Environment Configuration

**`.env.example`** - Reference configuration:

```bash
# Infrastructure
SOMABRAIN_POSTGRES_DSN=postgresql://user:pass@host/db
SOMABRAIN_REDIS_URL=redis://host:6379/0
SOMABRAIN_KAFKA_URL=kafka://host:9092
SOMABRAIN_MILVUS_HOST=milvus

# Security
SOMABRAIN_AUTH_REQUIRED=true
SOMABRAIN_API_TOKEN=<token>
SOMABRAIN_JWT_SECRET=<secret>
SOMABRAIN_JWT_PUBLIC_KEY_PATH=/path/to/key.pub

# Cognitive Parameters (300+ available)
SOMABRAIN_WM_SIZE=64
SOMABRAIN_HRR_DIM=8192
SOMABRAIN_SDR_BITS=2048
SOMABRAIN_EMBED_DIM=256
SOMABRAIN_ENABLE_SLEEP=true
SOMABRAIN_NEURO_DOPAMINE_BASE=0.4

# Rate Limiting
SOMABRAIN_RATE_RPS=100000
```

### 5.2 Settings Modules

Location: `somabrain/settings/`

| Module | Purpose |
|--------|---------|
| `base.py` | Common configuration |
| `cognitive.py` | Cognitive system parameters |
| `neuro.py` | Neuromodulator parameters |
| `infra.py` | Infrastructure backends |
| `standalone.py` | Standalone deployment config |
| `production.py` | Production overrides |
| `development.py` | Dev overrides |

### 5.3 Feature Flags

Runtime feature flags in `somabrain/services/feature_flags.py`:

- `integrator` - Enable integrator hub
- `segmentation` - Enable segmentation service
- `drift` - Enable drift detection
- `calibration` - Enable calibration
- `learner` - Enable online learning

### 5.4 Cognitive Presets

Three pre-configured parameter sets (`docs/technical/configuration_optimization.md`):

| Preset | Use Case | Plasticity | Temperature |
|-------|---------|----------|------------|
| **Stable** | Reliable, factual | Low | Low |
| **Plastic** | Rapid adaptation | High | Medium |
| **Lateral** | Creative tasks | Medium | High |

```python
from somabrain.services.parameter_supervisor import ParameterSupervisor
await ParameterSupervisor(config_svc).apply_preset(tenant="t1", preset_name="plastic")
```

---

## 6. Capabilities

### 6.1 Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Hyperdimensional Memory** | 8,192-dim HRR vectors with holographic encoding |
| **Sparse Distributed Representations** | 2% density for high-capacity storage |
| **Working Memory** | Salience-gated buffer with 64 slots |
| **Long-term Storage** | PostgreSQL + Milvus for persistent memories |
| **Vector Search** | O(1) similarity retrieval via HNSW |
| **Consolidation** | Sleep-cycle hippocampal consolidation |
| **Neuromodulation** | Dopamine, serotonin, norepinephrine simulation |

### 6.2 Cognitive Capabilities

| Capability | Description |
|-----------|-------------|
| **State Prediction** | Predict next cognitive state |
| **Action Prediction** | Predict optimal actions |
| **Agent Prediction** | Predict agent behavior |
| **Segmentation** | HMM-based session segmentation |
| **Calibration** | Temperature scaling for confidence |
| **Drift Detection** | Monitor model drift |
| **Online Learning** | Learn from feedback |
| **Planning** | Multi-step planning engine |

### 6.3 Enterprise Capabilities

| Capability | Description |
|-----------|-------------|
| **Multi-tenancy** | Cryptographic tenant isolation |
| **Audit Logging** | GDPR/HIPAA compliant |
| **Rate Limiting** | Per-tenant RPS limits |
| **OPA Policies** | Fine-grained authorization |
| **JWT Authentication** | With Keycloak/Auth0 support |
| **Circuit Breaker** | Resilience to failures |
| **Degradation** | Graceful degradation |

### 6.4 Observability

| Capability | Description |
|-----------|-------------|
| **Prometheus Metrics** | Counters, histograms, gauges |
| **OpenTelemetry** | Distributed tracing |
| **Health Checks** | `/health` with component status |
| **System Health** | `/health/system` with deep checks |
| **Service Health** | `/service-health/` detailed status |

---

## 7. Mathematical Foundation

### 7.1 Governed Trace Algorithm

The core memory update mechanism:

```
m_t = (1 - η) * m_{t-1} + η * b_t
```

| Symbol | Name | Description |
|--------|------|-------------|
| `m_t` | Memory State | High-dimensional superposition vector |
| `b_t` | Input Vector | New sparse, orthogonal memory trace |
| `η` | Plasticity Gain | Learning rate (0.0-1.0) |
| `(1-η)` | Decay Factor | Exponential forgetting |

### 7.2 Key Properties

```python
# Approximate orthogonality in R^N, N >> 1
E[x · y] ≈ 0
```

This enables:
- High-capacity associative memory
- Constant-time O(1) retrieval
- Noise tolerance through superposition

---

## 8. Performance Characteristics

| Operation | p95 Latency | Throughput |
|-----------|:---------:|:----------|
| Memory Store | 8ms | 12,000/sec |
| Vector Recall | 15ms | 5,000/sec |
| WM Update | 2ms | 50,000/sec |
| Consolidation | 30s | 10,000 memories |

*Benchmarked on 32-core, 128GB RAM, with Milvus on NVMe*

---

## 9. Key Files Reference

### 9.1 API Entry Points

| File | Purpose |
|------|---------|
| `somabrain/api/v1.py` | Main API router |
| `somabrain/api/endpoints/memory.py` | Memory endpoints |
| `somabrain/api/endpoints/health.py` | Health endpoints |

### 9.2 Core Services

| File | Purpose |
|------|---------|
| `somabrain/services/memory_service.py` | Memory facade with circuit breaker |
| `somabrain/services/retrieval_pipeline.py` | Recall pipeline |
| `somabrain/services/integrator_hub.py` | Confidence integration |
| `somabrain/services/entry.py` | Service orchestrator |

### 9.3 Brain Components

| File | Purpose |
|------|---------|
| `somabrain/admin/brain/neuromodulators.py` | Dopamine, serotonin, etc. |
| `somabrain/admin/brain/focus_state.py` | Attention state |
| `somabrain/admin/brain/fnom.py` | False negatives/positives |

### 9.4 Infrastructure

| File | Purpose |
|------|---------|
| `somabrain/infrastructure/circuit_breaker.py` | Resilience |
| `somabrain/infrastructure/tenant.py` | Multi-tenancy |
| `somabrain/settings/base.py` | Configuration |

---

## 10. Deployment

### 10.1 Docker Standalone

```bash
docker-compose up -d
# API at localhost:30101
```

### 10.2 Kubernetes

```bash
# Via Helm
helm install somabrain infra/helm/charts/soma-infra

# Via Tilt (development)
cd somaAgent01 && tilt up
```

### 10.3 Ports (Docker Compose)

| Service | Port |
|---------|------|
| API | 30101 |
| Redis | 30100 |
| Kafka | 30102 |
| OPA | 30104 |
| Prometheus | 30105 |
| Postgres | 30106 |

---

## 11. Documentation Links

| Document | Location |
|----------|----------|
| User Guide | `docs/user/USER_GUIDE.md` |
| Deployment | `docs/deployment/` |
| Technical | `docs/technical/` |
| Operations | `docs/operations/` |
| VIBE Rules | `docs/development/VIBE_CODING_RULES.md` |

---

## 12. Summary

SomaBrain provides **persistent memory for AI agents** using:

1. **Hyperdimensional computing** (8,192-dim HRR vectors) for high-capacity associative memory
2. **Django Ninja REST API** with 50+ endpoints for store/recall, configuration, and administration
3. **Multi-tier memory** - Working memory (64 slots) + PostgreSQL/Milvus for long-term storage
4. **Cognitive services** - Integrator, segmentation, calibration, drift detection, online learning
5. **Enterprise features** - Multi-tenancy, audit logging, circuit breakers, OPA policies

It integrates with SomaFractalMemory for distributed storage and SomaAgent01 for agent orchestration, forming the cognitive layer of the SomaStack platform.