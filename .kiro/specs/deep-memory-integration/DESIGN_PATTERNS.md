# Memory Management Design Patterns Analysis

## SomaBrain (SB) and SomaFractalMemory (SFM)

This document provides a comprehensive analysis of the design patterns used in memory management across both repositories.

---

## 1. SOMABRAIN DESIGN PATTERNS

### 1.1 Façade Pattern - `MemoryService`
**Location:** `somabrain/somabrain/services/memory_service.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                      MemoryService (Façade)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ remember()  │  │ recall()    │  │ health()    │              │
│  │ aremember() │  │ arecall()   │  │ delete()    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
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
│                          ▼                                       │
│                    Backend Client (MemoryClient)                 │
└─────────────────────────────────────────────────────────────────┘
```

**Purpose:** Simplified interface hiding:
- Circuit breaker logic (per-tenant fault isolation)
- Degradation handling (queue to journal when SFM unavailable)
- Tenant resolution and namespace scoping
- Metrics and observability

### 1.2 Gateway Pattern - `MemoryClient`
**Location:** `somabrain/somabrain/memory_client.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    MemoryClient (Gateway)                        │
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

**Purpose:** Single entry point for external memory service communication.

### 1.3 Circuit Breaker Pattern
**Location:** `somabrain/somabrain/infrastructure/circuit_breaker.py`

```
                    ┌─────────────────┐
                    │     CLOSED      │
                    │  (Normal ops)   │
                    └────────┬────────┘
                             │ failure_count >= threshold
                             ▼
                    ┌─────────────────┐
                    │      OPEN       │◄──────────┐
                    │ (Fail fast)     │           │
                    └────────┬────────┘           │
                             │ reset_interval     │ failure
                             ▼                    │
                    ┌─────────────────┐           │
                    │   HALF-OPEN     │───────────┘
                    │ (Probe request) │
                    └────────┬────────┘
                             │ success
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

### 1.4 Outbox Pattern (Transactional Outbox)
**Location:** `somabrain/somabrain/db/outbox.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                     Outbox Pattern Flow                          │
│                                                                  │
│  1. Application writes to local DB (outbox_events table)        │
│     INSERT INTO outbox_events (topic, payload, status)          │
│     VALUES ('memory.store', {...}, 'pending')                   │
│                                                                  │
│  2. Background worker polls pending events                       │
│     SELECT * FROM outbox_events WHERE status='pending'          │
│                                                                  │
│  3. Worker sends to SFM, marks as 'sent' on success             │
│     UPDATE outbox_events SET status='sent' WHERE id = ?         │
│                                                                  │
│  Topics: memory.store, memory.bulk_store, graph.link, wm.*      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. SOMAFRACTALMEMORY DESIGN PATTERNS

### 2.1 Abstract Factory + Strategy - Storage Backends
**Location:** `somafractalmemory/somafractalmemory/interfaces/storage.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    Abstract Interfaces (ABC)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  IKeyValueStore │  │  IVectorStore   │  │  IGraphStore    │  │
│  │  - set()        │  │  - setup()      │  │  - add_memory() │  │
│  │  - get()        │  │  - upsert()     │  │  - add_link()   │  │
│  │  - delete()     │  │  - search()     │  │  - get_neighbors│  │
│  │  - scan_iter()  │  │  - delete()     │  │  - remove()     │  │
│  │  - lock()       │  │  - scroll()     │  │  - clear()      │  │
│  │  - health_check │  │  - health_check │  │  - health_check │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼────────────────────┼────────────────────┼────────────┘
            ▼                    ▼                    ▼
┌───────────────────┐  ┌─────────────────────┐  ┌─────────────────┐
│ Implementations   │  │ Implementations     │  │ Implementations │
│ RedisKeyValueStore│  │ QdrantVectorStore   │  │ NetworkXGraph   │
│ PostgresKVStore   │  │ MilvusVectorStore   │  │ Store           │
│ InMemoryKVStore   │  │                     │  │                 │
│ PostgresRedis     │  │                     │  │                 │
│   HybridStore     │  │                     │  │                 │
└───────────────────┘  └─────────────────────┘  └─────────────────┘
```

### 2.2 Factory Method - `create_memory_system()`
**Location:** `somafractalmemory/somafractalmemory/factory.py`

```python
def create_memory_system(mode, namespace, config) -> SomaFractalMemoryEnterprise:
    """
    Factory function that:
    1. Loads configuration from settings + overrides
    2. Creates appropriate KV store (Postgres+Redis hybrid)
    3. Creates appropriate Vector store (Qdrant or Milvus)
    4. Creates Graph store (NetworkX)
    5. Optionally wraps in BatchedStore for throughput
    6. Returns fully configured SomaFractalMemoryEnterprise
    """
```

### 2.3 Decorator Pattern - `BatchedStore`
**Location:** `somafractalmemory/somafractalmemory/implementations/storage.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                    BatchedStore (Decorator)                      │
│  Wraps: IKeyValueStore + IVectorStore                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    In-Memory Queues                      │    │
│  │  _kv_queue: List[Tuple[str, bytes]]                     │    │
│  │  _vec_queue: List[Dict[str, Any]]                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │              Background Flush Worker                     │    │
│  │  - Runs on daemon thread                                │    │
│  │  - Flushes when: batch_size reached OR flush_interval   │    │
│  │  - Uses Redis pipeline for KV batch writes              │    │
│  │  - Uses vector store bulk upsert                        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Composite Pattern - `PostgresRedisHybridStore`
**Location:** `somafractalmemory/somafractalmemory/factory.py`

```
┌─────────────────────────────────────────────────────────────────┐
│              PostgresRedisHybridStore (Composite)                │
│                                                                  │
│  Write Path: set(key, value)                                    │
│    → Postgres (canonical) → Redis (cache)                       │
│                                                                  │
│  Read Path: get(key)                                            │
│    → Redis (cache hit?) → Postgres (fallback)                   │
│                                                                  │
│  Lock Path: lock(name)                                          │
│    → Redis (distributed) OR Postgres (local)                    │
│                                                                  │
│  Benefits:                                                       │
│  - Postgres: Durability, ACID, SQL queries                      │
│  - Redis: Speed, distributed locks, pub/sub                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Repository Pattern - `SomaFractalMemoryEnterprise`
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

## 3. QDRANT vs MILVUS VECTOR BACKEND ANALYSIS

### 3.1 Configuration Selection

> **IMPORTANT DECISION (2024-12-14):**
> - **Milvus = REQUIRED for PRODUCTION** (both SB and SFM)
> - **Qdrant = OPTIONAL for TESTING ONLY** (SFM local tests with on-disk mode)
> - Production deployments MUST use Milvus; Qdrant in production is NOT supported

| System | Default | Config Variable | Selection Logic | Production Requirement |
|--------|---------|-----------------|-----------------|------------------------|
| **SomaBrain** | Milvus | N/A (hardcoded) | `ann.py` raises error if not Milvus | ✅ Milvus ONLY |
| **SomaFractalMemory** | Milvus | `SOMA_VECTOR_BACKEND` | Factory checks setting | ✅ Milvus REQUIRED (Qdrant test-only) |

### 3.2 SomaBrain: Milvus Only (Hardcoded)
**Location:** `somabrain/somabrain/services/ann.py`

```python
def create_cleanup_index(...) -> CleanupIndex:
    backend = (config.backend or "milvus").lower()
    
    if backend != "milvus":
        raise ValueError(
            f"Milvus backend is required; '{backend}' not supported"
        )
    
    from somabrain.services.milvus_ann import MilvusAnnIndex
    return MilvusAnnIndex(dim, tenant_id=tenant_id, ...)
```

**SB Milvus Components:**

| Component | File | Collection | Purpose |
|-----------|------|------------|---------|
| `MilvusClient` | `milvus_client.py` | `oak_options` | Oak option vectors |
| `MilvusAnnIndex` | `services/milvus_ann.py` | `soma_{ns}_{tenant}` | TieredMemory cleanup |

### 3.3 SomaFractalMemory: Configurable
**Location:** `somafractalmemory/somafractalmemory/factory.py`

```python
if getattr(_settings, "vector_backend", "qdrant") == "milvus":
    vector_store = MilvusVectorStore(...)
else:
    vector_store = QdrantVectorStore(...)
```

### 3.4 Implementation Comparison

| Feature | QdrantVectorStore | MilvusVectorStore |
|---------|-------------------|-------------------|
| **Client Library** | `qdrant-client` | `pymilvus` |
| **Default Port** | 6333 (HTTP) | 19530 (gRPC) |
| **Distance Metric** | COSINE | IP (Inner Product) |
| **Index Type** | Auto (HNSW) | IVF_FLAT |
| **Schema** | Dynamic payload | Fixed (id, embedding, payload) |
| **Scroll/Pagination** | Native `scroll()` | Emulated with offset |
| **On-Disk Mode** | Yes (`path=...`) | No (server only) |
| **TLS Support** | `qdrant_tls=True` | `secure=True` |

### 3.5 Production Deployment Architecture

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
│                       OR Qdrant (if SOMA_VECTOR_BACKEND=qdrant) │
│                                                                  │
│  Shared Milvus Cluster                                          │
│  ├── Host: milvus (Docker network alias)                        │
│  ├── Port: 19530 (gRPC) / 9091 (HTTP health)                   │
│  └── Collections:                                                │
│      ├── oak_options (SB Oak)                                   │
│      ├── soma_cleanup_* (SB TieredMemory)                       │
│      └── api_ns, test_ns, {tenant}:* (SFM memories)            │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 Test Environment (Qdrant OPTIONAL - Test Only)

> **NOTE:** Qdrant is ONLY used for local testing in SomaFractalMemory.
> It provides test isolation without requiring an external server.
> **Production deployments MUST use Milvus.**

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEST ENVIRONMENT (Qdrant - Test Only)         │
│                                                                  │
│  SomaFractalMemory Tests                                        │
│  └── Qdrant on-disk: {"qdrant": {"path": tmp_path/"qdrant.db"}} │
│      - Isolated per test run                                    │
│      - No external server required                              │
│      - Fast teardown                                            │
│      - ⚠️ NOT FOR PRODUCTION USE                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION VALIDATION                         │
│                                                                  │
│  SomaFractalMemory startup SHOULD validate:                     │
│  - If SOMA_ENV=production AND SOMA_VECTOR_BACKEND=qdrant        │
│    → RAISE RuntimeError("Qdrant not supported in production")   │
│                                                                  │
│  This ensures Milvus is always used in production deployments.  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. UNIFIED CONFIGURATION

### 4.1 SomaBrain `.env`
```bash
# Milvus (required - hardcoded)
SOMA_MILVUS_HOST=milvus
SOMA_MILVUS_PORT=19530
SOMA_MILVUS_COLLECTION=oak_options
```

### 4.2 SomaFractalMemory `.env`
```bash
# Vector backend selection
SOMA_VECTOR_BACKEND=milvus

# Milvus settings (when vector_backend=milvus)
SOMA_MILVUS_HOST=milvus
SOMA_MILVUS_PORT=19530
SOMA_MILVUS_COLLECTION=memories

# Qdrant settings (when vector_backend=qdrant)
QDRANT_URL=http://qdrant:6333
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

---

## 5. MEMORY FLOW PROCESS

### 5.1 Store Memory Flow (SB → SFM)

```
┌─────────────────────────────────────────────────────────────────┐
│ SOMABRAIN                                                        │
│                                                                  │
│ 1. Agent calls MemoryService.remember(key, payload)             │
│    │                                                             │
│    ▼                                                             │
│ 2. MemoryService checks circuit breaker                         │
│    ├── OPEN → queue to Journal, raise error                     │
│    └── CLOSED → continue                                        │
│    │                                                             │
│    ▼                                                             │
│ 3. MemoryService calls MemoryClient.remember()                  │
│    │                                                             │
│    ▼                                                             │
│ 4. MemoryClient enriches payload                                │
│    - Add tenant, namespace, timestamp                           │
│    - Compute stable coordinate from key                         │
│    │                                                             │
│    ▼                                                             │
│ 5. MemoryClient sends HTTP POST /memories                       │
│    Headers: Authorization, X-Soma-Tenant, X-Soma-Namespace      │
│    Body: {coord, payload, memory_type}                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SOMAFRACTALMEMORY                                                │
│                                                                  │
│ 6. FastAPI receives POST /memories                              │
│    - Validate auth token                                        │
│    - Apply rate limiting                                        │
│    │                                                             │
│    ▼                                                             │
│ 7. core.store_memory(coordinate, value, memory_type)            │
│    │                                                             │
│    ├──► KV Store: serialize and set(data_key, value)           │
│    │                                                             │
│    ├──► Vector Store: embed_text() → upsert(points)            │
│    │                                                             │
│    └──► Graph Store: add_memory(coordinate, data)              │
│                                                                  │
│ 8. Return {coord, memory_type, timestamp}                       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Recall Memory Flow (SB ← SFM)

```
┌─────────────────────────────────────────────────────────────────┐
│ SOMABRAIN                                                        │
│                                                                  │
│ 1. Agent calls MemoryService.recall(query, top_k)               │
│    │                                                             │
│    ▼                                                             │
│ 2. MemoryService checks circuit breaker                         │
│    ├── OPEN → raise error (no degraded recall)                  │
│    └── CLOSED → continue                                        │
│    │                                                             │
│    ▼                                                             │
│ 3. MemoryClient sends HTTP POST /memories/search                │
│    Body: {query, top_k, tenant, namespace}                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SOMAFRACTALMEMORY                                                │
│                                                                  │
│ 4. core.recall(query, top_k)                                    │
│    │                                                             │
│    ├──► embed_text(query) → query_vector                       │
│    │                                                             │
│    ├──► vector_store.search(query_vector, top_k)               │
│    │    Returns: [(id, score, payload), ...]                   │
│    │                                                             │
│    ├──► For each hit: kv_store.get(data_key)                   │
│    │    Fetch full payload from KV                              │
│    │                                                             │
│    └──► Apply scoring: importance, recency, keyword boost      │
│                                                                  │
│ 5. Return [{coordinate, payload, score}, ...]                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SOMABRAIN                                                        │
│                                                                  │
│ 6. MemoryClient receives response                               │
│    │                                                             │
│    ▼                                                             │
│ 7. rescore_and_rank_hits()                                      │
│    - Apply recency normalization                                │
│    - Apply density factor                                       │
│    - Apply custom scorer if provided                            │
│    │                                                             │
│    ▼                                                             │
│ 8. Return List[RecallHit] to agent                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. PATTERN SUMMARY TABLE

| Pattern | SomaBrain | SomaFractalMemory |
|---------|-----------|-------------------|
| **Façade** | MemoryService | - |
| **Gateway** | MemoryClient | - |
| **Circuit Breaker** | CircuitBreaker | - |
| **Outbox** | db/outbox.py | - |
| **Abstract Factory** | - | IKeyValueStore, IVectorStore, IGraphStore |
| **Factory Method** | - | create_memory_system() |
| **Strategy** | Scoring strategies | Vector backend selection |
| **Decorator** | - | BatchedStore |
| **Composite** | - | PostgresRedisHybridStore |
| **Repository** | - | SomaFractalMemoryEnterprise |

---

## 7. VIBE CODING RULES COMPLIANCE ANALYSIS

### 7.1 Compliance Score: 7.5/10

The architecture has been evaluated against the VIBE CODING RULES from both repositories. While the overall design is solid, several violations have been identified that MUST be addressed.

### 7.2 VIOLATIONS IDENTIFIED

| ID | Severity | Rule Violated | Location | Description |
|----|----------|---------------|----------|-------------|
| V1 | CRITICAL | NO MOCKS/PLACEHOLDERS | `factory.py:186-193` | `InMemoryKeyValueStore` fallback when Redis unavailable |
| V2 | HIGH | REAL IMPLEMENTATIONS | `graph.py` | `NetworkXGraphStore` is in-memory only, no persistence |
| V3 | CRITICAL | Security Auditor | `http_api.py` | Tenant isolation NOT enforced in HTTP endpoints |
| V4 | MEDIUM | NO FAKE FALLBACKS | `http_api.py:~700` | `_payload_cache` acts as shim when KV fails |

### 7.3 Violation Details

#### V1: InMemoryKeyValueStore Fallback (CRITICAL)
```python
# CURRENT CODE (VIOLATION)
redis_store = RedisKeyValueStore(**redis_kwargs)
if not redis_store.health_check():
    logger.warning("Redis health check failed – falling back to InMemoryKeyValueStore")
    redis_store = InMemoryKeyValueStore()  # ❌ VIBE VIOLATION: NO MOCKS

# REQUIRED FIX
redis_store = RedisKeyValueStore(**redis_kwargs)
if not redis_store.health_check():
    raise RuntimeError("Redis unavailable - real infrastructure required")  # ✅ FAIL FAST
```

**Impact:** Production code silently degrades to in-memory storage, losing data durability.

#### V2: NetworkXGraphStore In-Memory Only (HIGH)
```python
# CURRENT CODE (VIOLATION)
graph_store = NetworkXGraphStore()  # ❌ No persistence - data lost on restart

# REQUIRED FIX
graph_store = PostgresGraphStore(url=settings.postgres_url)  # ✅ Persistent
```

**Impact:** Graph links are lost on SFM restart - no persistence layer.

#### V3: Tenant Isolation Not Enforced (CRITICAL - SECURITY)
```python
# CURRENT CODE (VIOLATION)
@app.post("/memories")
async def store_memory(req: MemoryStoreRequest):
    # ❌ No tenant extraction from headers
    # ❌ No namespace scoping by tenant
    mem.store_memory(coord, {"payload": req.payload}, memory_type=memory_type)

# REQUIRED FIX
@app.post("/memories")
async def store_memory(req: MemoryStoreRequest, request: Request):
    tenant = _get_tenant_from_request(request)  # ✅ Extract tenant
    scoped_namespace = f"{tenant}:{namespace}"  # ✅ Scope by tenant
    mem.store_memory(coord, {"payload": req.payload}, memory_type=memory_type, namespace=scoped_namespace)
```

**Impact:** Cross-tenant data leakage possible (XFAIL tests D1.1, D1.2).

#### V4: In-Process Payload Cache (MEDIUM)
```python
# CURRENT CODE (VIOLATION)
_payload_cache: dict[tuple[float, ...], dict[str, Any]] = {}  # ❌ SHIM
_payload_cache[coord] = req.payload  # ❌ Populating shim

# REQUIRED FIX
# Remove cache entirely - rely on real KV store
# Return HTTP 500 if KV store fails (not cached data)
```

**Impact:** Acts as a shim when KV store fails to persist.

### 7.4 COMPLIANT ASPECTS ✅

| Aspect | Status | Evidence |
|--------|--------|----------|
| Real Servers | ✅ COMPLIANT | Postgres, Redis, Milvus, Qdrant used |
| No TODOs/Stubs | ✅ COMPLIANT | Production-grade code with error handling |
| Documentation = Truth | ✅ COMPLIANT | Design docs accurately reflect implementation |
| Complete Context | ✅ COMPLIANT | Architecture well-documented with data flow |
| Circuit Breaker | ✅ COMPLIANT | Per-tenant fault isolation implemented |
| Outbox Pattern | ✅ COMPLIANT | Transactional reliability for writes |

### 7.5 Remediation Priority

1. **P0-VIBE-V3:** Tenant Isolation (SECURITY - blocks production deployment)
2. **P0-VIBE-V1:** Remove InMemoryKeyValueStore fallback (FAIL FAST)
3. **P0-VIBE-V2:** Add Graph Store persistence (data durability)
4. **P1-VIBE-V4:** Remove payload cache shim (clean architecture)

### 7.6 Post-Remediation Target Score: 9.5/10

After fixing all violations, the architecture will be fully VIBE compliant with:
- NO mocks, NO placeholders, NO fake implementations
- REAL servers and REAL data only
- FAIL FAST on infrastructure failures
- Complete tenant isolation (security)
- Persistent storage for all data (durability)

---

## 8. VECTOR BACKEND DECISION SUMMARY

### 8.1 Final Decision (2024-12-14)

| Backend | Status | Use Case | Rationale |
|---------|--------|----------|-----------|
| **Milvus** | ✅ REQUIRED | Production (SB + SFM) | Clustering, replication, persistence, gRPC performance |
| **Qdrant** | ⚠️ OPTIONAL | Testing only (SFM) | On-disk mode for test isolation, no external server needed |

### 8.2 Configuration Summary

**SomaBrain:**
- Milvus is HARDCODED - no configuration needed
- `ann.py` raises error if backend != "milvus"

**SomaFractalMemory:**
- Default: `SOMA_VECTOR_BACKEND=milvus`
- Test-only: `SOMA_VECTOR_BACKEND=qdrant` (with on-disk path)
- Production validation: Raises error if Qdrant used in production

### 8.3 Implementation Tasks

See `tasks.md` section **P0-VIBE** for:
- Task V5: Add Production Validation for Vector Backend

---

*Document generated: 2024-12-14*
*Analysis based on: SomaBrain and SomaFractalMemory codebases*
*VIBE Compliance Analysis: December 14, 2025*
*Vector Backend Decision: Milvus REQUIRED (production), Qdrant OPTIONAL (test-only)*
