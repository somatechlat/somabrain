# Design Document - SomaBrain Global Architecture Refactor

**Document Version:** 1.0  
**Date:** December 9, 2025  
**Status:** Draft for Review

---

## MULTI-PERSONA ARCHITECTURE REVIEW

### 🎓 PhD-Level Software Developer Analysis

**MATHEMATICAL CORRECTNESS ISSUES FOUND:**

1. **Cosine Similarity Numerical Stability**
   - Current implementations use `float(np.linalg.norm(a))` which can lose precision
   - Should use `np.float64` intermediate calculations
   - Edge case: When `a` and `b` are nearly parallel but opposite, result should be -1.0

2. **Vector Normalization Edge Cases**
   - `somabrain/numerics.py:normalize_array` is 250+ lines - TOO COMPLEX
   - Multiple code paths for "legacy_zero", "robust", "strict" modes
   - Should be simplified to single canonical implementation

3. **FFT-based HRR Operations**
   - `quantum.py` and `quantum_pure.py` have different unbind strategies
   - Pure version raises `ZeroDivisionError`, production uses regularization
   - Need unified mathematical contract

4. **Frequent Directions Sketch**
   - `fd_rho.py` uses `np.linalg.svd` which is O(n³) - expensive
   - Should document complexity and provide streaming alternative

### 🔬 PhD-Level Software Analyst Analysis

**ARCHITECTURAL VIOLATIONS:**

| Issue | Location | Severity |
|-------|----------|----------|
| God Object | `app.py` (4,421 lines) | CRITICAL |
| Mixed Concerns | `memory_client.py` (2,216 lines) | HIGH |
| Circular Dependencies | 17+ `importlib` workarounds | HIGH |
| Global State | 20+ module-level mutables | HIGH |
| Duplicate Code | 9 cosine + 25 normalize | HIGH |

**DEPENDENCY GRAPH ISSUES:**
```
somabrain.app → somabrain.runtime (CIRCULAR)
somabrain.hippocampus → somabrain.runtime (CIRCULAR)
somabrain.services.* → somabrain.metrics (LAZY IMPORT)
```

### 🧪 PhD-Level QA Engineer Analysis

**TESTING GAPS:**

1. **Missing Property Tests:**
   - No round-trip test for `normalize_array`
   - No symmetry test for cosine similarity
   - No idempotence test for normalization

2. **Silent Failures (40+ locations):**
   - `except Exception: pass` hides bugs
   - No metrics for error rates
   - No structured logging

3. **Test Data Issues:**
   - Tests use `os.environ.get()` directly (9+ files)
   - Should use fixtures from conftest.py

### 📚 ISO-Style Documenter Analysis

**DOCUMENTATION GAPS:**

1. **Missing Docstrings:** 15+ functions
2. **Missing Mathematical Proofs:** HRR algebra not documented
3. **Missing API Contracts:** Memory service interface unclear
4. **Missing Error Codes:** No standardized error taxonomy

### 🔒 Security Auditor Analysis

**SECURITY CONCERNS:**

1. **Input Validation:**
   - `CognitiveInputValidator` in `app.py` uses regex that may be bypassed
   - No rate limiting on admin endpoints

2. **Configuration Security:**
   - Secrets in environment variables (acceptable but should use Settings)
   - No validation of JWT secrets at startup

3. **Error Information Leakage:**
   - Some error responses include stack traces
   - Should sanitize before returning to client

### ⚡ Performance Engineer Analysis

**PERFORMANCE ISSUES:**

1. **Memory Allocation:**
   - `normalize_array` creates multiple intermediate arrays
   - Should use in-place operations where possible

2. **Computational Complexity:**
   - `fd_rho.py:_compress()` uses full SVD - O(n³)
   - `lanczos_chebyshev.py` allocates new arrays in loop

3. **Cache Efficiency:**
   - `_TINY_CACHE` in `numerics.py` is unbounded
   - `_token_cache` in `quantum_pure.py` is unbounded

4. **Duplicate Computation:**
   - Cosine similarity computed multiple times in recall path
   - Should cache intermediate results

### 🎨 UX Consultant Analysis

**API USABILITY ISSUES:**

1. **Inconsistent Error Responses:**
   - Some return `{"error": "..."}`, others return `{"detail": "..."}`
   - Should standardize on RFC 7807 Problem Details

2. **Missing Pagination:**
   - `/admin/outbox` returns all events
   - Should have cursor-based pagination

3. **Unclear Status Codes:**
   - 503 used for both "service unavailable" and "policy deny"
   - Should differentiate

---

## 1. Overview

This design document defines the architectural refactoring strategy for SomaBrain to eliminate 180+ violations of VIBE Coding Rules, consolidate duplicate implementations, and establish clean architectural boundaries.

### 1.1 Goals

1. **Eliminate ALL duplicate code** - 9 cosine similarity + 25+ vector normalization implementations
2. **Centralize configuration** - Remove 30+ direct `os.environ` accesses
3. **Fix error handling** - Replace 40+ silent `except: pass` blocks
4. **Remove global state** - Refactor 20+ module-level mutable variables
5. **Resolve circular imports** - Fix 17+ `importlib` workarounds
6. **Establish clean architecture** - Single responsibility, dependency injection

### 1.2 ARCHITECTURAL PATTERN: Clean Architecture + Hexagonal (Ports & Adapters)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  somabrain/api/                                                  │    │
│  │  ├── app.py (FastAPI setup, < 200 lines)                        │    │
│  │  ├── routes/ (HTTP handlers)                                     │    │
│  │  ├── middleware/ (cross-cutting concerns)                        │    │
│  │  └── schemas/ (request/response DTOs)                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (depends on)
┌─────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  somabrain/services/                                             │    │
│  │  ├── memory_service.py (orchestrates memory operations)          │    │
│  │  ├── recall_service.py (orchestrates recall logic)               │    │
│  │  ├── scoring_service.py (orchestrates scoring)                   │    │
│  │  └── prediction_service.py (orchestrates predictions)            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (depends on)
┌─────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  somabrain/cognitive/ (Brain-inspired domain logic)              │    │
│  │  ├── amygdala/ (salience computation)                            │    │
│  │  ├── hippocampus/ (memory consolidation)                         │    │
│  │  ├── thalamus/ (input routing)                                   │    │
│  │  ├── prefrontal/ (executive control)                             │    │
│  │  └── neuromodulators/ (state modulation)                         │    │
│  │                                                                   │    │
│  │  somabrain/memory/ (Memory domain)                               │    │
│  │  ├── gateway.py (MemoryGateway interface - PORT)                 │    │
│  │  ├── working/ (working memory buffer)                            │    │
│  │  └── longterm/ (consolidation logic)                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (depends on)
┌─────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  somabrain/infrastructure/ (External adapters)                   │    │
│  │  ├── http_client.py (HTTP adapter for memory service)            │    │
│  │  ├── circuit_breaker.py (fault tolerance)                        │    │
│  │  └── messaging/kafka.py (event streaming adapter)                │    │
│  │                                                                   │    │
│  │  somabrain/memory/client/ (Memory service adapter - ADAPTER)     │    │
│  │  ├── transport.py (HTTP transport)                               │    │
│  │  ├── serialization.py (payload serialization)                    │    │
│  │  └── normalization.py (response normalization)                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (depends on)
┌─────────────────────────────────────────────────────────────────────────┐
│                          FOUNDATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  somabrain/core/ (NO external dependencies)                      │    │
│  │  ├── container.py (Dependency Injection container)               │    │
│  │  ├── types.py (shared type definitions)                          │    │
│  │  └── exceptions.py (exception hierarchy)                         │    │
│  │                                                                   │    │
│  │  somabrain/math/ (Pure mathematical operations)                  │    │
│  │  ├── similarity.py (CANONICAL cosine_similarity)                 │    │
│  │  ├── normalize.py (CANONICAL normalize_vector)                   │    │
│  │  ├── hrr/ (holographic representations)                          │    │
│  │  └── sdr/ (sparse distributed representations)                   │    │
│  │                                                                   │    │
│  │  common/config/settings/ (Configuration)                         │    │
│  │  └── Settings singleton (SINGLE SOURCE OF TRUTH)                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 KEY ARCHITECTURAL PATTERNS

| Pattern | Purpose | Location |
|---------|---------|----------|
| **Clean Architecture** | Dependency inversion, testability | All layers |
| **Hexagonal (Ports & Adapters)** | Isolate domain from infrastructure | `memory/gateway.py` (port), `memory/client/` (adapter) |
| **Dependency Injection** | Explicit dependencies, no global state | `core/container.py` |
| **Repository Pattern** | Abstract data access | `memory/gateway.py` |
| **Circuit Breaker** | Fault tolerance | `infrastructure/circuit_breaker.py` |
| **Strategy Pattern** | Pluggable algorithms | `scoring_service.py`, `prediction_service.py` |
| **Singleton (via DI)** | Controlled shared state | `core/container.py` |
| **Factory Pattern** | Object creation | `bootstrap/singletons.py` |

### 1.4 DEPENDENCY RULES (STRICT)

```
ALLOWED:
  Presentation → Application → Domain → Foundation
  Infrastructure → Domain (implements interfaces)
  Infrastructure → Foundation

FORBIDDEN:
  Domain → Infrastructure (use interfaces/ports instead)
  Foundation → anything above
  Circular dependencies of any kind
```

### 1.5 PORTS AND ADAPTERS DETAIL

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOMAIN                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MemoryGateway (PORT - Interface)                         │   │
│  │  ├── remember(key, payload) → Coordinate                  │   │
│  │  ├── recall(query, top_k) → List[RecallHit]              │   │
│  │  ├── health() → HealthStatus                              │   │
│  │  └── ...                                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▲                                     │
│                            │ implements                          │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                         INFRASTRUCTURE                           │
│                            │                                     │
│  ┌─────────────────────────┴────────────────────────────────┐   │
│  │  HTTPMemoryAdapter (ADAPTER - Implementation)             │   │
│  │  ├── Uses MemoryHTTPTransport                             │   │
│  │  ├── Uses PayloadSerializer                               │   │
│  │  ├── Uses ResponseNormalizer                              │   │
│  │  └── Implements MemoryGateway interface                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  InMemoryAdapter (ADAPTER - For testing)                  │   │
│  │  └── Implements MemoryGateway interface                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.6 DEPENDENCY INJECTION FLOW

```python
# bootstrap/singletons.py - Factory functions
def create_memory_gateway() -> MemoryGateway:
    transport = MemoryHTTPTransport(settings.memory_http_endpoint)
    serializer = PayloadSerializer()
    normalizer = ResponseNormalizer()
    return HTTPMemoryAdapter(transport, serializer, normalizer)

def create_memory_service() -> MemoryService:
    gateway = container.get("memory_gateway")
    circuit_breaker = container.get("circuit_breaker")
    return MemoryService(gateway, circuit_breaker)

# core/container.py - Registration
container.register("memory_gateway", create_memory_gateway)
container.register("memory_service", create_memory_service)

# api/routes/memory.py - Usage
@router.post("/remember")
async def remember(request: RememberRequest):
    service = container.get("memory_service")  # Injected, not imported
    return await service.remember(request.key, request.payload)
```

---

## 2. Architecture

### 2.1 Current State (PROBLEMATIC)

```
somabrain/
├── app.py (4,421 lines - GOD OBJECT)
│   ├── Middleware definitions
│   ├── Route handlers
│   ├── Scoring functions
│   ├── Bootstrap logic
│   ├── Global state
│   └── Utility functions
├── memory_client.py (2,216 lines - MIXED CONCERNS)
├── metrics_original.py (1,698 lines - LEGACY)
└── [scattered duplicates across 25+ files]
```

### 2.2 Target State (CLEAN ARCHITECTURE)

```
somabrain/
├── core/                          # Foundation layer (NO external deps)
│   ├── __init__.py
│   ├── container.py               # Dependency injection container
│   ├── types.py                   # Shared type definitions
│   └── exceptions.py              # Custom exception hierarchy
│
├── math/                          # Pure mathematical operations
│   ├── __init__.py
│   ├── similarity.py              # CANONICAL cosine_similarity
│   ├── normalize.py               # CANONICAL normalize_vector
│   ├── hrr/                       # Holographic representations
│   │   ├── __init__.py
│   │   ├── encoder.py
│   │   └── operations.py
│   ├── sdr/                       # Sparse distributed representations
│   │   ├── __init__.py
│   │   └── encoder.py
│   └── spectral/                  # FFT/spectral operations
│       ├── __init__.py
│       └── lanczos.py
│
├── memory/                        # Memory system
│   ├── __init__.py
│   ├── gateway.py                 # Unified memory interface
│   ├── client/                    # HTTP client components
│   │   ├── __init__.py
│   │   ├── transport.py           # HTTP transport layer
│   │   ├── serialization.py       # Payload serialization
│   │   └── normalization.py       # Response normalization
│   ├── working/                   # Working memory
│   │   ├── __init__.py
│   │   ├── buffer.py
│   │   └── multi_tenant.py
│   └── longterm/                  # Long-term memory
│       ├── __init__.py
│       └── consolidation.py
│
├── cognitive/                     # Brain-inspired components
│   ├── __init__.py
│   ├── amygdala/                  # Salience computation
│   │   ├── __init__.py
│   │   └── salience.py
│   ├── hippocampus/               # Memory consolidation
│   │   ├── __init__.py
│   │   └── consolidation.py
│   ├── thalamus/                  # Input routing
│   │   ├── __init__.py
│   │   └── router.py
│   ├── prefrontal/                # Executive control
│   │   ├── __init__.py
│   │   └── controller.py
│   └── neuromodulators/           # State modulation
│       ├── __init__.py
│       └── state.py
│
├── services/                      # Business logic services
│   ├── __init__.py
│   ├── memory_service.py
│   ├── recall_service.py
│   ├── scoring_service.py
│   └── prediction_service.py
│
├── api/                           # API layer
│   ├── __init__.py
│   ├── app.py                     # FastAPI app (< 200 lines)
│   ├── routes/                    # Route handlers by domain
│   │   ├── __init__.py
│   │   ├── memory.py
│   │   ├── admin.py
│   │   ├── health.py
│   │   └── cognitive.py
│   ├── middleware/                # Request/response middleware
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── cognitive.py
│   │   ├── opa.py
│   │   └── timing.py
│   └── schemas/                   # Request/response schemas
│       ├── __init__.py
│       └── memory.py
│
├── infrastructure/                # External service integration
│   ├── __init__.py
│   ├── circuit_breaker.py
│   ├── http_client.py
│   └── messaging/
│       ├── __init__.py
│       └── kafka.py
│
├── metrics/                       # Observability (SINGLE SOURCE)
│   ├── __init__.py
│   ├── prometheus.py
│   └── interface.py               # Metrics interface for DI
│
└── bootstrap/                     # Application initialization
    ├── __init__.py
    ├── singletons.py
    ├── logging.py
    └── config.py
```

---

## 3. Components and Interfaces

### 3.1 Core Math Module (`somabrain/math/`)

#### 3.1.1 Canonical Similarity (`somabrain/math/similarity.py`)

```python
"""Canonical similarity functions - SINGLE SOURCE OF TRUTH.

Mathematical Foundation:
    cosine(a, b) = (a · b) / (||a|| × ||b||)
    
    where:
    - a · b is the dot product (inner product)
    - ||x|| is the L2 norm (Euclidean norm)
    
Numerical Considerations:
    - Use float64 for intermediate calculations to minimize rounding error
    - Handle zero-norm vectors explicitly (return 0.0, not NaN)
    - Clamp result to [-1, 1] to handle floating-point edge cases
"""

from __future__ import annotations
import numpy as np
from typing import Union

# Epsilon for numerical stability - chosen to be above float64 machine epsilon
# but small enough to not affect meaningful computations
_EPS = 1e-12

ArrayLike = Union[np.ndarray, list, tuple]


def cosine_similarity(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine similarity between two vectors.
    
    Args:
        a: First vector (any array-like)
        b: Second vector (any array-like)
        
    Returns:
        Cosine similarity in [-1, 1], or 0.0 if either vector has zero norm.
        
    Mathematical Properties (VERIFIED BY PROPERTY TESTS):
        1. Symmetric: cosine(a, b) == cosine(b, a)
        2. Self-similarity: cosine(a, a) == 1.0 for non-zero a
        3. Bounded: -1.0 <= cosine(a, b) <= 1.0
        4. Zero handling: cosine(0, x) == 0.0
        5. Orthogonality: cosine(a, b) == 0.0 when a ⊥ b
        
    Numerical Stability:
        - Uses float64 intermediate calculations
        - Handles denormalized floats via epsilon threshold
        - Clamps output to handle floating-point edge cases
        
    Raises:
        ValueError: If vectors have different lengths
    """
    # Convert to float64 for numerical stability
    a_arr = np.asarray(a, dtype=np.float64).ravel()
    b_arr = np.asarray(b, dtype=np.float64).ravel()
    
    # Validate dimensions
    if a_arr.shape[0] != b_arr.shape[0]:
        raise ValueError(
            f"Vector dimension mismatch: {a_arr.shape[0]} vs {b_arr.shape[0]}"
        )
    
    # Compute norms using float64
    na = np.linalg.norm(a_arr)
    nb = np.linalg.norm(b_arr)
    
    # Handle zero-norm vectors
    if na <= _EPS or nb <= _EPS:
        return 0.0
    
    # Compute similarity with numerical clamping
    # The clamp handles edge cases where floating-point arithmetic
    # produces values slightly outside [-1, 1]
    dot = np.dot(a_arr, b_arr)
    sim = dot / (na * nb)
    
    return float(np.clip(sim, -1.0, 1.0))


def cosine_error(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine error (1 - similarity) bounded to [0, 1].
    
    This is the standard error metric for vector comparison where:
    - 0.0 = identical vectors (perfect match)
    - 1.0 = orthogonal vectors (no similarity)
    - 2.0 = opposite vectors (maximum dissimilarity, clamped to 1.0)
    
    Note: We clamp to [0, 1] because negative similarity (opposite vectors)
    is treated as maximum error for most cognitive applications.
    """
    sim = cosine_similarity(a, b)
    # Clamp to [0, 1] - opposite vectors (sim < 0) are maximum error
    return float(max(0.0, min(1.0, 1.0 - sim)))


def cosine_distance(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine distance (1 - similarity) in [0, 2].
    
    Unlike cosine_error, this preserves the full range:
    - 0.0 = identical vectors
    - 1.0 = orthogonal vectors
    - 2.0 = opposite vectors
    """
    sim = cosine_similarity(a, b)
    return float(1.0 - sim)
```

#### 3.1.2 Canonical Normalization (`somabrain/math/normalize.py`)

```python
"""Canonical vector normalization - SINGLE SOURCE OF TRUTH.

Mathematical Foundation:
    normalize(v) = v / ||v||
    
    where ||v|| = sqrt(sum(v_i^2)) is the L2 (Euclidean) norm.
    
Design Decision:
    The existing `somabrain/numerics.py:normalize_array` is 250+ lines with
    multiple modes ("legacy_zero", "robust", "strict"). This is a VIBE violation
    (complexity without justification). We replace it with a simple, correct
    implementation that handles the common case.
    
    For the rare cases needing special behavior, callers should handle
    edge cases explicitly rather than hiding them in mode flags.
"""

from __future__ import annotations
import numpy as np
from typing import Union, Tuple

# Epsilon for numerical stability
# Chosen to be above float32 machine epsilon (~1.2e-7) but small enough
# to not affect meaningful computations
_EPS = 1e-12

ArrayLike = Union[np.ndarray, list, tuple]


def normalize_vector(
    v: ArrayLike,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Normalize vector to unit L2 norm.
    
    Args:
        v: Input vector (any array-like)
        eps: Minimum norm threshold (returns zero vector if below)
        dtype: Output dtype (default float32 for memory efficiency)
        
    Returns:
        Unit-norm vector, or zero vector if input norm < eps.
        
    Mathematical Properties (VERIFIED BY PROPERTY TESTS):
        1. Idempotent: normalize(normalize(v)) == normalize(v)
        2. Unit norm: ||normalize(v)|| == 1.0 for non-zero v (within tolerance)
        3. Zero preservation: normalize(0) == 0
        4. Direction preservation: normalize(v) is parallel to v
        5. Scale invariance: normalize(k*v) == normalize(v) for k > 0
        
    Numerical Stability:
        - Uses float64 for intermediate norm calculation
        - Handles denormalized floats via epsilon threshold
        - Final cast to output dtype preserves precision where needed
        
    Performance:
        - Single pass through data for norm calculation
        - In-place division where possible
        - O(n) time complexity, O(1) extra space (excluding output)
    """
    # Convert to float64 for numerical stability in norm calculation
    v_arr = np.asarray(v, dtype=np.float64).ravel()
    
    # Compute L2 norm
    norm = np.linalg.norm(v_arr)
    
    # Handle zero/near-zero vectors
    if norm <= eps:
        return np.zeros(v_arr.shape, dtype=dtype)
    
    # Normalize and cast to output dtype
    normalized = v_arr / norm
    return normalized.astype(dtype, copy=False)


def safe_normalize(
    v: ArrayLike,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> Tuple[np.ndarray, float]:
    """Normalize vector and return original norm.
    
    Useful when the original magnitude is needed for downstream computation
    (e.g., weighting, scaling, or diagnostics).
    
    Args:
        v: Input vector
        eps: Minimum norm threshold
        dtype: Output dtype
        
    Returns:
        Tuple of (normalized_vector, original_norm)
        If original_norm < eps, returns (zero_vector, 0.0)
    """
    v_arr = np.asarray(v, dtype=np.float64).ravel()
    norm = float(np.linalg.norm(v_arr))
    
    if norm <= eps:
        return np.zeros(v_arr.shape, dtype=dtype), 0.0
    
    normalized = (v_arr / norm).astype(dtype, copy=False)
    return normalized, norm


def normalize_batch(
    vectors: np.ndarray,
    axis: int = -1,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Normalize a batch of vectors along specified axis.
    
    Args:
        vectors: Array of shape (..., dim) or (dim, ...)
        axis: Axis along which to normalize (default -1, last axis)
        eps: Minimum norm threshold
        dtype: Output dtype
        
    Returns:
        Normalized array with same shape as input.
        Vectors with norm < eps are set to zero.
        
    Example:
        >>> batch = np.random.randn(100, 256)  # 100 vectors of dim 256
        >>> normalized = normalize_batch(batch, axis=-1)
        >>> norms = np.linalg.norm(normalized, axis=-1)
        >>> assert np.allclose(norms[norms > 0], 1.0)
    """
    arr = np.asarray(vectors, dtype=np.float64)
    
    # Compute norms along axis, keeping dims for broadcasting
    norms = np.linalg.norm(arr, axis=axis, keepdims=True)
    
    # Create mask for zero/near-zero vectors
    mask = norms > eps
    
    # Normalize where norm is sufficient, zero otherwise
    result = np.where(mask, arr / norms, 0.0)
    
    return result.astype(dtype, copy=False)
```

### 3.2 Dependency Injection Container (`somabrain/core/container.py`)

```python
"""Dependency injection container for runtime singletons."""

from __future__ import annotations
from typing import TypeVar, Generic, Callable, Optional
from dataclasses import dataclass, field
import threading

T = TypeVar('T')

@dataclass
class Container:
    """Thread-safe dependency injection container."""
    
    _instances: dict[str, object] = field(default_factory=dict)
    _factories: dict[str, Callable[[], object]] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    def register(self, name: str, factory: Callable[[], T]) -> None:
        """Register a factory for lazy instantiation."""
        with self._lock:
            self._factories[name] = factory
    
    def get(self, name: str) -> object:
        """Get or create instance by name."""
        with self._lock:
            if name not in self._instances:
                if name not in self._factories:
                    raise KeyError(f"No factory registered for '{name}'")
                self._instances[name] = self._factories[name]()
            return self._instances[name]
    
    def reset(self) -> None:
        """Clear all instances (for testing)."""
        with self._lock:
            self._instances.clear()


# Global container instance
container = Container()
```

### 3.3 Metrics Interface (`somabrain/metrics/interface.py`)

```python
"""Metrics interface for dependency injection without circular imports."""

from __future__ import annotations
from typing import Protocol, Optional

class MetricsInterface(Protocol):
    """Protocol for metrics recording."""
    
    def inc_counter(self, name: str, labels: Optional[dict] = None) -> None: ...
    def observe_histogram(self, name: str, value: float, labels: Optional[dict] = None) -> None: ...
    def set_gauge(self, name: str, value: float, labels: Optional[dict] = None) -> None: ...


class NullMetrics:
    """No-op metrics implementation for testing."""
    
    def inc_counter(self, name: str, labels: Optional[dict] = None) -> None:
        pass
    
    def observe_histogram(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        pass
    
    def set_gauge(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        pass
```

---

## 4. Data Models

### 4.1 Configuration Model

All configuration flows through `common.config.settings.Settings`:

```python
# Settings attributes for previously hardcoded values
class Settings:
    # From nano_profile.py
    hrr_dim: int = 8192
    bhdc_sparsity: float = 0.1
    sdr_bits: int = 2048
    sdr_density: float = 0.03
    context_budget_tokens: int = 2048
    max_superpose: int = 32
    wm_slots: int = 12
    global_seed: int = 42
    
    # From dataclass defaults
    salience_soft_temperature: float = 0.15
    salience_fd_energy_floor: float = 0.9
    drift_window: int = 128
    drift_threshold: float = 5.0
    circuit_breaker_reset_interval: float = 60.0
    quota_daily_writes: int = 10000
    exec_conflict_threshold: float = 0.7
    exec_bandit_eps: float = 0.1
    policy_safety_threshold: float = 0.9
```

---

## 5. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Mathematical Properties (Core Math Module)

#### Property 1: Cosine Similarity Symmetry
*For any* two vectors a and b of the same dimension, `cosine_similarity(a, b) == cosine_similarity(b, a)` within floating-point tolerance (1e-10).

**Mathematical Basis:** Dot product is commutative: a·b = b·a
**Validates: Requirements 11.1, 4.5**

#### Property 2: Cosine Self-Similarity
*For any* non-zero vector v, `cosine_similarity(v, v) == 1.0` within floating-point tolerance.

**Mathematical Basis:** cos(θ) = 1 when θ = 0 (angle between v and itself)
**Validates: Requirements 11.1, 4.5**

#### Property 3: Cosine Boundedness
*For any* two vectors a and b, `-1.0 <= cosine_similarity(a, b) <= 1.0`.

**Mathematical Basis:** Cauchy-Schwarz inequality: |a·b| ≤ ||a|| × ||b||
**Validates: Requirements 11.1, 4.5**

#### Property 4: Zero Vector Handling
*For any* vector v and zero vector z, `cosine_similarity(z, v) == 0.0`.

**Mathematical Basis:** Division by zero is undefined; we define it as 0.0 by convention.
**Validates: Requirements 11.1, 4.5**

#### Property 5: Normalization Idempotence
*For any* vector v, `normalize(normalize(v)) == normalize(v)` within floating-point tolerance.

**Mathematical Basis:** If ||v|| = 1, then v/||v|| = v.
**Validates: Requirements 11.3, 4.3**

#### Property 6: Normalization Unit Norm
*For any* non-zero vector v, `||normalize(v)|| == 1.0` within floating-point tolerance (1e-6).

**Mathematical Basis:** By definition, normalize(v) = v/||v||, so ||normalize(v)|| = ||v||/||v|| = 1.
**Validates: Requirements 11.3, 4.1**

#### Property 7: Normalization Direction Preservation
*For any* non-zero vector v and its normalization n, `cosine_similarity(v, n) == 1.0`.

**Mathematical Basis:** Normalization only scales magnitude, not direction.
**Validates: Requirements 11.3, 4.3**

### HRR/BHDC Properties

#### Property 8: HRR Bind-Unbind Round-Trip
*For any* vectors a and b, `cosine_similarity(a, unbind(bind(a, b), b)) >= 0.95` (allowing for numerical noise).

**Mathematical Basis:** FFT-based circular convolution is invertible.
**Validates: Requirements 4.1**

#### Property 9: HRR Unit Norm Preservation
*For any* HRR operation (bind, unbind, superpose), the output has unit L2 norm when renorm=True.

**Mathematical Basis:** Explicit renormalization after each operation.
**Validates: Requirements 4.1, 4.3**

### Memory System Properties

#### Property 10: Serialization Round-Trip
*For any* valid memory payload p, `deserialize(serialize(p)) == p`.

**Mathematical Basis:** Bijective mapping between objects and byte sequences.
**Validates: Requirements 2.3, 2.4**

#### Property 11: Memory Store-Recall Consistency
*For any* stored memory with key k and payload p, recalling with query matching k returns p.

**Validates: Requirements 2.1, 2.5**

### Configuration Properties

#### Property 12: Configuration Completeness
*For any* Settings instance, all required attributes have valid non-None values at startup.

**Validates: Requirements 3.4, 14.3**

#### Property 13: Configuration Immutability
*For any* Settings attribute accessed multiple times, the value is consistent (no race conditions).

**Validates: Requirements 3.1**

### Architectural Properties

#### Property 14: No Circular Imports
*For any* module in somabrain/, importing it completes without requiring lazy imports or importlib workarounds.

**Validates: Requirements 15.1, 15.5**

#### Property 15: Single Source of Truth
*For any* utility function (cosine_similarity, normalize_vector), there exists exactly one canonical implementation, and all callers import from that location.

**Validates: Requirements 11.1, 11.2, 11.3**

#### Property 16: Error Visibility
*For any* exception caught in the system, either a log entry is emitted OR a metric is incremented OR the exception is re-raised.

**Validates: Requirements 13.1, 13.2**

---

## 6. Error Handling

### 6.1 Error Handling Strategy

Replace ALL `except Exception: pass` with structured error handling:

```python
# BEFORE (VIOLATION)
try:
    do_something()
except Exception:
    pass  # Silent failure

# AFTER (COMPLIANT)
try:
    do_something()
except Exception as e:
    logger.warning("Operation failed: %s", e, exc_info=True)
    metrics.inc_counter("operation_failures", {"operation": "do_something"})
    # Either re-raise, return default, or handle explicitly
```

### 6.2 Exception Hierarchy

```python
# somabrain/core/exceptions.py
class SomaBrainError(Exception):
    """Base exception for all SomaBrain errors."""

class ConfigurationError(SomaBrainError):
    """Configuration is invalid or missing."""

class MemoryServiceError(SomaBrainError):
    """Memory service operation failed."""

class CircuitBreakerOpen(MemoryServiceError):
    """Circuit breaker is open, service unavailable."""

class ValidationError(SomaBrainError):
    """Input validation failed."""
```

---

## 7. Testing Strategy

### 7.1 Property-Based Testing

Use Hypothesis framework with minimum 100 iterations per property:

```python
from hypothesis import given, strategies as st, settings
import numpy as np

@settings(max_examples=100)
@given(
    a=st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False), min_size=1, max_size=1000),
    b=st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False), min_size=1, max_size=1000),
)
def test_cosine_symmetry(a, b):
    """**Feature: global-architecture-refactor, Property 1: Cosine Similarity Symmetry**"""
    # Ensure same length
    min_len = min(len(a), len(b))
    a, b = np.array(a[:min_len]), np.array(b[:min_len])
    
    from somabrain.math.similarity import cosine_similarity
    assert abs(cosine_similarity(a, b) - cosine_similarity(b, a)) < 1e-10
```

### 7.2 Unit Testing

- Test specific examples and edge cases
- Test error conditions
- Test integration points

### 7.3 Integration Testing

- Use real backends (no mocks per VIBE rules)
- Test circuit breaker behavior
- Test configuration loading

---

## 8. Migration Strategy

### Phase 1: Create Canonical Implementations
1. Create `somabrain/math/similarity.py` with canonical `cosine_similarity`
2. Create `somabrain/math/normalize.py` with canonical `normalize_vector`
3. Write property tests for both

### Phase 2: Update Callers
1. Update each duplicate location to import from canonical
2. Delete duplicate implementations
3. Run tests after each file change

### Phase 3: Configuration Centralization
1. Add missing Settings attributes
2. Update hardcoded values to use Settings
3. Replace os.environ access with Settings

### Phase 4: Error Handling
1. Create exception hierarchy
2. Replace silent failures with structured handling
3. Add metrics for error tracking

### Phase 5: Circular Import Resolution
1. Create metrics interface
2. Refactor lazy imports to use DI container
3. Remove importlib workarounds

### Phase 6: Module Decomposition
1. Extract middleware from app.py
2. Extract routes from app.py
3. Extract bootstrap logic
4. Verify app.py < 500 lines

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Duplicate implementations | 0 | grep for function definitions |
| os.environ direct access | 0 | grep for os.environ/os.getenv |
| Silent error swallowing | 0 | grep for `except.*: pass` |
| Global state variables | 0 | grep for module-level mutables |
| Importlib workarounds | 0 | grep for importlib |
| Max file size | < 500 lines | wc -l |
| Property test coverage | 100% of properties | pytest --cov |
| All tests passing | 100% | pytest exit code |

---

*Document prepared following ISO-style structure for clarity and professional documentation standards.*
