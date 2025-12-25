# Design Document - VIBE Compliance Audit

## Overview

This design document outlines the architectural approach for achieving full VIBE Coding Rules compliance across the SomaBrain codebase. The audit identified 500+ violations across 14 monolithic files, 284 silent pass statements, and numerous duplicate implementations that must be systematically resolved.

## Architecture

### Current State

```
┌─────────────────────────────────────────────────────────────┐
│                    VIOLATION HOTSPOTS                        │
├─────────────────────────────────────────────────────────────┤
│  app.py (4052 lines)          │  Monolithic, mixed concerns │
│  memory_client.py (2216 lines)│  Transport + normalization  │
│  metrics_original.py (1698)   │  All metrics in one file    │
│  api/memory_api.py (1615)     │  Models + handlers mixed    │
│  learning/adaptation.py (1071)│  Config + feedback mixed    │
└─────────────────────────────────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                    MODULAR ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│  somabrain/                                                  │
│  ├── routers/          # <500 lines each                    │
│  ├── middleware/       # Extracted from app.py              │
│  ├── bootstrap/        # Startup logic                      │
│  ├── brain/            # Core cognitive classes             │
│  ├── lifecycle/        # Startup/shutdown                   │
│  ├── helpers/          # Shared utilities                   │
│  ├── memory/           # Decomposed memory_client           │
│  ├── metrics/          # Domain-split metrics               │
│  ├── learning/         # Decomposed adaptation              │
│  └── core/             # DI container, exceptions           │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Dependency Injection Container

**Location:** `somabrain/core/container.py`

```python
class Container:
    """Thread-safe singleton container for dependency injection."""
    
    def register(self, name: str, factory: Callable) -> None:
        """Register a factory function for lazy instantiation."""
    
    def get(self, name: str) -> Any:
        """Get or create instance by name."""
    
    def reset(self, name: str) -> None:
        """Reset instance for testing."""
    
    def reset_all(self) -> None:
        """Reset all instances for testing."""
```

### 2. Canonical Math Utilities

**Location:** `somabrain/math/`

```python
# somabrain/math/similarity.py
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Canonical cosine similarity - ALL other implementations delegate here."""

def cosine_error(a: np.ndarray, b: np.ndarray) -> float:
    """Canonical cosine error = 1 - cosine_similarity."""

# somabrain/math/normalize.py
def normalize_vector(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Canonical L2 normalization - ALL other implementations delegate here."""

def normalize_batch(vectors: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Batch normalization for efficiency."""
```

### 3. Metrics Interface

**Location:** `somabrain/metrics/interface.py`

```python
class MetricsProtocol(Protocol):
    """Protocol for metrics to avoid circular imports."""
    
    def counter(self, name: str, labels: dict) -> Counter: ...
    def gauge(self, name: str, labels: dict) -> Gauge: ...
    def histogram(self, name: str, labels: dict) -> Histogram: ...

def get_metrics() -> MetricsProtocol:
    """Get metrics instance from DI container."""
```

### 4. Settings Centralization

**Location:** `common/config/settings.py`

All magic numbers and environment variables flow through Pydantic Settings:

```python
class Settings(BaseSettings):
    # Scoring
    scoring_recency_bonus: float = 0.05
    scoring_keyword_bonus: float = 0.02
    scoring_exact_bonus: float = 0.01
    
    # Validation
    max_payload_size: int = 10000
    max_query_length: int = 4096
    max_batch_size: int = 64
    
    # SDR
    sdr_dimension: int = 16384
    sdr_sparsity: float = 0.01
    
    # Cache
    recall_cache_maxsize: int = 1000
    recall_cache_ttl: int = 300
    jwt_cache_ttl: int = 3600
```

## Data Models

### Decomposed File Structure

| Original File | Target Lines | Extracted Modules |
|--------------|--------------|-------------------|
| `app.py` | <500 | `routers/`, `middleware/`, `bootstrap/`, `lifecycle/` |
| `memory_client.py` | <500 | `memory/transport.py`, `memory/normalization.py`, `memory/scoring.py` |
| `metrics_original.py` | <500 | `metrics/core.py`, `metrics/learning.py`, `metrics/memory.py`, etc. |
| `api/memory_api.py` | <500 | `api/memory/models.py`, `api/memory/helpers.py`, `api/memory/recall.py` |
| `learning/adaptation.py` | <500 | `learning/config.py`, `learning/annealing.py`, `learning/persistence.py` |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: File Size Constraint
*For any* source file in `somabrain/`, the line count SHALL be less than 500 lines (excluding comments and blank lines).
**Validates: Requirements 1.1-1.7**

### Property 2: Router Size Constraint
*For any* router file in `somabrain/routers/`, the line count SHALL be less than 500 lines.
**Validates: Requirements 1.7**

### Property 3: Cosine Implementation Consistency
*For any* pair of vectors (a, b), all cosine similarity implementations SHALL return identical results within floating-point tolerance (1e-10).
**Validates: Requirements 2.1-2.6**

### Property 4: Normalization Implementation Consistency
*For any* vector v, all normalize implementations SHALL return identical results within floating-point tolerance (1e-10).
**Validates: Requirements 2.7-2.10**

### Property 5: No Silent Error Swallowing
*For any* exception handler with `pass`, there SHALL be a corresponding log statement at appropriate level.
**Validates: Requirements 3.1-3.8**

### Property 6: No Magic Numbers in Business Logic
*For any* numeric literal in business logic files, it SHALL be defined in Settings or documented as a mathematical constant.
**Validates: Requirements 8.1-8.7**

### Property 7: No Lazy Import Workarounds
*For any* production code file, there SHALL be no `importlib.import_module` calls for circular import avoidance.
**Validates: Requirements 5.1-5.8**

### Property 8: No Module-Level Mutable State
*For any* module in `somabrain/`, mutable state SHALL be managed via the DI container, not module-level variables.
**Validates: Requirements 6.1-6.7**

### Property 9: No Deprecated Code Patterns
*For any* file in `somabrain/`, there SHALL be no deprecated markers, `FORCE_FULL_STACK`, or legacy comments.
**Validates: Requirements 7.1-7.6**

### Property 10: No Production Assertions
*For any* production code file, `assert` statements SHALL be replaced with proper validation and error handling.
**Validates: Requirements 15.4-15.7**

### Property 11: All Caches Bounded
*For any* cache in the codebase, it SHALL have either `maxsize` or `ttl` configured with monitoring metrics.
**Validates: Requirements 19.1-19.5**

### Property 12: Type Annotation Coverage
*For any* public function, it SHALL have complete type annotations for parameters and return value.
**Validates: Requirements 11.1-11.3**

### Property 13: Degradation Mode Correctness
*For any* service unavailability, the system SHALL transition to degraded mode, queue operations, and recover without data loss.
**Validates: Requirements 13.1-13.6**

### Property 14: Observability Coverage
*For any* critical code path, there SHALL be corresponding metrics, health checks, and error logging.
**Validates: Requirements 20.1-20.5**

## Error Handling

### Structured Logging Pattern

Replace all silent `pass` statements with structured logging:

```python
# BEFORE (VIBE violation)
try:
    do_something()
except Exception:
    pass  # Silent failure

# AFTER (VIBE compliant)
try:
    do_something()
except Exception as exc:
    logger.debug("Operation failed, continuing", error=str(exc), context=ctx)
```

### Log Level Guidelines

| Scenario | Level | Example |
|----------|-------|---------|
| Metrics update failure | DEBUG | `logger.debug("Metric update failed", metric=name)` |
| Cache miss/fallback | DEBUG | `logger.debug("Cache miss, fetching from source")` |
| Non-critical service unavailable | WARNING | `logger.warning("Redis unavailable, using fallback")` |
| Critical operation failure | ERROR | `logger.error("Memory store failed", error=str(exc))` |

## Testing Strategy

### Property-Based Testing

All 14 correctness properties will be validated using Hypothesis:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=64, max_size=64))
def test_cosine_consistency(vector_data):
    """Property 3: All cosine implementations return identical results."""
    a = np.array(vector_data)
    b = np.random.randn(64)
    
    # All implementations must match
    canonical = cosine_similarity(a, b)
    assert abs(scoring._cosine(a, b) - canonical) < 1e-10
    assert abs(quantum.cosine(a, b) - canonical) < 1e-10
```

### Static Analysis Tests

```python
def test_no_silent_pass():
    """Property 5: No silent error swallowing."""
    violations = []
    for path in Path("somabrain").rglob("*.py"):
        content = path.read_text()
        # Find except blocks with only pass
        if re.search(r"except.*:\s*\n\s*pass\s*\n", content):
            violations.append(path)
    assert not violations, f"Silent pass in: {violations}"
```

### Integration Tests

All tests run against REAL infrastructure:
- PostgreSQL for canonical storage
- Redis for caching
- Milvus for vector search
- Kafka for event streaming

**NO MOCKS, NO STUBS, NO FAKES** - per VIBE Coding Rules.

## Migration Strategy

### Phase Execution Order

1. **Phase 1-4**: Foundation (decomposition, deduplication, error handling, config)
2. **Phase 5-6**: Architecture (circular imports, global state)
3. **Phase 7-10**: Cleanup (deprecated code, assertions, caches, thread safety)
4. **Phase 11-14**: Documentation (fallbacks, JWT, types, NotImplementedError)
5. **Phase 15-16**: Hardening (degradation modes, observability)

### Backward Compatibility

All refactoring maintains backward compatibility:
- Public APIs unchanged
- Import paths preserved via re-exports
- Configuration defaults match current behavior

### Rollback Strategy

Each phase is independently deployable:
- Feature flags for new code paths
- Gradual rollout per tenant
- Instant rollback via config change
