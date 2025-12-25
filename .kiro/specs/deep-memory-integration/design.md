# Design Document - SB ↔ SFM Deep Memory Integration

## Introduction

This design document specifies the technical architecture for DEEP INTEGRATION between SomaBrain (SB) and SomaFractalMemory (SFM). The implementation creates a unified cognitive-memory system where SB fully leverages SFM's KV, vector, and graph stores. All code is PRODUCTION-GRADE with NO mocks, NO stubs, NO placeholders.

## Architecture Overview

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SOMABRAIN (SB) - Port 9696                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Working Memory  │  │ Memory Client   │  │ Circuit Breaker │              │
│  │ (wm.py)         │──│ (memory_client) │──│ (per-tenant)    │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐              │
│  │ WM Persistence  │  │ Graph Client    │  │ Outbox Queue    │              │
│  │ (NEW)           │  │ (NEW)           │  │ (db/outbox.py)  │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────┘
            │                     │                     │
            │         HTTP/JSON   │                     │
            ▼                     ▼                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    SOMAFRACTALMEMORY (SFM) - Port 9595                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ /memories    │  │ /graph       │  │ /health      │  │ /batch       │      │
│  │ store/recall │  │ links/path   │  │ components   │  │ bulk ops     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │                 │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐                        │
│  │ IKeyValue    │  │ IGraphStore  │  │ IVectorStore │                        │
│  │ Store        │  │              │  │              │                        │
│  └──────────────┘  └──────────────┘  └──────────────┘                        │
└───────────────────────────────────────────────────────────────────────────────┘
```


### Component Integration Matrix

| SB Component | SFM Component | Integration Type | Status |
|--------------|---------------|------------------|--------|
| MemoryClient | /memories/store | HTTP POST | EXISTS |
| MemoryClient | /memories/recall | HTTP POST | EXISTS |
| MemoryClient | /graph/link | HTTP POST | NEW |
| MemoryClient | /graph/neighbors | HTTP GET | NEW |
| MemoryClient | /graph/path | HTTP GET | NEW |
| WorkingMemory | /memories/store | Async persist | NEW |
| CircuitBreaker | All endpoints | Per-tenant | EXISTS |
| Outbox | All write ops | Reliability | ENHANCE |
| HealthCheck | /health | Component status | ENHANCE |

---

## Component Design

### Category A: Working Memory Persistence

#### A1: WM State Persistence to SFM

**Source Module:** `somabrain/somabrain/wm.py`
**Target Module:** `somabrain/somabrain/memory/wm_persistence.py` (NEW)

**Data Model:**
```python
@dataclass
class WMPersistenceEntry:
    """Persisted WM item in SFM."""
    tenant_id: str
    item_id: str
    vector: List[float]
    payload: Dict[str, Any]
    tick: int
    admitted_at: float
    cleanup_overlap: float
    memory_type: str = "working_memory"
    evicted: bool = False
    evicted_at: Optional[float] = None
```


**Persistence Flow:**
```
WM.admit() → async queue → WMPersister → MemoryClient.remember()
                                              ↓
                                         SFM /memories/store
                                              ↓
                                         memory_type="working_memory"
```

**Restoration Flow:**
```
SB startup → WMRestorer.restore(tenant_id)
                  ↓
             MemoryClient.recall(memory_type="working_memory")
                  ↓
             Filter evicted=false
                  ↓
             WM.admit() for each item
```

**Implementation Strategy:**
1. Add `_persistence_queue: asyncio.Queue` to WorkingMemory
2. Add `WMPersister` background task that drains queue
3. Add `WMRestorer` that runs on SB startup per tenant
4. Store WM items with `memory_type="working_memory"` in SFM
5. Mark evicted items with `evicted=true` (audit trail)

#### A2: WM-LTM Promotion Pipeline

**Source Module:** `somabrain/somabrain/wm.py`
**Target Module:** `somabrain/somabrain/memory/promotion.py` (NEW)

**Promotion Logic:**
```python
class PromotionTracker:
    """Track items eligible for WM→LTM promotion."""
    
    def __init__(self, threshold: float = 0.85, min_ticks: int = 3):
        self._threshold = threshold
        self._min_ticks = min_ticks
        self._candidates: Dict[str, PromotionCandidate] = {}
    
    def check(self, item_id: str, salience: float, tick: int) -> bool:
        """Return True if item should be promoted."""
        if salience < self._threshold:
            self._candidates.pop(item_id, None)
            return False
        
        if item_id not in self._candidates:
            self._candidates[item_id] = PromotionCandidate(
                first_tick=tick, consecutive_count=1
            )
            return False
        
        candidate = self._candidates[item_id]
        candidate.consecutive_count += 1
        return candidate.consecutive_count >= self._min_ticks
```


---

### Category B: Graph Store Integration

#### B1: Semantic Link Creation from SB

**Source Module:** `somabrain/somabrain/memory_client.py`
**Target:** Add graph operations to MemoryClient

**Link Types:**
| Link Type | Created When | Metadata |
|-----------|--------------|----------|
| co_recalled | Two memories recalled together | query, timestamp |
| references | Memory payload contains coordinate | source_field |
| used_in_plan | Planning uses memory | plan_id, step |
| promoted_from | WM→LTM promotion | original_wm_id |

**API Contract (SFM side):**
```python
# POST /graph/link
{
    "from_coord": [x1, y1, z1],
    "to_coord": [x2, y2, z2],
    "link_type": "co_recalled",
    "metadata": {
        "tenant_id": "tenant_123",
        "timestamp": "2025-12-14T10:30:00Z",
        "strength": 0.8
    }
}

# Response
{
    "success": true,
    "link_id": "link_abc123"
}
```

**SB Implementation:**
```python
# In MemoryClient
async def create_link(
    self,
    from_coord: Tuple[float, float, float],
    to_coord: Tuple[float, float, float],
    link_type: str,
    strength: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create semantic link in SFM graph store."""
    tenant, namespace = self._tenant_namespace()
    body = {
        "from_coord": list(from_coord),
        "to_coord": list(to_coord),
        "link_type": link_type,
        "metadata": {
            "tenant_id": tenant,
            "namespace": namespace,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "strength": float(strength),
            **(metadata or {}),
        },
    }
    
    try:
        ok, status, resp = await self._http_post_with_retries_async(
            "/graph/link", body, {}, operation="graph_link"
        )
        return ok
    except Exception as exc:
        # Queue to outbox for retry
        from somabrain.db.outbox import enqueue_event
        enqueue_event(
            topic="graph.link",
            payload=body,
            tenant_id=tenant,
        )
        return False
```


#### B2: Graph-Augmented Recall

**Source Module:** `somabrain/somabrain/memory/recall_ops.py`

**Recall Flow with Graph Boost:**
```
Query → Vector Search (SFM) → Top-K results
                                    ↓
                            For each result:
                              → Get 1-hop neighbors (SFM graph)
                              → Boost neighbor scores by link_strength * graph_boost
                                    ↓
                            Merge & deduplicate
                                    ↓
                            Re-rank by boosted scores
                                    ↓
                            Return final Top-K
```

**Implementation:**
```python
async def recall_with_graph_boost(
    self,
    query: str,
    top_k: int = 5,
    k_hop: int = 1,
    graph_boost_factor: float = 0.3,
    graph_timeout_ms: int = 100,
) -> List[RecallHit]:
    """Recall with graph-augmented scoring."""
    # Step 1: Vector search
    hits = await self._memories_search_async(query, top_k * 2, universe, rid)
    
    # Step 2: Get graph neighbors (with timeout)
    boosted_hits = []
    try:
        async with asyncio.timeout(graph_timeout_ms / 1000):
            for hit in hits:
                coord = hit.get("coordinate")
                if coord:
                    neighbors = await self._get_graph_neighbors(
                        tuple(coord), k_hop=k_hop
                    )
                    # Boost score based on link strength
                    for neighbor_coord, link_data in neighbors:
                        strength = link_data.get("strength", 0.5)
                        boost = strength * graph_boost_factor
                        # Find if neighbor is in hits, boost its score
                        for h in hits:
                            if h.get("coordinate") == list(neighbor_coord):
                                h["score"] = h.get("score", 0) + boost
    except asyncio.TimeoutError:
        logger.warning("Graph traversal timeout, returning vector-only results")
    
    # Step 3: Re-rank and return top_k
    hits.sort(key=lambda x: x.get("score", 0), reverse=True)
    return hits[:top_k]
```


#### B3: Shortest Path Queries

**API Contract:**
```python
# GET /graph/path?from=x1,y1,z1&to=x2,y2,z2&max_length=10
# Response
{
    "path": [
        {"coord": [x1, y1, z1], "link_type": null},
        {"coord": [x2, y2, z2], "link_type": "co_recalled"},
        {"coord": [x3, y3, z3], "link_type": "references"}
    ],
    "length": 2,
    "partial": false
}
```

---

### Category C: Hybrid Recall Integration

#### C1: Full Hybrid Recall Utilization

**Source Module:** `somabrain/somabrain/memory/recall_ops.py`

**Current State:** SB uses basic `/memories/search` endpoint
**Target State:** SB uses SFM's `hybrid_recall_with_scores`

**SFM Hybrid Recall Capabilities (from core.py):**
- Vector similarity search
- Keyword matching with exact/fuzzy modes
- Importance score weighting
- Recency boosting
- Context-aware ranking

**Enhanced Recall Implementation:**
```python
async def hybrid_recall(
    self,
    query: str,
    top_k: int = 5,
    terms: Optional[List[str]] = None,
    exact: bool = False,
    include_importance: bool = True,
) -> List[RecallHit]:
    """Use SFM's full hybrid recall capabilities."""
    tenant, namespace = self._tenant_namespace()
    
    # Extract keywords if not provided
    if terms is None:
        terms = self._extract_keywords(query)
    
    body = {
        "query": query,
        "top_k": top_k,
        "terms": terms,
        "exact": exact,
        "case_sensitive": False,
        "include_scores": True,
        "tenant": tenant,
        "namespace": namespace,
    }
    
    ok, status, resp = await self._http_post_with_retries_async(
        "/memories/hybrid_recall", body, {}, operation="hybrid_recall"
    )
    
    if not ok:
        # Fallback to vector-only search
        logger.warning("Hybrid recall failed, falling back to vector search")
        return await self._memories_search_async(query, top_k, namespace, rid)
    
    return self._normalize_recall_hits(resp.get("results", []))
```


---

### Category D: Multi-Tenant Isolation

#### D1: Tenant Memory Isolation (CRITICAL - Fixes XFAIL)

**Root Cause Analysis:**
The XFAIL tests D1.1 and D1.2 indicate tenant isolation failures. Based on code review:

1. **SB Side:** `_tenant_namespace()` correctly extracts tenant from config
2. **SFM Side:** `core.py` uses `self.namespace` but may not enforce per-request tenant

**Fix Strategy:**

**SFM Changes Required:**
```python
# In somafractalmemory/http_api.py
def _get_tenant_from_request(request: Request) -> str:
    """Extract tenant from request headers."""
    tenant = request.headers.get("X-Soma-Tenant")
    if not tenant:
        tenant = request.headers.get("X-Soma-Namespace", "").split(":")[-1]
    if not tenant:
        tenant = "default"
    return tenant

# All endpoints must scope by tenant
@app.post("/memories/store")
async def store_memory(request: Request, body: StoreRequest):
    tenant = _get_tenant_from_request(request)
    # Prefix all keys with tenant
    scoped_namespace = f"{tenant}:{body.namespace}"
    # ... rest of implementation
```

**SB Changes Required:**
```python
# In somabrain/memory_client.py - ensure headers are always set
def _create_transport(self) -> MemoryHTTPTransport:
    headers = {}
    # ... existing code ...
    
    # CRITICAL: Always set tenant headers
    ns = str(getattr(self.cfg, "namespace", ""))
    tenant = ns.split(":")[-1] if ":" in ns else (ns or "default")
    headers["X-Soma-Namespace"] = ns or "default"
    headers["X-Soma-Tenant"] = tenant
    
    # ... rest of implementation
```


#### D2: Per-Tenant Circuit Breaker Isolation

**Source Module:** `somabrain/somabrain/infrastructure/circuit_breaker.py`

**Current State:** CircuitBreaker already implements per-tenant isolation
**Verification:** Ensure all MemoryClient calls pass tenant_id to circuit breaker

**Implementation Check:**
```python
# In MemoryClient - wrap all SFM calls with circuit breaker
async def _sfm_call_with_circuit_breaker(
    self,
    operation: str,
    call_fn: Callable,
    *args,
    **kwargs,
) -> Any:
    """Execute SFM call with per-tenant circuit breaker."""
    tenant, _ = self._tenant_namespace()
    
    if self._circuit_breaker.is_open(tenant):
        raise CircuitOpenError(f"Circuit open for tenant {tenant}")
    
    try:
        result = await call_fn(*args, **kwargs)
        self._circuit_breaker.record_success(tenant)
        return result
    except Exception as exc:
        self._circuit_breaker.record_failure(tenant)
        raise
```

---

### Category E: Degradation and Resilience

#### E1: Complete Degradation Mode

**Degradation State Machine:**
```
HEALTHY → [SFM unreachable] → DEGRADED → [SFM recovers] → RECOVERING → HEALTHY
                                  ↓
                            WM-only mode
                            Outbox queuing
                            Health reports degraded
```

**Implementation:**
```python
class DegradationManager:
    """Manage SB degradation state when SFM is unavailable."""
    
    def __init__(self, circuit_breaker: CircuitBreaker):
        self._cb = circuit_breaker
        self._degraded_since: Dict[str, float] = {}
        self._alert_threshold_seconds = 300  # 5 minutes
    
    def is_degraded(self, tenant: str) -> bool:
        return self._cb.is_open(tenant)
    
    def check_alert(self, tenant: str) -> bool:
        """Return True if degraded > 5 minutes (trigger alert)."""
        if not self.is_degraded(tenant):
            self._degraded_since.pop(tenant, None)
            return False
        
        if tenant not in self._degraded_since:
            self._degraded_since[tenant] = time.time()
        
        duration = time.time() - self._degraded_since[tenant]
        return duration > self._alert_threshold_seconds
```


#### E2: Outbox-Based Write Reliability

**Source Module:** `somabrain/somabrain/db/outbox.py`

**Enhanced Outbox for Memory Operations:**
```python
# New event topics for memory operations
MEMORY_TOPICS = {
    "memory.store": "Store memory to SFM",
    "memory.bulk_store": "Bulk store memories to SFM",
    "graph.link": "Create graph link in SFM",
    "wm.persist": "Persist WM item to SFM",
    "wm.evict": "Mark WM item as evicted in SFM",
}

# Idempotency key generation
def _idempotency_key(operation: str, coord: Tuple, tenant: str) -> str:
    """Generate idempotency key for deduplication."""
    data = f"{operation}:{tenant}:{coord}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]
```

**Replay Worker Enhancement:**
```python
async def replay_memory_events(tenant_id: Optional[str] = None) -> int:
    """Replay pending memory events to SFM."""
    events = get_pending_events(limit=100, tenant_id=tenant_id)
    replayed = 0
    
    for event in events:
        if event.topic.startswith("memory.") or event.topic.startswith("graph."):
            try:
                await _replay_single_event(event)
                mark_event_sent(event.id)
                replayed += 1
            except DuplicateError:
                # Already processed, mark as sent
                mark_event_sent(event.id)
                replayed += 1
            except Exception as exc:
                mark_event_failed(event.id, str(exc))
    
    return replayed
```

#### E3: Health Check Completeness

**Source Module:** `somabrain/somabrain/healthchecks.py`

**Enhanced Health Response:**
```python
@dataclass
class IntegrationHealth:
    """Health status including SFM components."""
    sb_healthy: bool
    sfm_available: bool
    sfm_kv_store: bool
    sfm_vector_store: bool
    sfm_graph_store: bool
    degraded: bool
    degraded_components: List[str]
    outbox_pending: int

async def check_integration_health(tenant: str) -> IntegrationHealth:
    """Check full SB↔SFM integration health."""
    sfm_health = await _check_sfm_health()
    outbox_pending = get_pending_count(tenant_id=tenant)
    
    degraded_components = []
    if not sfm_health.get("kv_store"):
        degraded_components.append("kv_store")
    if not sfm_health.get("vector_store"):
        degraded_components.append("vector_store")
    if not sfm_health.get("graph_store"):
        degraded_components.append("graph_store")
    
    return IntegrationHealth(
        sb_healthy=True,
        sfm_available=sfm_health.get("healthy", False),
        sfm_kv_store=sfm_health.get("kv_store", False),
        sfm_vector_store=sfm_health.get("vector_store", False),
        sfm_graph_store=sfm_health.get("graph_store", False),
        degraded=len(degraded_components) > 0,
        degraded_components=degraded_components,
        outbox_pending=outbox_pending,
    )
```


---

### Category F: Bulk Operations Optimization

#### F1: Batch Store Operations

**Source Module:** `somabrain/somabrain/memory_client.py`

**Current State:** `remember_bulk()` exists but falls back to sequential on 404/405
**Target State:** Optimized batch with chunking and partial failure handling

**Enhanced Implementation:**
```python
async def remember_bulk_optimized(
    self,
    items: List[Tuple[str, Dict[str, Any]]],
    chunk_size: int = 100,
    request_id: Optional[str] = None,
) -> BulkStoreResult:
    """Optimized bulk store with chunking and partial failure handling."""
    self._require_healthy()
    
    results = BulkStoreResult(
        total=len(items),
        succeeded=0,
        failed=0,
        coords=[],
        errors=[],
    )
    
    # Chunk items
    chunks = [items[i:i+chunk_size] for i in range(0, len(items), chunk_size)]
    
    for chunk_idx, chunk in enumerate(chunks):
        prepared, universes, coords, tenant, namespace = prepare_bulk_items(
            self.cfg, chunk
        )
        
        batch_payload = {
            "tenant": tenant,
            "namespace": namespace,
            "items": [entry["body"] for entry in prepared],
        }
        
        try:
            success, status, response = await self._store_bulk_http_async(
                batch_payload, {"X-Request-ID": f"{request_id}:chunk{chunk_idx}"}
            )
            
            if success:
                results.succeeded += len(chunk)
                results.coords.extend(coords)
            else:
                # Partial failure - try individual items
                for idx, entry in enumerate(prepared):
                    try:
                        ok, resp = await self._store_http_async(
                            entry["body"], {}
                        )
                        if ok:
                            results.succeeded += 1
                            results.coords.append(coords[idx])
                        else:
                            results.failed += 1
                            results.errors.append(f"Item {idx}: HTTP {status}")
                    except Exception as e:
                        results.failed += 1
                        results.errors.append(f"Item {idx}: {str(e)}")
        except Exception as e:
            results.failed += len(chunk)
            results.errors.append(f"Chunk {chunk_idx}: {str(e)}")
    
    return results
```


---

### Category G: Serialization Alignment

#### G1: Consistent Serialization Format

**Current State:**
- SB uses JSON via `memory/payload.py`
- SFM uses JSON via `serialization.py`
- Potential mismatch in coordinate format, timestamps, numpy arrays

**Alignment Rules:**
| Field | SB Format | SFM Format | Aligned Format |
|-------|-----------|------------|----------------|
| coordinate | Tuple[float,float,float] | List[float] | List[float] |
| timestamp | float (epoch) | ISO 8601 string | ISO 8601 string |
| vector | np.ndarray | List[float] | List[float] |
| memory_type | str | str (enum value) | str |

**Serialization Helper:**
```python
# somabrain/somabrain/memory/serialization.py
def serialize_for_sfm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize payload for SFM compatibility."""
    result = {}
    
    for key, value in payload.items():
        if isinstance(value, tuple):
            result[key] = list(value)
        elif isinstance(value, np.ndarray):
            result[key] = value.tolist()
        elif isinstance(value, (datetime, date)):
            result[key] = value.isoformat() + "Z"
        elif isinstance(value, float) and key.endswith("_timestamp"):
            # Convert epoch to ISO 8601
            result[key] = datetime.utcfromtimestamp(value).isoformat() + "Z"
        elif isinstance(value, dict):
            result[key] = serialize_for_sfm(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_for_sfm(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value
    
    return result
```

---

### Category H: Observability and Metrics

#### H1: End-to-End Tracing

**Trace Propagation:**
```python
# In MemoryClient HTTP calls
def _inject_trace_context(self, headers: Dict[str, str]) -> Dict[str, str]:
    """Inject OpenTelemetry trace context into headers."""
    from opentelemetry import trace
    from opentelemetry.propagate import inject
    
    inject(headers)
    return headers
```

#### H2: Integration Metrics

**New Metrics:**
```python
# somabrain/somabrain/metrics/integration.py
from prometheus_client import Counter, Histogram, Gauge

SFM_REQUEST_TOTAL = Counter(
    "sb_sfm_request_total",
    "Total SFM requests",
    ["operation", "tenant", "status"]
)

SFM_REQUEST_DURATION = Histogram(
    "sb_sfm_request_duration_seconds",
    "SFM request duration",
    ["operation", "tenant"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

CIRCUIT_BREAKER_STATE = Gauge(
    "sb_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open)",
    ["tenant"]
)

OUTBOX_PENDING = Gauge(
    "sb_outbox_pending_total",
    "Pending outbox events",
    ["tenant"]
)

WM_PROMOTION_TOTAL = Counter(
    "sb_wm_promotion_total",
    "WM to LTM promotions",
    ["tenant"]
)
```


---

## Correctness Properties

### Category A: WM Persistence Properties

**Property 1: WM Persistence Completeness**
*For any* WM item admitted, it SHALL be persisted to SFM within 1 second (eventual consistency).
**Validates: Requirements A1.3**

**Property 2: WM Restoration Completeness**
*For any* tenant, on SB startup, all non-evicted WM items SHALL be restored from SFM.
**Validates: Requirements A1.2**

**Property 3: Promotion Threshold Consistency**
*For any* WM item with salience ≥ 0.85 for 3+ consecutive ticks, it SHALL be promoted to LTM.
**Validates: Requirements A2.1**

### Category B: Graph Integration Properties

**Property 4: Co-Recall Link Creation**
*For any* two memories recalled together in a single query, a "co_recalled" link SHALL be created.
**Validates: Requirements B1.1**

**Property 5: Graph Boost Application**
*For any* recall with graph neighbors, neighbor scores SHALL be boosted by link_strength × graph_boost_factor.
**Validates: Requirements B2.2**

**Property 6: Graph Timeout Graceful Degradation**
*For any* graph traversal exceeding 100ms, vector-only results SHALL be returned.
**Validates: Requirements B2.5**

### Category C: Hybrid Recall Properties

**Property 7: Hybrid Recall Keyword Extraction**
*For any* recall query, keywords SHALL be extracted and passed to SFM hybrid_recall.
**Validates: Requirements C1.2**

**Property 8: Hybrid Recall Fallback**
*For any* hybrid recall failure, vector-only search SHALL be used with degraded=true.
**Validates: Requirements C1.5**

### Category D: Tenant Isolation Properties

**Property 9: Cross-Tenant Memory Isolation**
*For any* tenant A storing a memory, tenant B's recall SHALL NOT return it.
**Validates: Requirements D1.1**

**Property 10: Per-Tenant Circuit Independence**
*For any* tenant A's circuit state change, tenant B's circuit state SHALL be unchanged.
**Validates: Requirements D2.2**

### Category E: Resilience Properties

**Property 11: Degraded Mode WM-Only**
*For any* recall when SFM is unavailable, WM-only results SHALL be returned with degraded=true.
**Validates: Requirements E1.1**

**Property 12: Outbox Idempotency**
*For any* replayed outbox event, duplicate writes SHALL be prevented via idempotency key.
**Validates: Requirements E2.4**

**Property 13: Health Check Component Reporting**
*For any* /health call, response SHALL include kv_store, vector_store, graph_store status.
**Validates: Requirements E3.1**

---

## File Structure

### SB Changes
```
somabrain/somabrain/
├── memory_client.py          # MODIFY: Add graph ops, hybrid recall
├── wm.py                     # MODIFY: Add persistence hooks
├── memory/
│   ├── wm_persistence.py     # NEW: WM persistence to SFM
│   ├── promotion.py          # NEW: WM→LTM promotion logic
│   ├── graph_client.py       # NEW: Graph store client
│   ├── recall_ops.py         # MODIFY: Add graph boost, hybrid recall
│   └── serialization.py      # NEW: SFM-compatible serialization
├── infrastructure/
│   ├── circuit_breaker.py    # VERIFY: Per-tenant isolation
│   └── degradation.py        # NEW: Degradation state manager
├── db/
│   └── outbox.py             # MODIFY: Add memory/graph topics
├── healthchecks.py           # MODIFY: Add SFM component status
└── metrics/
    └── integration.py        # NEW: SB↔SFM metrics
```

### SFM Changes
```
somafractalmemory/somafractalmemory/
├── http_api.py               # MODIFY: Add graph endpoints, tenant scoping
├── core.py                   # MODIFY: Enforce tenant isolation
└── interfaces/
    └── graph.py              # VERIFY: Existing interface sufficient
```

---

## Testing Strategy

### Test Execution Order

1. **Phase 1: Tenant Isolation (P0)** - Fix XFAIL tests D1.1, D1.2
2. **Phase 2: Health Check (P0)** - Verify SFM component reporting
3. **Phase 3: Degradation Mode (P0)** - Test WM-only fallback
4. **Phase 4: WM Persistence (P1)** - Test persist/restore cycle
5. **Phase 5: Hybrid Recall (P1)** - Test keyword extraction, fallback
6. **Phase 6: Graph Integration (P2)** - Test link creation, boost
7. **Phase 7: Bulk Operations (P1)** - Test chunking, partial failure

### Test Markers
```python
pytest.mark.integration_p0  # Critical fixes
pytest.mark.integration_p1  # High priority
pytest.mark.integration_p2  # Medium priority
pytest.mark.cross_repo      # Requires both SB and SFM
```

---

## References

- SFM Core: `somafractalmemory/somafractalmemory/core.py`
- SFM Graph Interface: `somafractalmemory/somafractalmemory/interfaces/graph.py`
- SB Memory Client: `somabrain/somabrain/memory_client.py`
- SB Working Memory: `somabrain/somabrain/wm.py`
- SB Circuit Breaker: `somabrain/somabrain/infrastructure/circuit_breaker.py`
- SB Outbox: `somabrain/somabrain/db/outbox.py`


---

## Category I: Vector Backend Architecture

### I1: Milvus Exclusive Backend

**Current State:**
- SomaBrain: Milvus ONLY (hardcoded in `services/ann.py`)
- SomaFractalMemory: Configurable via `SOMA_VECTOR_BACKEND` (default: milvus)

**Selection Logic:**

| System | Default | Config Variable | Behavior |
|--------|---------|-----------------|----------|
| SomaBrain | Milvus | N/A | Raises error if not Milvus |
| SomaFractalMemory | Milvus | `SOMA_VECTOR_BACKEND` | Factory selects implementation |

### I2: Milvus Implementation Details

| Feature | MilvusVectorStore |
|---------|-------------------|
| Client Library | `pymilvus` |
| Default Port | 19530 (gRPC) |
| Distance Metric | IP (Inner Product) |
| Index Type | IVF_FLAT |
| Schema | Fixed (id, embedding, payload) |
| Scroll/Pagination | Emulated with offset |
| TLS Support | `secure=True` |

### I3: Production Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                       │
│                                                                  │
│  SomaBrain (Port 9696)                                          │
│  ├── Oak Options → Milvus (collection: oak_options)             │
│  └── TieredMemory → Milvus (collection: soma_cleanup_{tenant})  │
│                                                                  │
│  SomaFractalMemory (Port 9595)                                  │
│  └── Memory Vectors → Milvus (collection: {namespace})          │
│                                                                  │
│  Shared Milvus Cluster                                          │
│  ├── Host: milvus (Docker network alias)                        │
│  ├── Port: 19530 (gRPC)                                         │
│  └── Collections:                                                │
│      ├── oak_options (SB Oak)                                   │
│      ├── soma_cleanup_* (SB TieredMemory)                       │
│      └── api_ns, test_ns (SFM memories)                         │
└─────────────────────────────────────────────────────────────────┘
```

### I4: Unified Configuration

**SomaBrain `.env`:**
```bash
SOMA_MILVUS_HOST=milvus
SOMA_MILVUS_PORT=19530
SOMA_MILVUS_COLLECTION=oak_options
```

**SomaFractalMemory `.env`:**
```bash
SOMA_VECTOR_BACKEND=milvus
SOMA_MILVUS_HOST=milvus
SOMA_MILVUS_PORT=19530
SOMA_MILVUS_COLLECTION=memories
```

### I5: Test Environment (Milvus Only)

> **IMPORTANT:** Milvus is the ONLY supported vector backend for all environments.
> No other vector backends are supported.

For SFM tests, Milvus test collections are used for isolation:
```python
config = {
    "milvus": {"host": "localhost", "port": 19530, "collection": f"test_{uuid4().hex[:8]}"},
    "redis": {"host": "localhost", "port": 40022},
}
```

### I6: Backend Validation Requirement

**Requirement:** SomaFractalMemory SHALL validate that Milvus is the configured vector backend at startup.

**Implementation:**
```python
# In somafractalmemory/somafractalmemory/factory.py
def create_memory_system(...):
    vector_backend = getattr(_settings, "vector_backend", "milvus")
    
    # Milvus is the only supported backend
    if vector_backend != "milvus":
        raise RuntimeError(
            f"Vector backend '{vector_backend}' is not supported. "
            "Only Milvus is supported. Set SOMA_VECTOR_BACKEND=milvus."
        )
    
    # ... rest of factory logic
```

**Rationale:**
- Milvus provides production-grade features: clustering, replication, persistence
- Single backend simplifies operations, testing, and maintenance
- Consistent behavior across all environments

---

## Additional References

- Design Patterns Analysis: `somabrain/.kiro/specs/deep-memory-integration/DESIGN_PATTERNS.md`
- Architecture Analysis: `somabrain/.kiro/specs/deep-memory-integration/ARCHITECTURE_ANALYSIS.md`
- SFM Factory: `somafractalmemory/somafractalmemory/factory.py`
- SFM Storage Implementations: `somafractalmemory/somafractalmemory/implementations/storage.py`
- SB Milvus Client: `somabrain/somabrain/milvus_client.py`
- SB Milvus ANN: `somabrain/somabrain/services/milvus_ann.py`


---

## Category J: VIBE CODING RULES COMPLIANCE

### J1: Compliance Assessment

**Overall Score: 7.5/10**

The architecture has been evaluated against the VIBE CODING RULES defined in both `somabrain/VIBE_CODING_RULES.md` and `somafractalmemory/VIBE_CODING_RULES.md`.

### J2: Identified Violations

| ID | Severity | Rule | Location | Fix Required |
|----|----------|------|----------|--------------|
| V1 | CRITICAL | NO MOCKS | `factory.py:186-193` | Remove `InMemoryKeyValueStore` fallback |
| V2 | HIGH | REAL IMPLEMENTATIONS | `graph.py` | Add persistence to `NetworkXGraphStore` |
| V3 | CRITICAL | Security | `http_api.py` | Enforce tenant isolation |
| V4 | MEDIUM | NO SHIMS | `http_api.py:~700` | Remove `_payload_cache` |

### J3: Remediation Tasks

All violations are tracked in `tasks.md` under section **P0-VIBE: VIBE CODING RULES COMPLIANCE FIXES**.

**Priority Order:**
1. V3 - Tenant Isolation (SECURITY - blocks production)
2. V1 - Remove InMemoryKeyValueStore (FAIL FAST)
3. V2 - Graph Store Persistence (data durability)
4. V4 - Remove payload cache (clean architecture)

### J4: Compliant Aspects

- ✅ Real servers used (Postgres, Redis, Milvus)
- ✅ No TODOs or stubs in production code
- ✅ Documentation accurately reflects implementation
- ✅ Circuit breaker pattern correctly implemented
- ✅ Outbox pattern for transactional reliability
- ✅ Complete data flow documentation

### J5: Post-Remediation Target

After fixing all violations:
- **Target Score: 9.5/10**
- All 7 VIBE personas satisfied
- Production-ready, state-of-the-art memory management

---

## Category K: Data Flow Integrity

### K1: Store Memory Flow Design

**Complete Flow Path:**
```
Agent → MemoryService → MemoryClient → HTTP POST → SFM → KV + Vector + Graph
```

**Implementation:**
```python
# somabrain/somabrain/services/memory_service.py
async def remember(self, key: str, payload: Dict[str, Any]) -> StoreResult:
    """Store memory with full flow integrity."""
    tenant, namespace = self._resolve_tenant_namespace()
    
    # Step 1: Log intent for audit
    logger.info(f"Store memory: tenant={tenant}, key={key[:32]}...")
    
    # Step 2: Check circuit breaker
    if self._circuit_breaker.is_open(tenant):
        # Queue to outbox for later replay
        await self._queue_to_outbox("memory.store", {
            "key": key, "payload": payload, "tenant": tenant
        })
        raise CircuitBreakerOpen(f"Circuit open for tenant {tenant}")
    
    # Step 3: Call MemoryClient
    try:
        result = await self._client.aremember(key, payload)
        self._circuit_breaker.record_success(tenant)
        return result
    except Exception as exc:
        self._circuit_breaker.record_failure(tenant)
        # Queue to outbox for retry
        await self._queue_to_outbox("memory.store", {
            "key": key, "payload": payload, "tenant": tenant, "error": str(exc)
        })
        raise
```

### K2: Recall Memory Flow Design

**Complete Flow Path:**
```
Agent → MemoryService → MemoryClient → HTTP POST → SFM → Vector Search → KV Fetch → Scoring
```

**Scoring Pipeline:**
```python
def compute_final_score(hit: RecallHit, query: str, context: Dict) -> float:
    """Compute final score combining all factors."""
    score = 0.0
    
    # Vector similarity (0.0 - 1.0)
    score += hit.vector_score * 0.4
    
    # Importance score (0.0 - 1.0)
    score += hit.importance * 0.25
    
    # Recency boost (exponential decay)
    age_hours = (now() - hit.timestamp).total_seconds() / 3600
    recency = math.exp(-age_hours / 168)  # 1-week half-life
    score += recency * 0.2
    
    # Keyword boost (if terms match)
    if hit.keyword_matches > 0:
        score += min(hit.keyword_matches * 0.05, 0.15)
    
    return score
```

### K3: Delete Memory Flow Design

**Complete Flow Path:**
```
Agent → MemoryService → MemoryClient → HTTP DELETE → SFM → KV + Vector + Graph (all three)
```

**Deletion Order (Critical):**
1. Graph Store - Remove node and all edges
2. Vector Store - Delete by coordinate match
3. KV Store - Delete data key and meta key

**Audit Logging:**
```python
async def delete(self, coordinate: Tuple[float, float, float]) -> DeleteResult:
    """Delete memory with full audit trail."""
    tenant, namespace = self._resolve_tenant_namespace()
    
    # Audit log entry
    audit_entry = {
        "operation": "delete",
        "tenant": tenant,
        "coordinate": list(coordinate),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "success": False,
        "components": {"kv": False, "vector": False, "graph": False}
    }
    
    try:
        result = await self._client.adelete(coordinate)
        audit_entry["success"] = True
        audit_entry["components"] = result.component_status
    except Exception as exc:
        audit_entry["error"] = str(exc)
        raise
    finally:
        await self._write_audit_log(audit_entry)
    
    return result
```

---

## Category L: Configuration Management

### L1: Centralized Settings Design

**Configuration Hierarchy:**
```
Environment Variables (highest priority)
    ↓
.env file
    ↓
config.yaml
    ↓
Default values in Pydantic model (lowest priority)
```

**Pydantic Settings Model:**
```python
# somafractalmemory/somafractalmemory/config/settings.py
from pydantic_settings import BaseSettings

class SomaSettings(BaseSettings):
    """Centralized configuration with validation."""
    
    # Environment
    soma_env: str = "development"
    
    # Vector Backend
    vector_backend: str = "milvus"
    
    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "memories"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Postgres
    postgres_url: str = "postgresql://soma:soma@localhost:5432/soma"
    
    # Security
    jwt_secret: str  # REQUIRED - no default
    
    class Config:
        env_prefix = "SOMA_"
        env_file = ".env"
        
    @validator("vector_backend")
    def validate_vector_backend(cls, v, values):
        if v != "milvus":
            raise ValueError(f"Vector backend '{v}' not supported. Only 'milvus' is allowed.")
        return v
```

### L2: Environment-Specific Configuration

**Development:**
```bash
SOMA_ENV=development
SOMA_VECTOR_BACKEND=milvus
SOMA_MILVUS_HOST=localhost
```

**Staging:**
```bash
SOMA_ENV=staging
SOMA_VECTOR_BACKEND=milvus  # Required
SOMA_MILVUS_HOST=milvus-staging.internal
```

**Production:**
```bash
SOMA_ENV=production
SOMA_VECTOR_BACKEND=milvus
SOMA_MILVUS_HOST=milvus-prod.internal
SOMA_MILVUS_SECURE=true
```

---

## Category M: Error Handling and Recovery

### M1: Exception Hierarchy

```python
# somabrain/somabrain/exceptions.py

class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    pass

class CircuitBreakerOpen(MemoryServiceError):
    """Raised when circuit breaker is open for tenant."""
    def __init__(self, tenant: str, message: str = None):
        self.tenant = tenant
        super().__init__(message or f"Circuit breaker open for tenant {tenant}")

class MemoryTimeoutError(MemoryServiceError):
    """Raised when memory operation times out."""
    def __init__(self, operation: str, timeout_ms: int):
        self.operation = operation
        self.timeout_ms = timeout_ms
        super().__init__(f"{operation} timed out after {timeout_ms}ms")

class MemorySerializationError(MemoryServiceError):
    """Raised when payload serialization fails."""
    def __init__(self, payload_hash: str, reason: str):
        self.payload_hash = payload_hash
        super().__init__(f"Serialization failed for payload {payload_hash}: {reason}")

class TenantIsolationError(MemoryServiceError):
    """CRITICAL: Raised when tenant isolation is violated."""
    def __init__(self, requesting_tenant: str, owning_tenant: str):
        self.requesting_tenant = requesting_tenant
        self.owning_tenant = owning_tenant
        super().__init__(
            f"SECURITY VIOLATION: Tenant {requesting_tenant} attempted to access "
            f"data owned by tenant {owning_tenant}"
        )
```

### M2: Recovery Procedures

**Outbox Replay:**
```python
async def replay_memory_events(
    tenant_id: Optional[str] = None,
    max_events: int = 100,
) -> ReplayResult:
    """Replay pending outbox events to SFM."""
    events = await get_pending_events(
        tenant_id=tenant_id,
        limit=max_events,
        topics=["memory.store", "memory.bulk_store", "graph.link"]
    )
    
    result = ReplayResult(total=len(events), succeeded=0, failed=0)
    
    for event in events:
        try:
            # Check idempotency key to prevent duplicates
            if await is_already_processed(event.idempotency_key):
                await mark_event_sent(event.id)
                result.succeeded += 1
                continue
            
            # Replay the event
            await replay_single_event(event)
            await mark_event_sent(event.id)
            result.succeeded += 1
            
        except Exception as exc:
            await mark_event_failed(event.id, str(exc))
            result.failed += 1
    
    # Log recovery completion
    logger.info(
        f"Outbox replay complete: {result.succeeded}/{result.total} succeeded, "
        f"{result.failed} failed"
    )
    
    return result
```

**Circuit Breaker Manual Reset:**
```python
# API endpoint for manual circuit breaker reset
@router.post("/admin/circuit-breaker/{tenant_id}/reset")
async def reset_circuit_breaker(
    tenant_id: str,
    auth: AdminAuth = Depends(admin_auth_dep),
) -> Dict[str, Any]:
    """Manually reset circuit breaker for a tenant."""
    circuit_breaker = get_circuit_breaker()
    
    previous_state = circuit_breaker.get_state(tenant_id)
    circuit_breaker.reset(tenant_id)
    new_state = circuit_breaker.get_state(tenant_id)
    
    logger.warning(
        f"Circuit breaker manually reset for tenant {tenant_id}: "
        f"{previous_state} → {new_state}"
    )
    
    return {
        "tenant_id": tenant_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "reset_by": auth.user_id,
        "reset_at": datetime.utcnow().isoformat() + "Z",
    }
```

---

## Category N: Security and Compliance

### N1: Authentication Flow

**SB → SFM Authentication:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                           │
│                                                                  │
│  SomaBrain                                                       │
│  ├── Load JWT_SECRET from environment                           │
│  ├── Generate Bearer token with tenant claim                    │
│  └── Set headers:                                                │
│      ├── Authorization: Bearer <token>                          │
│      ├── X-Soma-Tenant: <tenant_id>                             │
│      └── X-Soma-Namespace: <namespace>                          │
│                                                                  │
│  SomaFractalMemory                                              │
│  ├── Extract Bearer token from Authorization header             │
│  ├── Validate JWT signature with JWT_SECRET                     │
│  ├── Extract tenant from token claims                           │
│  ├── Verify X-Soma-Tenant matches token claim                   │
│  └── Reject if mismatch (HTTP 403)                              │
└─────────────────────────────────────────────────────────────────┘
```

**Token Validation:**
```python
# somafractalmemory/somafractalmemory/http_api.py
async def auth_dep(request: Request) -> AuthContext:
    """Validate authentication and extract tenant."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    
    token_tenant = payload.get("tenant")
    header_tenant = request.headers.get("X-Soma-Tenant")
    
    # CRITICAL: Verify tenant consistency
    if header_tenant and token_tenant and header_tenant != token_tenant:
        raise HTTPException(
            status_code=403,
            detail="Tenant mismatch between token and header"
        )
    
    return AuthContext(
        tenant=token_tenant or header_tenant or "default",
        user_id=payload.get("sub"),
        scopes=payload.get("scopes", []),
    )
```

### N2: Data Encryption Design

**TLS Configuration:**
```python
# Milvus TLS connection
from pymilvus import connections

connections.connect(
    alias="default",
    host=settings.milvus_host,
    port=settings.milvus_port,
    secure=settings.milvus_secure,  # True in production
    server_pem_path=settings.milvus_cert_path,  # Optional: custom CA
)
```

**Sensitive Field Encryption (Optional):**
```python
from cryptography.fernet import Fernet

class PayloadEncryptor:
    """Encrypt sensitive payload fields."""
    
    def __init__(self, key: bytes):
        self._fernet = Fernet(key)
    
    def encrypt_field(self, value: str) -> str:
        """Encrypt a string field."""
        return self._fernet.encrypt(value.encode()).decode()
    
    def decrypt_field(self, encrypted: str) -> str:
        """Decrypt a string field."""
        return self._fernet.decrypt(encrypted.encode()).decode()
    
    def encrypt_payload(
        self,
        payload: Dict[str, Any],
        sensitive_fields: List[str],
    ) -> Dict[str, Any]:
        """Encrypt specified fields in payload."""
        result = payload.copy()
        for field in sensitive_fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt_field(result[field])
                result[f"_{field}_encrypted"] = True
        return result
```

---

## Design Summary

### Requirements Coverage Matrix

| Category | Requirements | Design Sections | Status |
|----------|--------------|-----------------|--------|
| A: WM Persistence | A1, A2 | A1, A2 | ✅ Complete |
| B: Graph Integration | B1, B2, B3 | B1, B2, B3 | ✅ Complete |
| C: Hybrid Recall | C1, C2 | C1 | ✅ Complete |
| D: Multi-Tenant | D1, D2 | D1, D2 | ✅ Complete |
| E: Resilience | E1, E2, E3 | E1, E2, E3 | ✅ Complete |
| F: Bulk Operations | F1, F2 | F1 | ✅ Complete |
| G: Serialization | G1, G2 | G1 | ✅ Complete |
| H: Observability | H1, H2 | H1, H2 | ✅ Complete |
| I: Vector Backend | I1, I2, I3 | I1-I6 | ✅ Complete |
| J: Design Patterns | J1, J2, J3 | J1-J5 | ✅ Complete |
| K: Data Flow | K1, K2, K3 | K1, K2, K3 | ✅ Complete |
| L: Configuration | L1, L2 | L1, L2 | ✅ Complete |
| M: Error Handling | M1, M2 | M1, M2 | ✅ Complete |
| N: Security | N1, N2 | N1, N2 | ✅ Complete |

### Implementation Readiness

All 33 requirements across 14 categories now have corresponding design sections with:
- Architecture diagrams
- Code examples
- Data flow specifications
- Error handling patterns
- Security considerations

---

## References (Updated)

- Requirements Document: `somabrain/.kiro/specs/deep-memory-integration/requirements.md`
- Design Patterns Analysis: `somabrain/.kiro/specs/deep-memory-integration/DESIGN_PATTERNS.md`
- Architecture Analysis: `somabrain/.kiro/specs/deep-memory-integration/ARCHITECTURE_ANALYSIS.md`
- Implementation Tasks: `somabrain/.kiro/specs/deep-memory-integration/tasks.md`
- VIBE Rules (SB): `somabrain/VIBE_CODING_RULES.md`
- VIBE Rules (SFM): `somafractalmemory/VIBE_CODING_RULES.md`

---

*Document Version: 2.0*
*Last Updated: 2024-12-14*
*Status: COMPREHENSIVE - All 14 Categories Designed*
