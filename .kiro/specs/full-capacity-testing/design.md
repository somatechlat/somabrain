# Design Document - SomaBrain Full Capacity Real-World Testing

## Introduction

This design document specifies the technical architecture for REAL WORLD testing that PROVES the mathematical correctness and functional capabilities of SomaBrain's cognitive system. All tests run against REAL Docker infrastructure with REAL data - NO mocks, NO stubs, NO fake implementations.

## Architecture Overview

### Test Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TEST ORCHESTRATION LAYER                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ pytest fixtures │  │ docker-compose  │  │ health checks   │              │
│  │ (session scope) │  │ lifecycle mgmt  │  │ (all backends)  │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────┘
            │                     │                     │
┌───────────▼─────────────────────▼─────────────────────▼──────────────────────┐
│                        SOMABRAIN APPLICATION (port 30101)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ /memory/remember│  │ /memory/recall  │  │ /neuromodulators│              │
│  │ /plan/suggest   │  │ /health         │  │ /metrics        │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────┘
            │                     │                     │
┌───────────▼─────────────────────▼─────────────────────▼──────────────────────┐
│                        BACKEND SERVICES                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Redis   │  │  Kafka   │  │  Milvus  │  │ Postgres │  │   OPA    │       │
│  │  :30100  │  │  :30102  │  │  :30119  │  │  :30106  │  │  :30104  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Test Categories and Components

| Category | Component | Test Type | Backend Dependencies |
|----------|-----------|-----------|---------------------|
| A: Math Core | HRR Binding | Unit + Property | None (pure math) |
| A: Math Core | Vector Similarity | Unit + Property | None (pure math) |
| A: Math Core | Predictor Math | Unit + Property | None (pure math) |
| A: Math Core | Salience Computation | Unit + Property | None (pure math) |
| B: Memory | WM Capacity | Integration | Redis |
| B: Memory | LTM Search | Integration | Milvus |
| B: Memory | Round-Trip | Integration | Redis, Milvus, Postgres |
| B: Memory | Fusion | Integration | Redis, Milvus |
| C: Cognitive | Neuromodulators | Integration | Redis |
| C: Cognitive | Planning | Integration | Redis, Milvus |
| C: Cognitive | Learning | Integration | Redis, Postgres |
| C: Cognitive | Context | Integration | Redis |
| D: Multi-Tenant | Memory Isolation | Integration | All backends |
| D: Multi-Tenant | State Isolation | Integration | All backends |
| E: Infrastructure | Docker Setup | E2E | All backends |
| E: Infrastructure | Health Verification | E2E | All backends |
| E: Infrastructure | Resilience | E2E | All backends |
| F: Circuit Breaker | State Machine | Unit + Integration | Redis |
| F: Circuit Breaker | Per-Tenant | Integration | Redis |
| F: Circuit Breaker | Degraded Mode | Integration | All backends |
| G: Performance | Latency SLOs | Load | All backends |
| G: Performance | Throughput | Load | All backends |
| G: Performance | Recall Quality | Load | Milvus |

---

## Component Design

### Category A: Mathematical Core Proofs

#### A1: HRR Binding Mathematical Correctness

**Source Module:** `somabrain/quantum.py`

**Test Strategy:** Property-based testing with Hypothesis

**Data Model:**
```python
@dataclass
class HRRTestVector:
    """Test vector for HRR operations."""
    dim: int = 1024
    dtype: str = "float64"
    vector: np.ndarray = field(default_factory=lambda: np.zeros(1024))
    
@dataclass
class HRRBindingResult:
    """Result of HRR binding operation."""
    bound_vector: np.ndarray
    spectral_magnitudes: np.ndarray
    recovery_similarity: float
    superposition_similarities: List[float]
```

**Correctness Properties:**
1. Spectral Magnitude Bound: `∀k: 0.9 ≤ |H_k| ≤ 1.1`
2. Unit Norm Roles: `||role|| = 1.0 ± 1e-6`
3. Binding Invertibility: `cos(unbind(bind(a, b), b), a) > 0.95`
4. Superposition Recovery: `cos(cleanup(superpose(bind(a,r1), bind(b,r2)), r1), a) > 0.8`
5. Wiener Filter Optimality: `||unbind_wiener(c, b) - a|| < ||unbind_exact(c, b) - a||` for noisy c

**Implementation:**
```python
# tests/proofs/test_hrr_math.py
class TestHRRMathematicalCorrectness:
    """Property-based tests for HRR mathematical correctness."""
    
    @given(st.integers(min_value=256, max_value=2048))
    def test_spectral_magnitude_bounded(self, dim: int) -> None:
        """A1.1: Spectral magnitude remains bounded in [0.9, 1.1]."""
        
    @given(st.text(min_size=1, max_size=100))
    def test_role_unit_norm(self, token: str) -> None:
        """A1.2: Role vectors have unit norm."""
        
    @given(vectors_strategy())
    def test_bind_unbind_invertibility(self, a: np.ndarray, b: np.ndarray) -> None:
        """A1.3: Bind then unbind recovers original with similarity > 0.95."""
```

#### A2: Vector Similarity Mathematical Correctness

**Source Module:** `somabrain/math/similarity.py`

**Correctness Properties:**
1. Symmetry: `cos(a, b) = cos(b, a)`
2. Self-Similarity: `cos(a, a) = 1.0` for non-zero a
3. Boundedness: `-1.0 ≤ cos(a, b) ≤ 1.0`
4. Zero Handling: `cos(0, x) = 0.0` (no NaN/Inf)
5. Normalization: `||normalize(a)||_2 = 1.0 ± 1e-12`

**Implementation:**
```python
# tests/proofs/test_similarity_math.py
class TestSimilarityMathematicalCorrectness:
    """Property-based tests for similarity mathematical correctness."""
    
    @given(vectors_strategy(), vectors_strategy())
    def test_symmetry(self, a: np.ndarray, b: np.ndarray) -> None:
        """A2.1: Cosine similarity is symmetric."""
        
    @given(nonzero_vectors_strategy())
    def test_self_similarity(self, a: np.ndarray) -> None:
        """A2.2: Self-similarity equals 1.0."""
```

#### A3: Predictor Mathematical Correctness

**Source Modules:** `somabrain/predictors/`, `somabrain/math/`

**Correctness Properties:**
1. Chebyshev Convergence: `||exp(-tA)x - chebyshev_approx(t, A, x)|| < ε`
2. Lanczos Eigenvalue Bounds: `λ_min(A) ≤ θ_i ≤ λ_max(A)`
3. Mahalanobis Non-Negativity: `d_M(x, μ, Σ) ≥ 0`
4. Uncertainty Monotonicity: `σ(t+1) ≥ σ(t)` for increasing horizon
5. Singular Covariance Handling: No failure when `det(Σ) ≈ 0`

#### A4: Salience Computation Correctness

**Source Module:** `somabrain/salience.py`

**Correctness Properties:**
1. Weighted Formula: `S = w_n * novelty + w_e * error`
2. Neuromodulator Modulation: Threshold adjustment follows modulation curves
3. FD Energy Bounds: `0 ≤ FD_energy ≤ 1`
4. Soft Salience Bounds: `0 < sigmoid(S) < 1`
5. Hysteresis Margin: State transitions require crossing threshold by margin

---

### Category B: Memory System Functional Proofs

#### B1: Working Memory Capacity and Eviction

**Test Strategy:** Integration tests against Redis

**Data Model:**
```python
@dataclass
class WMTestItem:
    """Test item for working memory."""
    content: str
    salience: float
    recency: float
    timestamp: float
    
@dataclass
class WMCapacityResult:
    """Result of WM capacity test."""
    items_stored: int
    items_evicted: int
    evicted_saliences: List[float]
    final_capacity: int
```

**Test Scenarios:**
1. Fill WM to capacity, verify lowest-salience eviction
2. Verify recency decay over time
3. Verify duplicate detection and update
4. Verify ranking by combined salience + recency

#### B2: Long-Term Memory Vector Search

**Test Strategy:** Integration tests against Milvus

**Golden Test Set:**
```python
GOLDEN_LTM_DATASET = [
    {"id": "g001", "text": "quantum computing breakthrough", "embedding": [...], "relevance": 1.0},
    {"id": "g002", "text": "machine learning optimization", "embedding": [...], "relevance": 0.9},
    # ... 100 golden items with known relevance scores
]
```

**Metrics:**
- Recall@10 ≥ 0.95 for identical query
- Precision@10 ≥ 0.8 for semantic query
- nDCG@10 ≥ 0.75 for ranked relevance

#### B3: Memory Round-Trip Integrity

**Test Strategy:** End-to-end through API

**Verification:**
1. Store payload via `/memory/remember`
2. Recall via `/memory/recall` with exact query
3. Compare payload fields byte-for-byte
4. Verify timestamp precision to milliseconds
5. Verify metadata preservation

#### B4: Retrieval Pipeline Fusion

**Test Strategy:** Integration tests with multiple sources

**Fusion Verification:**
1. Store items in both WM and LTM
2. Query and verify merged results without duplicates
3. Verify weighted score combination
4. Verify graceful degradation when one source fails

---

### Category C: Cognitive Function Proofs

#### C1: Neuromodulator State Management

**Test Strategy:** Integration tests via API

**State Verification:**
```python
@dataclass
class NeuromodulatorState:
    """Neuromodulator state snapshot."""
    dopamine: float  # [0.0, 1.0]
    serotonin: float  # [0.0, 1.0]
    noradrenaline: float  # [0.0, 1.0]
    acetylcholine: float  # [0.0, 1.0]
    
    def validate(self) -> bool:
        return all(0.0 <= v <= 1.0 for v in [
            self.dopamine, self.serotonin, 
            self.noradrenaline, self.acetylcholine
        ])
```

#### C2: Planning and Decision Making

**Test Strategy:** Integration tests via `/plan/suggest`

**Verification:**
1. Provide context memories
2. Invoke planner
3. Verify options ranked by expected utility
4. Verify timeout handling returns best-so-far
5. Verify empty result for no valid options

#### C3: Learning and Adaptation

**Test Strategy:** Integration tests with persistence verification

**Learning Rule Verification:**
1. Apply positive feedback, verify weight increase
2. Apply negative feedback, verify weight decrease
3. Verify constraint clamping
4. Verify tau annealing decay
5. Verify state persistence across restart

#### C4: Context and Attention

**Test Strategy:** Integration tests via context API

**Verification:**
1. Add context anchors, verify HRR binding
2. Verify context decay over time
3. Verify attention prioritization in retrieval
4. Verify context clear resets to neutral
5. Verify saturation pruning

---

### Category D: Multi-Tenant Isolation Proofs

#### D1: Memory Isolation

**Test Strategy:** Concurrent multi-tenant integration tests

**Isolation Matrix:**
```
Tenant A stores → Tenant B queries → MUST return empty
Tenant A stores → Tenant A queries → MUST return item
100 tenants concurrent → Zero cross-tenant leakage
```

**Implementation:**
```python
# tests/proofs/test_tenant_isolation.py
class TestMemoryIsolation:
    """Prove memory isolation between tenants."""
    
    @pytest.mark.parametrize("num_tenants", [2, 10, 100])
    def test_concurrent_tenant_isolation(self, num_tenants: int) -> None:
        """D1.5: Zero cross-tenant leakage with concurrent access."""
```

#### D2: State Isolation

**Test Strategy:** Concurrent state modification tests

**Isolation Verification:**
1. Modify tenant A neuromodulators → tenant B unchanged
2. Open tenant A circuit breaker → tenant B operations continue
3. Exhaust tenant A quota → tenant B has full quota
4. Run tenant A adaptation → tenant B weights unchanged
5. Fill tenant A WM → tenant B WM unaffected

---

### Category E: Infrastructure Requirements

#### E1: Docker Infrastructure Setup

**Test Strategy:** Docker-compose lifecycle tests

**Health Check Sequence:**
```python
HEALTH_CHECK_SEQUENCE = [
    ("somabrain_redis", "redis-cli ping", 30),
    ("somabrain_kafka", "kafka health", 90),
    ("somabrain_postgres", "pg_isready", 30),
    ("somabrain_milvus", "curl healthz", 180),
    ("somabrain_opa", "opa check", 30),
    ("somabrain_app", "curl /health", 60),
]
```

#### E2: Service Health Verification

**Test Strategy:** Health endpoint verification

**Health Response Schema:**
```python
@dataclass
class HealthResponse:
    """Expected health response structure."""
    status: str  # "healthy" | "degraded" | "unhealthy"
    components: Dict[str, ComponentHealth]
    
@dataclass
class ComponentHealth:
    """Component health status."""
    healthy: bool
    latency_ms: Optional[float]
    error: Optional[str]
```

#### E3: Resilience Under Failure

**Test Strategy:** Chaos engineering tests

**Failure Scenarios:**
1. Stop Redis → verify degraded WM functionality
2. Stop Kafka → verify outbox queuing
3. Slow Milvus (>5s) → verify timeout and WM-only results
4. Stop Postgres → verify retry with exponential backoff
5. Stop OPA → verify fail-closed (deny all)

---

### Category F: Circuit Breaker and Fault Tolerance Proofs

#### F1: Circuit Breaker State Machine

**Source Module:** `somabrain/infrastructure/circuit_breaker.py`

**State Machine:**
```
CLOSED --[5 failures]--> OPEN --[reset_timeout]--> HALF_OPEN
                           ^                           |
                           |                           |
                           +----[failure]----<---------+
                                                       |
CLOSED <---------[success]-----------------------------+
```

**Test Strategy:** Unit + Integration tests

**State Transition Verification:**
```python
# tests/proofs/test_circuit_breaker.py
class TestCircuitBreakerStateMachine:
    """Prove circuit breaker state machine correctness."""
    
    def test_closed_to_open_on_threshold(self) -> None:
        """F1.1: Circuit opens after 5 consecutive failures."""
        
    def test_open_fails_fast(self) -> None:
        """F1.2: Open circuit fails fast without backend call."""
        
    def test_open_to_half_open_on_timeout(self) -> None:
        """F1.3: Circuit transitions to HALF_OPEN after reset timeout."""
        
    def test_half_open_to_closed_on_success(self) -> None:
        """F1.4: HALF_OPEN transitions to CLOSED on success."""
        
    def test_half_open_to_open_on_failure(self) -> None:
        """F1.5: HALF_OPEN returns to OPEN on failure."""
```

#### F2: Per-Tenant Circuit Isolation

**Test Strategy:** Multi-tenant concurrent tests

**Isolation Verification:**
1. Fail tenant A backend → tenant A circuit opens
2. Verify tenant B requests still reach backend
3. Reset tenant A → tenant B state unchanged
4. Fail multiple tenants → independent recovery
5. Query circuit metrics → labeled by tenant_id

#### F3: Degraded Mode Operation

**Test Strategy:** Integration tests with backend failures

**Degraded Mode Verification:**
1. Open LTM circuit → recall returns WM-only with `degraded=true`
2. Memory backend unavailable → writes queue to outbox
3. Degraded mode active → `/health` reports degraded status
4. Backend recovers → queued writes replay without duplicates
5. Replay completes → pending count returns to zero

---

### Category G: Performance and Load Proofs

#### G1: Latency SLOs

**Test Strategy:** Load tests with percentile measurement

**SLO Targets:**
| Endpoint | p95 Target | p99 Target |
|----------|------------|------------|
| /memory/remember | 300ms | 500ms |
| /memory/recall | 400ms | 600ms |
| /plan/suggest | 1000ms | 1500ms |
| /health | 50ms | 100ms |
| /neuromodulators | 50ms | 100ms |

**Implementation:**
```python
# tests/proofs/test_latency_slo.py
class TestLatencySLOs:
    """Prove latency SLOs are met under load."""
    
    @pytest.mark.parametrize("endpoint,p95_target", [
        ("/memory/remember", 300),
        ("/memory/recall", 400),
        ("/plan/suggest", 1000),
    ])
    def test_endpoint_latency_slo(self, endpoint: str, p95_target: int) -> None:
        """G1: Verify p95 latency meets target."""
```

#### G2: Throughput Capacity

**Test Strategy:** Concurrent load tests

**Throughput Targets:**
- 100 concurrent users → >99% success rate
- 1000 memories in 10s → 100% persistence
- 500 recalls in 10s → 100% completion
- 30 minute sustained load → stable memory (no leaks)
- 2x spike load → recovery within 30s

#### G3: Recall Quality Under Scale

**Test Strategy:** Quality metrics at scale

**Quality Targets:**
| Corpus Size | Precision@10 | Recall@10 | nDCG@10 |
|-------------|--------------|-----------|---------|
| 10K items | ≥0.8 | ≥0.85 | ≥0.75 |
| 100K items | ≥0.7 | ≥0.7 | ≥0.7 |

---

## Data Models

### Test Fixtures

```python
# tests/fixtures/golden_datasets.py

@dataclass
class GoldenMemoryItem:
    """Golden test item with known relevance."""
    id: str
    content: str
    embedding: np.ndarray
    relevance_score: float
    memory_type: str
    metadata: Dict[str, Any]

@dataclass
class GoldenTestSet:
    """Collection of golden items for quality testing."""
    name: str
    items: List[GoldenMemoryItem]
    queries: List[GoldenQuery]
    expected_rankings: Dict[str, List[str]]

@dataclass
class GoldenQuery:
    """Query with expected results."""
    query_text: str
    expected_top_k: List[str]
    relevance_judgments: Dict[str, float]
```

### Test Results

```python
# tests/fixtures/test_results.py

@dataclass
class MathProofResult:
    """Result of mathematical proof test."""
    property_name: str
    passed: bool
    actual_value: float
    expected_bound: Tuple[float, float]
    samples_tested: int
    counterexample: Optional[Any]

@dataclass
class PerformanceResult:
    """Result of performance test."""
    endpoint: str
    samples: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    success_rate: float
    errors: List[str]

@dataclass
class IsolationResult:
    """Result of isolation test."""
    tenant_a: str
    tenant_b: str
    leaked_items: int
    total_items: int
    isolation_verified: bool
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Category A: Mathematical Core Properties

**Property 1: HRR Spectral Magnitude Bounded**
*For any* two vectors a and b, when bound using circular convolution, the spectral magnitude of the result SHALL remain bounded in [0.9, 1.1] for all frequency bins.
**Validates: Requirements A1.1**

**Property 2: Role Vector Unit Norm**
*For any* role token string, the generated role vector SHALL have unit norm (||role|| = 1.0 ± 1e-6).
**Validates: Requirements A1.2**

**Property 3: Binding Round-Trip Invertibility**
*For any* vectors a and b, performing bind then unbind SHALL recover the original with cosine similarity > 0.95: cos(unbind(bind(a, b), b), a) > 0.95.
**Validates: Requirements A1.3**

**Property 4: Superposition Recovery**
*For any* set of items bound with distinct roles and superposed, cleanup SHALL recover individual items with similarity > 0.8.
**Validates: Requirements A1.4**

**Property 5: Cosine Similarity Symmetry**
*For any* vectors a and b, cosine similarity SHALL be symmetric: cos(a, b) = cos(b, a).
**Validates: Requirements A2.1**

**Property 6: Self-Similarity Identity**
*For any* non-zero vector a, self-similarity SHALL equal 1.0: cos(a, a) = 1.0.
**Validates: Requirements A2.2**

**Property 7: Similarity Boundedness**
*For any* vectors a and b, cosine similarity SHALL be bounded: -1.0 ≤ cos(a, b) ≤ 1.0.
**Validates: Requirements A2.3**

**Property 8: Normalization Unit Norm**
*For any* vector a, after normalization the L2 norm SHALL equal 1.0 ± 1e-12.
**Validates: Requirements A2.5**

**Property 9: Mahalanobis Non-Negativity**
*For any* point x, mean μ, and covariance Σ, Mahalanobis distance SHALL be non-negative: d_M(x, μ, Σ) ≥ 0.
**Validates: Requirements A3.3**

**Property 10: Uncertainty Monotonicity**
*For any* prediction, as horizon increases, uncertainty SHALL grow monotonically: σ(t+1) ≥ σ(t).
**Validates: Requirements A3.4**

**Property 11: Salience Weighted Formula**
*For any* novelty and error signals with weights w_n and w_e, salience SHALL follow: S = w_n * novelty + w_e * error.
**Validates: Requirements A4.1**

**Property 12: Soft Salience Bounds**
*For any* salience value S, the sigmoid transformation SHALL produce values in (0, 1).
**Validates: Requirements A4.4**

### Category B: Memory System Properties

**Property 13: WM Lowest Salience Eviction**
*For any* working memory at capacity, when a new item is added, the system SHALL evict the item with lowest salience score.
**Validates: Requirements B1.1**

**Property 14: Recency Exponential Decay**
*For any* item in working memory, as time passes, recency scores SHALL decay according to exponential formula: R(t) = R(0) * exp(-λt).
**Validates: Requirements B1.3**

**Property 15: Duplicate Update Not Create**
*For any* duplicate content admitted to WM, the system SHALL update the existing entry, not create a duplicate.
**Validates: Requirements B1.4**

**Property 16: ANN Identity Retrieval**
*For any* vector stored in Milvus, ANN search with identical query SHALL return it as top-1 result.
**Validates: Requirements B2.1**

**Property 17: K-Retrieval Exactness**
*For any* k items requested, the system SHALL return exactly k items (or all if fewer exist).
**Validates: Requirements B2.2**

**Property 18: Memory Payload Round-Trip**
*For any* payload stored via /memory/remember, recalling by exact query SHALL return identical payload.
**Validates: Requirements B3.1**

**Property 19: Coordinate Determinism**
*For any* input, coordinate generation SHALL always produce the same coordinate.
**Validates: Requirements B3.2**

**Property 20: JSON Round-Trip Integrity**
*For any* JSON payload, serialization then deserialization SHALL preserve all fields exactly.
**Validates: Requirements B3.3**

**Property 21: Fusion Deduplication**
*For any* results from WM and LTM, fusion SHALL merge without duplicates.
**Validates: Requirements B4.1**

**Property 22: Fusion Weight Application**
*For any* configured fusion weights, final scores SHALL reflect weighted combination.
**Validates: Requirements B4.2**

### Category C: Cognitive Function Properties

**Property 23: Neuromodulator Range Validity**
*For any* neuromodulator query, all values SHALL be in valid range [0.0, 1.0].
**Validates: Requirements C1.5**

**Property 24: Options Utility Ranking**
*For any* Oak planner invocation, options SHALL be ranked by expected utility in descending order.
**Validates: Requirements C2.1**

**Property 25: Tie-Breaking Consistency**
*For any* options with equal utility, the system SHALL break ties consistently (same inputs = same result).
**Validates: Requirements C2.3**

**Property 26: Positive Feedback Weight Increase**
*For any* positive feedback with learning rate lr, gain g, and signal s, weights SHALL increase by delta = lr × g × s.
**Validates: Requirements C3.1**

**Property 27: Constraint Clamping**
*For any* adapted values with constraints [min, max], values SHALL remain within bounds.
**Validates: Requirements C3.3**

**Property 28: Tau Annealing Decay**
*For any* tau annealing with rate r, learning rate SHALL decay as: tau_{t+1} = tau_t × (1 - r).
**Validates: Requirements C3.4**

**Property 29: Adaptation State Persistence Round-Trip**
*For any* adaptation state, persisting then restoring SHALL produce exact original state.
**Validates: Requirements C3.5**

### Category D: Multi-Tenant Isolation Properties

**Property 30: Cross-Tenant Memory Isolation**
*For any* tenant A storing a memory, tenant B's recall SHALL NOT return it.
**Validates: Requirements D1.1, D1.2**

**Property 31: Namespace Query Scoping**
*For any* namespace-scoped query, results SHALL only include items from that namespace.
**Validates: Requirements D1.3**

**Property 32: Concurrent Tenant Zero Leakage**
*For any* number of tenants (up to 100) storing data concurrently, zero cross-tenant leakage SHALL occur.
**Validates: Requirements D1.5**

**Property 33: Neuromodulator State Isolation**
*For any* tenant A modifying neuromodulators, tenant B's state SHALL remain unchanged.
**Validates: Requirements D2.1**

**Property 34: Circuit Breaker Tenant Isolation**
*For any* tenant A's circuit breaker opening, tenant B's operations SHALL continue normally.
**Validates: Requirements D2.2**

### Category F: Circuit Breaker Properties

**Property 35: Circuit Opens on Threshold**
*For any* backend failing 5 consecutive times, circuit breaker SHALL transition to OPEN state.
**Validates: Requirements F1.1**

**Property 36: Open Circuit Fails Fast**
*For any* request when circuit is OPEN, the system SHALL fail-fast without attempting backend call.
**Validates: Requirements F1.2**

**Property 37: Reset Timeout Transitions to Half-Open**
*For any* OPEN circuit after reset timeout expires, circuit SHALL transition to HALF-OPEN state.
**Validates: Requirements F1.3**

**Property 38: Half-Open Success Closes Circuit**
*For any* HALF-OPEN circuit with successful request, circuit SHALL transition to CLOSED state.
**Validates: Requirements F1.4**

**Property 39: Half-Open Failure Reopens Circuit**
*For any* HALF-OPEN circuit with failed request, circuit SHALL return to OPEN state.
**Validates: Requirements F1.5**

**Property 40: Per-Tenant Circuit Independence**
*For any* tenant A's circuit state change, tenant B's circuit state SHALL be unchanged.
**Validates: Requirements F2.1, F2.2, F2.3**

**Property 41: Degraded Mode WM-Only Results**
*For any* recall when LTM circuit is OPEN, results SHALL be WM-only with degraded=true flag.
**Validates: Requirements F3.1**

**Property 42: Replay Without Duplicates**
*For any* backend recovery, queued writes SHALL replay without creating duplicates.
**Validates: Requirements F3.4**

### Category G: Performance Properties

**Property 43: Remember Latency SLO**
*For any* sample of /memory/remember requests, p95 latency SHALL be under 300ms.
**Validates: Requirements G1.1**

**Property 44: Recall Latency SLO**
*For any* sample of /memory/recall requests, p95 latency SHALL be under 400ms.
**Validates: Requirements G1.2**

**Property 45: Concurrent Success Rate**
*For any* 100 concurrent users sending requests, the system SHALL maintain >99% success rate.
**Validates: Requirements G2.1**

**Property 46: Memory Stability Under Load**
*For any* sustained load running for 30 minutes, memory usage SHALL remain stable (no leaks).
**Validates: Requirements G2.4**

**Property 47: Diversity Below Threshold**
*For any* top-10 results, pairwise similarity SHALL be below 0.9.
**Validates: Requirements G3.4**

---

## Testing Strategy

### Test Execution Order

1. **Phase 1: Mathematical Core (Category A)**
   - Run first - no backend dependencies
   - Property-based tests with Hypothesis
   - Must pass before proceeding

2. **Phase 2: Infrastructure Setup (Category E)**
   - Verify Docker infrastructure is healthy
   - All backends must be reachable
   - Health checks must pass

3. **Phase 3: Memory System (Category B)**
   - Depends on Phase 2
   - Integration tests against real backends
   - Verify data integrity

4. **Phase 4: Cognitive Functions (Category C)**
   - Depends on Phase 3
   - Integration tests via API
   - Verify cognitive behaviors

5. **Phase 5: Multi-Tenant Isolation (Category D)**
   - Depends on Phase 4
   - Concurrent multi-tenant tests
   - Zero-leakage verification

6. **Phase 6: Circuit Breaker (Category F)**
   - Depends on Phase 2
   - State machine verification
   - Fault tolerance tests

7. **Phase 7: Performance (Category G)**
   - Run last - requires stable system
   - Load tests with SLO verification
   - Quality metrics at scale

### Code Quality Gates

After each task implementation:

1. **Black** - Code formatting
   ```bash
   black tests/proofs/ somabrain/
   ```

2. **Ruff** - Linting
   ```bash
   ruff check tests/proofs/ somabrain/ --fix
   ```

3. **Pyright** - Type checking
   ```bash
   pyright tests/proofs/ somabrain/
   ```

### Test Markers

```python
# pytest markers for test categorization
pytest.mark.math_proof  # Category A
pytest.mark.memory_proof  # Category B
pytest.mark.cognitive_proof  # Category C
pytest.mark.isolation_proof  # Category D
pytest.mark.infrastructure  # Category E
pytest.mark.circuit_breaker  # Category F
pytest.mark.performance  # Category G
pytest.mark.requires_docker  # Requires Docker infrastructure
pytest.mark.slow  # Long-running tests
```

---

## File Structure

```
tests/
├── proofs/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── category_a/
│   │   ├── __init__.py
│   │   ├── test_hrr_math.py           # A1: HRR binding
│   │   ├── test_similarity_math.py    # A2: Vector similarity
│   │   ├── test_predictor_math.py     # A3: Predictor math
│   │   └── test_salience_math.py      # A4: Salience computation
│   ├── category_b/
│   │   ├── __init__.py
│   │   ├── test_wm_capacity.py        # B1: WM capacity
│   │   ├── test_ltm_search.py         # B2: LTM search
│   │   ├── test_roundtrip.py          # B3: Round-trip integrity
│   │   └── test_fusion.py             # B4: Retrieval fusion
│   ├── category_c/
│   │   ├── __init__.py
│   │   ├── test_neuromodulators.py    # C1: Neuromodulator state
│   │   ├── test_planning.py           # C2: Planning
│   │   ├── test_learning.py           # C3: Learning
│   │   └── test_context.py            # C4: Context
│   ├── category_d/
│   │   ├── __init__.py
│   │   ├── test_memory_isolation.py   # D1: Memory isolation
│   │   └── test_state_isolation.py    # D2: State isolation
│   ├── category_e/
│   │   ├── __init__.py
│   │   ├── test_docker_setup.py       # E1: Docker setup
│   │   ├── test_health_verification.py # E2: Health verification
│   │   └── test_resilience.py         # E3: Resilience
│   ├── category_f/
│   │   ├── __init__.py
│   │   ├── test_circuit_state_machine.py  # F1: State machine
│   │   ├── test_circuit_per_tenant.py     # F2: Per-tenant
│   │   └── test_degraded_mode.py          # F3: Degraded mode
│   └── category_g/
│       ├── __init__.py
│       ├── test_latency_slo.py        # G1: Latency SLOs
│       ├── test_throughput.py         # G2: Throughput
│       └── test_recall_quality.py     # G3: Recall quality
├── fixtures/
│   ├── __init__.py
│   ├── golden_datasets.py             # Golden test data
│   ├── test_results.py                # Result data models
│   └── docker_helpers.py              # Docker lifecycle helpers
└── utils/
    ├── __init__.py
    ├── metrics.py                     # Existing metrics utilities
    └── assertions.py                  # Custom assertions
```

---

## Dependencies

### Required Packages

```
# requirements-dev.txt additions
hypothesis>=6.100.0  # Property-based testing
pytest-asyncio>=0.23.0  # Async test support
pytest-timeout>=2.3.0  # Test timeouts
pytest-xdist>=3.5.0  # Parallel execution
locust>=2.24.0  # Load testing (optional)
```

### Docker Services Required

| Service | Port | Health Check |
|---------|------|--------------|
| somabrain_redis | 30100 | redis-cli ping |
| somabrain_kafka | 30102 | TCP check |
| somabrain_postgres | 30106 | pg_isready |
| somabrain_milvus | 30119 | curl healthz |
| somabrain_opa | 30104 | opa check |
| somabrain_app | 30101 | curl /health |

---

## Acceptance Criteria Traceability

| Requirement | Test File | Test Method |
|-------------|-----------|-------------|
| A1.1 | test_hrr_math.py | test_spectral_magnitude_bounded |
| A1.2 | test_hrr_math.py | test_role_unit_norm |
| A1.3 | test_hrr_math.py | test_bind_unbind_invertibility |
| A1.4 | test_hrr_math.py | test_superposition_recovery |
| A1.5 | test_hrr_math.py | test_wiener_filter_optimality |
| A2.1 | test_similarity_math.py | test_symmetry |
| A2.2 | test_similarity_math.py | test_self_similarity |
| A2.3 | test_similarity_math.py | test_boundedness |
| A2.4 | test_similarity_math.py | test_zero_handling |
| A2.5 | test_similarity_math.py | test_normalization |
| ... | ... | ... |

(Full traceability matrix in tasks.md)
