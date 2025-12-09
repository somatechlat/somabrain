# Implementation Plan: SomaBrain Production Hardening

## Overview
This plan refactors SomaBrain to production-ready levels following VIBE Coding Rules and international standards. All tests run against REAL infrastructure - no mocks.

---

## Phase 1: Critical Architecture Refactoring

- [x] 1. Refactor app.py monolith (4373 lines → modular architecture)
  - [x] 1.1 Create routers directory structure
    - Create `somabrain/routers/__init__.py`
    - Create router modules for each endpoint group
    - _Requirements: 7.1, 7.3, 7.4_
  
  - [x] 1.2 Extract admin router (13 endpoints)
    - Move `/admin/services/*`, `/admin/outbox/*`, `/admin/quotas/*` endpoints
    - Move `_admin_guard_dep` dependency
    - _Requirements: 8.1, 8.3_
  
  - [x] 1.3 Extract health router (5 endpoints)
    - Move `/health`, `/healthz`, `/metrics`, `/diagnostics`, `/health/*` endpoints
    - _Requirements: 5.1, 8.1_
  
  - [x] 1.4 Extract memory router (4 endpoints)
    - Move `/recall`, `/remember`, `/delete`, `/recall/delete` endpoints
    - Move `_score_memory_candidate`, `_apply_diversity_reranking` functions
    - _Requirements: 2.1, 2.2, 8.1, 8.2_
  
  - [x] 1.5 Extract neuromodulator router (2 endpoints)
    - Move `/neuromodulators` GET and POST endpoints
    - _Requirements: 8.1_
  
  - [x] 1.6 Extract middleware modules
    - Move `CognitiveMiddleware` to `somabrain/middleware/cognitive.py`
    - Move `SecurityMiddleware` to `somabrain/middleware/security.py`
    - Move `SimpleOPAEngine` to `somabrain/middleware/opa.py`
    - _Requirements: 6.1, 6.3, 7.3_
  
  - [x] 1.7 Extract core modules
    - Move `CognitiveErrorHandler` to `somabrain/core/error_handler.py`
    - Move `CognitiveInputValidator` to `somabrain/core/validation.py`
    - Move `setup_logging` to `somabrain/core/logging_setup.py`
    - Move scoring functions to `somabrain/core/scoring.py`
    - _Requirements: 7.3, 12.1, 12.2_
  
  - [x] 1.8 Extract brain core classes
    - Move `UnifiedBrainCore` to `somabrain/brain/unified_core.py`
    - Move `AutoScalingFractalIntelligence` to `somabrain/brain/autoscaling.py`
    - Move `ComplexityDetector` to `somabrain/brain/complexity.py`
    - _Requirements: 7.3_
  
  - [x] 1.9 Update app.py to import and wire routers
    - Import all routers
    - Register routers with FastAPI app
    - Keep only startup/shutdown handlers and middleware registration
    - Target: <300 lines
    - _Requirements: 7.3, 7.4_

- [x] 2. Checkpoint - Verify app refactoring
  - All router modules compile successfully
  - Unit tests pass
  - Settings tests pass

---

## Phase 2: Configuration Refactoring

- [x] 3. Refactor settings.py (1638 lines → modular)
  - [x] 3.1 Create settings module structure
    - Created `common/config/settings/` directory
    - Created `__init__.py` with unified Settings export
    - _Requirements: 3.1, 3.4_
  
  - [x] 3.2 Extract infrastructure settings
    - Moved Redis, Kafka, Postgres, Milvus settings
    - Created `common/config/settings/infra.py`
    - _Requirements: 3.1_
  
  - [x] 3.3 Extract memory settings
    - Moved memory HTTP, weighting, degradation settings
    - Created `common/config/settings/memory.py`
    - _Requirements: 3.1_
  
  - [x] 3.4 Extract learning settings
    - Moved adaptation, tau, entropy settings
    - Created `common/config/settings/learning.py`
    - _Requirements: 3.1, 4.1_
  
  - [x] 3.5 Extract auth settings
    - Moved JWT, OPA, provenance settings
    - Created `common/config/settings/auth.py`
    - _Requirements: 3.1, 6.1_
  
  - [x] 3.6 Extract Oak settings
    - Moved Oak/ROAMDP settings
    - Created `common/config/settings/oak.py`
    - _Requirements: 3.1_

- [x] 3.7 Write property test for Settings parsing
  - **Property 9: Settings Comment Stripping** - IMPLEMENTED
  - **Property 10: Settings Boolean Parsing** - IMPLEMENTED
  - **Validates: Requirements 3.2, 3.5**
  - Created `tests/property/test_settings_properties.py`

- [x] 4. Checkpoint - Verify settings refactoring
  - All 38 tests pass (6 settings defaults + 32 property tests)

---

## Phase 3: Metrics Refactoring

- [x] 5. Refactor metrics.py (1698 lines → modular)
  - [x] 5.1 Create metrics module structure
    - Created `somabrain/metrics/` directory
    - Created `__init__.py` with all metric exports
    - Renamed original to `somabrain/metrics_original.py`
    - _Requirements: 5.4, 5.5_
  
  - [x] 5.2-5.5 Metrics organization
    - All metrics re-exported from package `__init__.py`
    - Backward compatibility maintained via star import
    - Original file preserved as `metrics_original.py`
    - _Requirements: 5.4, 5.5_

- [x] 6. Checkpoint - Verify metrics refactoring
  - All unit tests pass
  - Settings tests pass
  - Metrics import correctly from new package

---

## Phase 4: Mathematical Core Property Tests (REAL INFRA)

- [ ] 7. Implement mathematical core property tests
  - [ ] 7.1 Write property test for bind spectral invariant
    - **Property 1: Bind Spectral Invariant**
    - Test against real QuantumLayer with random vectors
    - Verify |H_k| ∈ [0.9, 1.1] for all frequency bins
    - **Validates: Requirements 1.1**
  
  - [ ] 7.2 Write property test for unitary role norm
    - **Property 2: Unitary Role Norm**
    - Test against real QuantumLayer with random role tokens
    - Verify ||role|| = 1.0 ± 1e-6
    - **Validates: Requirements 1.2**
  
  - [ ] 7.3 Write property test for binding round-trip
    - **Property 3: Binding Round-Trip**
    - Test unbind(bind(a, b), b) ≈ a
    - Verify cosine similarity ≥ 0.99
    - **Validates: Requirements 1.3**
  
  - [ ] 7.4 Write property test for tiny floor formula
    - **Property 4: Tiny Floor Formula**
    - Test compute_tiny_floor returns eps × sqrt(D)
    - **Validates: Requirements 1.5**
  
  - [ ] 7.5 Write property test for BHDC sparsity
    - **Property 5: BHDC Sparsity Count**
    - Test BHDCEncoder produces correct sparsity
    - **Validates: Requirements 1.6**

- [ ] 8. Checkpoint - Verify mathematical property tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 5: Memory System Integration Tests (REAL INFRA)

- [ ] 9. Implement memory system integration tests against REAL backends
  - [ ] 9.1 Write integration test for TieredMemory recall order
    - **Property 6: Tiered Memory Recall Order**
    - Test against REAL SuperposedTrace instances
    - Verify WM → LTM fallback behavior
    - **Validates: Requirements 2.2**
  
  - [ ] 9.2 Write integration test for SuperposedTrace decay
    - **Property 7: SuperposedTrace Decay Formula**
    - Test state update formula: (1-η)M + η·binding
    - **Validates: Requirements 2.3**
  
  - [ ] 9.3 Write integration test for memory promotion
    - **Property 8: Memory Promotion Margin**
    - Test promotion only when margin > threshold
    - **Validates: Requirements 2.7**
  
  - [ ] 9.4 Write integration test for MemoryClient against REAL memory service
    - Test remember/recall against running memory HTTP service
    - Verify RecallHit normalization
    - **Property 20: RecallHit Normalization**
    - **Validates: Requirements 2.5, 2.6**
  
  - [ ] 9.5 Write integration test for MemoryClient health check
    - Test against REAL memory service health endpoint
    - Verify component flags (kv_store, vector_store, graph_store)
    - **Validates: Requirements 2.4**

- [ ] 10. Checkpoint - Verify memory integration tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 6: Learning & Adaptation Property Tests

- [ ] 11. Implement learning property tests
  - [ ] 11.1 Write property test for adaptation delta formula
    - **Property 11: Adaptation Delta Formula**
    - Test delta = lr × gain × signal
    - **Validates: Requirements 4.1**
  
  - [ ] 11.2 Write property test for constraint clamping
    - **Property 12: Adaptation Constraint Clamping**
    - Test values clamped to [min, max]
    - **Validates: Requirements 4.2**
  
  - [ ] 11.3 Write property test for tau annealing
    - **Property 13: Tau Exponential Annealing**
    - Test tau_{t+1} = tau_t × (1 - rate)
    - **Validates: Requirements 4.3**
  
  - [ ] 11.4 Write property test for adaptation reset
    - **Property 14: Adaptation Reset**
    - Test reset restores defaults
    - **Validates: Requirements 4.6**

- [ ] 12. Checkpoint - Verify learning property tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 7: Infrastructure Integration Tests (REAL BACKENDS)

- [ ] 13. Implement infrastructure integration tests against REAL services
  - [ ] 13.1 Write integration test for Redis connectivity
    - Test against REAL Redis instance (SOMABRAIN_REDIS_URL)
    - Test AdaptationEngine state persistence
    - Test per-tenant state isolation
    - _Requirements: 4.5, 10.3_
  
  - [ ] 13.2 Write integration test for Kafka connectivity
    - Test against REAL Kafka cluster (SOMABRAIN_KAFKA_URL)
    - Test check_kafka() health check
    - Test metadata fetch
    - _Requirements: 5.2_
  
  - [ ] 13.3 Write integration test for Postgres connectivity
    - Test against REAL Postgres (SOMABRAIN_POSTGRES_DSN)
    - Test check_postgres() health check
    - Test SELECT 1 execution
    - _Requirements: 5.3_
  
  - [ ] 13.4 Write integration test for Milvus connectivity
    - Test against REAL Milvus (MILVUS_HOST:MILVUS_PORT)
    - Test collection operations
    - Test vector search
    - _Requirements: 2.5_
  
  - [ ] 13.5 Write integration test for OPA policy evaluation
    - Test against REAL OPA service (SOMABRAIN_OPA_URL)
    - Test policy allow/deny
    - _Requirements: 6.4_

- [ ] 14. Checkpoint - Verify infrastructure integration tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 8: Predictor Property Tests

- [ ] 15. Implement predictor property tests
  - [ ] 15.1 Write property test for Chebyshev heat approximation
    - **Property 15: Chebyshev Heat Approximation**
    - Test exp(-tA)x approximation accuracy
    - **Validates: Requirements 9.1**
  
  - [ ] 15.2 Write property test for Lanczos spectral bounds
    - **Property 16: Lanczos Spectral Bounds**
    - Test eigenvalue bounds contain true eigenvalues
    - **Validates: Requirements 9.2**

- [ ] 16. Checkpoint - Verify predictor property tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 9: Multi-Tenancy & Serialization Tests

- [ ] 17. Implement multi-tenancy and serialization tests
  - [ ] 17.1 Write property test for tenant isolation
    - **Property 17: Tenant Isolation**
    - Test PerTenantNeuromodulators state separation
    - **Validates: Requirements 10.2**
  
  - [ ] 17.2 Write property test for serialization round-trip
    - **Property 18: Serialization Round-Trip**
    - Test NeuromodState, RecallHit, AdaptationEngine state
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
  
  - [ ] 17.3 Write property test for timestamp normalization
    - **Property 19: Timestamp Normalization**
    - Test ISO-8601 and numeric string normalization
    - **Validates: Requirements 8.5**

- [ ] 18. Checkpoint - Verify multi-tenancy tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 10: End-to-End Integration Tests (FULL STACK)

- [ ] 19. Implement end-to-end tests against REAL full stack
  - [ ] 19.1 Write E2E test for remember → recall flow
    - Start REAL services (docker-compose)
    - POST /remember with payload
    - POST /recall and verify response
    - Verify data persisted in REAL memory service
    - _Requirements: 8.1, 8.2_
  
  - [ ] 19.2 Write E2E test for health endpoint
    - Test /health returns all backend statuses
    - Verify kafka_ok, postgres_ok, redis_ok, opa_ok, memory_ok
    - _Requirements: 5.1_
  
  - [ ] 19.3 Write E2E test for authentication flow
    - Test protected endpoints require auth
    - Test valid token grants access
    - Test invalid token returns 401
    - _Requirements: 6.1, 6.2_
  
  - [ ] 19.4 Write E2E test for feedback → adaptation flow
    - POST /context/feedback
    - Verify AdaptationEngine weights updated
    - Verify state persisted to REAL Redis
    - _Requirements: 4.1, 4.5_
  
  - [ ] 19.5 Write E2E test for Oak planning flow
    - Test /oak/plan endpoint
    - Verify options retrieved from REAL Milvus
    - _Requirements: 8.1_

- [ ] 20. Checkpoint - Verify E2E tests
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 11: VIBE Compliance Cleanup

- [ ] 21. Remove VIBE violations
  - [ ] 21.1 Audit and fix pass statements in exception handlers
    - Review all 50+ pass statements
    - Add proper logging or error handling where needed
    - _Requirements: 7.4, 12.1_
  
  - [ ] 21.2 Remove monkey-patching from production code
    - Fix `somabrain/learning/adaptation.py` monkey-patch reference
    - Fix `somabrain/oak/planner.py` monkey-patch reference
    - _Requirements: 7.1, 7.2_
  
  - [ ] 21.3 Ensure no direct os.getenv in production code
    - Run existing test: `tests/test_settings_defaults.py`
    - Fix any violations found
    - _Requirements: 3.1_
  
  - [ ] 21.4 Review test stubs for VIBE compliance
    - Ensure test stubs are clearly marked
    - Ensure no stubs leak into production paths
    - _Requirements: 7.2_

- [ ] 22. Checkpoint - Verify VIBE compliance
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 12: Documentation & Final Validation

- [ ] 23. Update documentation
  - [ ] 23.1 Update README with new architecture
    - Document router structure
    - Document configuration modules
    - _Requirements: 7.5_
  
  - [ ] 23.2 Update API documentation
    - Ensure OpenAPI spec reflects new router structure
    - _Requirements: 8.1_
  
  - [ ] 23.3 Create architecture diagram
    - Document new modular architecture
    - Document data flows
    - _Requirements: 7.5_

- [ ] 24. Final Checkpoint - Full test suite
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `pytest tests/ -v --tb=short`
  - Run: `pytest tests/integration/ -v` (against REAL infra)
  - Run: `pytest tests/property/ -v`

---

## Test Infrastructure Requirements

### Required Services for Integration Tests

All integration tests MUST run against REAL infrastructure:

```yaml
# docker-compose.test.yml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: somabrain_test
      POSTGRES_USER: soma
      POSTGRES_PASSWORD: soma
    ports: ["5432:5432"]
  
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports: ["9092:9092"]
  
  milvus:
    image: milvusdb/milvus:v2.3.0
    ports: ["19530:19530"]
  
  opa:
    image: openpolicyagent/opa:latest
    ports: ["8181:8181"]
  
  memory-service:
    build: ./memory
    ports: ["9595:9595"]
    depends_on: [redis, postgres, milvus]
```

### Environment Variables for Tests

```bash
# .env.test
SOMABRAIN_REDIS_URL=redis://localhost:6379/0
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma@localhost:5432/somabrain_test
SOMABRAIN_KAFKA_URL=localhost:9092
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595
SOMABRAIN_OPA_URL=http://localhost:8181
MILVUS_HOST=localhost
MILVUS_PORT=19530
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
```

### Test Execution

```bash
# Start infrastructure
docker-compose -f docker-compose.test.yml up -d

# Wait for services
./scripts/wait-for-services.sh

# Run all tests against REAL infra
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1 pytest tests/ -v

# Run only integration tests
pytest tests/integration/ -v --tb=short

# Run property tests
pytest tests/property/ -v --hypothesis-show-statistics
```

---

## Summary

| Phase | Tasks | Tests | Infrastructure |
|-------|-------|-------|----------------|
| 1 | app.py refactoring | Unit | None |
| 2 | settings.py refactoring | Property | None |
| 3 | metrics.py refactoring | Unit | None |
| 4 | Math core properties | Property | None |
| 5 | Memory integration | Integration | Memory Service, Redis |
| 6 | Learning properties | Property | None |
| 7 | Infra integration | Integration | Redis, Kafka, Postgres, Milvus, OPA |
| 8 | Predictor properties | Property | None |
| 9 | Multi-tenancy | Property + Integration | Redis |
| 10 | E2E tests | E2E | ALL services |
| 11 | VIBE cleanup | Static analysis | None |
| 12 | Documentation | None | None |

**Total: 24 task groups, 20 property tests, 15+ integration tests against REAL infrastructure**
