# Requirements Document - SB ↔ SFM Deep Memory Integration

## Introduction

This specification defines requirements for DEEP INTEGRATION between SomaBrain (SB) and SomaFractalMemory (SFM). The goal is to fully leverage SFM's capabilities from SB, eliminate integration gaps, and ensure both systems operate as a unified cognitive-memory architecture. All implementations must be REAL, PRODUCTION-GRADE code with NO mocks, NO stubs, NO placeholders.

## Glossary

- **SB (SomaBrain)**: Cognitive runtime system (port 9696) providing planning, neuromodulation, and working memory
- **SFM (SomaFractalMemory)**: Memory backend service (port 9595) providing KV, vector, and graph storage
- **WM (Working Memory)**: Capacity-limited fast buffer in SB with salience-based eviction
- **LTM (Long-Term Memory)**: Persistent storage in SFM via vector store with ANN search
- **Graph Store**: SFM's IGraphStore interface for semantic links between memories
- **Hybrid Recall**: SFM's combined vector + keyword search with importance scoring
- **Circuit Breaker**: SB's per-tenant fault isolation mechanism for SFM calls
- **Outbox**: SB's transactional queue for reliable event delivery during degradation
- **Coordinate**: 3-tuple (x, y, z) identifying memory location in fractal space

---

## CATEGORY A: WORKING MEMORY PERSISTENCE

### Requirement A1: WM State Persistence to SFM

**User Story:** As a system operator, I want WM state to persist across SB restarts, so that cognitive context is not lost during deployments or failures.

#### Acceptance Criteria

1. WHEN SB shuts down gracefully THEN all WM items SHALL be serialized and stored to SFM with memory_type="working_memory"
2. WHEN SB starts up THEN it SHALL restore WM state from SFM for each tenant within 5 seconds
3. WHEN WM item is admitted THEN it SHALL be asynchronously persisted to SFM within 1 second (eventual consistency)
4. WHEN WM item is evicted THEN the corresponding SFM entry SHALL be marked as evicted (not deleted) for audit
5. WHEN WM capacity changes dynamically THEN the new capacity SHALL be persisted to SFM tenant metadata

### Requirement A2: WM-LTM Promotion Pipeline

**User Story:** As a cognitive architect, I want salient WM items to automatically promote to LTM, so that important short-term memories become long-term.

#### Acceptance Criteria

1. WHEN WM item salience exceeds promotion_threshold (default 0.85) for 3+ ticks THEN it SHALL be promoted to LTM
2. WHEN promotion occurs THEN the WM item SHALL retain a reference to the LTM coordinate
3. WHEN promoted item is recalled from LTM THEN its WM recency SHALL be refreshed
4. WHEN promotion fails due to SFM unavailability THEN the item SHALL be queued in outbox for retry
5. WHEN promotion succeeds THEN metrics SHALL record promotion_count and promotion_latency_ms

---

## CATEGORY B: GRAPH STORE INTEGRATION

### Requirement B1: Semantic Link Creation from SB

**User Story:** As a knowledge engineer, I want SB to create semantic links in SFM's graph store, so that memories form a connected knowledge graph.

#### Acceptance Criteria

1. WHEN two memories are recalled together THEN SB SHALL create a "co-recalled" link in SFM graph store
2. WHEN a memory references another by coordinate THEN SB SHALL create a "references" link
3. WHEN planning uses multiple memories THEN SB SHALL create "used_in_plan" links with plan_id metadata
4. WHEN link creation fails THEN the operation SHALL be queued in outbox with link_type and coordinates
5. WHEN links are created THEN they SHALL include timestamp, tenant_id, and strength (0.0-1.0)

### Requirement B2: Graph-Augmented Recall

**User Story:** As a retrieval engineer, I want SB recall to leverage SFM's graph store, so that semantically linked memories boost relevance.

#### Acceptance Criteria

1. WHEN recall is performed THEN SB SHALL request 1-hop neighbors from SFM graph store
2. WHEN graph neighbors are returned THEN their relevance scores SHALL be boosted by link_strength * graph_boost_factor
3. WHEN graph store is unavailable THEN recall SHALL proceed with vector-only results (degraded=true)
4. WHEN k_hop parameter is specified THEN SB SHALL traverse up to k hops (max 3)
5. WHEN graph traversal exceeds 100ms THEN it SHALL timeout and return partial results

### Requirement B3: Shortest Path Queries

**User Story:** As a reasoning system, I want to find the shortest path between two memories, so that I can trace conceptual connections.

#### Acceptance Criteria

1. WHEN find_path(from_coord, to_coord) is called THEN SB SHALL invoke SFM's find_shortest_path
2. WHEN path exists THEN the response SHALL include all intermediate coordinates and link types
3. WHEN no path exists THEN the response SHALL return empty list (not error)
4. WHEN path length exceeds max_path_length (default 10) THEN search SHALL terminate with partial=true
5. WHEN path query succeeds THEN metrics SHALL record path_length and path_query_latency_ms

---

## CATEGORY C: HYBRID RECALL INTEGRATION

### Requirement C1: Full Hybrid Recall Utilization

**User Story:** As a search engineer, I want SB to use SFM's full hybrid recall capabilities, so that retrieval quality is maximized.

#### Acceptance Criteria

1. WHEN SB recall is invoked THEN it SHALL use SFM's hybrid_recall_with_scores endpoint
2. WHEN hybrid recall is used THEN keyword terms SHALL be extracted from query and passed to SFM
3. WHEN importance scores are returned THEN SB SHALL incorporate them into final ranking
4. WHEN exact match is required THEN SB SHALL set exact=true in hybrid recall request
5. WHEN hybrid recall fails THEN SB SHALL fallback to vector-only search with degraded=true flag

### Requirement C2: Context-Aware Recall

**User Story:** As a cognitive system, I want recall to consider current context, so that results are relevant to the active task.

#### Acceptance Criteria

1. WHEN context dict is provided THEN SB SHALL invoke SFM's find_hybrid_with_context
2. WHEN context includes neuromodulator state THEN it SHALL influence recall ranking weights
3. WHEN context includes active_plan_id THEN memories linked to that plan SHALL be boosted
4. WHEN context is empty THEN standard hybrid recall SHALL be used
5. WHEN context serialization exceeds 4KB THEN it SHALL be truncated with warning logged

---

## CATEGORY D: MULTI-TENANT ISOLATION

### Requirement D1: Tenant Memory Isolation

**User Story:** As a security engineer, I want complete tenant isolation in memory operations, so that data privacy is guaranteed.

#### Acceptance Criteria

1. WHEN tenant A stores a memory THEN tenant B's recall SHALL NOT return it (CRITICAL - currently XFAIL)
2. WHEN tenant A queries with tenant B's coordinate THEN results SHALL be empty
3. WHEN namespace header is set THEN all SFM operations SHALL be scoped to that namespace
4. WHEN tenant header is missing THEN SB SHALL use default tenant, NOT leak cross-tenant data
5. WHEN 100 tenants operate concurrently THEN zero cross-tenant leakage SHALL occur

### Requirement D2: Per-Tenant Circuit Breaker Isolation

**User Story:** As a platform architect, I want per-tenant circuit breakers, so that one tenant's SFM failures don't affect others.

#### Acceptance Criteria

1. WHEN tenant A's SFM calls fail 5 times THEN only tenant A's circuit SHALL open
2. WHEN tenant A's circuit is open THEN tenant B's SFM calls SHALL proceed normally
3. WHEN tenant A's circuit resets THEN tenant B's circuit state SHALL be unchanged
4. WHEN circuit state is queried THEN metrics SHALL be labeled by tenant_id
5. WHEN per-tenant thresholds are configured THEN they SHALL override global defaults

---

## CATEGORY E: DEGRADATION AND RESILIENCE

### Requirement E1: Complete Degradation Mode

**User Story:** As an SRE, I want SB to operate in degraded mode when SFM is unavailable, so that partial functionality remains.

#### Acceptance Criteria

1. WHEN SFM is unreachable THEN SB SHALL continue with WM-only operations (degraded=true)
2. WHEN degraded mode is active THEN all writes SHALL queue to outbox for later replay
3. WHEN SFM recovers THEN outbox SHALL replay queued operations without duplicates (idempotency)
4. WHEN replay completes THEN pending_count metric SHALL return to zero
5. WHEN degraded mode exceeds 5 minutes THEN alert SHALL be triggered via metrics

### Requirement E2: Outbox-Based Write Reliability

**User Story:** As a data engineer, I want all SFM writes to be reliable, so that no memories are lost during failures.

#### Acceptance Criteria

1. WHEN remember() is called THEN the operation SHALL be recorded in outbox before SFM call
2. WHEN SFM call succeeds THEN outbox entry SHALL be marked "sent"
3. WHEN SFM call fails THEN outbox entry SHALL remain "pending" for retry
4. WHEN retry succeeds THEN duplicate detection SHALL prevent double-writes
5. WHEN outbox grows beyond 10000 entries THEN backpressure SHALL be applied to new writes

### Requirement E3: Health Check Completeness

**User Story:** As an operator, I want SB health to reflect SFM component status, so that I can monitor the full system.

#### Acceptance Criteria

1. WHEN /health is called THEN response SHALL include kv_store, vector_store, graph_store status from SFM
2. WHEN any SFM component is unhealthy THEN SB health SHALL report degraded (not failed)
3. WHEN SFM is completely unreachable THEN SB health SHALL report degraded with sfm_available=false
4. WHEN health check exceeds 2 seconds THEN it SHALL timeout and report unknown status
5. WHEN health is degraded THEN the specific unhealthy components SHALL be listed

---

## CATEGORY F: BULK OPERATIONS OPTIMIZATION

### Requirement F1: Batch Store Operations

**User Story:** As a performance engineer, I want bulk memory operations to be efficient, so that batch imports are fast.

#### Acceptance Criteria

1. WHEN remember_bulk() is called with N items THEN SB SHALL send single batch request to SFM
2. WHEN batch size exceeds 100 items THEN SB SHALL chunk into multiple requests of 100
3. WHEN batch request fails partially THEN successful items SHALL be committed, failed items retried
4. WHEN batch completes THEN metrics SHALL record batch_size, batch_latency_ms, success_rate
5. WHEN SFM doesn't support bulk endpoint THEN SB SHALL fallback to sequential calls with warning

### Requirement F2: Batch Recall Operations

**User Story:** As an API consumer, I want to recall multiple queries efficiently, so that batch inference is fast.

#### Acceptance Criteria

1. WHEN recall_batch() is called with N queries THEN SB SHALL parallelize SFM calls (max 10 concurrent)
2. WHEN any query fails THEN it SHALL be retried once before returning error for that query
3. WHEN batch recall completes THEN results SHALL be returned in same order as queries
4. WHEN total batch time exceeds 5 seconds THEN partial results SHALL be returned with timeout=true
5. WHEN batch recall is used THEN metrics SHALL record queries_count, total_latency_ms, avg_latency_ms

---

## CATEGORY G: SERIALIZATION ALIGNMENT

### Requirement G1: Consistent Serialization Format

**User Story:** As a data engineer, I want consistent serialization between SB and SFM, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN SB sends payload to SFM THEN it SHALL use JSON serialization (not pickle)
2. WHEN coordinates are serialized THEN they SHALL be 3-element float arrays [x, y, z]
3. WHEN timestamps are serialized THEN they SHALL be ISO 8601 strings with timezone
4. WHEN numpy arrays are in payload THEN they SHALL be converted to lists before serialization
5. WHEN deserialization fails THEN error SHALL include payload hash for debugging

### Requirement G2: Schema Validation

**User Story:** As a QA engineer, I want payload schemas to be validated, so that malformed data is rejected early.

#### Acceptance Criteria

1. WHEN payload is sent to SFM THEN SB SHALL validate against memory_payload_schema
2. WHEN validation fails THEN error SHALL include specific field and violation
3. WHEN optional fields are missing THEN defaults SHALL be applied per schema
4. WHEN unknown fields are present THEN they SHALL be preserved (forward compatibility)
5. WHEN schema version changes THEN migration path SHALL be documented

---

## CATEGORY H: OBSERVABILITY AND METRICS

### Requirement H1: End-to-End Tracing

**User Story:** As an SRE, I want distributed traces across SB and SFM, so that I can debug latency issues.

#### Acceptance Criteria

1. WHEN SB calls SFM THEN trace context SHALL be propagated via headers (traceparent, tracestate)
2. WHEN SFM processes request THEN it SHALL create child span with operation name
3. WHEN trace is complete THEN it SHALL show SB→SFM call hierarchy with timing
4. WHEN error occurs THEN span SHALL include error details and stack trace
5. WHEN sampling is enabled THEN at least 1% of requests SHALL be traced

### Requirement H2: Integration Metrics

**User Story:** As a platform engineer, I want metrics for SB↔SFM integration, so that I can monitor health and performance.

#### Acceptance Criteria

1. WHEN SFM call is made THEN metrics SHALL record sfm_request_total{operation, tenant, status}
2. WHEN SFM call completes THEN metrics SHALL record sfm_request_duration_seconds{operation, tenant}
3. WHEN circuit breaker state changes THEN metrics SHALL record circuit_breaker_state{tenant, state}
4. WHEN outbox size changes THEN metrics SHALL record outbox_pending_total{tenant}
5. WHEN WM→LTM promotion occurs THEN metrics SHALL record wm_promotion_total{tenant}

---

## Implementation Priority

1. **P0 (Critical)**: D1 (Tenant Isolation - fixes XFAIL), E1 (Degradation Mode), E3 (Health Check)
2. **P1 (High)**: A1 (WM Persistence), C1 (Hybrid Recall), F1 (Batch Store)
3. **P2 (Medium)**: B1 (Graph Links), B2 (Graph Recall), G1 (Serialization)
4. **P3 (Low)**: A2 (WM-LTM Promotion), B3 (Shortest Path), H1 (Tracing)

---

## Cross-Repository Impact

This spec affects BOTH repositories:

**SomaBrain (SB) Changes:**
- `somabrain/memory_client.py` - Add graph store calls, hybrid recall, WM persistence
- `somabrain/wm.py` - Add persistence hooks, promotion logic
- `somabrain/infrastructure/circuit_breaker.py` - Ensure per-tenant isolation
- `somabrain/db/outbox.py` - Add link operations, WM state events
- `somabrain/memory/recall_ops.py` - Integrate hybrid recall, graph boost

**SomaFractalMemory (SFM) Changes:**
- `somafractalmemory/http_api.py` - Expose graph endpoints, batch endpoints
- `somafractalmemory/core.py` - Ensure tenant isolation in all operations
- `somafractalmemory/interfaces/graph.py` - May need additional methods

---

## References

- SFM Core: `somafractalmemory/somafractalmemory/core.py`
- SFM Graph Interface: `somafractalmemory/somafractalmemory/interfaces/graph.py`
- SB Memory Client: `somabrain/somabrain/memory_client.py`
- SB Working Memory: `somabrain/somabrain/wm.py`
- SB Circuit Breaker: `somabrain/somabrain/infrastructure/circuit_breaker.py`
- SB Outbox: `somabrain/somabrain/db/outbox.py`
- Existing Spec Format: `somabrain/.kiro/specs/full-capacity-testing/requirements.md`


---

## CATEGORY I: VECTOR BACKEND ARCHITECTURE

### Requirement I1: Milvus Required (Exclusive Vector Backend)

**User Story:** As a platform architect, I want Milvus as the exclusive vector backend for both SomaBrain and SomaFractalMemory, so that operational complexity is minimized and consistency is guaranteed.

#### Acceptance Criteria

1. WHEN SomaBrain initializes vector operations THEN it SHALL use Milvus exclusively (hardcoded, no alternatives)
2. WHEN SomaFractalMemory initializes THEN it SHALL use Milvus exclusively (no other backends supported)
3. WHEN Milvus is unavailable THEN the system SHALL fail fast with clear error (no silent degradation)
4. WHEN vector operations are performed THEN they SHALL use pymilvus client library
5. WHEN collections are created THEN they SHALL follow naming convention: {namespace}_{tenant}
6. WHEN any non-Milvus vector backend is configured THEN startup SHALL fail with RuntimeError

### Requirement I2: Milvus Connection Management

**User Story:** As an operations engineer, I want robust Milvus connection handling, so that the system recovers gracefully from network issues.

#### Acceptance Criteria

1. WHEN Milvus connection is established THEN it SHALL use connection pooling with alias="default"
2. WHEN connection fails THEN it SHALL retry with exponential backoff (max 3 attempts)
3. WHEN connection succeeds THEN health_check() SHALL verify collection accessibility
4. WHEN TLS is required THEN secure=True SHALL be set in connection parameters
5. WHEN connection parameters change THEN existing connections SHALL be gracefully closed

### Requirement I3: Milvus Schema Consistency

**User Story:** As a data engineer, I want consistent Milvus schemas across all collections, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN collection is created THEN schema SHALL include: id (VARCHAR, primary), embedding (FLOAT_VECTOR), payload (JSON)
2. WHEN vector dimension mismatches THEN collection creation SHALL fail with explicit error
3. WHEN index is created THEN it SHALL use IVF_FLAT with metric_type appropriate to use case
4. WHEN schema verification fails THEN startup SHALL abort with detailed error message
5. WHEN schema migration is needed THEN it SHALL be handled via explicit migration script (not auto-migrate)

---

## CATEGORY J: DESIGN PATTERN ENFORCEMENT

### Requirement J1: Façade Pattern - MemoryService

**User Story:** As a developer, I want a single entry point for memory operations, so that complexity is hidden and consistency is enforced.

#### Acceptance Criteria

1. WHEN any component needs memory operations THEN it SHALL use MemoryService (not MemoryClient directly)
2. WHEN MemoryService is instantiated THEN it SHALL inject CircuitBreaker and DegradationManager
3. WHEN operations fail THEN MemoryService SHALL handle retry/fallback logic transparently
4. WHEN tenant context is needed THEN MemoryService SHALL resolve it from namespace
5. WHEN metrics are recorded THEN MemoryService SHALL label them with tenant_id

### Requirement J2: Gateway Pattern - MemoryClient

**User Story:** As a system architect, I want HTTP communication encapsulated in a single gateway, so that transport concerns are isolated.

#### Acceptance Criteria

1. WHEN HTTP calls to SFM are needed THEN they SHALL go through MemoryClient exclusively
2. WHEN MemoryClient is created THEN it SHALL configure httpx with connection pooling
3. WHEN authentication is required THEN MemoryClient SHALL inject Bearer token and tenant headers
4. WHEN retries are needed THEN MemoryClient SHALL use exponential backoff with jitter
5. WHEN transport errors occur THEN MemoryClient SHALL translate them to domain exceptions

### Requirement J3: Repository Pattern - SomaFractalMemoryEnterprise

**User Story:** As a backend developer, I want coordinated multi-store operations, so that data consistency is maintained across KV, Vector, and Graph stores.

#### Acceptance Criteria

1. WHEN store_memory() is called THEN it SHALL write to KV, Vector, AND Graph stores atomically
2. WHEN delete() is called THEN it SHALL remove from all three stores in correct order
3. WHEN recall() is called THEN it SHALL coordinate Vector search with KV payload fetch
4. WHEN any store fails THEN the operation SHALL rollback or compensate appropriately
5. WHEN health_check() is called THEN it SHALL verify all three stores are operational

---

## CATEGORY K: DATA FLOW INTEGRITY

### Requirement K1: Store Memory Flow

**User Story:** As a data integrity engineer, I want guaranteed data flow from agent to database, so that no memories are lost.

#### Acceptance Criteria

1. WHEN agent calls remember() THEN data SHALL flow: Agent → MemoryService → MemoryClient → HTTP → SFM → KV+Vector+Graph
2. WHEN any step fails THEN the failure SHALL be logged with full context (tenant, coordinate, error)
3. WHEN SFM is unavailable THEN data SHALL be queued in outbox with retry metadata
4. WHEN data reaches SFM THEN it SHALL be persisted to Postgres (KV) AND Milvus (Vector) AND NetworkX (Graph)
5. WHEN persistence completes THEN response SHALL include server-assigned coordinate

### Requirement K2: Recall Memory Flow

**User Story:** As a retrieval engineer, I want consistent recall flow, so that results are accurate and timely.

#### Acceptance Criteria

1. WHEN agent calls recall() THEN query SHALL flow: Agent → MemoryService → MemoryClient → HTTP → SFM → Vector Search → KV Fetch
2. WHEN vector search returns hits THEN full payloads SHALL be fetched from KV store
3. WHEN scoring is applied THEN it SHALL include: vector_similarity, importance, recency, keyword_boost
4. WHEN results are returned THEN they SHALL be sorted by combined score descending
5. WHEN no results found THEN empty list SHALL be returned (not error)

### Requirement K3: Delete Memory Flow

**User Story:** As a compliance officer, I want complete memory deletion, so that data removal requests are honored.

#### Acceptance Criteria

1. WHEN delete(coordinate) is called THEN it SHALL remove from: KV (data+meta keys), Vector (by coordinate match), Graph (node+edges)
2. WHEN KV delete fails THEN operation SHALL raise KeyValueStoreError
3. WHEN Vector delete fails THEN it SHALL be logged but not block KV deletion (best-effort)
4. WHEN Graph delete fails THEN it SHALL be logged but not block other deletions
5. WHEN deletion completes THEN audit log SHALL record: tenant, coordinate, timestamp, success/failure

---

## CATEGORY L: CONFIGURATION MANAGEMENT

### Requirement L1: Centralized Settings

**User Story:** As a DevOps engineer, I want all configuration in one place, so that deployment is predictable.

#### Acceptance Criteria

1. WHEN configuration is needed THEN it SHALL be loaded from common.config.settings (Pydantic)
2. WHEN environment variables are set THEN they SHALL override default values
3. WHEN required config is missing THEN startup SHALL fail with explicit error listing missing keys
4. WHEN config is loaded THEN it SHALL be validated against schema before use
5. WHEN sensitive values (passwords, tokens) are logged THEN they SHALL be redacted

### Requirement L2: Environment-Specific Configuration

**User Story:** As a release engineer, I want environment-specific configs, so that dev/staging/prod behave correctly.

#### Acceptance Criteria

1. WHEN running in any environment THEN SOMA_VECTOR_BACKEND SHALL be "milvus" (exclusive)
2. WHEN running tests THEN Milvus test collections SHALL be used for isolation
3. WHEN any non-Milvus backend is configured THEN startup SHALL fail with RuntimeError
4. WHEN config file is provided THEN it SHALL be merged with environment variables
5. WHEN config validation fails THEN detailed error message SHALL indicate which field failed

---

## CATEGORY M: ERROR HANDLING AND RECOVERY

### Requirement M1: Explicit Error Types

**User Story:** As a developer, I want typed exceptions, so that error handling is precise.

#### Acceptance Criteria

1. WHEN memory operation fails THEN it SHALL raise MemoryServiceError (or subclass)
2. WHEN circuit breaker is open THEN it SHALL raise CircuitBreakerOpen
3. WHEN timeout occurs THEN it SHALL raise MemoryTimeoutError
4. WHEN serialization fails THEN it SHALL raise MemorySerializationError
5. WHEN tenant isolation is violated THEN it SHALL raise TenantIsolationError (CRITICAL)

### Requirement M2: Recovery Procedures

**User Story:** As an SRE, I want documented recovery procedures, so that incidents are resolved quickly.

#### Acceptance Criteria

1. WHEN outbox has pending items THEN replay_memory_events() SHALL process them in order
2. WHEN circuit breaker is stuck open THEN manual reset SHALL be available via API
3. WHEN Milvus collection is corrupted THEN reconciliation job SHALL repair it
4. WHEN tenant data needs migration THEN migration script SHALL handle it safely
5. WHEN system recovers from degraded mode THEN it SHALL log recovery timestamp and pending count

---

## CATEGORY N: SECURITY AND COMPLIANCE

### Requirement N1: Authentication and Authorization

**User Story:** As a security engineer, I want all API calls authenticated, so that unauthorized access is prevented.

#### Acceptance Criteria

1. WHEN SB calls SFM THEN Authorization header SHALL contain valid Bearer token
2. WHEN token is invalid THEN SFM SHALL return 401 Unauthorized
3. WHEN tenant header is missing THEN SFM SHALL reject request (not use default)
4. WHEN rate limit is exceeded THEN SFM SHALL return 429 Too Many Requests
5. WHEN audit is required THEN all write operations SHALL be logged with tenant and timestamp

### Requirement N2: Data Encryption

**User Story:** As a compliance officer, I want data encrypted at rest and in transit, so that privacy is protected.

#### Acceptance Criteria

1. WHEN data is transmitted THEN TLS SHALL be used (HTTPS for HTTP, secure=True for Milvus)
2. WHEN sensitive payload fields are stored THEN they MAY be encrypted with Fernet
3. WHEN encryption key is rotated THEN existing data SHALL remain readable
4. WHEN encryption fails THEN operation SHALL fail (not store unencrypted)
5. WHEN decryption fails THEN error SHALL be logged with payload hash (not content)

---

## Updated Implementation Priority

1. **P0 (Critical - Security/Stability)**:
   - D1 (Tenant Isolation - fixes XFAIL)
   - E1 (Degradation Mode)
   - E3 (Health Check)
   - I1 (Milvus-Only Backend)
   - N1 (Authentication)

2. **P1 (High - Core Functionality)**:
   - A1 (WM Persistence)
   - C1 (Hybrid Recall)
   - F1 (Batch Store)
   - J1 (Façade Pattern)
   - K1 (Store Flow)

3. **P2 (Medium - Enhanced Features)**:
   - B1 (Graph Links)
   - B2 (Graph Recall)
   - G1 (Serialization)
   - I2 (Milvus Connection)
   - L1 (Centralized Settings)

4. **P3 (Low - Optimization)**:
   - A2 (WM-LTM Promotion)
   - B3 (Shortest Path)
   - H1 (Tracing)
   - M1 (Error Types)
   - N2 (Encryption)

---

## Requirements Summary

| Category | Requirements | Acceptance Criteria | Priority |
|----------|--------------|---------------------|----------|
| A: WM Persistence | 2 | 10 | P1 |
| B: Graph Integration | 3 | 15 | P2-P3 |
| C: Hybrid Recall | 2 | 10 | P1 |
| D: Multi-Tenant | 2 | 10 | P0 |
| E: Resilience | 3 | 15 | P0-P1 |
| F: Bulk Operations | 2 | 10 | P1 |
| G: Serialization | 2 | 10 | P2 |
| H: Observability | 2 | 10 | P2-P3 |
| I: Vector Backend | 3 | 15 | P0-P2 |
| J: Design Patterns | 3 | 15 | P1 |
| K: Data Flow | 3 | 15 | P1 |
| L: Configuration | 2 | 10 | P2 |
| M: Error Handling | 2 | 10 | P2-P3 |
| N: Security | 2 | 10 | P0-P3 |
| **TOTAL** | **33** | **165** | - |

---

*Document Version: 2.0*
*Last Updated: 2024-12-14*
*Status: COMPREHENSIVE - Ready for Implementation*
