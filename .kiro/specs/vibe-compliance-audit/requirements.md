# Requirements Document

## Introduction

This specification defines the requirements for achieving full VIBE Coding Rules compliance across the SomaBrain codebase. The audit was conducted by applying all seven VIBE personas simultaneously to identify violations, duplications, and architectural issues that must be resolved for production-grade quality.

## Glossary

- **VIBE Coding Rules**: The project's strict coding standards requiring real implementations, no mocks/stubs, complete context verification, and ISO-style documentation
- **Silent Error Swallowing**: Exception handlers that use `pass` without logging or metrics
- **Magic Number**: Hardcoded numeric values that should be in configuration
- **Circular Import**: Module dependencies that form a cycle, requiring lazy imports
- **Duplicate Implementation**: Multiple implementations of the same algorithm
- **Global State**: Module-level mutable variables that should use dependency injection
- **Monolithic File**: A single source file exceeding 500 lines with mixed concerns

---

## Multi-Persona Audit Summary

### 🎓 PhD-Level Software Developer Findings

| Category | Count | Severity |
|----------|-------|----------|
| Monolithic Files (>500 lines) | 14 | CRITICAL |
| Duplicate Cosine Implementations | 6 | HIGH |
| Duplicate Normalize Implementations | 8 | HIGH |
| np.linalg.norm Direct Usage | 44 | MEDIUM |
| NotImplementedError in Production | 1 | MEDIUM |

### 🔬 PhD-Level Software Analyst Findings

| Category | Count | Severity |
|----------|-------|----------|
| Lazy Import Workarounds | 13 | HIGH |
| Global State Variables | 15+ | HIGH |
| Circular Import Guards | 8 | HIGH |
| importlib Dynamic Loading | 12 | MEDIUM |

### 🧪 PhD-Level QA Engineer Findings

| Category | Count | Severity |
|----------|-------|----------|
| Silent `pass` Statements | 284 | HIGH |
| Exception Handlers | 1010 | MEDIUM |
| Type Ignore Comments | 30 | LOW |
| Deprecated Code Patterns | 6 | MEDIUM |

### 📚 ISO-Style Documenter Findings

| Category | Count | Severity |
|----------|-------|----------|
| Files Missing Module Docstrings | ~50 | MEDIUM |
| Functions Missing Docstrings | ~100 | LOW |
| Undocumented Magic Numbers | 40+ | MEDIUM |

### 🔒 Security Auditor Findings

| Category | Count | Severity |
|----------|-------|----------|
| Direct os.environ Access | 22 | MEDIUM |
| Hardcoded Credentials | 0 | N/A |
| Stub/Mock References | 20 | LOW |

### ⚡ Performance Engineer Findings

| Category | Count | Severity |
|----------|-------|----------|
| Duplicate Computation Patterns | 44 | MEDIUM |
| Unbounded Caches | 3 | MEDIUM |
| O(n³) Operations | 2 | LOW |

---

## Requirements

### Requirement 1: Monolithic File Decomposition

**User Story:** As a developer, I want all source files to be under 500 lines with single responsibility, so that the codebase is maintainable and navigable.

#### Acceptance Criteria

1. WHEN `somabrain/app.py` is refactored THEN the System SHALL reduce it from 4052 lines to under 500 lines by extracting routers, middleware, and services
2. WHEN `somabrain/memory_client.py` is refactored THEN the System SHALL reduce it from 2216 lines to under 500 lines by extracting transport and normalization
3. WHEN `somabrain/metrics_original.py` is refactored THEN the System SHALL reduce it from 1698 lines to under 500 lines by domain-based splitting
4. WHEN `somabrain/api/memory_api.py` is refactored THEN the System SHALL reduce it from 1615 lines to under 500 lines by extracting models and helpers
5. WHEN `somabrain/learning/adaptation.py` is refactored THEN the System SHALL reduce it from 1071 lines to under 500 lines by extracting config and feedback modules
6. WHEN `somabrain/schemas.py` is refactored THEN the System SHALL reduce it from 1003 lines to under 500 lines by domain-based splitting
7. WHEN `somabrain/routers/memory.py` is refactored THEN the System SHALL reduce it from 720 lines to under 500 lines by extracting scoring helpers

### Requirement 2: Duplicate Code Elimination

**User Story:** As a developer, I want a single canonical implementation for each utility function, so that behavior is consistent and maintenance is simplified.

#### Acceptance Criteria

1. WHEN cosine similarity is computed THEN the System SHALL use only `somabrain/math/similarity.py:cosine_similarity`
2. WHEN vector normalization is performed THEN the System SHALL use only `somabrain/math/normalize.py:normalize_vector`
3. WHEN `somabrain/scoring.py:_cosine` is called THEN the System SHALL delegate to the canonical implementation
4. WHEN `somabrain/prediction.py:cosine_error` is called THEN the System SHALL delegate to the canonical implementation
5. WHEN `somabrain/quantum.py:cosine` is called THEN the System SHALL delegate to the canonical implementation
6. WHEN `somabrain/quantum_pure.py:cosine` is called THEN the System SHALL delegate to the canonical implementation
7. WHEN `somabrain/schemas.py:normalize_vector` is called THEN the System SHALL delegate to the canonical implementation
8. WHEN `somabrain/context_hrr.py:_normalize` is called THEN the System SHALL delegate to the canonical implementation
9. WHEN `somabrain/services/ann.py:_normalize` is called THEN the System SHALL delegate to the canonical implementation
10. WHEN `somabrain/services/milvus_ann.py:_normalize` is called THEN the System SHALL delegate to the canonical implementation

### Requirement 3: Silent Error Handling Elimination

**User Story:** As an operator, I want all exceptions to be logged with context, so that failures are visible and debuggable.

#### Acceptance Criteria

1. WHEN an exception is caught with `pass` THEN the System SHALL replace it with structured logging at appropriate level
2. WHEN `somabrain/routers/memory.py` handles exceptions THEN the System SHALL log all 18 silent pass statements with context
3. WHEN `somabrain/routers/admin.py` handles exceptions THEN the System SHALL log all 14 silent pass statements with context
4. WHEN `somabrain/routers/neuromod.py` handles exceptions THEN the System SHALL log all 2 silent pass statements with context
5. WHEN `somabrain/journal/local_journal.py` handles exceptions THEN the System SHALL log all 3 silent pass statements with context
6. WHEN `somabrain/neuromodulators.py` handles exceptions THEN the System SHALL log all 2 silent pass statements with context
7. WHEN `somabrain/microcircuits.py` handles exceptions THEN the System SHALL log all 2 silent pass statements with context
8. WHEN `somabrain/cognitive/thread_model.py` handles exceptions THEN the System SHALL log all 1 silent pass statement with context

### Requirement 4: Configuration Centralization

**User Story:** As a DevOps engineer, I want all configuration to flow through Settings, so that environment management is consistent.

#### Acceptance Criteria

1. WHEN `scripts/constitution_sign.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ
2. WHEN `scripts/verify_deployment.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ
3. WHEN `scripts/check_memory_endpoint.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ
4. WHEN `benchmarks/diffusion_predictor_bench.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ
5. WHEN `benchmarks/cognition_core_bench.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ
6. WHEN `common/provider_sdk/discover.py` accesses environment THEN the System SHALL use Settings instead of direct os.environ

### Requirement 5: Circular Import Resolution

**User Story:** As a developer, I want clean import graphs without lazy loading workarounds, so that startup is predictable.

#### Acceptance Criteria

1. WHEN `somabrain/hippocampus.py` imports runtime THEN the System SHALL use dependency injection instead of lazy import
2. WHEN `somabrain/app.py` imports runtime THEN the System SHALL use dependency injection instead of importlib workaround
3. WHEN `somabrain/services/planning_service.py` imports metrics THEN the System SHALL use the metrics interface
4. WHEN `somabrain/services/cognitive_loop_service.py` imports metrics THEN the System SHALL use the metrics interface
5. WHEN `somabrain/amygdala.py` imports metrics THEN the System SHALL use the metrics interface
6. WHEN `somabrain/exec_controller.py` imports metrics THEN the System SHALL use the metrics interface
7. WHEN `somabrain/neuromodulators.py` imports metrics THEN the System SHALL use the metrics interface
8. WHEN `somabrain/context/builder.py` has circular import guard THEN the System SHALL refactor to eliminate the guard

### Requirement 6: Global State Elimination

**User Story:** As a developer, I want explicit dependency injection instead of global state, so that code is testable.

#### Acceptance Criteria

1. WHEN `somabrain/journal/local_journal.py` uses global `_journal` THEN the System SHALL use the DI container
2. WHEN `somabrain/metrics/interface.py` uses global `_metrics_instance` THEN the System SHALL use the DI container
3. WHEN `somabrain/auth.py` uses global `_JWT_PUBLIC_CACHE` THEN the System SHALL use the DI container
4. WHEN `somabrain/bootstrap/logging.py` uses global loggers THEN the System SHALL use the DI container
5. WHEN `somabrain/core/logging_setup.py` uses global loggers THEN the System SHALL use the DI container
6. WHEN `somabrain/segmentation/evaluator.py` uses global metrics THEN the System SHALL use the DI container
7. WHEN `observability/provider.py` uses global `_initialized` THEN the System SHALL use the DI container

### Requirement 7: Deprecated Code Removal

**User Story:** As a maintainer, I want deprecated code removed, so that the codebase is clean.

#### Acceptance Criteria

1. WHEN `SOMABRAIN_FORCE_FULL_STACK` is detected THEN the System SHALL remove support and use only `SOMABRAIN_MODE`
2. WHEN `somabrain/api/dependencies/auth.py` deprecated functions are called THEN the System SHALL remove them after migration
3. WHEN `somabrain/api/context_route.py` backward compatibility reference is used THEN the System SHALL remove it
4. WHEN `somabrain/infrastructure/__init__.py` deprecated getenv pattern is used THEN the System SHALL remove it
5. WHEN `somabrain/metrics_original.py` deprecated metric is referenced THEN the System SHALL remove it
6. WHEN `somabrain/api/routers/opa.py` deprecated getenv comment exists THEN the System SHALL verify and clean up

### Requirement 8: Magic Number Elimination

**User Story:** As a developer, I want all numeric constants in configuration, so that tuning is centralized.

#### Acceptance Criteria

1. WHEN `somabrain/routers/memory.py` uses hardcoded scoring bonuses (0.05, 0.02, 0.01) THEN the System SHALL move them to Settings
2. WHEN `somabrain/middleware/validation.py` uses hardcoded limits (10000, 4096, 64) THEN the System SHALL move them to Settings
3. WHEN `somabrain/sdr.py` uses hardcoded dimensions (16384, 0.01) THEN the System SHALL move them to Settings
4. WHEN `somabrain/cognitive/emotion.py` uses hardcoded decay rate (0.01) THEN the System SHALL move them to Settings
5. WHEN `somabrain/context/planner.py` uses hardcoded penalty scales (1024.0, 10.0) THEN the System SHALL move them to Settings
6. WHEN `somabrain/journal/local_journal.py` uses hardcoded file limits (100MB, 10 files) THEN the System SHALL move them to Settings
7. WHEN `somabrain/microcircuits.py` uses hardcoded hash constants THEN the System SHALL document or move to Settings

### Requirement 9: Benchmark Code Cleanup

**User Story:** As a developer, I want benchmark code to follow VIBE rules, so that examples are production-grade.

#### Acceptance Criteria

1. WHEN `benchmarks/colored_noise_bench.py` defines inline cosine THEN the System SHALL use the canonical implementation
2. WHEN `benchmarks/numerics_workbench.py` defines inline cosine THEN the System SHALL use the canonical implementation
3. WHEN `benchmarks/tinyfloor_bench.py` computes cosine inline THEN the System SHALL use the canonical implementation
4. WHEN `benchmarks/capacity_curves.py` computes cosine inline THEN the System SHALL use the canonical implementation
5. WHEN `benchmarks/cognition_core_bench.py` computes cosine inline THEN the System SHALL use the canonical implementation

### Requirement 10: JWT Module Cleanup

**User Story:** As a developer, I want clean module imports without dynamic loading hacks, so that the codebase is maintainable.

#### Acceptance Criteria

1. WHEN `jwt/__init__.py` loads PyJWT THEN the System SHALL use standard imports or document the necessity
2. WHEN `jwt/exceptions.py` loads PyJWT exceptions THEN the System SHALL use standard imports or document the necessity
3. IF dynamic loading is required THEN the System SHALL document the reason in module docstring

### Requirement 11: Type Safety Improvement

**User Story:** As a developer, I want type annotations without ignore comments, so that type checking is effective.

#### Acceptance Criteria

1. WHEN `# type: ignore` comments exist THEN the System SHALL fix the underlying type issue or document why ignore is necessary
2. WHEN type annotations are missing THEN the System SHALL add them for public functions
3. WHEN return types are `Any` THEN the System SHALL specify concrete types where possible

### Requirement 12: NotImplementedError Removal

**User Story:** As a developer, I want all code paths implemented, so that there are no runtime surprises.

#### Acceptance Criteria

1. WHEN `somabrain/services/recall_service.py:diversify_payloads` is called with unsupported method THEN the System SHALL implement the method or raise a descriptive ValueError

---

## Violation Inventory

### Monolithic Files (>500 lines)

| File | Lines | Target |
|------|-------|--------|
| `somabrain/app.py` | 4052 | <500 |
| `somabrain/memory_client.py` | 2216 | <500 |
| `somabrain/metrics_original.py` | 1698 | <500 |
| `somabrain/api/memory_api.py` | 1615 | <500 |
| `somabrain/learning/adaptation.py` | 1071 | <500 |
| `somabrain/schemas.py` | 1003 | <500 |
| `somabrain/routers/memory.py` | 720 | <500 |
| `somabrain/api/context_route.py` | 655 | <500 |
| `somabrain/tenant_registry.py` | 579 | <500 |
| `somabrain/db/outbox.py` | 529 | <500 |
| `somabrain/context/builder.py` | 528 | <500 |
| `somabrain/workers/outbox_publisher.py` | 526 | <500 |
| `somabrain/routers/admin.py` | 510 | <500 |
| `somabrain/constitution/__init__.py` | 503 | <500 |

### Silent Pass Statements by File

| File | Count |
|------|-------|
| `somabrain/routers/memory.py` | 18 |
| `somabrain/routers/admin.py` | 14 |
| `somabrain/journal/local_journal.py` | 3 |
| `somabrain/routers/neuromod.py` | 2 |
| `somabrain/neuromodulators.py` | 2 |
| `somabrain/microcircuits.py` | 2 |
| `somabrain/cognitive/thread_model.py` | 1 |
| `somabrain/middleware/security.py` | 1 |
| `somabrain/oak/planner.py` | 1 |
| Other files | ~240 |

### Duplicate Implementations

| Function | Locations |
|----------|-----------|
| cosine_similarity | `math/similarity.py`, `scoring.py`, `quantum.py`, `quantum_pure.py`, `prediction.py`, benchmarks (5) |
| normalize_vector | `math/normalize.py`, `schemas.py`, `context_hrr.py`, `services/ann.py`, `services/milvus_ann.py` |

### Direct os.environ Access (Non-Settings)

| File | Lines |
|------|-------|
| `scripts/constitution_sign.py` | 58, 62 |
| `scripts/verify_deployment.py` | 138, 173 |
| `scripts/check_memory_endpoint.py` | 12, 50 |
| `benchmarks/diffusion_predictor_bench.py` | 77 |
| `benchmarks/cognition_core_bench.py` | 300, 304, 305 |
| `common/provider_sdk/discover.py` | 24, 25 |

### Requirement 13: Degradation Mode Architecture

**User Story:** As an SRE, I want proper degradation modes with clear state transitions, so that the system fails gracefully under load.

#### Acceptance Criteria

1. WHEN the memory service is unavailable THEN the System SHALL transition to "degraded" status and queue operations
2. WHEN the circuit breaker trips THEN the System SHALL emit metrics and log the state transition
3. WHEN degraded mode is active THEN the System SHALL provide clear status via /health endpoint
4. WHEN services recover THEN the System SHALL replay queued operations from the outbox
5. WHEN fallback behavior is used THEN the System SHALL log the fallback with context
6. IF `somabrain/memory_pool.py` uses fallback THEN the System SHALL document the fallback clearly

### Requirement 14: Backup and Recovery

**User Story:** As an operator, I want reliable backup and recovery mechanisms, so that data is not lost during failures.

#### Acceptance Criteria

1. WHEN events are persisted THEN the System SHALL use the outbox pattern for durability
2. WHEN the journal writes events THEN the System SHALL verify write success before acknowledging
3. WHEN episodic snapshots are created THEN the System SHALL store them in the database
4. WHEN state is persisted to Redis THEN the System SHALL use tenant-prefixed keys
5. WHEN recovery is needed THEN the System SHALL replay from the outbox with idempotency

### Requirement 15: QA Infrastructure

**User Story:** As a QA engineer, I want comprehensive testing infrastructure, so that I can verify system correctness.

#### Acceptance Criteria

1. WHEN property tests are written THEN the System SHALL use Hypothesis with minimum 100 iterations
2. WHEN integration tests run THEN the System SHALL use real backends (no mocks)
3. WHEN assertions are used in production code THEN the System SHALL replace them with proper validation
4. WHEN `somabrain/math/sinkhorn.py` uses assert THEN the System SHALL replace with ValueError
5. WHEN `somabrain/prediction.py` uses assert THEN the System SHALL replace with proper error handling
6. WHEN `somabrain/milvus_client.py` uses assert THEN the System SHALL replace with proper validation
7. WHEN `somabrain/app.py` uses assert THEN the System SHALL replace with proper error handling

### Requirement 16: Rate Limiting and Quotas

**User Story:** As an operator, I want proper rate limiting and quota enforcement, so that the system is protected from abuse.

#### Acceptance Criteria

1. WHEN rate limiting is applied THEN the System SHALL use the centralized rate_limiter
2. WHEN quotas are exceeded THEN the System SHALL return HTTP 429 with clear message
3. WHEN quota state is tracked THEN the System SHALL persist it for tenant isolation
4. WHEN rate limit metrics are recorded THEN the System SHALL use RATE_LIMITED_TOTAL counter

### Requirement 17: Security Hardening

**User Story:** As a security engineer, I want proper authentication and secret management, so that the API is secure.

#### Acceptance Criteria

1. WHEN JWT validation is required THEN the System SHALL verify tokens against configured keys
2. WHEN secrets are accessed THEN the System SHALL use Settings, not environment variables
3. WHEN authentication fails THEN the System SHALL return HTTP 401 with generic message
4. WHEN authorization fails THEN the System SHALL return HTTP 403 with policy reference
5. WHEN `_JWT_PUBLIC_CACHE` is used THEN the System SHALL move to DI container

### Requirement 18: Async Architecture Consistency

**User Story:** As a developer, I want consistent async patterns, so that concurrency is predictable.

#### Acceptance Criteria

1. WHEN async functions are defined THEN the System SHALL use consistent naming conventions
2. WHEN thread locks are used THEN the System SHALL document the synchronization strategy
3. WHEN global state is accessed from async code THEN the System SHALL use thread-safe patterns
4. WHEN `somabrain/journal/local_journal.py` uses threading.RLock THEN the System SHALL document thread safety

### Requirement 19: Cache Management

**User Story:** As a developer, I want bounded caches with clear eviction policies, so that memory is managed.

#### Acceptance Criteria

1. WHEN TTLCache is used THEN the System SHALL configure appropriate maxsize and ttl
2. WHEN lru_cache is used THEN the System SHALL configure appropriate maxsize
3. WHEN caches are created THEN the System SHALL register them for monitoring
4. WHEN `_recall_cache` is used THEN the System SHALL bound it per tenant
5. WHEN `_JWT_PUBLIC_CACHE` is used THEN the System SHALL add TTL or invalidation

### Requirement 20: Observability Completeness

**User Story:** As an SRE, I want comprehensive metrics and health checks, so that I can monitor the system.

#### Acceptance Criteria

1. WHEN health checks are performed THEN the System SHALL check all critical dependencies
2. WHEN metrics are recorded THEN the System SHALL use consistent naming conventions
3. WHEN errors occur THEN the System SHALL emit error metrics with context
4. WHEN circuit breakers change state THEN the System SHALL emit state change metrics
5. WHEN degraded mode is active THEN the System SHALL emit degradation metrics

---

## Additional Violation Inventory

### Production Assertions (Must Replace)

| File | Line | Issue |
|------|------|-------|
| `somabrain/math/sinkhorn.py` | 30, 31 | assert for shape validation |
| `somabrain/prediction.py` | 211 | assert result is not None |
| `somabrain/milvus_client.py` | 200 | assert self.collection is not None |
| `somabrain/app.py` | 1717 | assert _spec and _spec.loader |

### Unbounded Caches

| File | Cache | Issue |
|------|-------|-------|
| `somabrain/routers/memory.py` | `_recall_cache` | Per-tenant TTLCache, needs monitoring |
| `somabrain/auth.py` | `_JWT_PUBLIC_CACHE` | No TTL, no invalidation |
| `somabrain/context/factory.py` | `lru_cache(maxsize=1)` | OK - bounded |
| `somabrain/context/builder.py` | `_tenant_overrides_cache` | Unbounded dict |

### Fallback Patterns (Need Documentation)

| File | Pattern | Issue |
|------|---------|-------|
| `somabrain/memory_pool.py` | Local in-process fallback | Needs clear documentation |
| `somabrain/runtime/working_memory.py` | In-process buffer fallback | Needs clear documentation |
| `somabrain/runtime/fusion.py` | Uniform fallback | Needs clear documentation |
| `somabrain/oak/planner.py` | Empty list fallback | Needs clear documentation |
| `somabrain/config/__init__.py` | model_dump fallback | Needs clear documentation |

### Thread Safety Concerns

| File | Pattern | Issue |
|------|---------|-------|
| `somabrain/journal/local_journal.py` | threading.RLock | Needs documentation |
| `somabrain/metrics/interface.py` | threading.Lock | Needs documentation |
| `somabrain/routers/memory.py` | Global `_recall_cache` | Thread safety unclear |

### Degradation Mode Gaps

| Component | Issue |
|-----------|-------|
| Memory Service | Degradation documented but fallback behavior unclear |
| Circuit Breaker | State transitions need metrics |
| Outbox Replay | Idempotency needs verification |
| Health Endpoint | Degraded status classification needs review |

---

## Success Criteria

1. No file exceeds 500 lines (with documented exceptions)
2. Zero duplicate implementations of cosine/normalize
3. Zero silent `pass` statements without logging
4. Zero direct `os.environ` access outside Settings helpers
5. Zero lazy import workarounds for circular dependencies
6. Zero global state variables (use DI container)
7. Zero deprecated code patterns
8. Zero hardcoded magic numbers in business logic
9. All benchmarks use canonical implementations
10. All type ignore comments documented or resolved
11. Zero production assertions (use proper validation)
12. All caches bounded with monitoring
13. All fallback patterns documented
14. Thread safety documented for all concurrent code
15. Degradation modes fully implemented with metrics
