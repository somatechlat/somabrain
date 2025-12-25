# End-to-End Architecture Analysis: SomaBrain ↔ SomaFractalMemory

## Executive Summary

This document provides a complete analysis of the data flow from agent messages in SomaBrain (SB) to persistent storage in SomaFractalMemory (SFM). The analysis identifies architectural gaps, integration issues, and proposes improvements for production-ready, state-of-the-art memory management.

---

## 0. DESIGN PATTERNS IN MEMORY MANAGEMENT

### 0.1 SomaBrain (SB) Design Patterns

###
**Location:** `somabrain/somabrain/services/memory_service.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      MemoryService (Façade)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ remember()  │  │ recall()    │  │ health()    │              │
│  │ aremember() │  │ arecall()   │  │ delete()    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────┐              │
│  │              Circuit Breaker                   │              │
│  │  _is_circuit_open() / _mark_success/failure() │              │
│  └───────────────────────┬───────────────────────┘              │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────┐              │
│  │              Degradation Manager               │              │
│  │  _queue_degraded() → Journal (outbox)         │              │
│  └───────────────────────┬───────────────────────┘              │
│                          │                                       │
│                          ▼                                       │
│                    Backend Client                                │
│                   (MemoryClient)                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Purpose:** Provides a simplified interface to the complex memory subsystem, hiding:
- Circuit breaker logic (per-tenant fault isolation)
- Degradation handling (queue to journal when SFM unavailable)
- Tenant resolution and namespace scoping
- Metrics and observability

#### Pattern 2: Gateway Pattern - `MemoryClient`
**Location:** `somabrain/somabrain/memory_client.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    MemoryClient (Gateway)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Public API                             │   │
│  │  remember() / aremember() / remember_bulk()              │   │
│  │  recall() / arecall() / recall_with_scores()             │   │
│  │  health() / fetch_by_coord() / delete()                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                 HTTP Transport Layer                      │   │
│  │  MemoryHTTPTransport (httpx sync + async clients)        │   │
│  │  - Connection pooling (max_connections, keepalive)       │   │
│  │  - Retry logic with exponential backoff                  │   │
│  │  - Request/response metrics                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                 Helper Modules                            │   │
│  │  payload.py      - enrich_payload(), prepare_memory()    │   │
│  │  recall_ops.py   - memories_search_sync/async()          │   │
│  │  http_helpers.py - store_http_sync/async(), retries      │   │
│  │  scoring.py      - rescore_and_rank_hits()               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**P:

- Handles sync/async duality
headers)
- P

#### Pattern 3: Circuit Breaker Pattern
**Location:** `somabrain/somabrain/infrastructure/circuit_breaker.py`

```
                    ┌─────────────────┐
                    │     CLOSED      │
                    │  (Normal ops)   │
                    └────────┬────────┘
                             │
                    failure_count >= threshold
                             │
                             ▼
                    ┌─────────────────┐
                    │      OPEN       │
                    │ (Fail fast)     │◄────────────────┐
                    └────────┬────────┘                 │
                             │                          │
                    reset_interval elapsed              │
                             │                          │
                             ▼                          │
                    ┌─────────────────┐                 │
                    │   HALF-OPEN     │                 │
                    │ (Probe request) │─────────────────┘
                    └────────┬────────┘    failure
                             │
                         success
                             │
                             ▼
                    ┌─────────────────┐
                    │     CLOSED      │
                    └─────────────────┘
```

**Per-Tenant Isolation:**
```python
class CircuitBreaker:
    _circuit_open: Dict[str, bool]           # tenant → is_open
    _failure_counts: Dict[str, int]          # tenant → count
    _last_failure_time: Dict[str, float]     # tenant → timestamp
    _tenant_thresholds: Dict[str, int]       # tenant → custom threshold
```

#### Pattern 4: Outbox Pattern (Transactional Outbox)
**Location:** `somabrain/somabrain/db/outbox.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                     Outbox Pattern Flow                          │
│                                                                  │
│  1. Application writes to local DB (outbox_events table)        │
│     ┌─────────────────────────────────────────────────────┐     │
│     │ INSERT INTO outbox_events (topic, payload, status)  │     │
│     │ VALUES ('memory.store', {...}, 'pending')           │     │
│     └─────────────────────────────────────────────────────┘     │
│                              │                                   │
│  2. Background worker polls pending events                       │
│     ┌─────────────────────────────────────────────────────┐     │
│     │ SELECT * FROM outbox_events WHERE status='pending'  │     │
│     │ ORDER BY created_at LIMIT 100                       │     │
│     └─────────────────────────────────────────────────────┘     │
│                              │                                   │
│  3. Worker sends to SFM, marks as 'sent' on success             │
│     ┌─────────────────────────────────────────────────────┐     │
│     │ UPDATE outbox_events SET status='sent'              │     │
│     │ WHERE id = ? AND status='pending'                   │     │
│     └─────────────────────────────────────────────────────┘     │
│                                                                  │
│    │
┘
```

#### Pattern 5: Strategy Patt



# Different scoring strategies can be ped in
def rescore_and_rank_hits(
    hits: List[RecallHit],
    query: str,
    cfg: Config,
    scorer: Optional[Any],      # Strategy 1: Custom scorer
    embedder: Optional[Any],    # Strategy 2: Embedding-based
) -> List[RecallHit]:
    # Apply recency normalization
    # Apply density factor
    # Apply custom scorer if provided
e
```

---

### 0.2 SomaFractalMemory (SFM) Design Patterns

#### Pattern 1: Abstract Factory + Strategy - Storage Backends
**Location:** `somafractalmemory/somafractalmemory/interfaces/storage.py`

```
┌─────────────────────────────────────────────────────────────────┐
│
│       │
 │
│  │  IKeyValueStore │  │  IVect│  │
│
│  │  - get()        │  │   │
  │
│  │  - scan_iter()  │  │  - delete()     │  │    │
│  │  - lock()       │  │  - scroll()     │    │
│  │  - health_check │  │  - health_check │  │  - health_check │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │     │
└──────────┘
            │                    │                    │
            ▼                    ▼                  ▼
┌───────────────────┐
│ Implementations   │  │ Implementations     │  │ Implementations │
│                   │  │      
│ R│

│ InMemoryKVStore   │  │                       │
│ PostgresRedis     │  │                     
│   HybridStore     │  │                     │  │                 │
└───────────────────┘  └─────────────────────┘  └─────────────────┘
```

#### Pattern 2: Factory Method - `create_m
**Location:** `somafractalmemory/somafrac

```python
def create_memory_system(
e,
    namespace: str,

) -> SomaFractalMemoryEnterprise:
    """
    Factory function that:
    1. Loads configuration from settingserrides
    2. Creates appropriate KV store (Postgres+Redis hybrid)
Milvus)
    4. Creates Graph store (NetworkX)
    5. Optionally wraps in BatchedStore for throughput
    6. Returns fully configured SomaFractalMemoryEnterprise
    """
```

**Vector Backend Selection:**
```python
if getattr(_settings, "vector_backend", "qdrant") == "milvus":
    vector_store = MilvusVectorStore(...)
else:
)
```

#### Pattern 3: Decorator Pattern Store`
**Location:** `somafractalmemory/somafractalmemory/implement

```

│                    BatchedStore (Decorator)       │
│                                                  │
│  Wraps: IKeyValueStore + IVectorStore                  
│                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
 │
│  │  _kv_queue: List[Tuple[str, bytes│
│  │  _vec_queue: List[Dict[str, Any]]                       │    │
│  └─────────────────────────────────────────────────────    │
│                              │               │
│  ┌─────────────────────────▼───────────────────────────────┐ 
  │
│  │  - Runs on daemon thread  │    │

│  │  - Uses Redis pipeline for KV batch writ
│  │  - Uses vector store bulk upsert                         │
│  └──────────────────────────────────────── │
     │
│  Benefits:                                     │
│  - Reduces network round-trips                       │
│  - Improves throughput under high QPS                │
 │
└───────────────────────────────────────
```


**L

```
────────┐
│              PostgresRedisHy │

│  ┌─────────────────────────────────────────────────────────┐    │
 │
│   │
│  └───────────
│          │
│  ┌───────────────
│  │                    Read Path                             │   │
│  │  get(key) → Redis (cache hit?) → Postgres (fallb│
│  └─────────────────────────────────────────────────    │
│          
│  ┌───────────────  │
│  │                    Lock Path                           │
│  │  lock(name) → │
│  └───────────────
│                                                    
│         │
 │
│  - Redis: Speed, distributed loc │
────────┘
```

#### Pattern 5: Repository Pattern - Core Memory Operations
**Location:** `somafractalmemory/somafractalmemory/core.py`

```python
class SomaFractalMemoryEnterprise:
    """
    Repository-like pattern for memory operations.
    Coordinates across multiple stores (KV, Vector, Graph).
    """
    
    def store_memory(self, coordinate, value, memory_type):
        # 1. Serialize and store in KV
        # 2. Generate embedding and upsert to Vector
        # 3. Add node to Graph
        # 4. Update metadata (timestamps, importance)
        
    def recall(self, query, top_k):
        # 1. Embed query
        # 2. Vector similarity search
        # 3. Fetch payloads from KV
        # 4. Apply scoring/ranking
        
    def delete(self, coordinate):
        # 1. Delete from KV
        # 2. Delete from Vector
        # 3. Remove from Graph
```

---

### 0.3 MILVUS: Exclusive Vector Backend

#### Configuration

| System | Backend | Config Variable | Selection Logic |
|--------|---------|-----------------|-----------------|
| **SomaBrain** | Milvus | N/A (hardcoded) | `ann.py` raises error if not Milvus |
| **SomaFractalMemory** | Milvus | `SOMA_VECTOR_BACKEND` | Factory validates Milvus-only |

#### SomaBrain: Milvus Only (Hardcoded)
**Location:** `somabrain/somabrain/services/ann.py`

```python
def create_cleanup_index(...) -> CleanupIndex:
    backend = (config.backend or "milvus").lower()
    
    if backend != "milvus":
        raise ValueError(
            f"Milvus backend is required; configured backend '{backend}' is not supported"
        )
    
    from somabrain.services.milvus_ann import MilvusAnnIndex
    return MilvusAnnIndex(dim, tenant_id=tenant_id, ...)
```

#### SomaFractalMemory: Milvus Only
**Location:** `somafractalmemory/somafractalmemory/factory.py`

```python
# Vector store selection - Milvus only
vector_backend = getattr(_settings, "vector_backend", "milvus")
if vector_backend != "milvus":
    raise RuntimeError(f"Vector backend '{vector_backend}' not supported. Only 'milvus' is allowed.")

from .implementations.storage import MilvusVectorStore
vector_store = MilvusVectorStore(
    collection_name=namespace,
    host=_settings.milvus_host,
    port=_settings.milvus_port,
)
```

#### Milvus Implementation Details

| Feature | MilvusVectorStore |
|---------|-------------------|
| **Client Library** | `pymilvus` |
| **Default Port** | 19530 (gRPC) |
| **Distance Metric** | IP (Inner Product) |
| **Index Type** | IVF_FLAT |
| **Schema** | Fixed (id, embedding, payload) |
| **Scroll/Pagination** | Emulated with offset |
| **TLS Support** | `secure=True` |
| **Connection Pooling** | Connection alias |

#### Production Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                         │
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

#### Unified Configuration

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

---

## 1. COMPLETE DATA FLOW: Agent Message → Database

### 1.1 SomaBrain Side (Port 9696)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOMABRAIN DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ Agent Message    │  Entry point: agent_memory.py, cognitive/planning.py   │
│  │ (Observation,    │                                                        │
│  │  Thought, etc.)  │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ encode_memory()  │  Converts to Memory schema with:                       │
│  │ agent_memory.py  │  - Unit-normalized vector (HRR_DIM)                    │
│  │                  │  - Payload dict                                        │
│  │                  │  - Memory type (episodic/semantic)                     │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Working Memory   │  wm.py - Fast buffer with:                             │
│  │ (WM)             │  - Capacity-limited storage                            │
│  │                  │  - Salience-based eviction                             │
│  │                  │  - Novelty detection                                   │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ MemoryClient     │  memory_client.py - Gateway to SFM:                    │
│  │                  │  - remember() / aremember()                            │
│  │                  │  - recall() / arecall()                                │
│  │                  │  - remember_bulk() / aremember_bulk()                  │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Payload          │  memory/payload.py:                                    │
│  │ Enrichment       │  - enrich_payload() adds tenant, namespace, timestamp  │
│  │                  │  - prepare_memory_payload() adds memory_type           │
│  │                  │  - normalize_metadata() cleans fields                  │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ HTTP Transport   │  memory/transport.py:                                  │
│  │                  │  - MemoryHTTPTransport class                           │
│  │                  │  - Sync/Async httpx clients                            │
│  │                  │  - Retry logic with backoff                            │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ HTTP Helpers     │  memory/http_helpers.py:                               │
│  │                  │  - store_http_sync() → POST /memories                  │
│  │                  │  - store_http_async() → POST /memories                 │
│  │                  │  - http_post_with_retries_sync/async()                 │
│  │                  │  - record_http_metrics()                               │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │  HTTP POST to http://localhost:9595/memories                     │
│           │  Headers: Authorization, X-Soma-Tenant, X-Soma-Namespace         │
│           │  Body: {coord, payload, memory_type}                             │
│           │                                                                  │
└───────────┼──────────────────────────────────────────────────────────────────┘
            │
            ▼
```

### 1.2 SomaFractalMemory Side (Port 9595)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOMAFRACTALMEMORY DATA FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ FastAPI Router   │  http_api.py:                                          │
│  │ POST /memories   │  - auth_dep() validates Bearer token                   │
│  │                  │  - rate_limit_dep() enforces limits                    │
│  │                  │  - store_memory() endpoint handler                     │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Request Parsing  │  Pydantic models:                                      │
│  │                  │  - MemoryStoreRequest(coord, payload, memory_type)     │
│  │                  │  - safe_parse_coord() validates coordinate             │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Core Memory      │  core.py - SomaFractalMemoryEnterprise:                │
│  │ System           │  - store_memory(coordinate, value, memory_type)        │
│  │                  │  - Wraps payload under "payload" key                   │
│  │                  │  - Adds metadata: memory_type, timestamp, coordinate   │
│  │                  │  - Computes importance_norm (adaptive normalization)   │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ├─────────────────────────────────────────────────────────────┐    │
│           │                                                             │    │
│           ▼                                                             ▼    │
│  ┌──────────────────┐                                    ┌──────────────────┐│
│  │ KV Store         │                                    │ Vector Store     ││
│  │ (Postgres+Redis) │                                    │ (Milvus)         ││
│  │                  │                                    │                  ││
│  │ PostgresRedis-   │                                    │ MilvusVectorStore││
│  │ HybridStore:     │                                    │                  ││
│  │ - set(data_key,  │                                    │                  ││
│  │   serialized)    │                                    │                  ││
│  │ - hset(meta_key, │                                    │ - embed_text()   ││
│  │   timestamps)    │                                    │ - upsert(points) ││
│  └────────┬─────────┘                                    └────────┬─────────┘│
│           │                                                       │          │
│           │                                                       │          │
│           ▼                                                       ▼          │
│  ┌──────────────────┐                                    ┌──────────────────┐│
│  │ PostgreSQL       │                                    │ Milvus           ││
│  │ (Canonical KV)   │                                    │ (Vector DB)      ││
│  │                  │                                    │                  ││
│  │ Table: kv_store  │                                    │ Collection:      ││
│  │ - key (VARCHAR)  │                                    │   {namespace}    ││
│  │ - value (JSONB)  │                                    │ - id (UUID)      ││
│  └──────────────────┘                                    │ - vector (768d)  ││
│           │                                              │ - payload (JSON) ││
│           │                                              └──────────────────┘│
│           │                                                       │          │
│           └───────────────────────┬───────────────────────────────┘          │
│                                   │                                          │
│                                   ▼                                          │
│                          ┌──────────────────┐                                │
│                          │ Graph Store      │                                │
│                          │ (NetworkX)       │                                │
│                          │                  │                                │
│                          │ - add_memory()   │                                │
│                          │ - add_link()     │                                │
│                          │ - get_neighbors()│                                │
│                          └──────────────────┘                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. KEY COMPONENTS ANALYSIS

### 2.1 SomaBrain Components

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| MemoryClient | `memory_client.py` | Gateway to SFM HTTP API | ✅ EXISTS |
| WorkingMemory | `wm.py` | Fast buffer with salience eviction | ✅ EXISTS |
| HTTP Transport | `memory/transport.py` | httpx client management | ✅ EXISTS |
| HTTP Helpers | `memory/http_helpers.py` | POST/retry logic | ✅ EXISTS |
| Payload Enrichment | `memory/payload.py` | Tenant/namespace injection | ✅ EXISTS |
| Recall Ops | `memory/recall_ops.py` | Search with tenant filtering | ✅ EXISTS |
| Circuit Breaker | `infrastructure/circuit_breaker.py` | Per-tenant fault isolation | ✅ EXISTS |
| Outbox | `db/outbox.py` | Transactional event queue | ✅ EXISTS |
| Agent Memory | `agent_memory.py` | In-memory store (demo only) | ⚠️ NOT INTEGRATED |

### 2.2 SomaFractalMemory Components

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| HTTP API | `http_api.py` | FastAPI endpoints | ✅ EXISTS |
| Core | `core.py` | SomaFractalMemoryEnterprise | ✅ EXISTS |
| Factory | `factory.py` | Memory system creation | ✅ EXISTS |
| KV Store | `implementations/storage.py` | PostgresRedisHybridStore | ✅ EXISTS |
| Vector Store | `implementations/storage.py` | MilvusVectorStore | ✅ EXISTS |
| Graph Store | `implementations/graph.py` | NetworkXGraphStore | ✅ EXISTS |
| Serialization | `serialization.py` | JSON serialize/deserialize | ✅ EXISTS |

---

## 3. IDENTIFIED GAPS AND ISSUES

### 3.1 CRITICAL GAPS (P0)

#### GAP-1: Tenant Isolation Not Enforced in SFM
**Location:** `somafractalmemory/http_api.py`
**Issue:** The HTTP API does not extract tenant from headers and scope operations.
**Impact:** Cross-tenant data leakage possible (XFAIL tests D1.1, D1.2)
**Fix Required:**
```python
def _get_tenant_from_request(request: Request) -> str:
    tenant = request.headers.get("X-Soma-Tenant")
    if not tenant:
        tenant = request.headers.get("X-Soma-Namespace", "").split(":")[-1]
    return tenant or "default"
```

#### GAP-2: Graph Store Endpoints Missing
**Location:** `somafractalmemory/http_api.py`
**Issue:** No HTTP endpoints for graph operations (link, neighbors, path)
**Impact:** SB cannot create semantic links or use graph-augmented recall
**Fix Required:** Add `/graph/link`, `/graph/neighbors`, `/graph/path` endpoints

#### GAP-3: WM Persistence Not Implemented
**Location:** `somabrain/somabrain/wm.py`
**Issue:** Working Memory items are not persisted to SFM
**Impact:** WM state lost on SB restart
**Fix Required:** Add async persistence queue and restoration logic

### 3.2 HIGH PRIORITY GAPS (P1)

#### GAP-4: Hybrid Recall Not Utilized
**Location:** `somabrain/somabrain/memory/recall_ops.py`
**Issue:** SB uses basic `/memories/search`, not SFM's `hybrid_recall_with_scores`
**Impact:** Suboptimal retrieval quality
**Fix Required:** Update recall to use hybrid endpoint with keyword extraction

#### GAP-5: Bulk Operations Inefficient
**Location:** `somabrain/somabrain/memory/http_helpers.py`
**Issue:** `store_bulk_http_sync` iterates items sequentially
**Impact:** Poor performance for batch imports
**Fix Required:** Implement true batch endpoint in SFM, use chunking in SB

#### GAP-6: Health Check Incomplete
**Location:** `somabrain/somabrain/memory_client.py`
**Issue:** Health check doesn't report individual SFM component status
**Impact:** Operators can't identify which component is failing
**Fix Required:** Parse SFM health response and expose component status

### 3.3 MEDIUM PRIORITY GAPS (P2)

#### GAP-7: Serialization Mismatch
**Issue:** SB uses tuples for coordinates, SFM expects lists
**Impact:** Potential deserialization errors
**Fix Required:** Add `serialize_for_sfm()` helper

#### GAP-8: Outbox Not Used for Memory Operations
**Location:** `somabrain/somabrain/db/outbox.py`
**Issue:** Memory writes don't use outbox for reliability
**Impact:** Writes can be lost during SFM unavailability
**Fix Required:** Record to outbox before SFM call, mark sent on success

#### GAP-9: Graph Store In-Memory Only
**Location:** `somafractalmemory/somafractalmemory/implementations/graph.py`
**Issue:** NetworkXGraphStore is in-memory, not persisted
**Impact:** Graph links lost on SFM restart
**Fix Required:** Add persistence layer or use Neo4j/JanusGraph

### 3.4 LOW PRIORITY GAPS (P3)

#### GAP-10: WM-LTM Promotion Not Implemented
**Issue:** No automatic promotion of salient WM items to LTM
**Fix Required:** Add PromotionTracker class

#### GAP-11: Distributed Tracing Incomplete
**Issue:** Trace context not propagated from SB to SFM
**Fix Required:** Inject traceparent/tracestate headers

#### GAP-12: Integration Metrics Missing
**Issue:** No dedicated metrics for SB↔SFM integration
**Fix Required:** Add sfm_request_total, sfm_request_duration, etc.

---

## 4. PROPOSED ARCHITECTURE IMPROVEMENTS

### 4.1 Unified Contract Layer

Create a shared interface package that both SB and SFM import:

```
soma-contracts/
├── memory/
│   ├── __init__.py
│   ├── types.py          # MemoryPayload, Coordinate, RecallHit
│   ├── interfaces.py     # IMemoryStore, IGraphStore
│   └── serialization.py  # Shared JSON serialization
├── tenant/
│   ├── __init__.py
│   └── context.py        # TenantContext, tenant extraction
└── observability/
    ├── __init__.py
    └── tracing.py        # Trace context propagation
```

### 4.2 Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROPOSED ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOMABRAIN                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        MemoryService                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │ WM Manager  │  │ LTM Manager │  │ Graph Mgr   │  │ Batch Mgr   │ │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │    │
│  │         │                │                │                │        │    │
│  │         └────────────────┴────────────────┴────────────────┘        │    │
│  │                                   │                                  │    │
│  │                          ┌────────▼────────┐                         │    │
│  │                          │ MemoryClient    │                         │    │
│  │                          │ (HTTP Gateway)  │                         │    │
│  │                          └────────┬────────┘                         │    │
│  │                                   │                                  │    │
│  │  ┌────────────────────────────────┼────────────────────────────────┐│    │
│  │  │              Resilience Layer  │                                ││    │
│  │  │  ┌─────────────┐  ┌────────────▼───────┐  ┌─────────────┐       ││    │
│  │  │  │ Circuit     │  │ Outbox             │  │ Degradation │       ││    │
│  │  │  │ Breaker     │  │ (Write-Ahead Log)  │  │ Manager     │       ││    │
│  │  │  └─────────────┘  └────────────────────┘  └─────────────┘       ││    │
│  │  └─────────────────────────────────────────────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  SOMAFRACTALMEMORY                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        HTTP API Layer                                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │ /memories   │  │ /graph      │  │ /batch      │  │ /health     │ │    │
│  │  │ CRUD        │  │ links/path  │  │ bulk ops    │  │ components  │ │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │    │
│  │         │                │                │                │        │    │
│  │         └────────────────┴────────────────┴────────────────┘        │    │
│  │                                   │                                  │    │
│  │                          ┌────────▼────────┐                         │    │
│  │                          │ Tenant Router   │                         │    │
│  │                          │ (Namespace      │                         │    │
│  │                          │  Isolation)     │                         │    │
│  │                          └────────┬────────┘                         │    │
│  │                                   │                                  │    │
│  │                          ┌────────▼────────┐                         │    │
│  │                          │ Core Memory     │                         │    │
│  │                          │ System          │                         │    │
│  │                          └────────┬────────┘                         │    │
│  │                                   │                                  │    │
│  │  ┌────────────────────────────────┼────────────────────────────────┐│    │
│  │  │              Storage Layer     │                                ││    │
│  │  │  ┌─────────────┐  ┌────────────▼───────┐  ┌─────────────┐       ││    │
│  │  │  │ KV Store    │  │ Vector Store       │  │ Graph Store │       ││    │
│  │  │  │ (Postgres+  │  │ (Milvus)           │  │ (NetworkX/  │       ││    │
│  │  │  │  Redis)     │  │                    │  │  Neo4j)     │       ││    │
│  │  │  └─────────────┘  └────────────────────┘  └─────────────┘       ││    │
│  │  └─────────────────────────────────────────────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 New SFM Endpoints Required

```python
# Graph Endpoints
POST   /graph/link          # Create semantic link
GET    /graph/neighbors     # Get k-hop neighbors
GET    /graph/path          # Find shortest path

# Batch Endpoints
POST   /batch/store         # Bulk memory store
POST   /batch/recall        # Batch recall queries

# Enhanced Health
GET    /health/components   # Detailed component status
```

### 4.4 Tenant Isolation Implementation

```python
# SFM: Add to all endpoints
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant = request.headers.get("X-Soma-Tenant", "default")
    request.state.tenant = tenant
    response = await call_next(request)
    return response

# SFM: Scope all operations
def store_memory(req: MemoryStoreRequest, request: Request):
    tenant = request.state.tenant
    scoped_namespace = f"{tenant}:{mem.namespace}"
    # ... use scoped_namespace for all operations
```

---

## 5. IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Week 1)
1. Fix tenant isolation in SFM (GAP-1)
2. Add graph endpoints to SFM (GAP-2)
3. Implement WM persistence (GAP-3)

### Phase 2: High Priority (Week 2)
4. Integrate hybrid recall (GAP-4)
5. Implement batch endpoints (GAP-5)
6. Complete health check (GAP-6)

### Phase 3: Medium Priority (Week 3)
7. Align serialization (GAP-7)
8. Integrate outbox for writes (GAP-8)
9. Persist graph store (GAP-9)

### Phase 4: Low Priority (Week 4)
10. WM-LTM promotion (GAP-10)
11. Distributed tracing (GAP-11)
12. Integration metrics (GAP-12)

---

## 6. TESTING STRATEGY

### 6.1 Integration Tests Required

```python
# Category D: Tenant Isolation
def test_tenant_a_cannot_see_tenant_b_memories()
def test_100_concurrent_tenants_no_leakage()

# Category E: Resilience
def test_sfm_unavailable_returns_wm_only()
def test_outbox_replay_no_duplicates()

# Category B: Graph Integration
def test_co_recall_creates_links()
def test_graph_boost_applied_in_recall()

# Category A: WM Persistence
def test_wm_persists_across_restart()
def test_wm_restoration_within_5_seconds()
```

### 6.2 Property-Based Tests

```python
# Round-trip properties
def test_serialize_deserialize_roundtrip()
def test_store_recall_roundtrip()

# Invariants
def test_tenant_isolation_invariant()
def test_vector_norm_invariant()
```

---

## 7. CONCLUSION

The current architecture has a solid foundation but requires several critical fixes to achieve production-ready status:

1. **Tenant isolation** is the most critical gap - must be fixed before any production deployment
2. **Graph store integration** is incomplete - SFM has the capability but no HTTP endpoints
3. **WM persistence** is missing - cognitive context lost on restart
4. **Resilience patterns** exist but aren't fully utilized

The proposed improvements maintain backward compatibility while adding the missing capabilities for a state-of-the-art memory management system.

---

*Document generated: 2024-12-14*
*Analysis based on: SomaBrain and SomaFractalMemory codebases*
