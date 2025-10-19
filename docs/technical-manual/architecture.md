# System Architecture

**Purpose**: This document provides a comprehensive overview of SomaBrain's system design, component interactions, and architectural decisions.

**Audience**: System administrators, SREs, architects, and technical stakeholders.

**Prerequisites**: Understanding of distributed systems, microservices, and containerization concepts.

---

## System Topology

```mermaid
graph TD
    subgraph Client Edge
        Agents[Agents / Tooling]
    end

    Agents -->|HTTPS| API

    subgraph Runtime
        API[SomaBrain FastAPI]
        WM[Working Memory (MultiTenantWM)]
        LTM[MemoryClient + HTTP memory service]
        Scorer[UnifiedScorer + DensityMatrix]
        Quantum[QuantumLayer (BHDC HRR)]
        Control[Neuromodulators & Policy Gates]
    end

    API -->|Recall / Remember| WM
    API -->|Recall / Remember| LTM
    API -->|Scoring| Scorer
    API -->|HRR Encode| Quantum
    API -->|Safety Gates| Control

    subgraph Auxiliary Services
        SMF[SomaFractalMemory Gateway]
        GRPC[gRPC MemoryService]
    end

    LTM -->|Vector IO| SMF
    API -->|Optional Transport| GRPC
```

## Core Components

### 🧩 The Brain Behind The Magic:

**🌐 Neural Gateway** (`somabrain.app`)
*Human Impact:* Your apps get a simple, powerful interface to cognitive superpowers
*The Science:* Production FastAPI with cognitive middleware and strict mathematical validation

**🧠 Lightning Memory** (`somabrain/mt_wm.py`)
*Human Impact:* Instant access to the most important memories - no waiting
*The Science:* Multi-tenant working memory with Redis backing and intelligent LRU eviction

**⚛️ Meaning Engine** (`somabrain/quantum.py`)
*Human Impact:* Understands that "car" and "automobile" mean the same thing
*The Science:* Binary Hyperdimensional Computing (BHDC) with 2048D vector spaces using permutation-based binding (PermutationBinder). Perfectly invertible by construction. Deterministic unitary roles with verified spectral properties (‖H_k‖≈1). Orthogonality and binding correctness verified via MathematicalMetrics on every operation.

**📊 Relevance Oracle** (`somabrain/scoring.py`)
*Human Impact:* Finds exactly what you need, even when you ask imperfectly
*The Science:* UnifiedScorer combining cosine similarity, FD subspace projection (via FDSalienceSketch), and exponential recency decay (exp(-age/τ)) with configurable weight bounds

**🔗 Memory Vault** (`somabrain/memory_client.py`)
*Human Impact:* Never loses anything, remembers everything, proves what happened
*The Science:* HTTP-first persistence with cryptographic audit trails and strict-mode validation

**📈 Health Guardian**
*Human Impact:* Self-monitoring system that prevents problems before you notice them
*The Science:* Prometheus metrics, structured logging, and real-time health diagnostics

## Infrastructure Components

### Redis Cache
- **Purpose**: High-performance cache for working memory and session state
- **Configuration**:
  - Memory limit: 8GB (configurable)
  - Eviction policy: LRU
  - Persistence: RDB snapshots + AOF
- **Monitoring**: Memory usage, hit/miss ratio, connection count
- **Backup**: Daily RDB snapshots to object storage

### PostgreSQL Database
- **Purpose**: Persistent storage for configuration, audit logs, and metadata
- **Schema**:
  - Configuration tables (tenants, policies, settings)
  - Audit log tables (operations, events, metrics)
  - Memory metadata (embeddings, relationships)
- **Monitoring**: Connection pool, query performance, disk usage
- **Backup**: Daily `pg_dump` with point-in-time recovery

### Kafka Message Broker
- **Purpose**: Event streaming for audit trails and system integration
- **Topics**:
  - `audit.operations`: Memory operations audit trail
  - `audit.events`: System events and state changes
  - `metrics.streams`: Real-time metrics publishing
- **Configuration**: 3 brokers, replication factor 3, retention 7 days
- **Monitoring**: Topic lag, broker health, partition distribution

### OPA Policy Engine
- **Purpose**: Centralized authorization and policy enforcement
- **Policies**:
  - Tenant access control
  - Rate limiting rules
  - Data classification policies
- **Integration**: Middleware in SomaBrain API request pipeline
- **Monitoring**: Policy evaluation latency, decision audit logs

## Data Flow Patterns

### Memory Storage Flow
1. Client sends `/remember` request with content and metadata
2. OPA middleware validates tenant permissions and rate limits
3. Content processed through QuantumLayer for hypervector encoding
4. MemoryClient writes to both working memory (Redis) and long-term storage
5. DensityMatrix updated with new memory relationships
6. Audit event published to Kafka
7. Metrics emitted to Prometheus
8. Success response returned to client

### Memory Recall Flow
1. Client sends `/recall` request with query and context
2. OPA middleware validates access permissions
3. MultiTenantWM checked for cached results (cosine similarity in base space)
4. If miss, MemoryClient queries long-term storage via HTTP
5. UnifiedScorer ranks results:
   - w_cosine * cosine_similarity(query, candidate)
   - w_fd * fd_projection_similarity(query, candidate)
   - w_recency * exp(-recency_steps / recency_tau)
6. Results filtered and formatted for response
7. Working memory updated with recalled items
8. Metrics emitted: SCORER_COMPONENT, SCORER_FINAL, memory_snapshot

### Health Check Flow
1. `/health` endpoint receives request
2. Validates Redis connectivity and response time
3. Checks Postgres connection and query execution
4. Verifies Kafka broker availability (if configured)
5. Tests OPA policy engine responsiveness
6. Aggregates component health into overall status
7. Returns 200 OK if all components healthy, 503 if degraded

## Scaling Considerations

### Horizontal Scaling
- **API Layer**: Multiple SomaBrain API instances behind load balancer
- **Working Memory**: Tenant-based sharding across Redis instances
- **Long-term Storage**: Partitioned by tenant or semantic bucket
- **Message Processing**: Kafka consumer groups for parallel processing

### Performance Optimization
- **Connection Pooling**: HTTP and database connection reuse
- **Caching Strategy**: Multi-tier caching (working memory → Redis → storage)
- **Batch Operations**: Bulk memory operations where possible
- **Asynchronous Processing**: Non-blocking I/O for concurrent requests

### Resource Management
- **Memory Limits**: Per-tenant working memory quotas
- **CPU Allocation**: Quantum operations benefit from CPU affinity
- **Storage Tiering**: Hot data in Redis, warm in Postgres, cold in object storage
- **Network Optimization**: Keep-alive connections, compression for bulk transfers

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication with configurable expiration
- **OPA Policies**: Fine-grained authorization rules
- **Tenant Isolation**: Strict separation of memory spaces
- **Audit Logging**: All operations recorded with user context

### Data Protection
- **Encryption in Transit**: TLS 1.2+ for all HTTP communications
- **Encryption at Rest**: Database and Redis encryption enabled
- **Secret Management**: External secret store integration
- **Data Classification**: Sensitive data handling policies

### Network Security
- **Service Mesh**: Optional Istio deployment for mTLS
- **Firewall Rules**: Restrictive ingress/egress policies
- **Private Networks**: Internal services on isolated subnets
- **Rate Limiting**: Per-tenant and global rate limits

## Monitoring & Observability

### Metrics Collection
- **Application Metrics**: Request latency, memory operations, error rates
- **Infrastructure Metrics**: CPU, memory, disk, network utilization
- **Business Metrics**: Tenant usage, cognitive performance measures
- **Mathematical Invariants**: BHDC spectral properties (‖H_k‖≈1), role orthogonality, binding correctness, trace normalization

### Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: Debug, info, warn, error with appropriate filtering
- **Audit Trail**: Immutable operation logs for compliance
- **Performance Logging**: Slow query identification and optimization

### Alerting Rules
- **Critical Alerts**: Service outages, data inconsistency, security violations
- **Warning Alerts**: Performance degradation, resource utilization thresholds
- **Informational**: Deployment notifications, configuration changes

## Recall Lifecycle (Production Mode)

1. Request enters FastAPI handlers (`somabrain/api/memory_api.py`).
2. Backend-enforcement middleware verifies `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` if enabled.
3. Working-memory probe (`somabrain/mt_wm.py::MultiTenantWM.recall`) checks cache.
4. Unified scoring (`somabrain/scoring.py::UnifiedScorer`) combines:
   - Cosine similarity in base space
   - FD subspace projection (via FDSalienceSketch.project)
   - Exponential recency: exp(-age/τ)
5. Memory client (`somabrain/memory_client.py::MemoryClient.recall`) queries HTTP memory service.
6. Circuit breaker (`somabrain/services/memory_service.py::MemoryService`) tracks failures and journals operations when backend is down (if `allow_journal_fallback=true`).
7. Response returns scored items; metrics emitted via `somabrain/metrics.py`.

Strict-mode deployments (backend enforcement enabled, journal disabled) fail fast when dependencies are unavailable.

## Core Invariants

| Invariant | Code Reference | Enforcement |
| --- | --- | --- |
| Spectral property: ‖H_k‖≈1 | `MathematicalMetrics.verify_spectral_property` | Called after every bind operation in QuantumLayer |
| Role orthogonality | `MathematicalMetrics.verify_role_orthogonality` | Checked when caching new unitary roles |
| Binding correctness | `MathematicalMetrics.verify_operation_correctness` | Validates cosine(a, bind(a,b)) is low |
| Weight bounds | `UnifiedScorer._clamp` | Keeps scorer weights within [weight_min, weight_max] |
| Trace normalization | `SuperposedTrace._decayed_update` | Renormalizes after every exponential decay step: (1-η)M_t + η·bind(k,v) |
| Circuit breaker | `MemoryService._mark_failure` | Opens after failure_threshold consecutive errors |

Expose these guarantees through Prometheus metrics (`SCORER_WEIGHT_CLAMPED`, `SCORER_COMPONENT`, `CIRCUIT_BREAKER_STATE`, `HTTP_FAILURES`).

## Configuration Touchpoints

- Environment flags: `common.config.settings.Settings` and `somabrain.config.get_config()`
- Scorer weights: `w_cosine`, `w_fd`, `w_recency` with bounds `weight_min`/`weight_max`
- Recency decay: `recency_tau` controls exponential decay rate (exp(-age/τ))
- Adaptation: `learning_rate_dynamic=true` enables dopamine-modulated learning rates
- Circuit breaker: `failure_threshold` (default 3), `reset_interval` (default 60s)
- Journal fallback: `allow_journal_fallback` (default false in strict mode)
- Backend enforcement: `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` disables all fallbacks
- Optional components (Kafka, Postgres) are auto-detected; backend enforcement keeps readiness false when dependencies are offline

## Extending the System

1. Implement new math in a dedicated module (for example `somabrain/math/new_component.py`).
2. Add integration points inside `MultiTenantWM` or `UnifiedScorer` guarded by explicit feature flags.
3. Cover invariants with property tests and expose new metrics.
4. Update the architecture manual and linked diagrams within the same change.

---

**Verification**: System health can be validated via `/health` endpoint and Prometheus metrics dashboard.

**Common Errors**:
- Redis connection failures → Check network connectivity and Redis service status
- OPA policy evaluation timeouts → Review policy complexity and OPA resource allocation
- Memory storage inconsistencies → Validate write mirroring configuration

**References**:
- [Deployment Guide](deployment.md) for installation procedures
- [Monitoring Setup](monitoring.md) for observability configuration
- [Runbooks](runbooks/) for operational procedures
