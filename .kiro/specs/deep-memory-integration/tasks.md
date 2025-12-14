# Implementation Tasks - SB ↔ SFM Deep Memory Integration

## Task Overview

This document contains actionable implementation tasks for deep integration between SomaBrain (SB) and SomaFractalMemory (SFM). Tasks are ordered by priority (P0 → P3) and dependency.

---

## P0-VIBE: VIBE CODING RULES COMPLIANCE FIXES (CRITICAL)

> **VIBE COMPLIANCE SCORE: 7.5/10** - The following violations MUST be fixed before any other work.

### Task V1: Remove InMemoryKeyValueStore (COMPLETE)

- [x] **V1.1** Remove fallback when Redis health check fails
- [x] **V1.2** Raise RuntimeError on Redis unavailable
- [x] **V1.3** Remove import of InMemoryKeyValueStore
- [x] **V1.4** Remove InMemoryKeyValueStore class entirely from storage.py
- [ ] **V1.5** Update CI/CD to ensure Redis is always available for tests
- [ ] **V1.6** Write test: Redis unavailable → factory raises RuntimeError

### Task V2: Add Graph Store Persistence Layer (HIGH)

- [ ] **V2.1** Add `PostgresGraphStore` class that persists to Postgres
- [ ] **V2.2** Create `graph_nodes` and `graph_edges` tables
- [ ] **V2.3** Implement `add_memory()` with INSERT
- [ ] **V2.4** Implement `add_link()` with INSERT
- [ ] **V2.5** Implement `get_neighbors()` with JOIN query
- [ ] **V2.6** Replace `NetworkXGraphStore()` with `PostgresGraphStore()`
- [ ] **V2.7** Write test: SFM restart → graph links still exist

### Task V3: Enforce Tenant Isolation in HTTP API (CRITICAL - SECURITY)

- [ ] **V3.1** Add `_get_tenant_from_request()` helper function
- [ ] **V3.2** Add tenant middleware that sets `request.state.tenant`
- [ ] **V3.3** Prefix namespace with tenant from request in `store_memory()`
- [ ] **V3.4** Scope search by tenant in `search_memories_get()`
- [ ] **V3.5** Validate tenant owns the requested coordinate in `fetch_memory()`
- [ ] **V3.6** Add HTTP 403 response when tenant mismatch detected
- [ ] **V3.7** Write test: Tenant A stores → Tenant B fetches → HTTP 403

### Task V4: Remove In-Process Payload Cache (COMPLETE)

- [x] **V4.1** Remove `_payload_cache` global dict
- [x] **V4.2** Remove cache population in `store_memory()`
- [x] **V4.3** Remove cache lookup fallback in `fetch_memory()`
- [x] **V4.4** Rely on real KV store only
- [ ] **V4.5** Write test: KV store failure → HTTP 500

### Task V5: Add Production Validation for Vector Backend (MEDIUM)
**Violation:** Qdrant should NOT be used in production - Milvus is REQUIRED
**Location:** `somafractalmemory/somafractalmemory/factory.py`

- [ ] **V5.1** In `factory.py`: Add environment check at start of `create_memory_system()`
- [ ] **V5.2** If `SOMA_ENV=production` AND `SOMA_VECTOR_BACKEND=qdrant`, raise `RuntimeError`
- [ ] **V5.3** Log warning if `SOMA_VECTOR_BACKEND=qdrant` in non-production
- [ ] **V5.4** Update `.env.example` to document Milvus requirement
- [ ] **V5.5** Write test: production + qdrant → RuntimeError raised

---

## P0: CRITICAL FIXES

### Task 1: Fix Multi-Tenant Memory Isolation (D1)
- [x] **1.1** In `somafractalmemory/somafractalmemory/http_api.py`: Add `_get_tenant_from_request()` helper to extract tenant from X-Soma-Tenant header
- [x] **1.2** In `somafractalmemory/somafractalmemory/http_api.py`: Modify all `/memories/*` endpoints to scope operations by tenant prefix
- [x] **1.3** In `somabrain/somabrain/memory_client.py`: Ensure `_create_transport()` always sets X-Soma-Tenant header (never empty)
- [x] **1.4** In `somabrain/somabrain/memory_client.py`: Add tenant validation in `_tenant_namespace()` - return "default" if empty
- [ ] **1.5** Write integration test: Tenant A stores → Tenant B recalls → MUST return empty
- [ ] **1.6** Remove XFAIL markers from tests D1.1 and D1.2 after fix verified

**Requirement References:** D1.1, D1.2, D1.3, D1.4, D1.5

### Task 2: Complete Health Check with SFM Components (E3)
- [x] **2.1** In `somabrain/somabrain/memory_client.py`: Modify `health()` to return structured component status
- [x] **2.2** In `somabrain/somabrain/healthchecks.py`: Add `check_sfm_integration_health()` function
- [x] **2.3** In `somabrain/somabrain/healthchecks.py`: Return degraded (not failed) when any SFM component unhealthy
- [x] **2.4** Add 2-second timeout to SFM health check call
- [ ] **2.5** Write test: SFM partially unhealthy → SB health reports degraded with component list

**Requirement References:** E3.1, E3.2, E3.3, E3.4, E3.5


### Task 3: Complete Degradation Mode (E1)
- [x] **3.1** Create `somabrain/somabrain/infrastructure/degradation.py` with `DegradationManager` class
- [x] **3.2** In `DegradationManager`: Track degraded_since timestamp per tenant
- [x] **3.3** In `DegradationManager`: Implement `check_alert()` returning True if degraded > 5 minutes
- [x] **3.4** In `somabrain/somabrain/memory_client.py`: Wrap recall to return WM-only when circuit open
- [x] **3.5** In `somabrain/somabrain/memory_client.py`: Add `degraded=true` flag to recall response when in degraded mode
- [ ] **3.6** Write test: SFM unreachable → recall returns WM-only with degraded=true

**Requirement References:** E1.1, E1.2, E1.3, E1.4, E1.5

---

## P1: HIGH PRIORITY

### Task 4: WM State Persistence to SFM (A1)
- [ ] **4.1** Create `somabrain/somabrain/memory/wm_persistence.py` with `WMPersister` class
- [ ] **4.2** In `WMPersister`: Implement async queue for WM items pending persistence
- [ ] **4.3** In `WMPersister`: Implement background task draining queue to SFM
- [ ] **4.4** In `somabrain/somabrain/wm.py`: Add `_persistence_queue` and hook in `admit()`
- [ ] **4.5** In `WMPersister`: Store items with `memory_type="working_memory"`
- [ ] **4.6** Create `WMRestorer` class to restore WM state on SB startup
- [ ] **4.7** In `WMRestorer`: Filter by `evicted=false` when restoring
- [ ] **4.8** In `somabrain/somabrain/wm.py`: Mark evicted items in SFM (not delete)
- [ ] **4.9** Write test: SB shutdown → restart → WM state restored within 5 seconds

**Requirement References:** A1.1, A1.2, A1.3, A1.4, A1.5

### Task 5: Full Hybrid Recall Integration (C1)
- [x] **5.1** In `somabrain/somabrain/memory_client.py`: Add `hybrid_recall()` method
- [x] **5.2** In `hybrid_recall()`: Extract keywords from query using `_extract_keywords()`
- [x] **5.3** In `hybrid_recall()`: Call SFM `/memories/search` endpoint with filters
- [x] **5.4** In `hybrid_recall()`: Include importance scores in ranking (via rescore_fn)
- [x] **5.5** In `hybrid_recall()`: Fallback to vector-only on failure with degraded=true
- [ ] **5.6** In `somabrain/somabrain/memory/recall_ops.py`: Update `memories_search_async` to use hybrid by default
- [ ] **5.7** Write test: Query with keywords → hybrid recall used → results include keyword matches

**Requirement References:** C1.1, C1.2, C1.3, C1.4, C1.5

### Task 6: Batch Store Optimization (F1)
- [x] **6.1** In `somabrain/somabrain/memory_client.py`: Add `remember_bulk_optimized()` method
- [x] **6.2** In `remember_bulk_optimized()`: Implement chunking (max 100 items per request)
- [x] **6.3** In `remember_bulk_optimized()`: Handle partial failures - commit successful, retry failed
- [x] **6.4** In `remember_bulk_optimized()`: Return `BulkStoreResult` with succeeded/failed counts
- [x] **6.5** Add metrics: batch_size, batch_latency_ms, success_rate
- [ ] **6.6** Write test: 250 items → 3 chunks → partial failure in chunk 2 → 200+ succeeded

**Requirement References:** F1.1, F1.2, F1.3, F1.4, F1.5


---

## P2: MEDIUM PRIORITY

### Task 7: Graph Store Link Creation (B1)
- [x] **7.1** Create `somabrain/somabrain/memory/graph_client.py` with `GraphClient` class
- [x] **7.2** In `GraphClient`: Implement `create_link()` calling SFM `/graph/link`
- [x] **7.3** In `GraphClient`: Queue failed links to outbox with topic "graph.link"
- [x] **7.4** In `GraphClient`: Implement `create_co_recalled_links()` for co-recall linking
- [x] **7.5** In link creation: Include tenant_id, timestamp, strength in metadata
- [ ] **7.6** In `somabrain/somabrain/db/outbox.py`: Add "graph.link" to MEMORY_TOPICS
- [ ] **7.7** Write test: Recall returns 3 memories → 3 co_recalled links created

**Requirement References:** B1.1, B1.2, B1.3, B1.4, B1.5

### Task 8: Graph-Augmented Recall (B2)
- [x] **8.1** In `GraphClient`: Implement `get_neighbors()` calling SFM `/graph/neighbors`
- [ ] **8.2** In `somabrain/somabrain/memory/recall_ops.py`: Add `recall_with_graph_boost()` method
- [ ] **8.3** In `recall_with_graph_boost()`: Get 1-hop neighbors for each result
- [ ] **8.4** In `recall_with_graph_boost()`: Boost neighbor scores by link_strength × graph_boost_factor
- [x] **8.5** In `GraphClient`: Add 100ms timeout for graph traversal
- [x] **8.6** In `GraphClient`: Return empty on timeout (degraded mode)
- [ ] **8.7** Write test: Memory A linked to B → Query matches A → B score boosted

**Requirement References:** B2.1, B2.2, B2.3, B2.4, B2.5

### Task 9: Serialization Alignment (G1)
- [x] **9.1** Create `somabrain/somabrain/memory/serialization.py` with `serialize_for_sfm()`
- [x] **9.2** In `serialize_for_sfm()`: Convert tuples to lists
- [x] **9.3** In `serialize_for_sfm()`: Convert numpy arrays to lists
- [x] **9.4** In `serialize_for_sfm()`: Convert epoch timestamps to ISO 8601 strings
- [ ] **9.5** In `somabrain/somabrain/memory_client.py`: Use `serialize_for_sfm()` before all SFM calls
- [ ] **9.6** Write test: Payload with tuple, ndarray, epoch → serialized correctly for SFM

**Requirement References:** G1.1, G1.2, G1.3, G1.4, G1.5

### Task 10: Outbox Enhancement for Memory Operations (E2)
- [ ] **10.1** In `somabrain/somabrain/db/outbox.py`: Add MEMORY_TOPICS dict with all memory/graph topics
- [ ] **10.2** In `somabrain/somabrain/db/outbox.py`: Add `_idempotency_key()` function
- [ ] **10.3** In `somabrain/somabrain/memory_client.py`: Record to outbox before SFM call
- [ ] **10.4** In `somabrain/somabrain/memory_client.py`: Mark outbox entry "sent" on success
- [ ] **10.5** Add backpressure when outbox > 10000 entries
- [ ] **10.6** Write test: SFM fails → outbox entry pending → SFM recovers → replay succeeds → no duplicates

**Requirement References:** E2.1, E2.2, E2.3, E2.4, E2.5


---

## P3: LOW PRIORITY

### Task 11: WM-LTM Promotion Pipeline (A2)
- [ ] **11.1** Create `somabrain/somabrain/memory/promotion.py` with `PromotionTracker` class
- [ ] **11.2** In `PromotionTracker`: Track candidates with salience ≥ threshold
- [ ] **11.3** In `PromotionTracker`: Implement `check()` returning True after 3+ consecutive ticks
- [ ] **11.4** In `somabrain/somabrain/wm.py`: Integrate PromotionTracker in recall/salience calculation
- [ ] **11.5** In promotion: Store to LTM with `memory_type="episodic"` and `promoted_from_wm=true`
- [ ] **11.6** In promotion: Create "promoted_from" link in graph store
- [ ] **11.7** Add metrics: promotion_count, promotion_latency_ms
- [ ] **11.8** Write test: Item salience > 0.85 for 3 ticks → promoted to LTM

**Requirement References:** A2.1, A2.2, A2.3, A2.4, A2.5

### Task 12: Shortest Path Queries (B3)
- [ ] **12.1** In `GraphClient`: Implement `find_path()` calling SFM `/graph/path`
- [ ] **12.2** In `find_path()`: Return list of coordinates and link types
- [ ] **12.3** In `find_path()`: Return empty list if no path exists (not error)
- [ ] **12.4** In `find_path()`: Terminate search if path length > max_path_length (default 10)
- [ ] **12.5** Add metrics: path_length, path_query_latency_ms
- [ ] **12.6** Write test: A→B→C path exists → find_path returns [A, B, C] with link types

**Requirement References:** B3.1, B3.2, B3.3, B3.4, B3.5

### Task 13: End-to-End Tracing (H1)
- [ ] **13.1** In `somabrain/somabrain/memory_client.py`: Add `_inject_trace_context()` method
- [ ] **13.2** In all HTTP calls: Inject traceparent and tracestate headers
- [ ] **13.3** In `somafractalmemory/somafractalmemory/http_api.py`: Extract trace context and create child spans
- [ ] **13.4** Configure sampling rate (default 1%)
- [ ] **13.5** Write test: SB call → SFM span created → trace shows hierarchy

**Requirement References:** H1.1, H1.2, H1.3, H1.4, H1.5

### Task 14: Integration Metrics (H2)
- [ ] **14.1** Create `somabrain/somabrain/metrics/integration.py` with SFM metrics
- [ ] **14.2** Add SFM_REQUEST_TOTAL counter with operation, tenant, status labels
- [ ] **14.3** Add SFM_REQUEST_DURATION histogram with operation, tenant labels
- [ ] **14.4** Add CIRCUIT_BREAKER_STATE gauge with tenant label
- [ ] **14.5** Add OUTBOX_PENDING gauge with tenant label
- [ ] **14.6** Add WM_PROMOTION_TOTAL counter with tenant label
- [ ] **14.7** In `somabrain/somabrain/memory_client.py`: Record metrics on all SFM calls
- [ ] **14.8** Write test: SFM calls → metrics recorded with correct labels

**Requirement References:** H2.1, H2.2, H2.3, H2.4, H2.5

---

## SFM-Side Tasks (Cross-Repository)

### Task 15: SFM Graph Endpoints (B1, B2, B3)
- [x] **15.1** In `somafractalmemory/somafractalmemory/http_api.py`: Add POST `/graph/link` endpoint
- [x] **15.2** In `/graph/link`: Validate from_coord, to_coord, link_type
- [x] **15.3** In `/graph/link`: Call `graph_store.add_link()` with metadata
- [x] **15.4** In `somafractalmemory/somafractalmemory/http_api.py`: Add GET `/graph/neighbors` endpoint
- [x] **15.5** In `/graph/neighbors`: Accept coord, k_hop, limit parameters
- [x] **15.6** In `/graph/neighbors`: Call `graph_store.get_neighbors()` with tenant filtering
- [x] **15.7** In `somafractalmemory/somafractalmemory/http_api.py`: Add GET `/graph/path` endpoint
- [x] **15.8** In `/graph/path`: Call `graph_store.find_shortest_path()` with max_length limit

**Requirement References:** B1.1, B2.1, B3.1

### Task 16: SFM Tenant Isolation Enforcement (D1)
- [ ] **16.1** In `somafractalmemory/somafractalmemory/http_api.py`: Add `_get_tenant_from_request()` helper
- [ ] **16.2** In all `/memories/*` endpoints: Prefix namespace with tenant
- [ ] **16.3** In `somafractalmemory/somafractalmemory/core.py`: Ensure `store_memory()` scopes by tenant
- [ ] **16.4** In `somafractalmemory/somafractalmemory/core.py`: Ensure `recall()` scopes by tenant
- [ ] **16.5** In `somafractalmemory/somafractalmemory/core.py`: Ensure `hybrid_recall()` scopes by tenant
- [ ] **16.6** Write test: 100 concurrent tenants → zero cross-tenant leakage

**Requirement References:** D1.1, D1.2, D1.3, D1.4, D1.5

---

## Verification Checklist

After all tasks complete:

- [ ] All XFAIL tests D1.1, D1.2 pass
- [ ] Health check reports all SFM components
- [ ] Degraded mode returns WM-only with flag
- [ ] WM persists and restores across restart
- [ ] Hybrid recall uses keywords
- [ ] Bulk operations chunk correctly
- [ ] Graph links created on co-recall
- [ ] Graph boost applied in recall
- [ ] Serialization consistent between SB and SFM
- [ ] Outbox replays without duplicates
- [ ] Metrics recorded for all SFM calls
- [ ] Traces propagate across SB→SFM

---

## Notes

- Tasks 1-3 are P0 (Critical) and should be completed first
- Tasks 4-6 are P1 (High) and enable core functionality
- Tasks 7-10 are P2 (Medium) and enhance integration
- Tasks 11-14 are P3 (Low) and add advanced features
- Tasks 15-16 require changes in SFM repository
- All tasks must follow VIBE CODING RULES: NO mocks, NO stubs, NO placeholders
