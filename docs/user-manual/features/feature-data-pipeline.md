# Data Pipeline Feature

**Purpose**: Document the data flow through SomaBrain's memory and cognitive pipeline.

**Audience**: Users integrating SomaBrain into data processing workflows.

---

## Overview

SomaBrain processes data through multiple stages:

1. **Ingestion** → `/remember`
2. **Embedding** → Vector generation via configured embedder
3. **Working Memory** → Admission to MultiTenantWM (Redis-backed)
4. **Long-Term Storage** → HTTP memory service persistence
5. **Tiered Memory** → Governed superposition in TieredMemoryRegistry
6. **Retrieval** → Multi-retriever pipeline (vector, wm, graph, lexical)

---

## Data Flow Diagram

```
Client Request
    ↓
/remember
    ↓
OPA Authorization (fail-closed)
    ↓
Circuit Breaker Check
    ↓
Payload Composition (signals, attachments, links)
    ↓
Embedder → Vector Generation
    ↓
┌─────────────────┬──────────────────┬────────────────────┐
│ Working Memory  │ HTTP Memory Svc  │ Tiered Registry    │
│ (MultiTenantWM) │ (External)       │ (Superposition)    │
└─────────────────┴──────────────────┴────────────────────┘
    ↓
Outbox Event → Kafka
    ↓
Metrics → Prometheus
    ↓
Response to Client
```

---

## Pipeline Stages

### 1. Ingestion

**Endpoint**: `POST /remember`

**Input**:
```json
{
  "tenant": "acme",
  "namespace": "production",
  "key": "user-action-123",
  "value": {
    "task": "User clicked checkout button",
    "content": "E-commerce checkout flow initiated"
  },
  "signals": {
    "importance": 0.8,
    "novelty": 0.6,
    "ttl_seconds": 86400
  }
}
```

**Processing**:
- OPA middleware validates tenant permissions
- Circuit breaker checks memory service health
- Payload enriched with metadata and signals

### 2. Embedding

**Provider**: Configured via `SOMABRAIN_EMBED_PROVIDER` (default: `tiny`)

**Output**: 256-dimensional vector (configurable via `embed_dim`)

### 3. Working Memory Admission

**Component**: `MultiTenantWM` (`somabrain/mt_wm.py`)

**Behavior**:
- LRU eviction when capacity reached
- Per-tenant isolation
- Redis-backed persistence

### 4. Long-Term Storage

**Component**: `MemoryClient` (`somabrain/memory_client.py`)

**Behavior**:
- HTTP POST to external memory service
- Circuit breaker protection (fail-fast on 503)
- Coordinate generation for spatial indexing

### 5. Tiered Memory

**Component**: `TieredMemoryRegistry` (`somabrain/services/tiered_memory_registry.py`)

**Behavior**:
- Governed superposition with decay (η)
- Cleanup indexes (cosine or HNSW)
- Per-tenant/namespace traces

### 6. Event Publishing

**Component**: Outbox pattern (`somabrain/db/outbox.py`)

**Behavior**:
- Transactional write to Postgres outbox table
- Async Kafka publish via outbox worker
- Guaranteed delivery semantics

---

## Retrieval Pipeline

**Endpoint**: `POST /recall`

**Retrievers** (default full-power mode):
- **Vector**: Cosine similarity in embedding space
- **WM**: Working memory cache lookup
- **Graph**: K-hop traversal from query key
- **Lexical**: Token-based matching

**Reranking** (default: `auto`):
- HRR (Hyperdimensional Resonance Retrieval)
- MMR (Maximal Marginal Relevance)
- Cosine similarity

**Scoring**:
```
score = w_cosine * cosine_sim + w_fd * fd_projection + w_recency * exp(-age/τ)
```

---

## Configuration

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Embed Provider | `SOMABRAIN_EMBED_PROVIDER` | `tiny` | Embedding model |
| Embed Dimension | `SOMABRAIN_EMBED_DIM` | `256` | Vector dimensionality |
| WM Size | `SOMABRAIN_WM_SIZE` | `64` | Working memory capacity |
| Circuit Breaker Threshold | `SOMABRAIN_FAILURE_THRESHOLD` | `3` | Consecutive failures before open |
| Recall Full Power | `SOMABRAIN_RECALL_FULL_POWER` | `1` | Enable all retrievers |

---

## Monitoring

**Metrics**:
- `somabrain_memory_snapshot` - WM items, circuit state
- `somabrain_recall_requests_total` - Recall request count
- `somabrain_recall_wm_latency_seconds` - WM lookup latency
- `somabrain_recall_ltm_latency_seconds` - LTM query latency
- `somabrain_circuit_breaker_state` - Circuit breaker status

**Health Check**:
```bash
curl http://localhost:9696/health | jq '.memory_circuit_open'
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| 503 on remember | Memory service unavailable | Check circuit breaker state, verify memory service health |
| Empty recall results | No matching memories | Verify ingestion succeeded, check namespace/universe scoping |
| High recall latency | Multiple retrievers enabled | Tune `SOMABRAIN_RECALL_DEFAULT_RETRIEVERS` to reduce scope |
| Circuit breaker open | Repeated memory service failures | Investigate memory service logs, increase `failure_threshold` if transient |

---

## Related Documentation

- [Memory Operations](memory-operations.md) - API details
- [Architecture](../../technical-manual/architecture.md) - System design
- [Full-Power Recall](../../technical-manual/full-power-recall.md) - Retrieval pipeline
