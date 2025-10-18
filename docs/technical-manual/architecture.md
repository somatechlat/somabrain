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
*The Science:* Binary Hyperdimensional Computing with 2048-8192D vector spaces and permutation binding. Deterministic unitary roles now record spectral/orthogonality invariants so the system raises immediate telemetry if mathematical guarantees drift.

**📊 Relevance Oracle** (`somabrain/scoring.py`)  
*Human Impact:* Finds exactly what you need, even when you ask imperfectly  
*The Science:* Unified similarity combining cosine, frequency-domain, and temporal weighting

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
3. MultiTenantWM checked for cached results
4. If miss, MemoryClient queries long-term storage
5. UnifiedScorer ranks results using cosine similarity, FD projection, a log-damped recency curve with configurable floor, and density-aware cleanup penalties
6. Results filtered and formatted for response
7. Working memory updated with recalled items
8. Metrics and audit events recorded

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
- **Mathematical Invariants**: Density matrix trace, BHDC binding accuracy

### Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: Debug, info, warn, error with appropriate filtering
- **Audit Trail**: Immutable operation logs for compliance
- **Performance Logging**: Slow query identification and optimization

### Alerting Rules
- **Critical Alerts**: Service outages, data inconsistency, security violations
- **Warning Alerts**: Performance degradation, resource utilization thresholds
- **Informational**: Deployment notifications, configuration changes

## Recall Lifecycle (Strict Mode)

1. Request enters FastAPI handlers (`somabrain.app`).
2. Backend-enforcement middleware verifies `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`, `SOMABRAIN_FORCE_FULL_STACK`, and `SOMABRAIN_REQUIRE_MEMORY`.
3. Working-memory probe (`somabrain/mt_wm.py::MultiTenantWM.recall`) checks cache and neuromodulator state.
4. Unified scoring (`somabrain/scoring.py::UnifiedScorer`) combines cosine, frequency-domain, and log-damped recency terms while MemoryClient applies density-aware cleanup penalties before final ranking.
5. Memory client (`somabrain/memory_client.py::MemoryClient.recall`) expands to the HTTP memory service when required.
6. Density matrix update (`somabrain/memory/density.py::DensityMatrix.observe`) folds evidence back into state and exports metrics.
7. Response returns scored items plus audit metadata; structured logs emit via `somabrain/audit.py`.

Strict-real deployments abort the request if any stage fails—there are no silent fallbacks.

## Core Invariants

| Invariant | Code Reference | Enforcement |
| --- | --- | --- |
| `abs(trace(ρ) - 1) < 1e-4` | `DensityMatrix.normalize_trace` | Called after every observe/update cycle |
| PSD spectrum | `DensityMatrix.project_psd` | Clips negative eigenvalues before persistence |
| Weight bounds | `UnifiedScorer._clamp_weight` | Keeps component weights within configured bounds |
| Stub usage = 0 | `_audit_stub_usage` in `MemoryClient` | Raises immediately if a stub path executes |
| Health realism | `somabrain/metrics.py::emit_health` | `/health` reports ready only when all deps respond |

Expose these guarantees through Prometheus metrics (`somabrain_density_trace_error_total`, `somabrain_stub_usage_total`, `somabrain_recall_latency_seconds`).

## Configuration Touchpoints

- Environment flags are sourced via `common.config.settings.Settings`—see `configuration.md`.
- Temporal damping is governed by `recall_recency_time_scale`, `recall_recency_sharpness`, and `recall_recency_floor`; density penalties are tuned via `recall_density_margin_*` fields in `Config`.
- Compose and Kubernetes manifests supply the same flags; backend enforcement must be enabled in every promoted environment.
- Optional components (Kafka, Postgres) are auto-detected. If endpoints exist they are used; backend enforcement keeps readiness false when dependencies are offline.

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
