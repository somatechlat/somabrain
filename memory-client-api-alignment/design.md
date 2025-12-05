# Design Document - VIBE Violations Comprehensive Cleanup

## Overview

This design document outlines the systematic approach to eliminate all VIBE coding rule violations discovered during the comprehensive codebase audit. The cleanup involves removing dead code, placeholder implementations, mock usage in tests, and updating documentation to reflect the actual API surface.

The primary goal is to ensure the codebase adheres to VIBE Rule 1 (NO BULLSHIT) - no mocks, no placeholders, no fake functions, no stubs, no TODOs - and VIBE Rule 5 (DOCUMENTATION = TRUTH) - documentation must reflect reality.

## Architecture

### Current State

```mermaid
graph TB
    subgraph "Dead Code Paths"
        A[memory_service.py] -->|calls| B[link/alink methods]
        A -->|calls| C[payloads_for_coords]
        A -->|calls| D[links_from]
        B -->|POST| E[/link endpoint - DOES NOT EXIST]
        C -->|GET| F[/payloads endpoint - DOES NOT EXIST]
        D -->|GET| G[/neighbors endpoint - DOES NOT EXIST]
    end

    subgraph "Working API"
        H[memory_client.py] -->|POST| I[/memories]
        H -->|POST| J[/memories/search]
        H -->|GET| K[/health]
    end
```

### Target State

```mermaid
graph TB
    subgraph "Clean Architecture"
        A[memory_service.py] -->|delegates to| B[memory_client.py]
        B -->|POST| C[/memories]
        B -->|POST| D[/memories/search]
        B -->|GET| E[/memories/coord]
        B -->|DELETE| F[/memories/coord]
        B -->|GET| G[/health, /stats, /ping]
    end

    subgraph "Interface"
        H[MemoryBackend Protocol] -->|defines| I[remember/aremember]
        H -->|defines| J[recall/arecall]
        H -->|defines| K[delete]
        H -->|defines| L[coord_for_key]
    end
```

## Components and Interfaces

### 1. Memory Interface (`somabrain/interfaces/memory.py`)

**Current State:** Defines 4 methods that don't exist in the implementation:
- `link()` - calls non-existent `/link` endpoint
- `alink()` - async version of above
- `payloads_for_coords()` - calls non-existent `/payloads` endpoint
- `links_from()` - calls non-existent `/neighbors` endpoint

**Target State:** Interface defines only methods that exist:
- `remember()` / `aremember()` - store memories via `/memories`
- `recall()` / `arecall()` - search memories via `/memories/search`
- `delete()` - delete memory via `/memories/{coord}`
- `coord_for_key()` - local utility, no API call
- `health()` - check service health via `/health`

### 2. Memory Service (`somabrain/services/memory_service.py`)

**Current State:** Contains proxy methods for dead functionality:
- `link()` at line ~163-176
- `alink()` at line ~178-195
- `payloads_for_coords()` at line ~237-238
- `links_from()` at line ~243-244

**Target State:** Only exposes working methods that delegate to `memory_client.py`.

### 3. Dead Routers and Endpoints

**Files to Delete:**
- `somabrain/api/routers/link.py` - entire router for non-existent endpoint

**Endpoints to Remove from `app.py`:**
- `/graph/links` endpoint (line ~4106-4150)

### 4. Placeholder/Stub Classes

**Files Requiring Action:**
| File | Class/Function | Action |
|------|----------------|--------|
| `somabrain/services/cutover_controller.py` | Entire file | DELETE (stub) |
| `somabrain/services/segmentation_service.py` | `CPDSegmenter` | DELETE placeholder |
| `somabrain/services/segmentation_service.py` | `HazardSegmenter` | DELETE placeholder |
| `somabrain/milvus_client.py` | `_DummyCollection` | DELETE stub |
| `somabrain/prefrontal.py` | Entire class | Evaluate - implement or delete |

### 5. Test Files with Mock Violations

| File | Violation | Action |
|------|-----------|--------|
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | Uses `MagicMock`, `patch` | Rewrite with real services or skip |
| `tests/oak/test_thread.py` | Uses `DummySession` | Use real PostgreSQL or skip |
| `tests/unit/test_outbox_sync.py` | Uses `DummyEvent`, `DummyClient` | Use real services or skip |

## Data Models

### Memory Store Request (Working)

```python
@dataclass
class MemoryStoreRequest:
    """Request body for POST /memories"""
    key: str
    payload: dict
    namespace: Optional[str] = None
    universe: Optional[str] = None
    embedding: Optional[List[float]] = None
```

### Memory Search Request (Working)

```python
@dataclass
class MemorySearchRequest:
    """Request body for POST /memories/search"""
    query: str
    limit: int = 10
    namespace: Optional[str] = None
    universe: Optional[str] = None
    threshold: Optional[float] = None
```

### RecallHit (Working - Already Implemented)

```python
@dataclass
class RecallHit:
    """Normalized memory recall hit from the SFM service."""
    payload: Dict[str, Any]
    score: float | None = None
    coordinate: Tuple[float, float, float] | None = None
    raw: Dict[str, Any] | None = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following correctness properties have been identified:

### Property 1: Deterministic Coordinate Generation

*For any* string key, the `_stable_coord()` function SHALL return the same 3D coordinate tuple every time, and all coordinate values SHALL be within the range [-1, 1].

**Validates: Requirements 7.1, 7.2**

This property ensures that coordinate generation is:
- Deterministic: same input always produces same output
- Bounded: coordinates stay within the valid range
- Consistent: no randomness or external state affects the result

### Property 2: Memory Round-Trip Consistency

*For any* valid memory payload, storing it via `remember()` and then recalling it via `recall()` with a matching query SHALL return a result containing the original payload data.

**Validates: Requirements 8.3, 8.4**

This property ensures that:
- The memory service correctly stores data
- The search functionality can retrieve stored data
- Response parsing correctly extracts memory payloads
- The round-trip preserves data integrity

### Property 3: No Forbidden Terms in Production Code

*For any* Python file in the `somabrain/` directory (excluding `tests/`), the file SHALL NOT contain the terms "mock", "stub", "placeholder", "TODO", "FIXME", or "dummy" in comments or docstrings (case-insensitive).

**Validates: Requirements 4.1-4.5, 10.1, 10.2**

This property ensures VIBE Rule 1 compliance by verifying that:
- No placeholder implementations exist
- No stub classes remain
- No mock references exist in production code
- All code is production-ready

## Error Handling

### Dead Code Removal Strategy

When removing dead code, the following error handling approach applies:

1. **Import Errors:** If removing a method causes import errors elsewhere, those imports must also be removed.

2. **AttributeError Prevention:** All callers of removed methods must be updated to either:
   - Remove the call entirely if the functionality is not needed
   - Raise `NotImplementedError` with a clear message if the functionality should exist but doesn't

3. **Graceful Degradation:** For features that depend on removed functionality:
- Log a warning at startup if the feature is disabled

## Testing Workbench Design (New)

**Purpose**: Prove SomaBrain recall correctness, degradation handling, tenant isolation, and performance against the real memory backend.

**Scope & Surfaces**
- Endpoints: `/remember`, `/recall`, `/health`, `/memory/metrics`.
- Client: `MemoryClient.remember/recall`, `_stable_coord`, dedupe/rerank helpers.
- Background: outbox sync loop, circuit breaker, sleep CB adapter.

**Datasets**
- Labeled mini-corpus for relevance (text).
- Orthogonal vector corpus for perfect nearest-neighbor ground truth.
- Multi-tenant fixtures (tenant_a, tenant_b) with disjoint corpora.
- Failure fixtures: forced 5xx/timeouts on memory backend.

**Metrics & Assertions**
- Quality: precision@k, recall@k, nDCG@k (targets: ≥0.8 on labeled set).
- Performance: p95 remember <300 ms, recall <400 ms (dev stack).
- Degradation: writes queued when memory fails; `/recall` returns `degraded=true`; pending drains to 0 post-recovery; no duplicates.
- Isolation: no cross-tenant hits; metrics labeled by tenant_id.

**Planned Test Assets**
- `tests/integration/test_recall_quality.py` (quality, degradation, isolation).
- `tests/utils/metrics.py` (precision/recall/nDCG helpers).
- Parametrized run of `benchmarks/recall_latency_bench.py` for SLO enforcement.
- Outbox durability scenario using forced backend failure and replay.

**Documentation**
- Add a “Testing Workbench” section to `docs/development-manual/testing-guidelines.md` detailing env vars (memory URL/token, Postgres DSN), datasets, commands, and SLO thresholds.
   - Return empty results rather than crashing
   - Document the limitation in the code

### Test Failure Handling

When tests fail due to mock removal:

1. **Skip if Service Unavailable:** Use `pytest.mark.skipif` to skip tests when required services are not available
2. **Integration Test Markers:** Mark tests that require real services with `@pytest.mark.integration`
3. **Clear Error Messages:** Provide actionable error messages when tests cannot run

## Testing Strategy

### Dual Testing Approach

This cleanup requires both unit tests and property-based tests:

#### Unit Tests

Unit tests will verify specific examples:
- File deletion verification (link.py, benchmark_link_latency.py)
- Method removal verification (specific line checks)
- Import cleanup verification
- Documentation accuracy checks

#### Property-Based Testing

Property-based tests will verify universal properties using **Hypothesis** (Python's standard PBT library):

1. **Coordinate Generation Property Test**
   - Generate random strings
   - Verify `_stable_coord()` returns consistent results
   - Verify all coordinates are in [-1, 1]

2. **Memory Round-Trip Property Test**
   - Generate random payloads
   - Store via `remember()`
   - Recall and verify data integrity

3. **No Forbidden Terms Property Test**
   - Scan all production Python files
   - Verify no forbidden terms exist

### Test Configuration

```python
# pytest.ini additions
[pytest]
markers =
    integration: marks tests as integration tests (require real services)
    property: marks tests as property-based tests
```

### Property Test Requirements

- Each property-based test MUST run a minimum of 100 iterations
- Each property-based test MUST be tagged with the format: `**Feature: memory-client-api-alignment, Property {number}: {property_text}**`
- Property tests MUST use Hypothesis library
- Property tests MUST NOT use mocks

## Implementation Order

The cleanup should proceed in this order to minimize breakage:

1. **Phase 1: Interface Cleanup**
   - Remove dead method signatures from `interfaces/memory.py`
   - This establishes the contract for what methods should exist

2. **Phase 2: Dead Code Removal**
   - Remove dead methods from `memory_service.py`
   - Remove dead routers (`link.py`)
   - Remove dead endpoints from `app.py`
   - Remove dead CLI commands from `memory_cli.py`

3. **Phase 3: Caller Cleanup**
   - Update all files that call removed methods
   - Remove or disable functionality that depends on dead code

4. **Phase 4: Placeholder Removal**
   - Delete stub files (`cutover_controller.py`)
   - Remove placeholder classes (`CPDSegmenter`, `HazardSegmenter`)
   - Remove dummy classes (`_DummyCollection`)

5. **Phase 5: Test Cleanup**
   - Remove mock usage from test files
   - Add skip markers for tests requiring unavailable services
   - Rewrite tests to use real services where possible

6. **Phase 6: Documentation Update**
   - Update README.md with correct endpoints
   - Update API reference documentation
   - Update testing guidelines

7. **Phase 7: Benchmark Cleanup**
   - Delete dead benchmark files
   - Update remaining benchmarks to use correct endpoints

8. **Phase 8: Milvus Hardening (no fallbacks)**
   - Enforce Milvus as the sole ANN backend when configured; fail fast on connect/index errors
   - Validate collection schema/metric/index params at startup; refuse to run on drift
   - Add golden-set recall@10 smoke to CI/workbench against live Milvus
   - Expose Milvus p95 ingest/search + segment load in health/metrics payloads
   - Add reconciliation (Postgres ↔ Milvus) to detect/repair missing/extra vectors
   - Oak option upserts must retry with backoff; failures propagate (no log-only)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing functionality | Medium | High | Run full test suite after each phase |
| Missing dead code references | Low | Medium | Use grep to find all references before removal |
| Test suite failures | High | Medium | Add skip markers for integration tests |
| Documentation drift | Low | Low | Update docs in same PR as code changes |

## Dependencies

- **Hypothesis**: Property-based testing library (already in requirements-dev.txt)
- **pytest**: Test framework (already installed)
- **httpx**: HTTP client for integration tests (already installed)
