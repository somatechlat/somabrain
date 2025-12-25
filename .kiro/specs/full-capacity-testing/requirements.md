# Requirements Document - SomaBrain Full Capacity Real-World Testing

## Introduction

This specification defines REAL WORLD testing requirements that PROVE the mathematical correctness and functional capabilities of SomaBrain's cognitive system. All tests run against REAL Docker infrastructure with REAL data - NO mocks, NO stubs, NO fake implementations. The goal is to validate that the brain ACTUALLY WORKS as designed.

## Glossary

- **SomaBrain**: The cognitive AI system under test
- **HRR (Holographic Reduced Representation)**: Mathematical binding operation using circular convolution in frequency domain
- **Quantum Layer**: HRR implementation providing bind/unbind operations
- **Working Memory (WM)**: Capacity-limited fast storage with salience-based eviction
- **Long-Term Memory (LTM)**: Persistent vector storage via Milvus with ANN search
- **Neuromodulators**: Four chemical signals (dopamine, serotonin, noradrenaline, acetylcholine) that modulate cognition
- **Salience**: Computed importance score combining novelty, error, and neuromodulator state
- **Oak Planner**: Option-Action-Knowledge system for decision making
- **Retrieval Pipeline**: Unified recall combining WM, LTM, graph, and fusion
- **Adaptation Engine**: Online learning system with tau annealing and constraint clamping

---

## CATEGORY A: MATHEMATICAL CORE PROOFS

### Requirement A1: HRR Binding Mathematical Correctness

**User Story:** As a neuroscientist, I want to verify HRR binding preserves mathematical properties, so that I can trust the representational system.

#### Acceptance Criteria

1. WHEN two vectors are bound using circular convolution THEN the spectral magnitude SHALL remain bounded in [0.9, 1.1] for all frequency bins
2. WHEN a role vector is generated THEN the system SHALL produce a unit-norm vector (||role|| = 1.0 ± 1e-6)
3. WHEN bind then unbind is performed THEN cosine similarity between original and recovered SHALL exceed 0.95
4. WHEN multiple bindings are superposed THEN the system SHALL recover individual items with similarity > 0.8
5. WHEN the Wiener filter is applied for unbinding THEN the reconstruction error SHALL be minimized

### Requirement A2: Vector Similarity Mathematical Correctness

**User Story:** As a mathematician, I want to verify similarity computations are correct, so that I can trust retrieval ranking.

#### Acceptance Criteria

1. WHEN cosine similarity is computed THEN the result SHALL satisfy symmetry: cos(a,b) = cos(b,a)
2. WHEN self-similarity is computed THEN the result SHALL equal 1.0 for non-zero vectors
3. WHEN similarity is computed THEN the result SHALL be bounded in [-1.0, 1.0]
4. WHEN zero vectors are involved THEN the system SHALL return 0.0 without NaN or infinity
5. WHEN vectors are normalized THEN the L2 norm SHALL equal 1.0 ± 1e-12

### Requirement A3: Predictor Mathematical Correctness

**User Story:** As a control theorist, I want to verify predictors compute correctly, so that I can trust forecasting.

#### Acceptance Criteria

1. WHEN Chebyshev heat approximation is computed THEN exp(-tA)x SHALL converge to exact solution within tolerance
2. WHEN Lanczos spectral bounds are computed THEN eigenvalue estimates SHALL contain true eigenvalues
3. WHEN Mahalanobis distance is computed THEN the result SHALL be non-negative and scale-invariant
4. WHEN prediction horizon increases THEN uncertainty SHALL grow monotonically
5. WHEN covariance matrix is singular THEN the system SHALL use regularization without failure

### Requirement A4: Salience Computation Correctness

**User Story:** As a cognitive scientist, I want to verify salience scoring is correct, so that I can trust attention allocation.

#### Acceptance Criteria

1. WHEN novelty and error signals are combined THEN salience SHALL follow the weighted formula: S = w_n * novelty + w_e * error
2. WHEN neuromodulators are elevated THEN salience thresholds SHALL adjust according to modulation curves
3. WHEN FD (Fractal Dimension) energy is computed THEN the result SHALL capture signal complexity
4. WHEN soft salience is enabled THEN the sigmoid transformation SHALL produce values in (0, 1)
5. WHEN hysteresis is applied THEN state transitions SHALL require crossing threshold by margin

---

## CATEGORY B: MEMORY SYSTEM FUNCTIONAL PROOFS

### Requirement B1: Working Memory Capacity and Eviction

**User Story:** As a cognitive architect, I want to verify WM behaves like biological working memory, so that I can trust capacity limits.

#### Acceptance Criteria

1. WHEN WM reaches capacity THEN the system SHALL evict the item with lowest salience score
2. WHEN an item is admitted to WM THEN recency score SHALL be set to maximum
3. WHEN time passes THEN recency scores SHALL decay according to exponential formula
4. WHEN duplicate content is admitted THEN the system SHALL update existing entry, not create duplicate
5. WHEN WM is queried THEN results SHALL be ranked by combined salience and recency

### Requirement B2: Long-Term Memory Vector Search

**User Story:** As a search engineer, I want to verify LTM retrieval is accurate, so that I can trust recall quality.

#### Acceptance Criteria

1. WHEN a vector is stored in Milvus THEN ANN search SHALL return it as top-1 for identical query
2. WHEN k items are requested THEN the system SHALL return exactly k items (or all if fewer exist)
3. WHEN similarity threshold is set THEN results below threshold SHALL be excluded
4. WHEN index is rebuilt THEN recall@10 SHALL remain above 0.95 for golden test set
5. WHEN vectors are normalized before storage THEN search distances SHALL be valid cosine similarities

### Requirement B3: Memory Round-Trip Integrity

**User Story:** As a data engineer, I want to verify memory operations preserve data, so that I can trust persistence.

#### Acceptance Criteria

1. WHEN a payload is stored via /memory/remember THEN recalling by exact query SHALL return identical payload
2. WHEN coordinates are generated THEN the same input SHALL always produce the same coordinate
3. WHEN JSON serialization occurs THEN all fields SHALL survive round-trip exactly
4. WHEN timestamps are stored THEN they SHALL be preserved with millisecond precision
5. WHEN metadata is attached THEN it SHALL be retrievable without modification

### Requirement B4: Retrieval Pipeline Fusion

**User Story:** As a retrieval engineer, I want to verify fusion combines sources correctly, so that I can trust hybrid search.

#### Acceptance Criteria

1. WHEN WM and LTM both return results THEN fusion SHALL merge without duplicates
2. WHEN fusion weights are configured THEN final scores SHALL reflect weighted combination
3. WHEN one source fails THEN the system SHALL return results from healthy sources
4. WHEN graph retrieval is enabled THEN linked items SHALL boost relevance scores
5. WHEN diversity reranking is applied THEN results SHALL maximize coverage of semantic space

---

## CATEGORY C: COGNITIVE FUNCTION PROOFS

### Requirement C1: Neuromodulator State Management

**User Story:** As a neuroscientist, I want to verify neuromodulators behave biologically, so that I can trust modulation effects.

#### Acceptance Criteria

1. WHEN dopamine is elevated THEN reward sensitivity SHALL increase in planning
2. WHEN serotonin is elevated THEN exploration-exploitation balance SHALL shift toward exploitation
3. WHEN noradrenaline is elevated THEN attention focus SHALL narrow
4. WHEN acetylcholine is elevated THEN learning rate SHALL increase
5. WHEN all neuromodulators are queried THEN values SHALL be in valid range [0.0, 1.0]

### Requirement C2: Planning and Decision Making

**User Story:** As a decision theorist, I want to verify planning produces rational choices, so that I can trust recommendations.

#### Acceptance Criteria

1. WHEN Oak planner is invoked THEN options SHALL be ranked by expected utility
2. WHEN context memories are provided THEN plan relevance SHALL increase measurably
3. WHEN multiple options have equal utility THEN the system SHALL break ties consistently
4. WHEN planning timeout is reached THEN the system SHALL return best-so-far result
5. WHEN no valid options exist THEN the system SHALL return empty result, not error

### Requirement C3: Learning and Adaptation

**User Story:** As a learning theorist, I want to verify adaptation follows learning rules, so that I can trust improvement.

#### Acceptance Criteria

1. WHEN positive feedback is provided THEN weights SHALL increase by delta = lr × gain × signal
2. WHEN negative feedback is provided THEN weights SHALL decrease proportionally
3. WHEN constraints are defined THEN adapted values SHALL remain within [min, max] bounds
4. WHEN tau annealing is enabled THEN learning rate SHALL decay as tau_{t+1} = tau_t × (1 - rate)
5. WHEN adaptation state is persisted THEN restart SHALL restore exact state

### Requirement C4: Context and Attention

**User Story:** As an attention researcher, I want to verify context management works, so that I can trust focus.

#### Acceptance Criteria

1. WHEN context anchors are added THEN HRR binding SHALL create composite representation
2. WHEN context decays THEN older anchors SHALL have reduced influence
3. WHEN attention is focused THEN retrieval SHALL prioritize attended items
4. WHEN context is cleared THEN the system SHALL reset to neutral state
5. WHEN context saturation is reached THEN oldest anchors SHALL be pruned

---

## CATEGORY D: MULTI-TENANT ISOLATION PROOFS

### Requirement D1: Memory Isolation

**User Story:** As a security engineer, I want to verify tenant data is isolated, so that I can trust data privacy.

#### Acceptance Criteria

1. WHEN tenant A stores a memory THEN tenant B's recall SHALL NOT return it
2. WHEN tenant A queries with tenant B's content THEN results SHALL be empty
3. WHEN namespace is specified THEN queries SHALL be scoped to that namespace only
4. WHEN tenant header is missing THEN the system SHALL use default tenant, not leak data
5. WHEN 100 tenants store data concurrently THEN zero cross-tenant leakage SHALL occur

### Requirement D2: State Isolation

**User Story:** As a platform architect, I want to verify tenant state is isolated, so that I can trust independence.

#### Acceptance Criteria

1. WHEN tenant A modifies neuromodulators THEN tenant B's state SHALL remain unchanged
2. WHEN tenant A's circuit breaker opens THEN tenant B's operations SHALL continue normally
3. WHEN tenant A exhausts quota THEN tenant B SHALL still have full quota
4. WHEN tenant A's adaptation runs THEN tenant B's weights SHALL not change
5. WHEN tenant A's WM fills THEN tenant B's WM capacity SHALL be unaffected

---

## CATEGORY E: INFRASTRUCTURE REQUIREMENTS

### Requirement E1: Docker Infrastructure Setup

**User Story:** As a DevOps engineer, I want complete Docker infrastructure, so that I can run real tests.

#### Acceptance Criteria

1. WHEN docker-compose up is run THEN all services SHALL start and become healthy within 5 minutes
2. WHEN Redis container starts THEN it SHALL be accessible on configured port with persistence enabled
3. WHEN Kafka container starts THEN it SHALL create required topics automatically
4. WHEN Milvus container starts THEN it SHALL be ready for vector operations with etcd and minio
5. WHEN Postgres container starts THEN migrations SHALL apply successfully

### Requirement E2: Service Health Verification

**User Story:** As an SRE, I want to verify all services are healthy, so that I can trust test environment.

#### Acceptance Criteria

1. WHEN /health is called THEN the response SHALL include status for Redis, Kafka, Postgres, Milvus, OPA
2. WHEN any backend is unhealthy THEN health endpoint SHALL report degraded status
3. WHEN Prometheus scrapes /metrics THEN all expected metrics SHALL be present
4. WHEN Jaeger receives traces THEN spans SHALL show complete request flow
5. WHEN OPA is queried THEN policy decisions SHALL be logged

### Requirement E3: Resilience Under Failure

**User Story:** As a reliability engineer, I want to verify graceful degradation, so that I can trust fault tolerance.

#### Acceptance Criteria

1. WHEN Redis becomes unavailable THEN the system SHALL continue with degraded WM functionality
2. WHEN Kafka is unreachable THEN outbox SHALL queue events locally for later replay
3. WHEN Milvus is slow (>5s) THEN the system SHALL timeout and return WM-only results
4. WHEN Postgres connection fails THEN the system SHALL retry with exponential backoff
5. WHEN OPA is unavailable THEN the system SHALL fail-closed (deny all)

---

## CATEGORY F: CIRCUIT BREAKER AND FAULT TOLERANCE PROOFS

### Requirement F1: Circuit Breaker State Machine

**User Story:** As a reliability engineer, I want to verify circuit breaker behavior, so that I can trust fault isolation.

#### Acceptance Criteria

1. WHEN backend fails 5 consecutive times THEN circuit breaker SHALL transition to OPEN state
2. WHEN circuit is OPEN THEN requests SHALL fail-fast without attempting backend call
3. WHEN reset timeout expires THEN circuit SHALL transition to HALF-OPEN state
4. WHEN HALF-OPEN request succeeds THEN circuit SHALL transition to CLOSED state
5. WHEN HALF-OPEN request fails THEN circuit SHALL return to OPEN state

### Requirement F2: Per-Tenant Circuit Isolation

**User Story:** As a platform architect, I want per-tenant circuit breakers, so that one tenant's failures don't affect others.

#### Acceptance Criteria

1. WHEN tenant A's backend fails THEN tenant A's circuit SHALL open independently
2. WHEN tenant A's circuit is OPEN THEN tenant B's requests SHALL still reach backend
3. WHEN tenant A's circuit resets THEN tenant B's circuit state SHALL be unchanged
4. WHEN multiple tenants fail simultaneously THEN each SHALL have independent recovery
5. WHEN circuit state is queried THEN metrics SHALL be labeled by tenant_id

### Requirement F3: Degraded Mode Operation

**User Story:** As an operator, I want the system to degrade gracefully, so that partial functionality remains available.

#### Acceptance Criteria

1. WHEN LTM circuit is OPEN THEN recall SHALL return WM-only results with degraded=true flag
2. WHEN memory backend is unavailable THEN writes SHALL queue to outbox for replay
3. WHEN degraded mode is active THEN /health SHALL report degraded status
4. WHEN backend recovers THEN queued writes SHALL replay without duplicates
5. WHEN replay completes THEN pending count SHALL return to zero

---

## CATEGORY G: PERFORMANCE AND LOAD PROOFS

### Requirement G1: Latency SLOs

**User Story:** As a product owner, I want to verify latency meets targets, so that I can guarantee UX.

#### Acceptance Criteria

1. WHEN measuring /memory/remember latency THEN p95 SHALL be under 300ms
2. WHEN measuring /memory/recall latency THEN p95 SHALL be under 400ms
3. WHEN measuring /plan/suggest latency THEN p95 SHALL be under 1000ms
4. WHEN measuring /health latency THEN p99 SHALL be under 100ms
5. WHEN measuring /neuromodulators latency THEN p95 SHALL be under 50ms

### Requirement G2: Throughput Capacity

**User Story:** As a capacity planner, I want to verify throughput limits, so that I can plan infrastructure.

#### Acceptance Criteria

1. WHEN 100 concurrent users send requests THEN the system SHALL maintain >99% success rate
2. WHEN 1000 memories are stored in 10 seconds THEN all SHALL persist without loss
3. WHEN 500 recall requests are sent in 10 seconds THEN all SHALL complete successfully
4. WHEN sustained load runs for 30 minutes THEN memory usage SHALL remain stable (no leaks)
5. WHEN spike load doubles baseline THEN the system SHALL recover within 30 seconds

### Requirement G3: Recall Quality Under Scale

**User Story:** As a search quality engineer, I want to verify recall quality at scale, so that I can trust relevance.

#### Acceptance Criteria

1. WHEN corpus contains 10K items THEN precision@10 SHALL exceed 0.8 on golden test set
2. WHEN corpus contains 100K items THEN recall@10 SHALL exceed 0.7 on golden test set
3. WHEN nDCG@10 is measured THEN score SHALL exceed 0.75 on labeled relevance data
4. WHEN diversity is measured THEN pairwise similarity of top-10 SHALL be below 0.9
5. WHEN freshness is measured THEN recent items SHALL rank higher for recency-weighted queries
