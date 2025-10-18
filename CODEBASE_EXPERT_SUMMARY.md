# SomaBrain Codebase Expert Summary

## Core Architecture

### 1. BHDC (Binary Hyperdimensional Computing) - The Math Foundation

**File**: `somabrain/math/bhdc_encoder.py`

- **BHDCEncoder**: Generates deterministic binary/sparse hypervectors
  - Supports `pm_one` mode: {-1, +1} values
  - Supports `zero_one` mode: {0, 1} centered
  - Uses blake2b hashing for deterministic seed generation
  - Caches vectors for performance
  - Sparsity control: active_count = sparsity * dim

- **PermutationBinder**: Core binding/unbinding operations
  - `bind(a, b)`: elementwise multiplication (a * b)
  - `unbind(c, b)`: elementwise division (c / b)
  - Perfectly invertible by construction
  - Optional Hadamard mixing via Walsh-Hadamard transform
  - No FFT required - pure elementwise operations

**Key Insight**: This is NOT FFT-based. It's pure elementwise multiplication/division, making it hardware-friendly and perfectly invertible.

### 2. Quantum Layer - High-Level BHDC Interface

**File**: `somabrain/quantum.py`

- **QuantumLayer**: Wraps BHDCEncoder + PermutationBinder
  - `bind(a, b)`: Binds two vectors, verifies spectral properties
  - `unbind(a, b)`: Unbinds, perfectly invertible
  - `superpose(*vectors)`: Adds vectors, renormalizes
  - `make_unitary_role(token)`: Creates deterministic orthogonal roles
  - `bind_unitary(a, role_token)`: Binds with named role
  - `cleanup(query, anchors)`: Nearest neighbor via cosine

- **Mathematical Verification**: Every operation emits metrics
  - `MathematicalMetrics.verify_spectral_property`: ||H_k|| ≈ 1
  - `MathematicalMetrics.verify_role_orthogonality`: cosine(role_i, role_j) ≈ 0
  - `MathematicalMetrics.verify_operation_correctness`: cosine(a, bind(a,b)) is low
  - `AdvancedMathematicalMetrics`: interference, energy conservation, frame properties

### 3. Governed Memory Traces

**File**: `somabrain/memory/superposed_trace.py`

- **SuperposedTrace**: Exponentially decayed HRR superposition
  ```python
  M_{t+1} = (1-η) * M_t + η * bind(R*k, v)
  ```
  - η (eta): decay/injection factor (0 < η ≤ 1)
  - R: optional orthogonal rotation matrix
  - Bounded interference as trace grows
  - Cleanup via nearest neighbor or pluggable ANN index

- **TraceConfig**:
  - `dim`: vector dimensionality
  - `eta`: exponential decay factor
  - `rotation_enabled`: apply orthogonal rotation to keys
  - `cleanup_topk`: number of anchors to evaluate

- **Key Methods**:
  - `upsert(anchor_id, key, value)`: Bind and update state
  - `recall(key)`: Unbind and cleanup
  - `recall_raw(key)`: Unbind without cleanup
  - `update_parameters(eta, cleanup_topk)`: Hot-reload config

### 4. Tiered Memory Hierarchy

**File**: `somabrain/memory/hierarchical.py`

- **TieredMemory**: Coordinates WM (working memory) and LTM (long-term memory)
  - Each tier is a SuperposedTrace instance
  - Hierarchical recall: WM first, fallback to LTM
  - Promotion policy: threshold + margin requirements
  - Configurable per-layer policies

- **LayerPolicy**:
  - `threshold`: minimum cleanup score to accept hit
  - `promote_margin`: margin requirement for promotion

- **RecallContext**: Result with layer, anchor_id, score, margin

### 5. Working Memory

**File**: `somabrain/wm.py`

- **WorkingMemory**: Fixed-capacity buffer with LRU eviction
  - Stores WMItem: (vector, payload, tick, admitted_at, cleanup_overlap)
  - `admit(vector, payload)`: Add item, enforce capacity
  - `recall(query_vec, top_k)`: Cosine similarity ranking
  - `novelty(query_vec)`: 1 - max_cosine
  - `salience(query_vec, reward)`: α*novelty + β*reward + γ*recency

- **Density-Aware Cleanup**: Uses cleanup_overlap to down-weight duplicates
  ```python
  density_factor = max(0.1, 1.0 - cleanup_overlap)
  adjusted_score = score * density_factor
  ```

**File**: `somabrain/mt_wm.py`

- **MultiTenantWM**: LRU-evicted tenant-specific working memories
  - OrderedDict for LRU tenant eviction
  - Per-tenant capacity limits
  - Automatic cleanup of inactive tenants

### 6. Unified Scoring

**File**: `somabrain/scoring.py`

- **UnifiedScorer**: Multi-component similarity
  ```python
  total = w_cosine * cosine(q, c) + 
          w_fd * fd_projection(q, c) + 
          w_recency * exp(-age/τ)
  ```
  - Weight clamping with metrics emission
  - FD subspace projection via FDSalienceSketch
  - Exponential recency decay

- **ScorerWeights**: (w_cosine, w_fd, w_recency)
- **Bounds**: (weight_min, weight_max) enforced via _clamp

### 7. FD Salience Sketch

**File**: `somabrain/salience.py`

- **FDSalienceSketch**: Frequent-Directions sketch for online covariance
  - Maintains low-rank approximation of covariance
  - `observe(vector)`: Stream vector, return (residual_ratio, capture_ratio)
  - `project(vector)`: Project into FD subspace
  - Exponential decay support
  - PSD verification

**File**: `somabrain/math/fd_rho.py`

- **FrequentDirections**: Core FD algorithm
  - `insert(v)`: Add vector to sketch
  - `_compress()`: SVD-based compression when full
  - `approx_cov()`: Return S^T S approximation

### 8. Memory Client - HTTP Gateway

**File**: `somabrain/memory_client.py` (MASSIVE - 2000+ lines)

- **MemoryClient**: Single gateway to external memory service
  - HTTP-first architecture (httpx)
  - Circuit breaker pattern
  - Outbox journaling for failed operations
  - Async/sync dual API

- **Core Operations**:
  - `remember(coord_key, payload)`: Store memory, return 3D coordinate
  - `recall(query, top_k, universe)`: Retrieve memories
  - `link(from_coord, to_coord, link_type, weight)`: Create graph edge
  - `links_from(start, type_filter, limit)`: Query neighbors
  - `k_hop(starts, depth, limit)`: Multi-hop traversal

- **Coordinate System**: Deterministic 3D coords via blake2b hash
  ```python
  coord = _stable_coord(f"{universe}::{coord_key}")
  # Returns (x, y, z) in [-1, 1]^3
  ```

- **Recall Pipeline**:
  1. HTTP POST to `/memories/search`
  2. Normalize hits (extract payload, score, coordinate)
  3. Filter by universe
  4. Filter by keyword (lexical matching)
  5. Deduplicate by identity
  6. Rescore with UnifiedScorer + recency + density
  7. Rank and return top_k

- **Recency Features**:
  ```python
  age_seconds = now - timestamp
  normalised = age_seconds / recency_time_scale
  damp_steps = log1p(normalised) * sharpness
  boost = max(floor, exp(-(normalised^sharpness)))
  ```

- **Density Factor**:
  ```python
  if margin >= target: return 1.0
  deficit = (target - margin) / target
  penalty = 1.0 - (weight * deficit)
  return max(floor, penalty)
  ```

### 9. Adaptive Learning

**File**: `somabrain/learning/adaptation.py`

- **AdaptationEngine**: Online parameter updates
  - Per-tenant state persistence to Redis (7-day TTL)
  - Dynamic learning rate via neuromodulators
  - Rollback support with history tracking
  - Constraint enforcement

- **Parameter Updates**:
  ```python
  if enable_dynamic_lr:
      dopamine = get_dopamine_level()
      lr = base_lr * (0.5 + dopamine)  # [0.5, 1.2]
  else:
      lr = base_lr * (1.0 + signal)
  
  delta = lr * signal
  alpha += delta              # Semantic weight
  gamma -= 0.5 * delta        # Temporal penalty
  lambda_ += delta            # Utility weight
  mu -= 0.25 * delta          # Cost factor
  nu -= 0.25 * delta          # Complexity factor
  ```

- **Coordinated Updates**: Parameters move together intentionally to maintain balance
- **Different Scaling**: Each parameter has different scaling factors
- **Redis Persistence**: State survives restarts

### 10. Autonomous Learning

**File**: `somabrain/autonomous/learning.py`

- **FeedbackCollector**: Tracks performance metrics
- **ParameterOptimizer**: Adjusts parameters based on trends
- **ExperimentManager**: A/B testing with Welch's t-test
  - `create_experiment`, `add_experiment_group`
  - `record_experiment_result`
  - `analyze_experiment`: Welch's t-test + Cohen's d
- **AutonomousLearner**: Coordinates all learning components

### 11. Memory Service

**File**: `somabrain/services/memory_service.py`

- **MemoryService**: Façade around MultiTenantMemory
  - Circuit breaker with failure tracking
  - Outbox processing for queued operations
  - Journal fallback (configurable)
  - Health checking

- **Circuit Breaker**:
  - Opens after `failure_threshold` consecutive errors
  - Resets after `reset_interval` seconds
  - Journals operations when open

### 12. Numerics Primitives

**File**: `somabrain/numerics.py`

- **compute_tiny_floor(dim, dtype, strategy)**:
  - `sqrt`: eps * sqrt(D) (default)
  - `linear`: eps * D
  - `absolute`: eps
  - Returns amplitude floor (L2 units)

- **normalize_array(x, axis, mode)**:
  - `legacy_zero`: zero vector for subtiny norms
  - `robust`: deterministic baseline unit vector
  - `strict`: raise on subtiny norms
  - Always enforces unit L2 norm

- **rfft_norm / irfft_norm**: Unitary FFT wrappers (norm='ortho')

### 13. Roles & Seeds

**File**: `somabrain/roles.py`

- **make_unitary_role(dim, seed)**: Creates unitary role vectors
  - Random phase spectrum: exp(1j * phase)
  - IRFFT to time domain
  - Renormalize to unit norm
  - Returns (time_domain, rfft_spectrum)

**File**: `somabrain/seed.py`

- **seed_to_uint64(seed)**: Deterministic seed conversion
  - None → 0
  - int → masked to 64 bits
  - str/bytes → blake2b hash → uint64
- **rng_from_seed(seed)**: Returns numpy Generator

### 14. Sinkhorn Transport

**File**: `somabrain/math/sinkhorn.py`

- **sinkhorn_log_stabilized**: Entropy-regularized optimal transport
  - Log-domain for numerical stability
  - Returns transport matrix P and error
  - Minimizes <P, C> - eps * H(P)

## Key Design Patterns

### 1. Deterministic Everything
- Seeds → blake2b → uint64
- Roles are reproducible from token strings
- Coordinates are stable hashes of keys
- No randomness in production paths

### 2. Metrics Everywhere
- MathematicalMetrics for invariants
- AdvancedMathematicalMetrics for diagnostics
- Prometheus counters/gauges/histograms
- Every operation emits telemetry

### 3. Graceful Degradation
- Circuit breaker for HTTP failures
- Outbox journaling for replay
- Configurable fallbacks
- Backend enforcement mode for strict operation

### 4. Multi-Tenancy
- Namespace isolation
- Per-tenant working memory
- Per-tenant adaptation state
- Redis TTL for automatic cleanup

### 5. Hot-Reload Support
- SuperposedTrace.update_parameters
- TieredMemory.configure
- AdaptationEngine parameter updates
- No restart required

## Critical Configuration

### Environment Variables
- `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`: Strict mode
- `SOMABRAIN_MEMORY_HTTP_ENDPOINT`: Memory service URL
- `SOMABRAIN_LEARNING_RATE_DYNAMIC`: Enable dopamine modulation
- `ALLOW_JOURNAL_FALLBACK`: Enable journaling
- `SOMABRAIN_HTTP_MAX_CONNS`: Connection pool size
- `SOMABRAIN_HTTP_RETRIES`: Retry count

### Config Parameters
- `w_cosine`, `w_fd`, `w_recency`: Scorer weights
- `weight_min`, `weight_max`: Weight bounds
- `recency_tau`: Exponential decay rate
- `eta`: SuperposedTrace decay factor
- `failure_threshold`: Circuit breaker threshold
- `reset_interval`: Circuit breaker reset time

## Production Readiness

### ✅ Production-Ready
- BHDC permutation binding
- SuperposedTrace with exponential decay
- MultiTenantWM with LRU eviction
- UnifiedScorer with three components
- Circuit breaker pattern
- Outbox journaling
- Comprehensive metrics
- Per-tenant state isolation

### 🚧 Needs Deployment
- TieredMemory wiring into FastAPI routes
- ANN cleanup indexes (FAISS/HNSW)
- ParameterSupervisor automation
- Config hot-reload dispatcher
- Journal-to-outbox migration script

## Mathematical Guarantees

1. **Spectral Property**: ||H_k|| ≈ 1 for all operations
2. **Role Orthogonality**: cosine(role_i, role_j) ≈ 0
3. **Binding Correctness**: cosine(a, bind(a,b)) is low
4. **Trace Normalization**: ||M|| = 1 after every update
5. **Energy Conservation**: ||bind(a,b)|| ≈ ||a|| * ||b||
6. **Perfect Invertibility**: unbind(bind(a,b), b) = a

## Performance Characteristics

- **BHDC Binding**: O(D) elementwise multiplication
- **Unbinding**: O(D) elementwise division
- **Cleanup**: O(K*D) for K anchors
- **Working Memory Recall**: O(N*D) for N items
- **FD Sketch**: O(ℓ²*D) for rank ℓ
- **Coordinate Hash**: O(1) blake2b

## Testing Strategy

- Unit tests for all math primitives
- Property tests for invariants
- Integration tests for memory flows
- Benchmarks for performance regression
- Golden data for reproducibility

This codebase is a production-grade cognitive platform with solid mathematical foundations and proper engineering practices.
