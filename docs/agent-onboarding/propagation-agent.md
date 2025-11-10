# Propagation Agent Guide

**Purpose**: Understand memory storage and retrieval operations in SomaBrain.

## Memory Operations (Code-Verified)

### 1. Remember (Store Memory)

**Endpoint**: `POST /remember`

**Implementation**: `somabrain/app.py` line ~2800

**Request Body** (two formats supported):

```json
{
  "payload": {
    "task": "Paris is the capital of France",
    "memory_type": "episodic",
    "timestamp": 1234567890
  }
}
```

OR (legacy format):

```json
{
  "task": "Paris is the capital of France",
  "memory_type": "episodic"
}
```

**What Happens** (actual code flow):

1. **Auth Check**: `require_auth(request, cfg)` - validates Bearer token
2. **Tenant Resolution**: `get_tenant(request, cfg.namespace)` - extracts tenant ID
3. **Rate Limiting**: `rate_limiter.allow(ctx.tenant_id)` - checks RPS limits
4. **Quota Check**: `quotas.allow_write(ctx.tenant_id, 1)` - daily write limit
5. **Embedding**: `embedder.embed(text)` - generates vector
6. **Memory Service**: `memsvc.aremember(key, payload)` - stores to backend
7. **WM Admission**: `mt_wm.admit(ctx.tenant_id, wm_vec, payload)` - adds to working memory
8. **HRR Context**: `mt_ctx.admit(ctx.tenant_id, anchor_id, hrr_vec)` - if HRR enabled

**Response**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns",
  "trace_id": "...",
  "deadline_ms": null,
  "idempotency_key": null
}
```

### 2. Recall (Retrieve Memory)

**Endpoint**: `POST /recall`

**Implementation**: `somabrain/app.py` line ~2400

**Request**:

```json
{
  "query": "capital of France",
  "top_k": 3
}
```

**What Happens** (actual code flow):

1. **Embedding**: `embedder.embed(text)` - query vector
2. **WM Recall**: `mt_wm.recall(ctx.tenant_id, wm_qv, top_k)` - working memory hits
3. **LTM Recall**: `_recall_ltm(mem_client, text, top_k, ...)` - long-term memory
4. **Scoring**: `_score_memory_candidate(...)` - composite scoring (cosine + FD + recency)
5. **HRR Cleanup**: `mt_ctx.cleanup(ctx.tenant_id, hrr_qv)` - if enabled
6. **Caching**: Results cached in `_recall_cache` with 2s TTL

**Response**:

```json
{
  "wm": [
    {"score": 0.95, "payload": {"task": "..."}}
  ],
  "memory": [
    {"task": "Paris is the capital of France", "timestamp": 1234567890}
  ],
  "results": [...],  // alias for memory
  "namespace": "somabrain_ns",
  "trace_id": "..."
}
```

## Scoring System (UnifiedScorer)

**File**: `somabrain/scoring.py`

**Components** (actual weights from code):

```python
w_cosine: float = 0.6      # Cosine similarity weight
w_fd: float = 0.25          # Frequent-Directions weight
w_recency: float = 0.15     # Recency boost weight
recency_tau: float = 32.0   # Decay time constant
```

**Formula**:

```
score = w_cosine * cosine(q, c) + w_fd * fd_sim(q, c) + w_recency * exp(-age/tau)
```

## Working Memory (MultiTenantWM)

**File**: `somabrain/mt_wm.py`

**Default Capacity**: 64 items per tenant (`wm_size` in config)

**Operations**:
- `admit(tenant_id, vec, payload)` - add item
- `recall(tenant_id, query_vec, top_k)` - retrieve similar items
- `items(tenant_id)` - list all items

## HRR Context (MultiTenantHRRContext)

**File**: `somabrain/mt_context.py`

**Purpose**: Cleanup/disambiguation using hyperdimensional anchors

**Config** (from `HRRContextConfig`):
- `max_anchors`: 10000 (default)
- `decay_lambda`: 0.0 (no decay by default)
- `min_confidence`: 0.0 (accept all matches)

**Operations**:
- `admit(tenant_id, anchor_id, hrr_vec)` - register anchor
- `cleanup(tenant_id, query_hrr)` - find best matching anchor
- `analyze(tenant_id, hrr_vec)` - get score + margin

## Memory Service Client

**File**: `somabrain/services/memory_service.py`

**Backend**: HTTP-based external memory service

**Required Config**:
```python
http.endpoint = "http://localhost:9595"  # SOMABRAIN_MEMORY_HTTP_ENDPOINT
http.token = "devtoken"                   # SOMABRAIN_MEMORY_HTTP_TOKEN
```

**Circuit Breaker** (fail-fast):
- `_failure_threshold`: 3 consecutive failures
- `_reset_interval`: 60 seconds
- Raises `RuntimeError` when circuit open

## Example: Complete Remember Flow

```python
# 1. Client sends request
POST /remember
{
  "payload": {
    "task": "Learn Python",
    "memory_type": "episodic"
  }
}

# 2. API processes (somabrain/app.py)
# - Auth: require_auth()
# - Tenant: get_tenant() → "sandbox"
# - Rate limit: rate_limiter.allow("sandbox") → True
# - Quota: quotas.allow_write("sandbox", 1) → True
# - Embed: embedder.embed("Learn Python") → [256-dim vector]
# - Store: memsvc.aremember("Learn Python", payload)
# - WM: mt_wm.admit("sandbox", vec, payload)
# - HRR: mt_ctx.admit("sandbox", "Learn Python", hrr_vec)

# 3. Response
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

## Testing Memory Operations

```bash
# Store a memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "Test memory", "memory_type": "episodic"}}'

# Recall it
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "Test memory", "top_k": 3}'
```

## Key Files to Read

1. `somabrain/app.py` - API endpoints (remember, recall)
2. `somabrain/scoring.py` - UnifiedScorer implementation
3. `somabrain/mt_wm.py` - Working memory
4. `somabrain/services/memory_service.py` - Backend client
5. `somabrain/quantum.py` - HRR operations
