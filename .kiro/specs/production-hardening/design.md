# Design Document: SomaBrain Production Hardening

**Version:** 1.0  
**Date:** December 8, 2025

---

## 1. Overview

This design document specifies the architectural improvements and code hardening required to bring SomaBrain to production-ready levels. The design addresses mathematical correctness, memory system reliability, configuration centralization, learning adaptation, observability, security, and code quality.

### 1.1 Goals

1. **Mathematical Integrity**: Ensure all BHDC/HRR operations maintain numerical invariants
2. **Memory Reliability**: Guarantee tiered memory operations are correct and consistent
3. **Configuration Purity**: Eliminate all direct `os.getenv()` calls in favor of centralized Settings
4. **Learning Correctness**: Verify adaptation engine formulas and constraints
5. **Observability**: Comprehensive health checks and metrics
6. **Security**: Proper authentication and authorization
7. **Code Quality**: Zero VIBE violations (no TODOs, mocks, placeholders)

### 1.2 Non-Goals

- Performance optimization (separate effort)
- New feature development
- UI/UX changes

---

## 2. Architecture

### 2.1 Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI REST Surface (app.py)                │
│  /remember, /recall, /context/evaluate, /context/feedback, etc. │
├─────────────────────────────────────────────────────────────────┤
│                    Cognitive Processing Layer                    │
│  ContextBuilder │ AdaptationEngine │ Neuromodulators │ Planner  │
├─────────────────────────────────────────────────────────────────┤
│                    Memory & Retrieval Layer                      │
│  TieredMemory │ SuperposedTrace │ UnifiedScorer │ RetrievalPipe │
├─────────────────────────────────────────────────────────────────┤
│                    Mathematical Core (BHDC)                      │
│  QuantumLayer │ BHDCEncoder │ PermutationBinder │ Numerics      │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│  Redis │ Kafka │ PostgreSQL │ Milvus │ OPA │ Prometheus         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Target Architecture (Refactored)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ memory   │ │ context  │ │ health   │ │ oak      │           │
│  │ router   │ │ router   │ │ router   │ │ router   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                    Service Layer                                 │
│  MemoryService │ ContextService │ LearningService │ PlanService │
├─────────────────────────────────────────────────────────────────┤
│                    Domain Layer                                  │
│  TieredMemory │ AdaptationEngine │ Neuromodulators │ Predictors │
├─────────────────────────────────────────────────────────────────┤
│                    Mathematical Core                             │
│  QuantumLayer │ BHDCEncoder │ Numerics │ HeatDiffusion          │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│  Settings │ HealthChecks │ Metrics │ CircuitBreaker             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Components and Interfaces

### 3.1 Mathematical Core

#### 3.1.1 QuantumLayer

```python
class QuantumLayer:
    """BHDC-powered hyperdimensional operations."""
    
    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Bind two vectors with spectral verification."""
        
    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Unbind with perfect invertibility."""
        
    def make_unitary_role(self, token: str) -> np.ndarray:
        """Create unit-norm role vector."""
        
    def superpose(self, *vectors) -> np.ndarray:
        """Superpose vectors with normalization."""
```

**Invariants:**
- `|H_k| ∈ [0.9, 1.1]` for all frequency bins after bind
- `||role|| = 1.0 ± 1e-6` for all unitary roles
- `cosine(unbind(bind(a, b), b), a) ≥ 0.99`

#### 3.1.2 BHDCEncoder

```python
class BHDCEncoder:
    """Generate deterministic binary/sparse hypervectors."""
    
    def random_vector(self) -> np.ndarray:
        """Generate random vector with configured sparsity."""
        
    def vector_for_key(self, key: str) -> np.ndarray:
        """Deterministic vector from string key."""
```

**Invariants:**
- Active element count = `round(sparsity * dim)`
- Deterministic: same key → same vector

#### 3.1.3 Numerics

```python
def compute_tiny_floor(dim: int, dtype, strategy: str = "sqrt") -> float:
    """Compute dtype-aware amplitude tiny-floor."""
    # Returns: eps * sqrt(D) for 'sqrt' strategy

def normalize_array(x, axis: int = -1, mode: str = "legacy_zero") -> np.ndarray:
    """L2-normalize with subtiny handling."""
    # Returns: deterministic baseline for zero-norm inputs
```

### 3.2 Memory System

#### 3.2.1 TieredMemory

```python
class TieredMemory:
    """Coordinates WM and LTM layers for governed recall."""
    
    def remember(self, anchor_id: str, key: np.ndarray, value: np.ndarray) -> None:
        """Store in WM, optionally promote to LTM."""
        
    def recall(self, key: np.ndarray) -> RecallContext:
        """Recall via WM, fall back to LTM."""
```

**Policies:**
- WM threshold: 0.65 (configurable)
- LTM threshold: 0.55 (configurable)
- Promotion margin: 0.1 (configurable)

#### 3.2.2 SuperposedTrace

```python
class SuperposedTrace:
    """Decayed HRR superposition with cleanup anchors."""
    
    def upsert(self, anchor_id: str, key: np.ndarray, value: np.ndarray) -> None:
        """Bind and update state with decay: M_{t+1} = (1-η)M_t + η·bind(Rk, v)"""
        
    def recall(self, key: np.ndarray) -> Tuple[np.ndarray, Tuple[str, float, float]]:
        """Recall with cleanup against managed anchors."""
```

**Parameters:**
- η (eta): Decay factor in (0, 1]
- cleanup_topk: Number of anchors to evaluate

#### 3.2.3 MemoryClient

```python
class MemoryClient:
    """Gateway to external memory HTTP service."""
    
    def health(self) -> dict:
        """Return health status with component flags."""
        
    def remember(self, payload: dict) -> Tuple[float, float, float]:
        """Store memory, return coordinate."""
        
    def recall(self, query: str, k: int) -> List[RecallHit]:
        """Recall memories, return normalized hits."""
```

**Contract:**
- Raises `RuntimeError` if health check fails
- Returns `RecallHit` objects with payload, score, coordinate

### 3.3 Learning & Adaptation

#### 3.3.1 AdaptationEngine

```python
class AdaptationEngine:
    """Online weight updates for retrieval/utility parameters."""
    
    def apply_feedback(self, utility: float, reward: float = None) -> bool:
        """Update weights: delta = lr × gain × signal"""
        
    def reset(self) -> None:
        """Restore default weights, clear history."""
```

**Formulas:**
- `alpha_delta = lr × gain_alpha × signal`
- `tau_{t+1} = tau_t × (1 - anneal_rate)` (exponential mode)

**Constraints:**
- All parameters clamped to [min, max] bounds
- Entropy cap enforced with RuntimeError on violation

#### 3.3.2 Neuromodulators

```python
class PerTenantNeuromodulators:
    """Per-tenant neuromodulator state management."""
    
    def get_state(self, tenant_id: str) -> NeuromodState:
        """Return tenant-specific or global default state."""
        
    def set_state(self, tenant_id: str, state: NeuromodState) -> None:
        """Update tenant state, notify subscribers."""
```

### 3.4 Configuration

#### 3.4.1 Settings

```python
class Settings(BaseSettings):
    """Centralized configuration with pydantic validation."""
    
    # Precedence: env vars > .env file > config.yaml
    # All modules MUST import from common.config.settings
```

**Rules:**
- No direct `os.getenv()` calls anywhere
- All defaults defined in Settings class
- Boolean parsing: "1", "true", "yes", "on" (case-insensitive)
- Comment stripping: "value # comment" → "value"

### 3.5 Predictors

#### 3.5.1 Heat Diffusion

```python
def chebyshev_heat_apply(apply_A, x, t, K, a, b) -> np.ndarray:
    """Approximate exp(-tA)x using Chebyshev polynomials of degree K."""
    
def estimate_spectral_interval(apply_A, n, m=16) -> Tuple[float, float]:
    """Run m-step Lanczos to estimate eigenvalue bounds."""
    
def lanczos_expv(apply_A, x, t, m=32) -> np.ndarray:
    """Approximate exp(-tA)x using Krylov subspace projection."""
```

---

## 4. Data Models

### 4.1 RecallHit

```python
@dataclass
class RecallHit:
    payload: Dict[str, Any]
    score: float | None = None
    coordinate: Tuple[float, float, float] | None = None
    raw: Dict[str, Any] | None = None
```

### 4.2 NeuromodState

```python
@dataclass
class NeuromodState:
    dopamine: float      # [0.2, 0.8]
    serotonin: float     # [0.0, 1.0]
    noradrenaline: float # [0.0, 0.1]
    acetylcholine: float # [0.0, 0.1]
    timestamp: float
```

### 4.3 RecallContext

```python
@dataclass
class RecallContext:
    layer: str           # "wm" or "ltm"
    anchor_id: str | None
    score: float
    second_score: float
    raw: np.ndarray
```

### 4.4 TraceConfig

```python
@dataclass(frozen=True)
class TraceConfig:
    dim: int = 1024
    eta: float = 0.08
    rotation_enabled: bool = True
    rotation_seed: int = 0
    cleanup_topk: int = 64
    epsilon: float = 1e-12
```

---

## 5. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Bind Spectral Invariant
*For any* two vectors a and b of dimension D, when bind(a, b) is performed, the FFT magnitude |H_k| of the result SHALL be within [0.9, 1.1] for all frequency bins k.
**Validates: Requirements 1.1**

### Property 2: Unitary Role Norm
*For any* role token string, when make_unitary_role(token) is called, the resulting vector SHALL have L2 norm equal to 1.0 ± 1e-6.
**Validates: Requirements 1.2**

### Property 3: Binding Round-Trip
*For any* two vectors a and b of dimension D, unbind(bind(a, b), b) SHALL return a vector with cosine similarity ≥ 0.99 to the original vector a.
**Validates: Requirements 1.3**

### Property 4: Tiny Floor Formula
*For any* dimension D and dtype, compute_tiny_floor(D, dtype, "sqrt") SHALL return eps × sqrt(D) where eps is the machine epsilon for dtype.
**Validates: Requirements 1.5**

### Property 5: BHDC Sparsity Count
*For any* BHDCEncoder with configured sparsity s and dimension D, all generated vectors SHALL have exactly round(s × D) non-zero elements.
**Validates: Requirements 1.6**

### Property 6: Tiered Memory Recall Order
*For any* TieredMemory instance with memories in both WM and LTM, recall() SHALL first query WM and only fall back to LTM if WM score is below the configured threshold.
**Validates: Requirements 2.2**

### Property 7: SuperposedTrace Decay Formula
*For any* SuperposedTrace with decay factor η, after upsert(key, value), the new state SHALL equal (1-η)×M_old + η×bind(R×key, value).
**Validates: Requirements 2.3**

### Property 8: Memory Promotion Margin
*For any* memory stored via TieredMemory.remember(), promotion to LTM SHALL only occur if the WM recall margin exceeds the configured promote_margin threshold.
**Validates: Requirements 2.7**

### Property 9: Settings Comment Stripping
*For any* environment variable value containing "#", the Settings parser SHALL strip the comment portion before parsing.
**Validates: Requirements 3.2**

### Property 10: Settings Boolean Parsing
*For any* boolean setting, the values "1", "true", "yes", "on" (case-insensitive) SHALL parse as True, and all other values SHALL parse as False.
**Validates: Requirements 3.5**

### Property 11: Adaptation Delta Formula
*For any* feedback signal s, AdaptationEngine.apply_feedback() SHALL compute parameter delta as learning_rate × gain × s.
**Validates: Requirements 4.1**

### Property 12: Adaptation Constraint Clamping
*For any* parameter update that would exceed [min, max] bounds, the AdaptationEngine SHALL clamp the value to the nearest bound.
**Validates: Requirements 4.2**

### Property 13: Tau Exponential Annealing
*For any* AdaptationEngine with tau_anneal_mode="exp" and anneal_rate r, after apply_feedback(), tau SHALL equal tau_old × (1 - r).
**Validates: Requirements 4.3**

### Property 14: Adaptation Reset
*For any* AdaptationEngine after reset(), all weights SHALL equal their default values and history SHALL be empty.
**Validates: Requirements 4.6**

### Property 15: Chebyshev Heat Approximation
*For any* symmetric matrix A with spectral interval [a, b] and vector x, chebyshev_heat_apply(A, x, t, K, a, b) SHALL approximate exp(-tA)x with error decreasing as K increases.
**Validates: Requirements 9.1**

### Property 16: Lanczos Spectral Bounds
*For any* symmetric matrix A, estimate_spectral_interval(A, n, m) SHALL return bounds [a, b] that contain all eigenvalues of A.
**Validates: Requirements 9.2**

### Property 17: Tenant Isolation
*For any* two distinct tenant IDs, PerTenantNeuromodulators SHALL maintain separate state objects that do not interfere with each other.
**Validates: Requirements 10.2**

### Property 18: Serialization Round-Trip
*For any* NeuromodState, RecallHit, or AdaptationEngine state, JSON serialization followed by deserialization SHALL produce an equivalent object.
**Validates: Requirements 11.1, 11.2, 11.3, 11.4**

### Property 19: Timestamp Normalization
*For any* timestamp in ISO-8601 format or numeric string, the System SHALL normalize it to Unix epoch seconds (float).
**Validates: Requirements 8.5**

### Property 20: RecallHit Normalization
*For any* memory service response format, MemoryClient._normalize_recall_hits() SHALL produce RecallHit objects with payload, score, and coordinate fields.
**Validates: Requirements 2.6**

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Exception Type | When to Use |
|----------|---------------|-------------|
| Configuration | `RuntimeError` | Missing required setting |
| Validation | `ValueError` | Invalid input value |
| Dimension | `ValueError` | Vector dimension mismatch |
| Service | `RuntimeError` | External service unavailable |
| Timeout | `TimeoutError` | Async operation timeout |
| Auth | `HTTPException(401)` | Missing/invalid authentication |
| Policy | `HTTPException(403)` | OPA policy denial |

### 6.2 Error Message Format

All error messages SHALL include:
1. What failed (operation name)
2. Why it failed (specific reason)
3. What was expected (if applicable)
4. What was received (if applicable)

Example:
```python
raise ValueError(
    f"Vector dimension mismatch in bind operation: "
    f"expected {self.cfg.dim}, got {vec.shape[0]}"
)
```

---

## 7. Testing Strategy

### 7.1 Property-Based Testing

**Framework:** Hypothesis (Python)

**Configuration:**
- Minimum 100 iterations per property
- Deadline: 5000ms per example
- Database: `.hypothesis` directory

**Annotation Format:**
```python
@given(...)
@settings(max_examples=100)
def test_property_name(self, ...):
    """
    **Feature: production-hardening, Property 1: Bind Spectral Invariant**
    **Validates: Requirements 1.1**
    """
```

### 7.2 Unit Testing

**Framework:** pytest

**Coverage Targets:**
- Mathematical core: 95%
- Memory system: 90%
- Configuration: 100%
- Error paths: 100%

### 7.3 Integration Testing

**Scope:**
- MemoryClient ↔ Memory Service
- HealthChecks ↔ Kafka/Postgres/Redis
- AdaptationEngine ↔ Redis persistence

### 7.4 Static Analysis

**Tools:**
- ruff: Linting and formatting
- mypy: Type checking
- Custom scanner: VIBE violation detection

---

## 8. Migration Plan

### 8.1 Phase 1: Configuration Centralization
1. Audit all `os.getenv()` calls
2. Add missing fields to Settings
3. Replace direct calls with Settings imports
4. Remove duplicate field definitions

### 8.2 Phase 2: Code Quality
1. Remove all TODO/FIXME comments
2. Remove all placeholder implementations
3. Implement missing error handlers
4. Add missing docstrings

### 8.3 Phase 3: Architecture Refactoring
1. Split `app.py` into routers
2. Split `settings.py` by domain
3. Modularize `metrics.py`
4. Resolve circular imports

### 8.4 Phase 4: Testing
1. Implement property-based tests
2. Add missing unit tests
3. Add integration tests
4. Run static analysis

---

## 9. Appendix: Comprehensive Refactoring Analysis

### 9.1 Critical Monolithic Files (>500 lines) - MUST REFACTOR

| File | Lines | Functions | Classes | Issue | Refactoring Target |
|------|-------|-----------|---------|-------|-------------------|
| `somabrain/app.py` | 4373 | 87 | 6 | **GOD FILE** - 44 endpoints, mixed concerns | Split into 8+ routers |
| `somabrain/memory_client.py` | 2216 | 55 | 3 | Large but cohesive | Extract transport layer |
| `somabrain/metrics.py` | 1698 | 43 | 1 | Metric definitions sprawl | Split by domain |
| `common/config/settings.py` | 1638 | 15 | 1 | Configuration sprawl | Split by domain |
| `somabrain/api/memory_api.py` | 1473 | ~40 | 0 | Large API module | Already separate, OK |
| `somabrain/learning/adaptation.py` | 1022 | ~30 | 4 | Complex learning logic | Extract tau/entropy modules |
| `somabrain/schemas.py` | 989 | 0 | ~50 | Schema definitions | Split by domain |
| `somabrain/api/context_route.py` | 589 | ~15 | 0 | Context API | OK size |
| `somabrain/tenant_registry.py` | 579 | ~20 | 2 | Tenant management | OK size |
| `somabrain/context/builder.py` | 542 | ~15 | 3 | Context building | OK size |
| `somabrain/db/outbox.py` | 523 | ~20 | 0 | Outbox operations | OK size |
| `somabrain/workers/outbox_publisher.py` | 521 | ~15 | 1 | Outbox worker | OK size |
| `somabrain/constitution/__init__.py` | 503 | ~15 | 3 | Constitution logic | OK size |

### 9.2 app.py Refactoring Plan (CRITICAL)

**Current State:** 4373 lines, 87 functions, 6 classes, 44 endpoints

**Problem:** Violates Single Responsibility Principle - contains:
- OPA engine wrapper
- Cognitive middleware
- Input validation
- Security middleware
- Logging setup
- Error handling
- Memory scoring functions
- Diversity reranking
- Admin endpoints (13)
- Health endpoints (5)
- Memory endpoints (recall, remember, delete)
- Sleep endpoints (3)
- Oak endpoints (4)
- Neuromodulator endpoints (2)
- Personality endpoint
- Plan endpoint
- Act endpoint
- Startup/shutdown handlers
- Predictor initialization
- Brain core classes

**Target Architecture:**

```
somabrain/
├── app.py                    # ~200 lines - FastAPI app creation, middleware, startup
├── routers/
│   ├── __init__.py
│   ├── admin.py              # Admin endpoints (13 endpoints)
│   ├── health.py             # Health/metrics endpoints (5 endpoints)
│   ├── memory.py             # /recall, /remember, /delete (4 endpoints)
│   ├── sleep.py              # Sleep endpoints (3 endpoints)
│   ├── oak.py                # Oak endpoints (4 endpoints) - ALREADY EXISTS
│   ├── neuromod.py           # Neuromodulator endpoints (2 endpoints)
│   ├── personality.py        # Personality endpoint (1 endpoint)
│   ├── plan.py               # Plan endpoint (1 endpoint)
│   └── act.py                # Act endpoint (1 endpoint)
├── middleware/
│   ├── __init__.py
│   ├── cognitive.py          # CognitiveMiddleware class
│   ├── security.py           # SecurityMiddleware class
│   └── opa.py                # SimpleOPAEngine - ALREADY EXISTS
├── core/
│   ├── __init__.py
│   ├── scoring.py            # _score_memory_candidate, _apply_diversity_reranking
│   ├── validation.py         # CognitiveInputValidator class
│   ├── error_handler.py      # CognitiveErrorHandler class
│   └── logging_setup.py      # setup_logging function
└── brain/
    ├── __init__.py
    ├── unified_core.py       # UnifiedBrainCore class
    ├── autoscaling.py        # AutoScalingFractalIntelligence class
    └── complexity.py         # ComplexityDetector class
```

### 9.3 settings.py Refactoring Plan

**Current State:** 1638 lines, single Settings class with 200+ fields

**Target Architecture:**

```
common/config/
├── __init__.py               # Re-export unified settings
├── settings.py               # ~300 lines - Base Settings class, core fields
├── settings_memory.py        # Memory-related settings
├── settings_learning.py      # Learning/adaptation settings
├── settings_oak.py           # Oak/ROAMDP settings
├── settings_auth.py          # Auth/JWT/OPA settings
├── settings_infra.py         # Redis/Kafka/Postgres settings
└── settings_milvus.py        # Milvus settings
```

### 9.4 metrics.py Refactoring Plan

**Current State:** 1698 lines, all metrics in one file

**Target Architecture:**

```
somabrain/metrics/
├── __init__.py               # Re-export all metrics
├── core.py                   # Core system metrics
├── memory.py                 # Memory operation metrics
├── learning.py               # Learning/adaptation metrics
├── neuromod.py               # Neuromodulator metrics
├── scorer.py                 # Scorer metrics
└── health.py                 # Health check metrics
```

### 9.5 Existing Router Structure (Partial - Needs Completion)

Already exists:
- `somabrain/oak/router.py` - Oak endpoints
- `somabrain/cognitive/thread_router.py` - Cognitive thread endpoints
- `somabrain/sleep/brain_sleep_router.py` - Sleep endpoints
- `somabrain/sleep/policy_sleep_router.py` - Sleep policy
- `somabrain/sleep/util_sleep_router.py` - Sleep utilities
- `somabrain/api/context_route.py` - Context endpoints
- `somabrain/api/memory_api.py` - Memory API (large, 1473 lines)
- `somabrain/api/config_api.py` - Config endpoints

**Problem:** These routers exist but app.py STILL contains duplicate endpoint definitions!

### 9.6 VIBE Violations Found

#### 9.6.1 Direct os.getenv() Calls (VIOLATION)
Location: `common/config/settings.py` lines 81, 95, 107, 117
- These are in helper functions `_int_env`, `_bool_env`, `_float_env`, `_str_env`
- **Status:** ACCEPTABLE - These are the canonical helpers used by Settings

#### 9.6.2 Stub/Placeholder Patterns Found
- `somabrain/tests/services/test_cognitive_sleep_integration.py`: FakePredictor, FakeNeuromods, FakePersonalityStore, FakeAmygdala
- `tests/unit/test_memory_service.py`: _StubBackend
- **Status:** Test files - ACCEPTABLE for test isolation

#### 9.6.3 Pass Statements (Potential Issues)
- 50+ `pass` statements found, mostly in exception handlers
- **Status:** Most are legitimate `except Exception: pass` for optional metrics/logging
- **Action:** Review each for proper error handling

#### 9.6.4 Monkey-patching References
- `somabrain/learning/adaptation.py`: "monkeypatching" comment
- `somabrain/oak/planner.py`: "monkey-patches" comment
- `benchmarks/tinyfloor_bench.py`: `_patched_compute_tiny_floor`
- **Status:** VIOLATION in production code, ACCEPTABLE in benchmarks/tests

### 9.7 Duplicate Code Patterns

Multiple `recall` method definitions found:
- `somabrain/memory_client.py`
- `somabrain/services/memory_service.py`
- `somabrain/memory/superposed_trace.py`
- `somabrain/wm.py`

**Action:** Ensure clear interface hierarchy, no duplicate implementations

### 9.8 Files to Audit for Direct os.getenv

The test `tests/test_settings_defaults.py` already checks for this:
```python
if "os.getenv(" in text:
    offenders.append(str(path))
```

### 9.9 International Standards Compliance

#### ISO/IEC 25010 (Software Quality)
- **Maintainability:** FAILING - Monolithic files violate modularity
- **Reliability:** PASSING - Error handling present
- **Security:** PASSING - Auth/OPA integration
- **Performance:** UNKNOWN - Needs benchmarking

#### Clean Code Principles
- **Single Responsibility:** FAILING - app.py has 10+ responsibilities
- **Open/Closed:** PARTIAL - Some extension points exist
- **Dependency Inversion:** PARTIAL - Settings abstraction exists

#### SOLID Principles Violations
1. **S** - Single Responsibility: app.py, settings.py, metrics.py
2. **O** - Open/Closed: Hardcoded predictor providers
3. **L** - Liskov Substitution: OK
4. **I** - Interface Segregation: Large Settings class
5. **D** - Dependency Inversion: Direct imports in app.py

### 9.10 Recommended Refactoring Priority

| Priority | File | Action | Effort |
|----------|------|--------|--------|
| P0 | `somabrain/app.py` | Split into routers + middleware + core | HIGH |
| P1 | `common/config/settings.py` | Split by domain | MEDIUM |
| P1 | `somabrain/metrics.py` | Split by domain | MEDIUM |
| P2 | `somabrain/learning/adaptation.py` | Extract tau/entropy modules | LOW |
| P2 | `somabrain/schemas.py` | Split by domain | LOW |
| P3 | Test stubs | Review for VIBE compliance | LOW |
