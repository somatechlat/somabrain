# Agent Onboarding Guide

**Purpose**: Enable AI agents to understand and work with the SomaBrain codebase effectively.

## Quick Facts (Code-Verified)

| Property | Value | Source |
|----------|-------|--------|
| **Main API File** | `somabrain/app.py` | FastAPI application |
| **API Port** | 9696 (host and container) | `docker-compose.yml` |
| **Config System** | `somabrain/config.py` | Dataclass-based with env overrides |
| **Memory Dimension** | 256 (default `embed_dim`) | `Config` dataclass |
| **HRR Dimension** | 8192 (default `hrr_dim`) | `Config` dataclass |
| **Working Memory Size** | 64 (default `wm_size`) | `Config` dataclass |

## Core Components (Actual Locations)

### 1. API Layer
- **File**: `somabrain/app.py`
- **Framework**: FastAPI
- **Key Endpoints**:
  - `POST /remember` - Store memory
  - `POST /recall` - Retrieve memory
  - `POST /context/evaluate` - Build context
  - `POST /context/feedback` - Update weights
  - `GET /health` - Health check

### 2. Configuration
- **File**: `somabrain/config.py`
- **Class**: `Config` (dataclass)
- **Loading**: `load_config()` function
- **Env Prefix**: `SOMABRAIN_`

### 3. Quantum/HRR Layer
- **File**: `somabrain/quantum.py`
- **Class**: `QuantumLayer`
- **Math**: BHDC (Binary Hyperdimensional Computing)
- **Operations**: `bind()`, `unbind()`, `superpose()`

### 4. Memory System
- **Superposed Trace**: `somabrain/memory/superposed_trace.py`
- **Hierarchical**: `somabrain/memory/hierarchical.py`
- **Classes**: `SuperposedTrace`, `TieredMemory`

### 5. Scoring
- **File**: `somabrain/scoring.py`
- **Class**: `UnifiedScorer`
- **Components**: Cosine + FD + Recency

### 6. Learning/Adaptation
- **File**: `somabrain/learning/adaptation.py`
- **Class**: `AdaptationEngine`
- **Weights**: Retrieval (α, β, γ, τ) + Utility (λ, μ, ν)

## Environment Variables (Real Defaults)

```bash
# Memory Backend (REQUIRED)
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN_HERE>"  # Required - set your actual token

# Redis
SOMABRAIN_REDIS_URL="redis://localhost:30100"

# Kafka
SOMABRAIN_KAFKA_URL="somabrain_kafka:9092"

# Postgres
SOMABRAIN_POSTGRES_DSN="postgresql://soma:soma@localhost:30106/somabrain"

# OPA
SOMABRAIN_OPA_URL="http://localhost:30104"

# Mode
SOMABRAIN_MODE="full-local"  # or "prod"

# Predictor
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
```

## Docker Compose Ports (Verified)

| Service | Host Port | Container Port | Internal Name |
|---------|-----------|----------------|---------------|
| API | 9696 | 9696 | somabrain_app |
| Redis | 30100 | 6379 | somabrain_redis |
| Kafka | 30102 | 9092 | somabrain_kafka |
| OPA | 30104 | 8181 | somabrain_opa |
| Prometheus | 30105 | 9090 | somabrain_prometheus |
| Postgres | 30106 | 5432 | somabrain_postgres |
| Schema Registry | 30108 | 8081 | somabrain_schema_registry |

## Next Steps

1. Read [propagation-agent.md](propagation-agent.md) for memory operations
2. Read [monitoring-agent.md](monitoring-agent.md) for observability
3. Read [security-hardening.md](security-hardening.md) for security practices

## Code Navigation Tips

- **Start here**: `somabrain/app.py` (main FastAPI app)
- **Config**: `somabrain/config.py` (all settings)
- **Math**: `somabrain/quantum.py` (BHDC operations)
- **Memory**: `somabrain/memory/` (storage abstractions)
- **Tests**: `tests/` (examples of usage)
