# Multi-Tenant Usage

**Purpose** Explain how SomaBrain separates tenants, applies quotas, and scopes namespaces.

**Audience** Operators and developers running a single SomaBrain instance for multiple teams or customers.

**Prerequisites** The core API is running and you have at least one tenant credential.

---

## 1. How Tenants Are Identified

`somabrain.tenant.get_tenant` determines the tenant for every request using the following priority:

1. `X-Tenant-ID` header (explicit).
2. The first 16 characters of the bearer token (implicit).
3. Fallback `"public"` tenant when neither is available.

The namespace stored in Redis, Prometheus labels, and response bodies is constructed as `<base_namespace>:<tenant_id>`, where `base_namespace` defaults to `somabrain_ns` (see `.env`).

```bash
curl -sS http://localhost:9696/health \
  -H "Authorization: Bearer dev-token" \
  -H "X-Tenant-ID: org_acme" | jq '.namespace'
```

Output:

```json
"somabrain_ns:org_acme"
```

---

## 2. Isolation Guarantees

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| Working memory | `MultiTenantWM` maintains a per-tenant dictionary keyed by tenant ID. | Redis is optional; the in-process buffer respects namespace separation. |
| Long-term memory | HTTP memory service receives the tenant namespace (client libraries should propagate it). | Configure your backend to honour the namespace; the SomaBrain API does not multiplex responses. |
| Adaptation state | Redis keys prefixed with `adaptation:state:{tenant}`. | Retrieval/utility weights never mix between tenants. |
| Metrics | Prometheus metrics expose `tenant_id` labels (e.g., `somabrain_tau_gauge{tenant_id="org_acme"}`). | Use label filters to derive per-tenant dashboards. |
| Logs | Structured logs include `tenant` and `namespace` fields. | Filter centrally to audit tenant-specific activity. |

---

## 3. Quotas and Rate Limiting

- **Rate limiting** (`somabrain.ratelimit.RateLimiter`): simple leaky bucket enforced per tenant. Violation returns HTTP 429 with `{"detail": "rate limit exceeded"}` and increments the `somabrain_rate_limited_total` metric.
- **Daily write quota** (`somabrain.quotas.QuotaManager`): defaults to 10 000 writes per tenant per day. Configure via `SOMABRAIN_QUOTA_DAILY_WRITES` or by extending `QuotaConfig` in `somabrain.config.Config`. Tenants containing `AGENT_ZERO` are exempt by design.

Check remaining quota programmatically:

```python
from somabrain.quotas import QuotaManager, QuotaConfig

manager = QuotaManager(QuotaConfig(daily_writes=5000))
remaining = manager.remaining("org_acme")
```

In the API, quota enforcement occurs in `somabrain.app.remember` before writes reach the memory service.

---

## 4. Tenant Headers in Practice

Always include `X-Tenant-ID` when running shared environments:

```bash
AUTH="Authorization: Bearer ${SOMABRAIN_API_TOKEN}"
TENANT="X-Tenant-ID: org_acme"

curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"payload": {"task": "org_acme.memo", "content": "Tenant-specific note."}}'
```

If you omit the header, the request falls back to the token hash or `"public"`. Treat `"public"` as an unscoped sandbox tenant.

---

## 5. Tenant-Specific Configuration

SomaBrain does not ship a tenant registry in this repository. If you need per-tenant limits or feature flags:

1. Extend `common/config/settings.py` (if present in your deployment) to expose tenant metadata.
2. Inject tenant-specific settings via environment variables or a wrapper service before requests hit the API.
3. Use namespaces (e.g., `somabrain_ns:customer_a`) to map tenants to dedicated resources in external systems (memory service, dashboards, storage).

Remember that quota and rate-limiter state is in-memory on each API instance. In horizontally scaled environments back these managers with Redis or another shared store so every replica enforces the same counters.

---

## 6. Observability

Monitor per-tenant health with the following metrics:

| Metric | Description | Example |
|--------|-------------|---------|
| `somabrain_tau_gauge{tenant_id=…}` | Current τ value after duplicate-rate adjustments. | `curl -s http://localhost:9696/metrics \| rg tau_gauge` |
| `somabrain_feedback_total{tenant_id=…}` | Feedback events per tenant. | Track adaptation load. |
| `somabrain_ltm_store_total{tenant_id=…}` | Long-term store attempts per tenant. | Observe ingestion patterns. |
| `somabrain_rate_limited_total{tenant_id=…}` | Count of blocked writes due to rate limiting. | Investigate noisy tenants. |

Use these signals to validate isolation and catch runaway tenants early.

---

## 7. Best Practices

- Reserve uppercase or special marker tenants (e.g., `"AGENT_ZERO"`) for automated agents that need unlimited access.
- Enforce authentication even in dev environments when multiple tenants share the same deployment.
- Surface tenant context in your client logs—matching `trace_id` + `tenant_id` vastly simplifies debugging.
- When decommissioning a tenant, purge or archive associated data in the external memory service; SomaBrain itself does not delete tenant namespaces automatically.
# Real-Time Propagation Feature

**Purpose**: Document how SomaBrain propagates cognitive state changes in real-time via Kafka.

**Audience**: Users building event-driven applications on top of SomaBrain.

---

## Overview

SomaBrain uses Kafka topics to propagate cognitive events in real-time:

- **Outbox Events** → Memory operations, admin actions
- **Cognitive Threads** → Predictor beliefs, integrator frames, segmentation boundaries
- **Teach Feedback** → User ratings converted to reward signals
- **Config Updates** → Dynamic parameter adjustments

---

## Kafka Topics

| Topic | Schema | Purpose | Producer | Consumer |
|-------|--------|---------|----------|----------|
| `soma.audit` | JSON | Audit trail for memory operations | SomaBrain API | Audit service |
| `cog.global.frame` | Avro | Integrated belief state | IntegratorHub | Downstream agents |
| `cog.segments` | Avro | Episodic boundaries | SegmentationService | Memory consolidation |
| `cog.reward.events` | Avro | Reward signals | RewardProducer | LearnerOnline |
| `cog.config.updates` | Avro | Parameter updates | LearnerOnline | All cognitive services |
| `cog.teach.feedback` | Avro | User feedback | External systems | TeachFeedbackProcessor |

---

## Outbox Pattern

**Purpose**: Ensure transactional consistency between Postgres writes and Kafka publishes.

**Flow**:
1. API writes memory operation to Postgres outbox table
2. Outbox worker polls for pending events
3. Worker publishes to Kafka with at-least-once semantics
4. Worker marks event as `sent` in outbox table

**Configuration**:
```bash
SOMABRAIN_OUTBOX_BATCH_SIZE=100
SOMABRAIN_OUTBOX_MAX_DELAY=5.0
```

**Monitoring**:
```bash
# Check outbox backlog
curl http://localhost:9696/admin/outbox?status=pending | jq '.events | length'

# Replay failed events
curl -X POST http://localhost:9696/admin/outbox/replay \
  -H "Content-Type: application/json" \
  -d '{"ids": [123, 456]}'
```

---

## Cognitive Thread Events

### Global Frame

**Schema**: `proto/cog/global_frame.avsc`

**Fields**:
- `frame_id` - Unique identifier
- `timestamp` - Event time
- `leader` - Winning predictor domain
- `weights` - Domain confidence weights
- `rationale` - Explanation text

**Example**:
```json
{
  "frame_id": "frame-20250127-001",
  "timestamp": 1706313600000,
  "leader": "state",
  "weights": {
    "state": 0.7,
    "agent": 0.2,
    "action": 0.1
  },
  "rationale": "State predictor has highest confidence"
}
```

### Segment Boundaries

**Schema**: `proto/cog/segment_boundary.avsc`

**Fields**:
- `segment_id` - Unique identifier
- `start_frame_id` - First frame in segment
- `end_frame_id` - Last frame in segment
- `boundary_type` - `cpd` (change point detection) or `hazard`

**Example**:
```json
{
  "segment_id": "seg-20250127-001",
  "start_frame_id": "frame-20250127-001",
  "end_frame_id": "frame-20250127-050",
  "boundary_type": "cpd"
}
```

### Reward Events

**Schema**: `proto/cog/reward_event.avsc`

**Fields**:
- `frame_id` - Associated frame
- `r_task` - Task completion reward
- `r_user` - User satisfaction reward
- `r_latency` - Latency penalty
- `r_safety` - Safety compliance reward
- `r_cost` - Cost efficiency reward
- `total` - Weighted sum

**Example**:
```json
{
  "frame_id": "frame-20250127-001",
  "r_task": 0.8,
  "r_user": 0.9,
  "r_latency": -0.1,
  "r_safety": 1.0,
  "r_cost": 0.7,
  "total": 0.86
}
```

---

## Teach Feedback Integration

**Purpose**: Convert user ratings into reward signals for online learning.

**Flow**:
1. External system posts to `/teach/feedback` (or publishes to `cog.teach.feedback`)
2. TeachFeedbackProcessor consumes feedback events
3. Processor maps `rating` to `r_user` component
4. Processor publishes `RewardEvent` to `cog.reward.events`
5. LearnerOnline consumes rewards and emits config updates

**Mapping**:
```python
rating_map = {
    5: 1.0,   # Excellent
    4: 0.5,   # Good
    3: 0.0,   # Neutral
    2: -0.5,  # Poor
    1: -1.0   # Terrible
}
r_user = rating_map.get(rating, 0.0)
```

**Example**:
```bash
# Submit teach feedback
curl -X POST http://localhost:9696/teach/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_id": "fb-001",
    "frame_id": "frame-20250127-001",
    "rating": 5,
    "comment": "Perfect response"
  }'
```

---

## Config Updates

**Purpose**: Dynamically adjust cognitive parameters based on reward signals.

**Schema**: `proto/cog/config_update.avsc`

**Fields**:
- `config_id` - Unique identifier
- `timestamp` - Update time
- `learning_rate` - Adjusted learning rate
- `exploration_temp` - Temperature for exploration

**Example**:
```json
{
  "config_id": "cfg-20250127-001",
  "timestamp": 1706313600000,
  "learning_rate": 0.01,
  "exploration_temp": 0.5
}
```

---

## Consuming Events

### Python (confluent-kafka)

```python
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'localhost:30102',
    'group.id': 'my-consumer-group',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['cog.global.frame'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(f"Error: {msg.error()}")
        continue
    
    frame = json.loads(msg.value().decode('utf-8'))
    print(f"Received frame: {frame['frame_id']}")
```

### Python (kafka-python)

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'cog.global.frame',
    bootstrap_servers=['localhost:30102'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    frame = message.value
    print(f"Received frame: {frame['frame_id']}")
```

---

## Monitoring

**Metrics**:
- `somabrain_outbox_events_created_total` - Outbox events created
- `somabrain_outbox_failed_total` - Failed Kafka publishes
- `somabrain_teach_feedback_total` - Teach feedback received
- `somabrain_reward_events_published_total` - Reward events published

**Health Check**:
```bash
# Check Kafka connectivity
curl http://localhost:9696/health | jq '.kafka_ok'

# Check outbox backlog
curl http://localhost:9696/admin/outbox?status=pending
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Events not appearing in Kafka | Outbox worker not running | Check `somabrain_outbox_publisher` container logs |
| High outbox backlog | Kafka unavailable | Verify Kafka broker health, check network connectivity |
| Duplicate events | At-least-once semantics | Implement idempotency in consumers using `dedupe_key` |
| Missing teach feedback | Wrong topic name | Verify `cog.teach.feedback` topic exists and is spelled correctly |

---

## Related Documentation

- [Karpathy Architecture](../../technical/karpathy-architecture.md) - Cognitive threads design
- [Kafka Operations](../../technical/runbooks/kafka-operations.md) - Operational procedures
- [Outbox Backlog Playbook](../../operational/playbooks/outbox-backlog.md) - Incident response
# Cognitive Reasoning

**Purpose** Explain how SomaBrain builds contextual prompts, applies feedback, and updates its learning state.

**Audience** Users who need more than simple recall and want to use `/context/evaluate`, `/context/feedback`, sleep consolidation, and neuromodulation endpoints.

**Prerequisites** Completed the [Quick Start Tutorial](../quick-start-tutorial.md) and understand [Memory Operations](memory-operations.md).

---

## 1. Context Evaluation (`/context/evaluate`)

The evaluate endpoint orchestrates the `ContextBuilder`, `ContextPlanner`, and associated scoring logic. It returns a structured response defined in `somabrain/api/schemas/context.py::EvaluateResponse`.

### Request

```bash
curl -sS http://localhost:9696/context/evaluate \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "query": "Summarise our capital city policy",
        "top_k": 5,
        "session_id": "demo-session"
      }' | jq
```

### Response Fields

| Field | Description |
|-------|-------------|
| `prompt` | Generated prompt assembled by `ContextPlanner`, incorporating highlights when useful. |
| `memories` | Array of `MemoryItem` objects (id, score, metadata, optional embedding). |
| `weights` | Per-memory weights computed by `ContextBuilder` using the current retrieval parameters (α, β, γ, τ). |
| `residual_vector` | Residual HRR vector used for downstream models. |
| `working_memory` | Snapshot of the session’s working memory buffer. |
| `constitution_checksum` | Hash of the active constitution document (if configured). |

Evaluation emits metrics (`somabrain.metrics`) and updates the per-tenant tau gauge when duplicate ratios exceed thresholds.

---

## 2. Submitting Feedback (`/context/feedback`)

Feedback nudges the `AdaptationEngine` for a tenant. The update scales are configurable through the environment and shared settings (see `AdaptationGains` and `AdaptationConstraints`).

```bash
curl -sS http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "session_id": "demo-session",
        "query": "Summarise our capital city policy",
        "prompt": "Summarise the capital city policy succinctly.",
        "response_text": "Paris is recorded as the capital city.",
        "utility": 0.9,
        "reward": 0.9
      }' | jq
```

**Success response**

```json
{
  "accepted": true,
  "adaptation_applied": true
}
```

The engine records a history entry, persists the state to Redis (`adaptation:state:{tenant}`), and emits metrics capturing the new α/β/γ/τ and λ/μ/ν values.

Inspect the current state:

```bash
curl -sS http://localhost:9696/context/adaptation/state \
  -H "$AUTH" -H "$TENANT" | jq
```

Response (`AdaptationStateResponse`) includes retrieval weights, utility weights, effective learning rate, the configured gains, and the active parameter bounds so you can confirm overrides at runtime.

---

## 3. Neuromodulators (`/neuromodulators`)

`somabrain.neuromodulators.PerTenantNeuromodulators` stores dopamine, serotonin, noradrenaline, and acetylcholine levels that influence dynamic learning rates.

```bash
# fetch current state
curl -sS http://localhost:9696/neuromodulators \
  -H "$AUTH" -H "$TENANT" | jq

# update dopamine level
curl -sS http://localhost:9696/neuromodulators \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"dopamine": 0.35}' | jq
```

When `enable_dynamic_lr` is set (via config or `SOMABRAIN_LEARNING_RATE_DYNAMIC=1`), the AdaptationEngine scales the base learning rate by `0.5 + dopamine` (bounded `[0.5, 1.2]`).

---

## 4. Sleep & Consolidation (`/sleep/run`)

Trigger NREM/REM consolidation cycles to summarise working memory content or recombine long-term memories.

```bash
curl -sS http://localhost:9696/sleep/run \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"nrem": true, "rem": true}' | jq
```

The response (`SleepRunResponse`) reports the mode executed, timestamps, and per-phase results (NREM condensation summaries, REM recombination outputs). Internally this drives `somabrain.consolidation` against `MultiTenantWM` and the long-term memory client.

---

## 5. Planner Actions (`/plan/suggest`, `/act`)

- `/plan/suggest` calls `somabrain.planner.plan_from_graph` to propose actions or task decomposition. Provide a `task` string plus optional `top_k`, `tenant`, or history prompts.
- `/act` executes actions generated by the planner or external agents. Payloads follow `somabrain/schemas.py::ActRequest`.

These endpoints are guarded by the same auth and tenant rules as memory operations. Use them in conjunction with the evaluate/feedback loop to maintain consistency between context building and executed plans.

---

## 6. Observability Checklist

| Signal | Source | How to access |
|--------|--------|---------------|
| Adaptation weights | Redis (`adaptation:state:{tenant}`) or `/context/adaptation/state` | `curl` + `jq` |
| Tau adjustments | Prometheus gauge `somabrain_tau_gauge` | `curl http://localhost:9696/metrics` |
| Feedback throughput | Counter `somabrain_feedback_total` | Prometheus |
| Planner latency | Histogram `somabrain_plan_latency_seconds` | Prometheus |
| Working memory size | Gauge `somabrain_wm_utilization` | Prometheus |

Monitor these metrics to ensure reasoning workflows adapt as expected over time.

---

## 7. Teach feedback via Kafka (advanced)

When you need auditable human ratings to influence exploration and policy selection, SomaBrain supports a Kafka-native teach feedback loop.

- Produce TeachFeedback to `cog.teach.feedback` with fields:
  - `feedback_id`, `capsule_id`, `frame_id`, `ts`, `rating` (1–5), `comment`
- The `teach_feedback_processor` consumes `cog.teach.feedback` and emits a `RewardEvent` to `cog.reward.events`, mapping `rating` to `r_user`:
  - 1→-1.0, 2→-0.5, 3→0.0, 4→0.5, 5→1.0; `total=r_user`
- The `learner_online` service reads `cog.reward.events` and updates exploration temperature (`tau`) via `cog.config.updates`.

Quick validation (requires local Kafka):

```bash
# Install preferred Kafka client locally (recommended)
pip install confluent-kafka

# Seed topics (idempotent)
python scripts/seed_topics.py

# Run the smoke test (produces TeachFeedback and waits for a RewardEvent)
python scripts/e2e_teach_feedback_smoke.py
```

Schemas live in `proto/cog/teach_feedback.avsc` and `proto/cog/reward_event.avsc`. See `somabrain/services/teach_feedback_processor.py` for the mapping.

Notes:
- The teach feedback processor publishes rewards using the confluent-kafka client with no compression by default for maximum interoperability.
- The smoke script also prefers confluent-kafka; if unavailable it falls back to kafka-python.
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
- [Architecture](../../technical/architecture.md) - System design
- [Full-Power Recall](../../technical/full-power-recall.md) - Retrieval pipeline
# SomaBrain Features

**Purpose** Orient users to the major feature areas documented in the User Manual.

**Audience** Product owners and developers who want a map of the available guides.

**Prerequisites** Complete the [Quick Start Tutorial](../quick-start-tutorial.md).

---

## Core Themes

- **Memory Operations** – `/remember`, `/recall`, cleanup and quotas.
- **Context & Feedback** – Evaluate prompts, submit feedback, inspect adaptation state.
- **Integration Patterns** – Required headers, error handling, and examples using curl/httpx.
- **Tenant Isolation** – How namespaces, quotas, and metrics remain tenant-aware.

---

## Feature Matrix

| Feature | What it Covers | Link |
|---------|----------------|------|
| Memory Operations | Payload schema, ingestion responses, recall output, deletion helpers. | [Memory Operations](memory-operations.md) |
| Cognitive Reasoning | `/context/evaluate`, `/context/feedback`, neuromodulators, sleep cycles. | [Cognitive Reasoning](cognitive-reasoning.md) |
| API Integration | Base URL, authentication, endpoint catalogue, httpx examples. | [API Integration](api-integration.md) |
| Multi-Tenant Usage | Tenant headers, namespaces, quotas, monitoring per tenant. | [Multi-Tenant Usage](multi-tenant-usage.md) |
| Use Cases | Reference scenarios lifted from the codebase and tests. | [Use Cases](use-cases.md) |

---

## Verification Checklist

1. Open each linked feature page and run at least one sample request against your environment.
2. Confirm that response examples match the live API (schemas defined in `somabrain/schemas.py`).
3. Re-run the documentation link checker before merging changes (`markdownlint` + link validation CI jobs).

---

## Common Pitfalls

| Issue | Why it Happens | Remedy |
|-------|----------------|--------|
| Feature links drift | Pages get renamed without updating the matrix. | Update this index whenever files move. |
| Samples diverge from API | Code changes land without doc updates. | Compare docs to the relevant module (app, schemas, services) during reviews. |
| Missing prerequisites | Feature pages assume Quick Start knowledge. | Keep prerequisites section accurate and cross-link to Quick Start. |

---

**Further Reading**

- [Technical Manual](../../technical/index.md) for operational and deployment guidance.
- [Development Manual](../../development/index.md) if you plan to modify or extend SomaBrain.
# Memory Operations

**Purpose** Describe how to write and retrieve memories through SomaBrain’s public API.

**Audience** Developers integrating the `/remember`, `/recall`, and related endpoints.

**Prerequisites** Running SomaBrain instance, memory backend reachable at `SOMABRAIN_MEMORY_HTTP_ENDPOINT`, and an authentication token (unless auth disabled for development).

---

## 1. Memory Payload Schema

`somabrain/schemas.py::MemoryPayload` defines the attributes accepted by `/remember`. Important fields:

| Field | Type | Notes |
|-------|------|-------|
| `task` | string | Short identifier for the memory (also used as the working‑memory key if no coordinate is supplied). |
| `content` | string | Free‑form text stored with the memory. |
| `importance` | float | Defaults to `1.0`. Higher values increase salience in working memory. |
| `memory_type` | string | Defaults to `"episodic"`. |
| `timestamp` | string/float | ISO‑8601 or UNIX seconds; normalised to epoch seconds. |
| `universe` | string | Optional logical namespace (overrides any `X-Universe` header). |
| `phase`, `quality_score`, `domains`, `reasoning_chain` | optional metadata used by planning flows. |
| `who`, `did`, `what`, `where`, `when`, `why` | Optional event tuple; auto-populated from `task` if omitted. |

Requests can wrap the payload (`{"payload": {...}}`) or send the fields at the top level for backwards compatibility.

---

## 2. Storing a Memory – `/remember`

```bash
curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SOMABRAIN_API_TOKEN:-dev-token}" \
  -d '{
        "payload": {
          "task": "kb.geography.paris",
          "content": "Paris is the capital of France.",
          "memory_type": "episodic",
          "importance": 0.8,
          "timestamp": "2024-01-10T10:00:00Z"
        }
      }'
```

**Success response (`somabrain/schemas.py::RememberResponse`):**

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns:public",
  "trace_id": "140351384443504",
  "deadline_ms": null,
  "idempotency_key": null,
  "breaker_open": null,
  "queued": null
}
```

- `breaker_open=true` and `queued=true` mean the memory service was unavailable; the write was journaled and will be replayed when the backend recovers.
- `trace_id` echoes the request ID (either autogenerated or supplied as `X-Request-ID`).

**Failure scenarios**

| HTTP | Body | Cause | Remediation |
|------|------|-------|-------------|
| 400 | `{"detail": "Invalid payload: …"}` | Payload fails validation (missing required fields, malformed timestamp). | Fix request to match `MemoryPayload`. |
| 401/403 | `{"detail": "missing bearer token"}` | Auth required. | Provide valid token or disable auth for dev. |
| 429 | `{"detail": "rate limit exceeded"}` | Per-tenant write throttle triggered (`somabrain.ratelimit.RateLimiter`). | Slow down writes or adjust limits. |
| 503 | `{"detail": {"message": "memory backend unavailable; write queued", …}}` | `SOMABRAIN_REQUIRE_MEMORY=1` and the HTTP memory service failed. | Restore memory backend or relax the requirement. |

---

## 3. Recalling Memories – `/recall`

`somabrain/schemas.py::RecallResponse` surfaces three collections:

| Field | Description |
|-------|-------------|
| `wm` | Matches from working memory (`MultiTenantWM` or microcircuits). |
| `memory` | Long-term memory hits returned from the external memory service. |
| `results` | Legacy mirror of `memory` retained for client compatibility. |

Example query:

```bash
curl -sS http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
        "query": "capital of France",
        "top_k": 3
      }' | jq
```

Sample response (truncated):

```json
{
  "wm": [],
  "memory": [
    {
      "score": 0.86,
      "payload": {
        "task": "kb.geography.paris",
        "content": "Paris is the capital of France.",
        "memory_type": "episodic",
        "importance": 0.8
      },
      "_source": "ltm"
    }
  ],
  "results": [
    {
      "task": "kb.geography.paris",
      "content": "Paris is the capital of France.",
      "score": 0.86,
      "_source": "ltm"
    }
  ],
  "namespace": "somabrain_ns:public",
  "trace_id": "140351409864272"
}
```

The `score` is computed by `somabrain.scoring.UnifiedScorer` using weights drawn from the live adaptation state. If both `wm` and `memory` are empty, the memory backend did not return any matches (verify the write or adjust `top_k` / query text).

---

## 5. Controlling Namespaces and Universes

- Tenants are identified via `Authorization` + (optional) `X-Tenant-ID`. The default tenant is configured in `.env` (`SOMABRAIN_DEFAULT_TENANT`).
- Universes provide finer segmentation and can be supplied via the payload (`"universe": "support"`) or via `X-Universe`.
- Quotas are enforced per tenant (`somabrain.quotas.QuotaManager`). Exceeding quotas yields HTTP 429.

---

## 6. Cleanup & Deletion

SomaBrain exposes auxiliary endpoints when you need to tidy specific coordinates:

| Endpoint | Description |
|----------|-------------|
| `POST /delete` | Remove a memory by coord/key (requires payload with `coord` or `task`). |
| `POST /recall/delete` | Remove a memory surfaced by recall. |

Consult the [API Integration guide](api-integration.md) for request bodies and authentication requirements.

---

## 7. Monitoring Memory Operations

- Metrics: Prometheus exposes `somabrain_ltm_store_latency_seconds`, `somabrain_recall_latency_seconds`, and quota/rate-limit counters.
- Traces: Each response contains a `trace_id`. Supply `X-Request-ID` to correlate client calls with server logs.
- Journaling: When `persistent_journal_enabled` is `true` (see `somabrain.config.Config`), writes are appended to `journal_dir` for recovery if the memory backend is down.

Use these signals to verify that ingestion and recall behave as expected in your environment.
# API Integration Guide

**Purpose** Show how to call SomaBrain’s public HTTP endpoints safely and reproducibly.

**Audience** Developers building clients, SDKs, or integrations against the FastAPI runtime in `somabrain/app.py`.

**Prerequisites** SomaBrain stack is running (see [Installation](../installation.md)), and you can authenticate with either a static API token or JWT.

---

## 1. Base Configuration

| Setting | Default | Where it comes from |
|---------|---------|---------------------|
| Base URL | `http://localhost:9696` | `SOMABRAIN_HOST` / `SOMABRAIN_PORT` in `.env` |
| Auth | Bearer token | `SOMABRAIN_API_TOKEN` or JWT fields in `somabrain.config.Config` |
| Tenant header | `X-Tenant-ID` | Parsed by `somabrain.tenant.get_tenant` |
| Content type | `application/json` | All public endpoints expect JSON bodies |

**Authentication**

- For static tokens set `SOMABRAIN_API_TOKEN=...` and supply `Authorization: Bearer <token>`.
– In dev mode, auth may be relaxed; otherwise include a valid Bearer token.
- JWT validation uses HS or RS algorithms depending on `cfg.jwt_secret` / `cfg.jwt_public_key_path`. Configure `SOMABRAIN_JWT_ISSUER` / `SOMABRAIN_JWT_AUDIENCE` if needed.

Example curl:

```bash
AUTH="Authorization: Bearer ${SOMABRAIN_API_TOKEN:-dev-token}"
TENANT="X-Tenant-ID: demo"
curl -sS http://localhost:9696/health -H "$AUTH" -H "$TENANT" | jq
```

---

## 2. Endpoint Catalogue

| Endpoint | Method | Description | Code Reference |
|----------|--------|-------------|----------------|
| `/health` | GET | Component liveness (Redis, Postgres, Kafka, memory backend, embedder) | `somabrain.app.health` |
| `/metrics` | GET | Prometheus metrics | `somabrain.app` (global registry) |
| `/remember` | POST | Store a single memory payload | `somabrain.app.remember` |
| `/recall` | POST | Semantic recall from working + long-term memory | `somabrain.app.recall` |
| `/context/evaluate` | POST | Build contextual prompt and retrieve weighted memories | `somabrain.api.context_route.evaluate_endpoint` |
| `/context/feedback` | POST | Submit utility/feedback scores that drive `AdaptationEngine` | `somabrain.api.context_route.feedback_endpoint` |
| `/act` | POST | Execute planner actions (enabled in full stack) | `somabrain.app.act` |
| `/plan/suggest` | POST | Request plan suggestions | `somabrain.app.plan_suggest` |
| `/sleep/run` | POST | Trigger NREM/REM consolidation | `somabrain.app.sleep_run` |
| `/neuromodulators` | POST/GET | Inspect or set neuromodulator state | `somabrain.app.neuromodulators` |

Endpoints gated by `if not _MINIMAL_API` require the full Docker stack (see `.env` flags such as `SOMABRAIN_FORCE_FULL_STACK`, `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`).

---

## 3. Request & Response Patterns

### 3.1 Remember / Recall

See [Memory Operations](memory-operations.md) for full payloads. Always include the tenant header when running multi-tenant tests:

```bash
curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}}'
```

### 3.2 Context Evaluate / Feedback

`somabrain/api/schemas/context.py` defines strongly typed bodies:

```bash
# evaluate
curl -sS http://localhost:9696/context/evaluate \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "query": "capital of France",
        "top_k": 3,
        "session_id": "demo-session"
      }' | jq '.prompt, .weights'

# feedback
curl -sS http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "session_id": "demo-session",
        "query": "capital of France",
        "prompt": "Summarise the capital of France.",
        "response_text": "Paris is the capital of France.",
        "utility": 0.9,
        "reward": 0.9
      }'
```

Feedback drives the per-tenant adaptation state stored in Redis. Inspect the state with `GET /context/adaptation/state` (same headers; returns retrieval/utility weights, history length, learning rate).

### 3.3 Planning & Actions

Planning endpoints are optional and require the planner to be enabled (`SOMABRAIN_FORCE_FULL_STACK=1`):

```bash
curl -sS http://localhost:9696/plan/suggest \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"task": "draft release announcement", "top_k": 5}' | jq '.plans[:1]'
```

Consult `somabrain/schemas.py` for the exact response model (`PlanSuggestResponse`).

---

## 4. Error Handling & Observability

| Condition | HTTP code | Response field | Notes |
|-----------|-----------|----------------|-------|
| Missing/invalid token | 401 / 403 | `{"detail": "..."} ` | Implement retry/backoff only after reacquiring credentials. |
| Tenant quota exceeded | 429 | `{"detail": "daily write quota exceeded"}` | `somabrain.quotas.QuotaManager` enforces per-tenant caps. |
| Memory backend offline | 503 | `{"detail": {"message": "...", "breaker_open": true}}` | Writes are queued; check `somabrain.services.memory_service.MemoryService`. |
| Input validation | 400 | `{"detail": "Invalid payload: ..."}` | Raised by Pydantic models such as `MemoryPayload` and `FeedbackRequest`. |

**Tracing & Metrics**

- Supply `X-Request-ID` for end-to-end tracing. The same ID appears in responses and structured logs.
- Prometheus metrics at `/metrics` include request latency (`somabrain_request_latency_seconds`), memory operations, and adaptation counters.
- Kafka, Redis, and Postgres exporters in the Docker Compose stack expose infrastructure metrics on ports 20003–20007.

---

## 5. Python Example (httpx)

There is no official SDK. The snippet below uses `httpx` and the documented payloads.

```python
import asyncio
import httpx

AUTH = {"Authorization": "Bearer dev-token", "X-Tenant-ID": "demo"}
BASE = "http://localhost:9696"

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=AUTH, timeout=10) as client:
        # remember
        remember = await client.post(
            "/remember",
            json={"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}},
        )
        remember.raise_for_status()

        # recall
        recall = await client.post("/recall", json={"query": "capital of France", "top_k": 3})
        recall.raise_for_status()
        for hit in recall.json().get("results", []):
            print(f"{hit.get('score', 0):.2f} → {hit.get('content')}")

asyncio.run(main())
```

Use the same approach for feedback and planning—serialise the Pydantic models documented in `somabrain/api/schemas`.

---

## 6. Reference Documents

- [Memory Operations](memory-operations.md) – Payload specifics and error cases.
- [Cognitive Reasoning](cognitive-reasoning.md) – Context builder, planner, adaptation flows.
- [Multi-tenant Usage](multi-tenant-usage.md) – Tenancy, universes, quotas.
- [API Reference](../../development/api-reference.md) – Complete endpoint inventory for operators.
# Use Cases

**Purpose** Map real SomaBrain features to practical scenarios you can reproduce with the published APIs.

**Audience** Teams evaluating whether SomaBrain fits their product requirements.

**Prerequisites** Execute the [Quick Start Tutorial](../quick-start-tutorial.md) so you have a working environment.

---

## 1. Persistent Assistant Memory

**Goal** Store user preferences during a conversation and recall them later.

**Workflow**

1. Call `/remember` with `task="assistant.preferences"` whenever your assistant learns something durable (e.g., preferred language).
2. On subsequent conversations, call `/recall` with a query such as `"user preferences"` and `top_k` set high enough to surface the stored entry.
3. For better prompts, use `/context/evaluate` and feed the response’s `prompt` into your language model.

**Code Points**

- Memory payload schema: `somabrain/schemas.py::MemoryPayload`
- Recall response parsing: `somabrain/schemas.py::RecallResponse`
- Context building: `somabrain/context/builder.py`

---

## 2. Retrieval and Context Building

**Goal** Provide documents and summaries to a downstream model using unified recall.

**Workflow**

1. Ingest knowledge base articles via repeated `/remember` calls (one payload per request).
2. For each user question, call `/context/evaluate` to obtain:
   - `prompt` – ready-to-send context string.
   - `memories` – structured metadata you can use for citations.
3. Invoke `/context/feedback` with the user rating to refine retrieval weights for future calls.

**Code Points**

- Planner scoring: `somabrain/context/planner.py`
- Adaptation engine: `somabrain/learning/adaptation.py`
- Feedback schema: `somabrain/api/schemas/context.py::FeedbackRequest`

---

## 3. Multi-Tenant Platform

**Goal** Serve multiple customers from one deployment while keeping data and metrics isolated.

**Workflow**

1. Issue each tenant a unique bearer token and pass `X-Tenant-ID` on every request.
2. Monitor per-tenant metrics using the `tenant_id` label in Prometheus (e.g., `somabrain_feedback_total{tenant_id="org_acme"}`).
3. Enforce daily write caps via `SOMABRAIN_QUOTA_DAILY_WRITES` or by extending `QuotaConfig`.

**Code Points**

- Tenant resolution: `somabrain/tenant.py`
- Rate limiting: `somabrain/ratelimit.py`
- Quotas: `somabrain/quotas.py`

---

## 4. Offline Consolidation

**Goal** Summarise or reorganise memories during low-traffic windows.

**Workflow**

1. Trigger `/sleep/run` with `{"nrem": true, "rem": true}` to run consolidation cycles.
2. Inspect the response for generated summaries; the same information is logged by `somabrain.consolidation`.
3. Schedule the call via a job runner or use the built-in cron worker if available in your deployment.

**Code Points**

- Consolidation routines: `somabrain/consolidation.py`
- Hippocampus integration: `somabrain/hippocampus.py`
- Sleep API handler: `somabrain/app.py::sleep_run`

---

## 5. Neuromodulator Experiments

**Goal** Adjust learning speed dynamically in response to external signals (e.g., reinforcement signals from another system).

**Workflow**

1. Fetch the current neuromodulator state: `curl /neuromodulators`.
2. Update dopamine (or other fields) using `POST /neuromodulators`.
3. Submit feedback (`/context/feedback`) and observe how the learning rate changes (`learning_rate` in `/context/adaptation/state`).

**Code Points**

- Neuromodulator storage: `somabrain/neuromodulators.py`
- Dynamic learning rate flag: `SOMABRAIN_LEARNING_RATE_DYNAMIC`
- Adaptation gains and constraints: `somabrain/learning/adaptation.py`

---

## Verifying a Use Case

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run the relevant API requests | HTTP 200 with payload matching the schemas. |
| 2 | Inspect metrics (`/metrics`) | Tenant-labelled counters increase as expected. |
| 3 | Check Redis or logs | Confirm working memory admissions, adaptation state changes, or consolidation summaries. |

Update this page when new features are promoted from development or when code changes alter the recommended workflow.
# Frequently Asked Questions

**Purpose** Provide quick answers to operational and integration issues new users encounter most often.

**Audience** Developers and operators running SomaBrain locally or in a lab.

**Prerequisites** Read the [Installation Guide](installation.md) and [Quick Start Tutorial](quick-start-tutorial.md).

---

## Installation & Environment

### Q1. `/health` returns `"memory_ok": false`. What does that mean?

`somabrain.app.health` pings the external memory HTTP service using `SOMABRAIN_MEMORY_HTTP_ENDPOINT`. If the service is offline or misconfigured, the check fails and `/remember` will either queue writes (when `SOMABRAIN_REQUIRE_MEMORY=0`) or return HTTP 503.

Common local pitfall (Docker on macOS/Windows): using `http://127.0.0.1:9595` inside a container. Inside containers, `127.0.0.1` is the container itself, not your host. Use `http://host.docker.internal:9595` instead and verify via `GET /diagnostics` (check `memory_endpoint`).

### Q2. Can I run the API without Docker?

Yes, but you must provide the dependencies yourself (Redis, Kafka, OPA, Postgres, memory HTTP service). The `uvicorn somabrain.app:app` command in the [Installation Guide](installation.md) assumes these services already exist. For most users the Docker Compose bundle is the quickest path.

### Q3. How do I disable auth for local testing?
### Q4. How do I quickly verify my wiring?

Call `GET /diagnostics`. It returns a sanitized snapshot including:
- `in_container`: whether the API is running in a container
- `mode`: current deployment mode (`enterprise` maps to production policy)
- `memory_endpoint`: the effective endpoint the API will call
- `external_backends_required` and `require_memory`: enforcement flags

If `memory_endpoint` shows `localhost` while `in_container` is `true`, switch to `http://host.docker.internal:9595` and restart the API container.

Use development mode to relax authentication for local testing. Outside dev, authentication is required and enforced.

---

## Memory Operations

### Q5. `/remember` responded with `503 memory backend unavailable; write queued`. Did I lose data?

No. `MemoryService` journaled the payload to `journal_dir` and flagged the breaker. Once the memory service becomes reachable, queued entries are replayed. If you need the write to succeed synchronously, ensure the backend is online or set `SOMABRAIN_REQUIRE_MEMORY=0` while testing.

### Q6. `/recall` returns an empty list. How can I debug it?

1. Confirm `/remember` succeeded (`"ok": true`, `"breaker_open": null`).
2. Check the memory backend logs to verify it stored the payload.
3. Ensure the query text shares vocabulary with the stored content; the BHDC layer uses semantic similarity but still benefits from overlapping terms.
4. Increase `top_k` or lower scoring thresholds in your client; the API does not expose a server-side threshold parameter.

### Q7. Is there an update endpoint?

There is no dedicated PATCH/PUT endpoint. To “update” a memory, submit a new payload via `/remember` with the corrected content. If you need to remove old entries, call `/delete` with the relevant coordinate or task.

---

## Context & Feedback

### Q8. What happens when I call `/context/feedback`?

The payload is validated by `somabrain/api/schemas/context.py::FeedbackRequest`, then `AdaptationEngine.apply_feedback` adjusts retrieval (`alpha`, `gamma`) and utility (`lambda_`, `mu`, `nu`) weights for your tenant. The state is stored in Redis and mirrored by `/context/adaptation/state`. You can override the learning gains or bounds with the environment variables described in [Cognitive Reasoning](features/cognitive-reasoning.md).

### Q9. I see `"adaptation_applied": false` in the feedback response. Why?

`apply_feedback` returns `False` when the signal is `None`, when the adapter rejects the update due to constraint violations, or when the payload fails validation. Check the response HTTP status (should be 400 if validation failed) and inspect `somabrain/app.py::feedback_endpoint` log messages for details.

---

## Tenancy & Quotas

### Q10. How are tenants separated?

Every request uses `X-Tenant-ID` or, if absent, the first 16 characters of the bearer token. Redis keys, adaptation state, and metrics are namespaced by tenant (`somabrain_ns:<tenant>`). See [Multi-Tenant Usage](features/multi-tenant-usage.md) for a deeper explanation.

### Q11. What happens when the daily write quota is exceeded?

`QuotaManager.allow_write` returns `False`, causing `/remember` to raise HTTP 429 (`"daily write quota exceeded"`). Counters reset at midnight UTC. Adjust `SOMABRAIN_QUOTA_DAILY_WRITES` or modify `QuotaConfig` if you need a higher limit.

---

## Observability

### Q12. Where do I find metrics?

All runtime metrics are exposed at `GET /metrics` in Prometheus format. Look for:

- `somabrain_request_latency_seconds` – per-endpoint latency.
- `somabrain_feedback_total` – feedback submissions per tenant.
- `somabrain_tau_gauge` – current τ values after duplicate adjustments.

Exporters for Redis, Kafka, Postgres, and Prometheus itself are exposed on ports 20001–20007 when you run Docker Compose.

### Q13. How can I correlate logs with API responses?

Pass `X-Request-ID` with your call. The same ID appears in:

- API responses (`trace_id`).
- Structured logs (logged in `somabrain/app.py` handlers).
- Prometheus metrics labels when applicable.

---

Still stuck? Reach out via your team channel with the `trace_id`, tenant ID, and the command you ran. That information maps directly to the runtime state described above.
# User Manual

**Purpose** Explain how to interact with SomaBrain’s public API to store memories, recall context, and drive cognitive workflows.

**Audience** Product developers, application engineers, and operators who call the SomaBrain API directly.

**Prerequisites** A running SomaBrain stack (see [Installation](installation.md)), familiarity with HTTP/JSON, and a tenant credential issued by your platform administrator.

---

## What SomaBrain Provides

SomaBrain is a FastAPI service that exposes cognitive memory and planning primitives. The production binary defined in `somabrain/app.py` wires together:

- `/remember` for episodic memory ingestion handled by `somabrain.services.memory_service.MemoryService`.
- `/recall` for semantic retrieval backed by working memory (`somabrain.mt_wm.MultiTenantWM`) and long‑term storage via the external memory HTTP service.
- `/context/evaluate` and `/context/feedback` for end‑to‑end reasoning loops that exercise the BHDC `QuantumLayer`, `ContextBuilder`, `ContextPlanner`, and `AdaptationEngine`.
- Optional flows such as `/act`, `/plan/suggest`, and `/sleep/run` that are enabled when the full stack is running.

All endpoints are authenticated, tenant‑scoped, and observable with Prometheus metrics emitted from the same runtime.

---

## Quick Navigation

- [Installation](installation.md) – Bring up the Docker stack (API + Redis + Kafka + OPA + Prometheus + Postgres).
- [Quick Start Tutorial](quick-start-tutorial.md) – Issue your first `remember → recall → feedback` sequence.
- [Features](features/) – Detailed guides for each API:
  - [Memory Operations](features/memory-operations.md) – `/remember`, `/recall`, cleanup and quotas.
  - [Cognitive Reasoning](features/cognitive-reasoning.md) – `/context/evaluate`, `/context/feedback`, neuromodulators.
  - [API Integration](features/api-integration.md) – Headers, error handling, rate limits.
  - [Multi-tenant Usage](features/multi-tenant-usage.md) – Tenant isolation, namespaces, quotas.
- [FAQ](faq.md) – Troubleshooting common client issues.

---

## How to Use This Manual

1. Confirm the stack is running (`docker compose ps` and `/health` response) using the [Installation](installation.md) checklist.
2. Follow the [Quick Start Tutorial](quick-start-tutorial.md) to store a memory and verify retrieval with real JSON samples taken from the running API.
3. Deep‑dive into the [Features](features/) section for specialised workflows:
   - Memory ingestion & recall (payload schemas from `somabrain/schemas.py`).
   - Planning and adaptation (grounded in `somabrain/context` and `somabrain/learning` modules).
   - Multi‑tenant isolation and quotas.
4. Keep the [FAQ](faq.md) and the [Technical Manual](../technical/index.md) handy for operational and diagnostic tasks.

Each page includes prerequisites, verification steps, and references so you can audit the behaviour you see against the live codebase.

---

**Related Manuals**

- [Technical Manual](../technical/index.md) – Deployment, observability, runbooks.
- [Development Manual](../development/index.md) – Contributing code and running tests.
- [Onboarding Manual](../onboarding/index.md) – Project orientation for new contributors.
# Quick Start Tutorial

**Purpose** Walk through a minimal “remember → recall” loop against a live SomaBrain instance.

**Audience** First-time users who already have the stack running locally.

**Prerequisites**
- Followed the [Installation Guide](installation.md) and confirmed `/health` returns HTTP 200.
- A memory backend listening on port 9595.
  - For host runs (uvicorn on your machine): `http://localhost:9595`.
  - For Docker containers (macOS/Windows): `http://host.docker.internal:9595`.
  - Verify wiring at `GET /diagnostics` and check `memory_endpoint`.
- A valid bearer token. In dev mode auth may be relaxed; otherwise add `-H "Authorization: Bearer <token>"` to the examples.

Port note: The API host port is fixed at 9696 when started via `scripts/dev_up.sh`. Check `.env` or `ports.json` if needed and adjust the base URL accordingly.

---

## 1. Store a Memory

`/remember` accepts either the legacy payload shape (`{"task": ..., "content": ...}`) or the explicit schema with a `payload` object. The example below uses the explicit schema defined in `somabrain/schemas.py::RememberRequest`.

```bash
curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
        "payload": {
          "task": "geography.fact",
          "content": "Paris is the capital of France.",
          "memory_type": "episodic",
          "importance": 0.9,
          "timestamp": "2024-01-10T10:00:00Z"
        }
      }' | jq
```

Expected response (field names come directly from `RememberResponse`):

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns:public",
  "trace_id": "140351384443504",
  "deadline_ms": null,
  "idempotency_key": null,
  "breaker_open": null,
  "queued": null
}
```

If `breaker_open`/`queued` are `true`, the API could not reach the memory service. Either start the backend or set `SOMABRAIN_REQUIRE_MEMORY=0` while testing.

---

## 2. Recall the Memory

`/recall` returns working-memory hits (`wm`) and long-term candidates (`memory`). The legacy `results` list mirrors the `memory` field for backward compatibility.

```bash
curl -sS http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
        "query": "capital of France",
        "top_k": 5
      }' | jq '.results[:1]'
```

Example output:

```json
[
  {
    "task": "geography.fact",
    "content": "Paris is the capital of France.",
    "memory_type": "episodic",
    "importance": 0.9,
    "score": 0.86,
    "_source": "ltm",
    "_wm_hit": false
  }
]
```

Scores come from `somabrain.scoring.UnifiedScorer` (combination of cosine similarity, FD projection, and recency decay). If the array is empty, confirm the memory backend persisted the write.

---

## 3. (Optional) Capture Feedback

Close the loop by submitting user feedback, which drives the live adaptation engine (`somabrain/learning/adaptation.py`):

```bash
curl -sS http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -d '{
        "session_id": "demo-session",
        "query": "capital of France",
        "prompt": "Summarise the capital of France.",
        "response_text": "Paris is the capital of France.",
        "utility": 0.9,
        "reward": 0.9
      }' | jq
```

Successful responses contain:

```json
{
  "accepted": true,
  "adaptation_applied": true
}
```

The retrieval and utility weights are now updated and persisted to Redis. Inspect `/context/adaptation/state` to view the new values.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `503 memory backend unavailable` when calling `/remember` | HTTP memory service not reachable | Start the backend on port 9595 or disable the requirement for dev testing |
| `/recall` returns empty lists | Write queued or memory backend empty | Check `/remember` response flags and the memory service logs |
| `401 missing bearer token` | Auth enabled | Provide the correct API token; dev mode may relax auth for local testing |
| High latency (>1 s) | Kafka/Redis not ready | Wait for health probes, then retry |
| `/healthz` shows `"memory_ok": false` in Docker | Using `127.0.0.1` inside the container | Set `SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595` and verify via `GET /diagnostics` |

If problems persist, consult the [FAQ](faq.md) and the [Technical Manual](../technical/index.md) for deeper diagnostics.
# Installation Guide

**Purpose** Bring up a functioning SomaBrain stack for evaluation or development.

**Audience** Engineers and operators who need the API running locally or in a lab environment.

**Prerequisites**
- Docker Desktop **or** a host with Docker Engine + Compose Plugin.
- Python 3.11 (optional, for running the API directly).
- An HTTP memory backend listening on port 9595.

Important when using Docker Desktop:
- Inside containers, `127.0.0.1` refers to the container itself. Point the API to the host memory service using `http://host.docker.internal:9595`.
- The provided Dockerfile and dev scripts default to this safe value; you can verify wiring at `GET /diagnostics`.

---

## 1. Clone the Repository

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
```

Check out the branch/tag you intend to run, then copy `.env.example` to `.env` if you want to override defaults.

---

## 2. Start Required Dependencies

The Docker Compose bundle in the repo launches the FastAPI runtime plus Redis, Kafka, OPA, Postgres, Prometheus, and exporters. It **does not** ship the external memory HTTP service – start your memory backend separately before booting SomaBrain.

```bash
# bring up SomaBrain services
docker compose up -d

# follow logs if you need to confirm startup
docker compose logs -f somabrain_app
```

Alternatively, use the helper script that writes a complete `.env`, builds the image if needed, and waits for health:

```bash
./scripts/dev_up.sh
```

On Linux hosts where `host.docker.internal` doesn’t resolve inside containers, set `SOMABRAIN_MEMORY_HTTP_ENDPOINT` in `.env` to the host IP explicitly (e.g., `http://192.168.1.10:9595`).

Verify the stack:

```bash
curl -s http://localhost:9696/health | jq
curl -s http://localhost:9696/metrics | head
curl -s http://localhost:9696/diagnostics | jq   # wiring snapshot (sanitized)
```

A healthy response returns HTTP 200 with `memory_ok`, `embedder_ok`, and `predictor_ok` all `true`. If `ready` is `false`, the API is still booting or waiting for an external dependency (typically the memory service).

---

## 3. Running the API Without Docker (Optional)

Use this mode only when you already have the dependencies (Redis, memory service, Kafka, OPA, Postgres) running elsewhere.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e .[dev]

export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595   # For direct host runs (uvicorn)
export SOMABRAIN_MODE=development          # dev only (auth relaxed via mode)
export SOMABRAIN_REQUIRE_MEMORY=0          # unless you have a live backend

uvicorn somabrain.app:app --host 127.0.0.1 --port 9696 --reload
```

Do not relax auth outside development mode; use proper Bearer tokens in shared environments.

---

## 4. Shutdown & Cleanup

```bash
# stop services, keep volumes
docker compose down

# optional: remove persisted data
docker compose down --volumes

# optional: delete built images
docker image prune -f --filter label=com.docker.compose.project=somabrain
```

---

## Verification Checklist

| Step | Command | Expected |
|------|---------|----------|
| Health check | `curl -s http://localhost:9696/health` | JSON with `"memory_ok": true` (or descriptive error) |
| Remember test | `curl -X POST http://localhost:9696/remember ...` | Response containing `"ok": true` |
| Recall test | `curl -X POST http://localhost:9696/recall ...` | Results array (may be empty if memory backend ignored the write) |

If any check fails, consult [FAQ](faq.md) and `docker compose logs`.

---

**Common Issues**

- `503 memory backend unavailable` – the memory HTTP service on port 9595 was not reachable; either point `SOMABRAIN_MEMORY_HTTP_ENDPOINT` at a working endpoint or set `SOMABRAIN_REQUIRE_MEMORY=0` for non-production testing.
- Port clashes on 9696 / 20001‑20007 – adjust exported ports in `.env`.
- Kafka slow to start – wait for the broker healthcheck (`somabrain_kafka` container) before sending recall requests.
- Authentication failures – provide a Bearer token (see `.env` for `SOMABRAIN_API_TOKEN`). In dev mode, auth may be relaxed by policy.

---

**Next Steps**

- Walk through the [Quick Start Tutorial](quick-start-tutorial.md) to validate memory ingestion and recall.
- Review [features/api-integration.md](features/api-integration.md) for required headers and error handling.
- For production hardening, follow the [Technical Manual – Deployment](../technical/deployment.md).
