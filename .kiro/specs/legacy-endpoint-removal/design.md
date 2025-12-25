# Design Document - Complete VIBE Compliance Sweep

## Overview

This design document outlines the systematic approach to eliminate ALL VIBE coding rule violations from the SomaBrain codebase. The cleanup follows a HARD DELETE approach - no legacy code, no mentions, as if it never existed.

The primary goal is to ensure the codebase adheres to:
- **VIBE Rule 1 (NO BULLSHIT)** - No mocks, placeholders, fake functions, stubs, TODOs
- **VIBE Rule 4 (REAL IMPLEMENTATIONS ONLY)** - Production-grade code only
- **VIBE Rule 5 (DOCUMENTATION = TRUTH)** - Documentation reflects reality

## Architecture

### Current State (VIOLATIONS)

```mermaid
graph TB
    subgraph "Legacy Endpoints - TO DELETE"
        A[somabrain/routers/memory.py] -->|exposes| B[/remember]
        A -->|exposes| C[/recall]
        A -->|exposes| D[/delete]
    end
    
    subgraph "Canonical Endpoints - TO KEEP"
        E[somabrain/api/memory_api.py] -->|exposes| F[/memory/remember]
        E -->|exposes| G[/memory/recall]
    end
    
    subgraph "Consumers - TO UPDATE"
        H[benchmarks/*] -->|calls| B
        I[tests/*] -->|calls| B
        J[clients/*] -->|calls| B
        K[scripts/*] -->|calls| B
    end
```

### Target State (CLEAN)

```mermaid
graph TB
    subgraph "Single API Surface"
        E[somabrain/api/memory_api.py] -->|exposes| F[/memory/remember]
        E -->|exposes| G[/memory/recall]
        E -->|exposes| H[/memory/recall/stream]
        E -->|exposes| I[/memory/remember/batch]
    end
    
    subgraph "All Consumers - UPDATED"
        J[benchmarks/*] -->|calls| F
        K[tests/*] -->|calls| F
        L[clients/*] -->|calls| F
        M[scripts/*] -->|calls| F
    end
```

## Components and Interfaces

### 1. Legacy Router Removal

**File to DELETE:** `somabrain/routers/memory.py`

**Files to UPDATE:**
- `somabrain/routers/__init__.py` - Remove `memory_router` export
- `somabrain/app.py` - Remove `memory_router` import and registration

### 2. Endpoint Consumer Updates

All consumers must update from legacy to canonical endpoints:

| Legacy | Canonical |
|--------|-----------|
| `/remember` | `/memory/remember` |
| `/recall` | `/memory/recall` |
| `/delete` | `/memory/delete` (if exists) or remove |
| `/recall/delete` | Remove (use DELETE method) |

### 3. Fake/Mock/Stub Class Removal

**File to DELETE:** `somabrain/tests/services/test_cognitive_sleep_integration.py`

Classes to remove:
- `FakePredictor`
- `FakeNeuromods`
- `FakePersonalityStore`
- `FakeAmygdala`
- `SimplePredictor`
- `SimpleNeuromods`
- `SimplePersonalityStore`
- `SimpleAmygdala`

**File to UPDATE:** `tests/unit/test_memory_service.py`
- Remove `_StubBackend` class
- Use real backend or skip if unavailable

### 4. Shim Terminology Removal

| File | Current | Target |
|------|---------|--------|
| `somabrain/common/kafka.py` | `_ProducerShim` | `_KafkaProducerAdapter` |
| `somabrain/adaptive/core.py` | "Compatibility shim" | Remove reference |
| `somabrain/hippocampus.py` | "shim" | Remove reference |
| `somabrain/schemas.py` | "Compatibility Shim" | Remove reference |

### 5. Fallback Pattern Removal

**File:** `somabrain/memory/transport.py`
- Remove `_fallback_to_localhost()` method
- Remove all calls to fallback method
- Fail fast on connection errors

### 6. Legacy Comment Removal

| File | Comment to Remove |
|------|-------------------|
| `somabrain/metrics_original.py` | "Legacy Re-export Layer" |
| `somabrain/cli.py` | "Legacy code expects" |
| `somabrain/quotas.py` | "Falls back to legacy" |
| `somabrain/common/kafka.py` | "legacy environment variables" |
| `somabrain/numerics.py` | All "Legacy compatibility" comments |
| `somabrain/app.py` | "Test environment bypass" sections |

### 7. Schema Cleanup

**File:** `somabrain/schemas/health.py`
- Remove `stub_counts` field

**File:** `somabrain/routers/health.py`
- Remove all `stub_counts` references

## Data Models

No new data models. Existing models cleaned of legacy references.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: No Legacy Endpoint Exposure

*For any* HTTP request to `/remember` or `/recall` (without `/memory/` prefix), the system SHALL return 404 Not Found.

**Validates: Requirements 1.1, 1.2, 6.3**

### Property 2: Canonical Endpoint Functionality

*For any* valid memory payload, storing via `/memory/remember` and recalling via `/memory/recall` SHALL work identically to the removed legacy endpoints.

**Validates: Requirements 2.1-2.11, 3.1-3.8**

### Property 3: No Forbidden Terms in Production Code

*For any* Python file in `somabrain/` (excluding `tests/`), the file SHALL NOT contain: "mock", "stub", "placeholder", "fake", "dummy", "shim", "legacy", "TODO", "FIXME".

**Validates: Requirements 8.1-8.6, 10.1-10.6, 14.1-14.4**

### Property 4: No Fallback Patterns

*For any* service connection failure, the system SHALL fail fast with explicit error rather than silently degrading to fallback.

**Validates: Requirements 9.1, 9.2**

## Error Handling

### Connection Failures
- Remove all fallback logic
- Raise explicit `ConnectionError` or `RuntimeError`
- Log error with full context
- Return appropriate HTTP status (502, 503)

### Missing Services
- Tests skip with `pytest.skip()` when services unavailable
- No stub/mock replacements
- Clear skip message indicating required service

## Testing Strategy

### Property-Based Testing

Using **Hypothesis** library:

1. **No Forbidden Terms Test**
   - Scan all production Python files
   - Verify no forbidden terms exist
   - Run on every CI build

2. **Endpoint Routing Test**
   - Verify legacy endpoints return 404
   - Verify canonical endpoints work

### Integration Testing

- All existing integration tests updated to use `/memory/*` endpoints
- Tests skip when services unavailable (no mocks)
- Clear error messages for missing dependencies

## Implementation Order

### Phase 1: Delete Legacy Router (CRITICAL)
1. Delete `somabrain/routers/memory.py`
2. Update `somabrain/routers/__init__.py`
3. Update `somabrain/app.py`
4. Verify application starts

### Phase 2: Update Consumers
1. Update all benchmark files (11 files)
2. Update all integration tests (4 files)
3. Update scripts (1 file)
4. Update Python client (1 file)
5. Update CLI (1 file)

### Phase 3: Remove Fake/Mock/Stub Classes
1. Delete `somabrain/tests/services/test_cognitive_sleep_integration.py`
2. Update `tests/unit/test_memory_service.py`
3. Remove unittest.mock from `tests/property/test_settings_properties.py`

### Phase 4: Remove Shim Terminology
1. Rename `_ProducerShim` in `somabrain/common/kafka.py`
2. Clean docstrings in 4 files

### Phase 5: Remove Fallback Patterns
1. Remove `_fallback_to_localhost()` from `somabrain/memory/transport.py`

### Phase 6: Remove Legacy Comments
1. Clean 6 files of legacy references
2. Remove `stub_counts` from health schema

### Phase 7: Update Documentation
1. Update README.md
2. Update testing-guidelines.md
3. Update benchmarks/README.md

### Phase 8: Final Verification
1. Run full test suite
2. Verify no grep matches for forbidden terms
3. Verify application starts and endpoints work

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing functionality | Low | High | Run full test suite after each phase |
| Missing consumer updates | Low | Medium | Grep search for all endpoint references |
| Test failures from mock removal | Medium | Low | Add skip markers for unavailable services |

## Dependencies

- **pytest**: Test framework
- **httpx**: HTTP client for tests
- **Hypothesis**: Property-based testing (already installed)
