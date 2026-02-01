# Software Requirements Specification (SRS)
## SomaBrain Production Hardening & Architecture Perfection

**Document Version:** 1.0  
**Date:** December 8, 2025  
**Standard:** ISO/IEC/IEEE 29148:2018 (Structure Only)

---

## 1. Introduction

### 1.1 Purpose

This SRS defines the requirements for hardening SomaBrain to production-ready levels. The document establishes formal requirements using EARS patterns and INCOSE quality rules to ensure the cognitive AI system meets enterprise-grade reliability, security, and maintainability standards.

### 1.2 Scope

SomaBrain is a brain-inspired cognitive AI system implementing:
- Binary Hyperdimensional Computing (BHDC) for memory encoding
- Tiered memory architecture (Working Memory + Long-Term Memory)
- Adaptive learning with neuromodulator-driven weight updates
- Heat diffusion predictors using Chebyshev/Lanczos methods
- Multi-tenant isolation with per-tenant state management

### 1.3 Document Conventions

- **EARS Patterns:** All requirements follow Easy Approach to Requirements Syntax
- **INCOSE Rules:** All requirements comply with INCOSE semantic quality guidelines
- **VIBE Rules:** All implementations must follow VIBE Coding Rules (no mocks, no placeholders, no TODOs)

---

## 2. Glossary

- **BHDC:** Binary Hyperdimensional Computing - encoding method using sparse binary vectors
- **HRR:** Holographic Reduced Representations - vector symbolic architecture
- **WM:** Working Memory - fast, limited-capacity memory tier
- **LTM:** Long-Term Memory - persistent, high-capacity memory tier
- **SuperposedTrace:** Decayed HRR superposition with cleanup anchors
- **QuantumLayer:** BHDC-powered hyperdimensional operations module
- **UnifiedScorer:** Scoring system combining cosine, FD projection, and recency
- **Neuromodulators:** Simulated neurotransmitters (dopamine, serotonin, noradrenaline, acetylcholine)
- **AdaptationEngine:** Online weight update system for retrieval/utility parameters
- **TieredMemory:** Coordinated WM/LTM system with promotion policies
- **CleanupIndex:** Protocol for nearest-neighbor anchor search
- **MemoryClient:** Gateway to external memory HTTP service
- **Settings:** Centralized pydantic configuration class

---

## 3. Requirements

### Requirement 1: Mathematical Core Integrity

**User Story:** As a system operator, I want the mathematical core to maintain numerical stability and correctness invariants, so that cognitive computations produce reliable results.

#### Acceptance Criteria

1. WHEN the QuantumLayer performs a bind operation THEN the System SHALL verify that the spectral magnitude |H_k| remains within [0.9, 1.1] for all frequency bins
2. WHEN the QuantumLayer creates a unitary role THEN the System SHALL verify that the L2 norm equals 1.0 ± 1e-6
3. WHEN the QuantumLayer performs unbind(bind(a, b), b) THEN the System SHALL return a vector with cosine similarity ≥ 0.99 to the original vector a
4. WHEN normalize_array receives a zero-norm vector THEN the System SHALL return a deterministic baseline unit-vector (ones/sqrt(D))
5. WHEN compute_tiny_floor is called THEN the System SHALL return eps * sqrt(D) for the 'sqrt' strategy
6. WHEN the BHDCEncoder generates vectors THEN the System SHALL produce vectors with exactly the configured sparsity count of active elements
7. WHEN the PermutationBinder unbinds with zero-valued role components THEN the System SHALL raise a ValueError with a descriptive message

### Requirement 2: Memory System Reliability

**User Story:** As a developer, I want the memory system to reliably store and retrieve memories with proper tiering, so that cognitive context is preserved across sessions.

#### Acceptance Criteria

1. WHEN TieredMemory.remember() is called THEN the System SHALL store the item in Working Memory and evaluate promotion to LTM based on configured policy
2. WHEN TieredMemory.recall() is called THEN the System SHALL first query WM, then fall back to LTM if WM score is below threshold
3. WHEN SuperposedTrace.upsert() is called THEN the System SHALL apply exponential decay M_{t+1} = (1-η)M_t + η·bind(Rk, v)
4. WHEN the MemoryClient health check fails THEN the System SHALL raise a RuntimeError with specific failing components listed
5. WHEN the MemoryClient stores a memory THEN the System SHALL persist to the external HTTP service and return the coordinate tuple
6. WHEN the MemoryClient recalls memories THEN the System SHALL normalize response hits into RecallHit objects with payload, score, and coordinate
7. WHEN a memory is promoted from WM to LTM THEN the System SHALL verify the margin exceeds the configured promote_margin threshold

### Requirement 3: Configuration Centralization

**User Story:** As a DevOps engineer, I want all configuration to flow through a single Settings class, so that environment management is consistent and auditable.

#### Acceptance Criteria

1. WHEN any module requires configuration THEN the System SHALL import from common.config.settings
2. WHEN environment variables are read THEN the System SHALL strip inline comments before parsing
3. WHEN a required setting is missing THEN the System SHALL raise a RuntimeError with the setting name
4. WHEN Settings is instantiated THEN the System SHALL load values with precedence: env vars > .env file > config.yaml
5. WHEN boolean settings are parsed THEN the System SHALL accept "1", "true", "yes", "on" as truthy values (case-insensitive)

### Requirement 4: Learning & Adaptation Correctness

**User Story:** As a data scientist, I want the adaptation engine to correctly update weights based on feedback, so that the system learns from experience.

#### Acceptance Criteria

1. WHEN AdaptationEngine.apply_feedback() is called THEN the System SHALL compute delta = learning_rate × gain × signal for each parameter
2. WHEN a parameter update would exceed constraint bounds THEN the System SHALL clamp the value to [min, max]
3. WHEN tau annealing is enabled with mode "exp" THEN the System SHALL apply tau_{t+1} = tau_t × (1 - anneal_rate)
4. WHEN entropy cap is exceeded THEN the System SHALL raise a RuntimeError after incrementing the entropy_cap_events metric
5. WHEN per-tenant state persistence is enabled THEN the System SHALL serialize state to Redis with tenant-prefixed keys
6. WHEN AdaptationEngine.reset() is called THEN the System SHALL restore default weights and clear history

### Requirement 5: Observability & Health

**User Story:** As an SRE, I want comprehensive health checks and metrics, so that I can monitor system health and diagnose issues.

#### Acceptance Criteria

1. WHEN the /health endpoint is called THEN the System SHALL return status for Kafka, Postgres, Redis, OPA, and Memory backends
2. WHEN check_kafka() is called THEN the System SHALL perform a real metadata fetch using confluent-kafka Consumer
3. WHEN check_postgres() is called THEN the System SHALL execute "SELECT 1" using psycopg3
4. WHEN a scorer component produces a value THEN the System SHALL record it in the SCORER_COMPONENT histogram
5. WHEN neuromodulator state changes THEN the System SHALL update NEUROMOD_* gauges and increment NEUROMOD_UPDATE_COUNT

### Requirement 6: Security & Authentication

**User Story:** As a security engineer, I want proper authentication and authorization, so that the API is protected from unauthorized access.

#### Acceptance Criteria

1. WHEN auth_required is True THEN the System SHALL require a valid Bearer token on protected endpoints
2. WHEN a request lacks valid authentication THEN the System SHALL return HTTP 401 with a descriptive error
3. WHEN provenance_strict_deny is True THEN the System SHALL reject requests without valid X-Provenance headers
4. WHEN OPA policy evaluation fails THEN the System SHALL deny the request unless opa_allow_on_error is True
5. WHEN JWT validation is configured THEN the System SHALL verify tokens against the configured public key

### Requirement 7: Code Quality & VIBE Compliance

**User Story:** As a developer, I want the codebase to follow VIBE Coding Rules, so that the code is production-grade without mocks or placeholders.

#### Acceptance Criteria

1. WHEN any module is reviewed THEN the System SHALL contain zero TODO, FIXME, or placeholder comments
2. WHEN any module is reviewed THEN the System SHALL contain zero mock implementations or fake returns
3. WHEN any module is reviewed THEN the System SHALL contain zero hardcoded test values in production paths
4. WHEN any function handles errors THEN the System SHALL provide specific error messages with context
5. WHEN any module imports dependencies THEN the System SHALL handle import failures gracefully with clear error messages

### Requirement 8: API Surface Consistency

**User Story:** As an API consumer, I want consistent request/response formats, so that integration is predictable and reliable.

#### Acceptance Criteria

1. WHEN the /remember endpoint receives a valid payload THEN the System SHALL return the stored memory coordinate
2. WHEN the /recall endpoint receives a query THEN the System SHALL return normalized RecallHit objects with scores
3. WHEN any endpoint receives invalid input THEN the System SHALL return HTTP 422 with validation error details
4. WHEN any endpoint encounters an internal error THEN the System SHALL return HTTP 500 with a request_id for tracing
5. WHEN timestamps are provided THEN the System SHALL normalize them to Unix epoch seconds

### Requirement 9: Predictor Correctness

**User Story:** As a researcher, I want predictors to correctly apply heat diffusion methods, so that predictions are mathematically sound.

#### Acceptance Criteria

1. WHEN chebyshev_heat_apply() is called THEN the System SHALL approximate exp(-tA)x using Chebyshev polynomials of degree K
2. WHEN estimate_spectral_interval() is called THEN the System SHALL run m-step Lanczos to estimate eigenvalue bounds
3. WHEN lanczos_expv() is called THEN the System SHALL approximate exp(-tA)x using Krylov subspace projection
4. WHEN the spectral interval has b ≤ a THEN the System SHALL raise a ValueError

### Requirement 10: Multi-Tenancy Isolation

**User Story:** As a platform operator, I want proper tenant isolation, so that tenants cannot access each other's data or state.

#### Acceptance Criteria

1. WHEN a request includes tenant context THEN the System SHALL scope all memory operations to that tenant's namespace
2. WHEN PerTenantNeuromodulators.get_state() is called THEN the System SHALL return tenant-specific state or global defaults
3. WHEN AdaptationEngine persists state THEN the System SHALL use tenant-prefixed Redis keys
4. WHEN TieredMemory is instantiated THEN the System SHALL maintain separate WM/LTM instances per tenant

### Requirement 11: Serialization Round-Trip

**User Story:** As a developer, I want all serialization to be round-trip safe, so that data integrity is preserved.

#### Acceptance Criteria

1. WHEN a memory payload is serialized to JSON THEN the System SHALL produce valid JSON that deserializes to an equivalent object
2. WHEN RecallHit objects are serialized THEN the System SHALL preserve payload, score, and coordinate fields
3. WHEN NeuromodState is serialized THEN the System SHALL preserve all neurotransmitter values and timestamp
4. WHEN AdaptationEngine state is serialized THEN the System SHALL preserve retrieval weights, utility weights, and feedback count

### Requirement 12: Error Handling Consistency

**User Story:** As a developer, I want consistent error handling patterns, so that failures are predictable and debuggable.

#### Acceptance Criteria

1. WHEN a required external service is unavailable THEN the System SHALL raise RuntimeError with service name
2. WHEN a configuration value is invalid THEN the System SHALL raise ValueError with the invalid value and expected format
3. WHEN a vector dimension mismatch occurs THEN the System SHALL raise ValueError with actual and expected dimensions
4. WHEN an async operation times out THEN the System SHALL raise TimeoutError with the operation name and duration

---

## 4. Legacy Code Removal Targets

The following legacy patterns have been identified for removal:

### 4.1 Dead Code
- `link()` / `unlink()` methods in MemoryClient (already removed per existing spec)
- `payloads_for_coords()` method (already removed per existing spec)
- Unused import statements throughout codebase

### 4.2 VIBE Violations
- Any remaining `# TODO` comments
- Any remaining `# FIXME` comments
- Any `pass` statements that should have implementations
- Any `NotImplementedError` raises in production paths

### 4.3 Configuration Violations
- Direct `os.getenv()` calls (must use Settings)
- Hardcoded default values (must be in Settings)
- Duplicate configuration fields

### 4.4 Architecture Violations
- Circular imports
- God classes (>500 lines)
- Mixed concerns in single modules

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Memory recall latency: p99 < 100ms
- Memory store latency: p99 < 200ms
- Health check latency: p99 < 50ms

### 5.2 Reliability
- Service availability: 99.9%
- Data durability: 99.999%
- Graceful degradation when backends unavailable

### 5.3 Scalability
- Support 1000+ concurrent tenants
- Support 10GB+ memory per deployment
- Horizontal scaling via stateless API pods

---

## 6. Traceability Matrix

| Requirement | Design Section | Test Coverage |
|-------------|----------------|---------------|
| 1.1-1.7 | Mathematical Core | Property tests |
| 2.1-2.7 | Memory System | Integration tests |
| 3.1-3.5 | Configuration | Unit tests |
| 4.1-4.6 | Learning | Property tests |
| 5.1-5.5 | Observability | Integration tests |
| 6.1-6.5 | Security | Security tests |
| 7.1-7.5 | Code Quality | Static analysis |
| 8.1-8.5 | API Surface | Contract tests |
| 9.1-9.4 | Predictors | Property tests |
| 10.1-10.4 | Multi-Tenancy | Integration tests |
| 11.1-11.4 | Serialization | Round-trip tests |
| 12.1-12.4 | Error Handling | Unit tests |

---

## 7. Appendix: Current Architecture Analysis

### 7.1 Module Sizes (Lines of Code)
- `somabrain/app.py`: 4374 lines (NEEDS SPLITTING)
- `common/config/settings.py`: 1639 lines (NEEDS SPLITTING)
- `somabrain/metrics.py`: ~1700 lines (NEEDS MODULARIZATION)
- `somabrain/memory_client.py`: 2217 lines (ACCEPTABLE)

### 7.2 Identified Strengths
- Solid BHDC implementation with proper invariant verification
- Well-designed tiered memory with configurable policies
- Comprehensive Prometheus metrics
- Centralized Settings class with pydantic validation
- Circuit breaker patterns for external services

### 7.3 Identified Weaknesses
- `app.py` is a monolith that should be split into routers
- `settings.py` has duplicate field definitions
- Some modules still use direct `os.getenv()` calls
- Error handling inconsistency (RuntimeError vs ValueError)
- Missing property-based tests for mathematical invariants
