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
        API[SomaBrain Django/Ninja]
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
    API -->|Middleware| OPA[OPA Policy]

    subgraph Auxiliary Services
        SMF[SomaFractalMemory Gateway]
        GRPC[gRPC MemoryService]
    end

    LTM -->|Vector IO| SMF
    API -->|Optional Transport| GRPC
```

## Core Components

### 🧩 The Brain Behind The Magic:

**🌐 Neural Gateway** (`somabrain.api.v1`)
*Human Impact:* Your apps get a simple, powerful interface to cognitive superpowers
*The Science:* Production **Django Ninja** API with cognitive middleware, strict mathematical validation, and Django's robustness.

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
1. Client sends `/remember` request with content, signals, attachments, and links
2. OPA middleware validates tenant permissions (fail-closed)
3. MemoryService circuit breaker checked and reset if needed
4. Payload composed with signals (importance, novelty, ttl), tags, and metadata
5. Content embedded via embedder for working memory admission
6. MemoryClient writes to external HTTP memory service (fail-fast on 503)
7. Outbox event created in Postgres transaction before Kafka publish
8. Working memory (MultiTenantWM) admits vector with payload
9. TieredMemoryRegistry records memory in governed superposition
10. Metrics emitted to Prometheus (memory_snapshot, circuit_breaker_state)
11. Success response returned with coordinate, WM promotion status, and signal feedback

### Memory Recall Flow
1. Client sends `/recall` request (string or object body)
2. OPA middleware validates access permissions (fail-closed)
3. Request coerced to RetrievalRequest with environment-backed defaults
4. Retrieval pipeline orchestrates multiple retrievers:
   - Working memory (MultiTenantWM) via cosine similarity
   - Vector retrieval via MemoryClient HTTP (circuit breaker protected)
   - Graph traversal (k-hop expansion from query key)
   - Lexical matching (optional)
5. UnifiedScorer ranks candidates:
   - w_cosine * cosine_similarity(query, candidate)
   - w_fd * fd_projection_similarity(query, candidate)
   - w_recency * exp(-recency_steps / recency_tau)
6. Reranking applied (auto/mmr/hrr/cosine)
7. TieredMemoryRegistry provides governed recall with cleanup indexes
8. Session pinning (optional) stores results for follow-up queries
9. Cutover controller records shadow metrics for namespace migration
10. Metrics emitted: RECALL_REQUESTS, RECALL_WM_LAT, RECALL_LTM_LAT, memory_snapshot

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

1. Request enters Django Ninja handlers (`somabrain/api/endpoints/memory.py::recall_memory`).
2. OPA middleware enforces authorization (fail-closed).
3. Request coerced to `RetrievalRequest` with environment-backed defaults (full-power mode).
4. Retrieval pipeline (`somabrain/services/retrieval_pipeline.py::run_retrieval_pipeline`) orchestrates:
   - Working-memory probe (`somabrain/mt_wm.py::MultiTenantWM.recall`)
   - Vector retrieval via MemoryClient HTTP
   - Graph traversal (k-hop expansion)
   - Lexical matching (optional)
5. Unified scoring (`somabrain/scoring.py::UnifiedScorer`) combines:
   - Cosine similarity in base space
   - FD subspace projection (via FDSalienceSketch.project)
   - Exponential recency: exp(-age/τ)
6. Reranking (auto/mmr/hrr/cosine) applied to candidates.
7. Circuit breaker (`somabrain/services/memory_service.py::MemoryService`) tracks failures:
   - Opens after `failure_threshold` consecutive errors (default 3)
   - Resets after `reset_interval` seconds (default 60s)
   - Fails fast with 503 when open (no journal fallback)
8. Tiered memory (`TieredMemoryRegistry`) provides governed recall with cleanup indexes.
9. Outbox pattern (`somabrain/db/outbox.py`) ensures transactional Kafka event publishing.
10. Response returns scored items; metrics emitted via `somabrain/metrics.py`.

Strict-mode deployments (backend enforcement enabled) fail fast when dependencies are unavailable.

## Core Invariants

| Invariant | Code Reference | Enforcement |
| --- | --- | --- |
| Spectral property: ‖H_k‖≈1 | `MathematicalMetrics.verify_spectral_property` | Called after every bind operation in QuantumLayer |
| Role orthogonality | `MathematicalMetrics.verify_role_orthogonality` | Checked when caching new unitary roles |
| Binding correctness | `MathematicalMetrics.verify_operation_correctness` | Validates cosine(a, bind(a,b)) is low |
| Weight bounds | `UnifiedScorer._clamp` | Keeps scorer weights within [weight_min, weight_max] |
| Trace normalization | `SuperposedTrace._decayed_update` | Renormalizes after every exponential decay step: (1-η)M_t + η·bind(k,v) |
| Circuit breaker | `MemoryService._mark_failure` | Opens after failure_threshold consecutive errors (default 3) |
| Outbox transactionality | `outbox_db.create_event` | Atomic write to Postgres outbox table before Kafka publish |
| Fail-closed authorization | `OpaMiddleware` | All requests blocked when OPA unavailable (strict mode) |

Expose these guarantees through Prometheus metrics (`SCORER_WEIGHT_CLAMPED`, `SCORER_COMPONENT`, `CIRCUIT_BREAKER_STATE`, `HTTP_FAILURES`, `OUTBOX_EVENTS_CREATED`, `OUTBOX_FAILED_TOTAL`).

## Configuration Touchpoints

- Environment flags: `common.config.settings.Settings` (the central configuration singleton). The legacy `somabrain.config.get_config()` reference has been removed.
- Scorer weights: `w_cosine`, `w_fd`, `w_recency` with bounds `weight_min`/`weight_max`
- Recency decay: `recency_tau` controls exponential decay rate (exp(-age/τ))
- Adaptation: `learning_rate_dynamic=true` enables dopamine-modulated learning rates
- Circuit breaker: `failure_threshold` (default 3), `reset_interval` (default 60s)
- Backend enforcement: `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` disables all fallbacks
- Recall defaults: `SOMABRAIN_RECALL_FULL_POWER=1` (default), `SOMABRAIN_RECALL_DEFAULT_RERANK=auto`, `SOMABRAIN_RECALL_DEFAULT_PERSIST=1`
- Tiered memory: `SOMABRAIN_TIERED_MEMORY_ENABLED=1` enables governed superposition
- Outbox: `SOMABRAIN_OUTBOX_BATCH_SIZE=100`, `SOMABRAIN_OUTBOX_MAX_DELAY=5.0`
- Admin features: `SOMABRAIN_MODE=dev` enables feature flag overrides
- Optional components (Kafka, Postgres) are auto-detected; backend enforcement keeps readiness false when dependencies are offline

## Fail-Safe Design (Agent Integration)

**Purpose**: Enable SomaAgent01 to operate independently when SomaBrain is unavailable.

### Detection & Signaling

**Health Classification**:
- Poll `GET /health` every 3-5 seconds
- States: `up` (ok=true, ready=true, memory_ok=true), `degraded` (partial readiness), `down` (unreachable)
- Agent `/status` exposes `soma_brain.status` for UI consumption

### Behavioral Gating

**Structured Errors**:
- Return `{"kind": "soma_brain_unavailable"}` on failures
- Never convert failures to empty results or fake "no memory"
- Agent continues on local infrastructure (LLM, Redis, Postgres, Kafka, OPA)

### Durable Outbox

**Agent-Side Persistence**:
- DB table with `(tenant_id, dedupe_key)` unique constraint
- Schema: `id, tenant_id, dedupe_key, payload, status, retries, last_error, created_at`
- Replay worker syncs to SomaBrain when `status="up"`

**Metrics**:
- `somaagent_outbox_pending_total{tenant_id}`
- `somaagent_outbox_sent_total{tenant_id}`
- `somaagent_outbox_failed_total{tenant_id}`

### UI Indicator

**Frontend Contract**:
- Poll agent `/status` for `soma_brain.status`
- Display near bell icon: green (up), amber (degraded), red (down)
- Tooltip: "SomaBrain cognitive memory: available/partially available/unavailable"

**No Mocks Policy**:
- All behavior based on real SomaBrain responses or real agent infrastructure
- No fake memories or offline brain substitutes

---

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

---

## Cognitive Threads and Teach Feedback (Kafka)

**For comprehensive Karpathy tripartite architecture documentation (predictors, integrator, segmentation with heat diffusion), see [Karpathy Architecture](karpathy-architecture.md). For predictor math, configuration, and tests, see [Diffusion-backed Predictors](predictors.md).**


SomaBrain’s cognition loop uses Kafka topics and small services for modularity and safety:

- Contracts (Avro under `proto/cog/`):
  - `global_frame.avsc` — leader, weights, rationale
  - `segment_boundary.avsc` — boundaries for episodic segmentation
  - `reward_event.avsc` — `r_task`, `r_user`, `r_latency`, `r_safety`, `r_cost`, `total`
  - `config_update.avsc` — `learning_rate`, `exploration_temp`
  - `teach_feedback.avsc` — `feedback_id`, `capsule_id`, `frame_id`, `rating`, `comment`

- Topics:
  - `cog.global.frame`, `cog.segments`, `cog.reward.events`, `cog.config.updates`, `cog.teach.feedback`

- Services:
  - `integrator_hub` — fuses predictor signals → `cog.global.frame`
  - `segmentation_service` — derives `cog.segments` from frames
  - `teach_feedback_processor` — maps TeachFeedback to RewardEvent (`rating`→`r_user`, `total=r_user`). Uses confluent-kafka for publishing with `compression.type=none` for maximum client compatibility; falls back to kafka-python if needed.
  - `learner_online` — consumes rewards, emits `cog.config.updates` (`tau` from EMA of reward)

### Operations

- Topics are seeded via `scripts/seed_topics.py` (idempotent)
- `somabrain_cog` container runs cognition services under Supervisor (see `ops/supervisor/supervisord.conf`)
- Observability:
  - `somabrain_teach_feedback_total`, `somabrain_teach_r_user`
  - `somabrain_reward_events_published_total`, `somabrain_reward_events_failed_total`
  - `somabrain_reward_value`, `soma_exploration_ratio`, `soma_policy_regret_estimate`

### Safety and Policy

- OPA middleware protects API edges; Kafka processors publish best-effort and log; deploy Kafka ACLs per-tenant where applicable
- Teach-derived `r_user` is bounded in [-1, 1] via rating mapping to prevent extreme control signals

### Validation

- Run `python scripts/e2e_teach_feedback_smoke.py` to verify `cog.teach.feedback` → `cog.reward.events`
- Run `python scripts/e2e_reward_smoke.py` to validate RewardProducer and topic bindings

Note: Local smoke tests prefer the confluent-kafka client; install with `pip install confluent-kafka`.

**References**:
- [Deployment Guide](deployment.md) for installation procedures
- [Monitoring Setup](monitoring.md) for observability configuration
- [Runbooks](runbooks/) for operational procedures
