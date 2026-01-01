# Software Requirements Specification (SRS)
## SomaBrain Global Architecture Refactoring

**Document Version:** 1.0  
**Date:** December 9, 2025  
**Status:** Draft for Review

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the requirements for a comprehensive architectural refactoring of the SomaBrain cognitive AI system. The refactoring aims to eliminate legacy code, resolve VIBE Coding Rules violations, establish clean architectural boundaries, and transform monolithic modules into well-structured, maintainable components.

### 1.2 Scope

This specification covers:
- Global architecture assessment and restructuring
- Legacy code identification and removal
- VIBE Coding Rules compliance enforcement
- Module decomposition and clean architecture implementation
- Mathematical component isolation and verification
- Memory system consolidation
- Configuration system unification

### 1.3 Glossary

- **SomaBrain**: The cognitive AI system under refactoring
- **VIBE Coding Rules**: The project's strict coding standards requiring real implementations, no mocks/stubs, complete context verification, and ISO-style documentation
- **HRR**: Holographic Reduced Representation - mathematical encoding for cognitive vectors
- **SDR**: Sparse Distributed Representation - memory indexing technique
- **WM**: Working Memory - short-term cognitive buffer
- **LTM**: Long-Term Memory - persistent memory storage
- **OPA**: Open Policy Agent - policy enforcement system
- **Neuromodulators**: Dopamine, noradrenaline, acetylcholine state management
- **Circuit Breaker**: Fault tolerance pattern for service degradation

---

## 2. Current Architecture Analysis - DETAILED VIOLATION INVENTORY

### 2.1 Critical Findings

#### 2.1.1 Monolithic Files Requiring Decomposition

| File | Lines | Issue | Priority |
|------|-------|-------|----------|
| `somabrain/app.py` | 4,421 | God object - contains middleware, routes, utilities, bootstrap, scoring | CRITICAL |
| `somabrain/memory_client.py` | 2,216 | Mixed concerns - HTTP transport, caching, normalization, weighting | HIGH |
| `somabrain/metrics_original.py` | 1,698 | Legacy metrics with deprecated patterns | HIGH |
| `somabrain/api/memory_api.py` | 1,473 | Oversized API module | MEDIUM |
| `somabrain/learning/adaptation.py` | 1,022 | Complex learning logic needs separation | MEDIUM |
| `somabrain/schemas.py` | 989 | Monolithic schema definitions | MEDIUM |
| `somabrain/routers/memory.py` | 720 | Large router file | MEDIUM |
| `somabrain/api/context_route.py` | 589 | Oversized context API | MEDIUM |
| `somabrain/tenant_registry.py` | 579 | Complex tenant logic | MEDIUM |
| `somabrain/context/builder.py` | 542 | Large context builder | MEDIUM |

#### 2.1.2 DUPLICATE CODE VIOLATIONS (6 instances of _cosine function)

| Location | Function | Action Required |
|----------|----------|-----------------|
| `somabrain/app.py:448` | `_cosine_similarity` | REMOVE - use canonical |
| `somabrain/app.py:459` | `_cosine_similarity_vectors` | REMOVE - alias |
| `somabrain/reflect.py:161` | `_cosine_sim` | REMOVE - use canonical |
| `somabrain/agent_memory.py:42` | `_cosine` | REMOVE - use canonical |
| `somabrain/scoring.py:94` | `_cosine` | KEEP AS CANONICAL |
| `somabrain/wm.py:158` | `_cosine` | REMOVE - use canonical |
| `somabrain/context/builder.py:489` | `_cosine` | REMOVE - use canonical |

#### 2.1.3 LAZY IMPORT VIOLATIONS (Circular Dependency Indicators)

| File | Import Pattern | Risk Level |
|------|----------------|------------|
| `somabrain/hippocampus.py:53` | `from . import runtime as _rt` | HIGH |
| `somabrain/hippocampus.py:55` | `import_module("somabrain.runtime_module")` | HIGH |
| `somabrain/services/cognitive_loop_service.py:117` | `from .. import metrics as M` | MEDIUM |
| `somabrain/services/planning_service.py:19` | `from .. import metrics as M` | MEDIUM |
| `somabrain/exec_controller.py:153` | `from . import metrics as _mx` | MEDIUM |
| `somabrain/amygdala.py:138` | `from . import metrics as M` | MEDIUM |
| `somabrain/infrastructure/circuit_breaker.py:90` | `from . import metrics` | MEDIUM |
| `somabrain/app.py:3176,3219,3605` | `from . import metrics as _mx` | MEDIUM |
| `somabrain/libs/__init__.py:15` | `importlib.import_module` | LOW |

#### 2.1.4 GLOBAL STATE VIOLATIONS (Mutable Module-Level State)

| File | Variable | Issue |
|------|----------|-------|
| `somabrain/runtime.py:36-40` | `embedder, quantum, mt_wm, mc_wm, mt_memory = None` | Global singletons |
| `somabrain/app.py:600-602` | `logger, cognitive_logger, error_logger = None` | Global loggers |
| `somabrain/app.py:2023` | `fd_sketch = None` | Global state |
| `somabrain/app.py:2121` | `_recall_cache: dict = {}` | Global cache |
| `somabrain/app.py:2329` | `unified_brain = None` | Global state |
| `somabrain/app.py:2602` | `_sleep_last: dict = {}` | Global state |
| `somabrain/app.py:2620` | `_sdr_idx: dict = {}` | Global state |
| `somabrain/app.py:4128` | `_health_watchdog_task = None` | Global task |
| `somabrain/services/retrieval_cache.py:23` | `_cache: Dict = {}` | Global cache |
| `somabrain/services/cognitive_loop_service.py:17,30` | `_BU_PUBLISHER, _SLEEP_STATE_CACHE` | Global state |
| `somabrain/api/memory_api.py:45` | `_RECALL_SESSIONS: Dict = {}` | Global sessions |
| `somabrain/api/context_route.py:115-116,396` | `_feedback_store, _token_ledger, _adaptation_engines` | Global state |
| `somabrain/metrics_original.py:237,1389` | `_external_metrics_scraped, _regret_ema` | Global state |
| `somabrain/learning/adaptation.py:30-32` | `_TENANT_OVERRIDES, _TENANT_OVERRIDES_PATH` | Global state |
| `somabrain/milvus_client.py:67` | `_LATENCY_WINDOWS: Dict` | Global state |
| `somabrain/routers/memory.py:41,44` | `_recall_cache, _MATH_DOMAIN_KEYWORDS` | Global state |

#### 2.1.5 HARDCODED MAGIC NUMBERS (Configuration Values in Code)

| File | Line | Value | Should Be |
|------|------|-------|-----------|
| `somabrain/nano_profile.py:6` | `HRR_DIM = 8192` | Settings.hrr_dim |
| `somabrain/nano_profile.py:10` | `BHDC_SPARSITY = 0.1` | Settings.bhdc_sparsity |
| `somabrain/nano_profile.py:11` | `SDR_BITS = 2048` | Settings.sdr_bits |
| `somabrain/nano_profile.py:12` | `SDR_DENSITY = 0.03` | Settings.sdr_density |
| `somabrain/nano_profile.py:13` | `CONTEXT_BUDGET_TOKENS = 2048` | Settings.context_budget |
| `somabrain/nano_profile.py:14` | `MAX_SUPERPOSE = 32` | Settings.max_superpose |
| `somabrain/nano_profile.py:15` | `DEFAULT_WM_SLOTS = 12` | Settings.wm_slots |
| `somabrain/nano_profile.py:16` | `DEFAULT_SEED = 42` | Settings.seed |
| `somabrain/amygdala.py:52` | `soft_temperature: float = 0.15` | Settings |
| `somabrain/amygdala.py:55` | `fd_energy_floor: float = 0.9` | Settings |
| `somabrain/controls/drift_monitor.py:47-48` | `window=128, threshold=5.0` | Settings |
| `somabrain/quantum.py:38-43` | `dim=2048, seed=42, sparsity=0.1` | Settings |
| `somabrain/quotas.py:57` | `daily_writes: int = 10000` | Settings |
| `somabrain/exec_controller.py:45-48` | `window=8, conflict_threshold=0.7, bandit_eps=0.1` | Settings |
| `somabrain/controls/policy.py:51` | `safety_threshold: float = 0.9` | Settings |
| `somabrain/reflect.py:176` | `sim_threshold=0.35, min_cluster_size=2` | Settings |
| `somabrain/infrastructure/circuit_breaker.py:38` | `global_reset_interval=60.0` | Settings |

#### 2.1.6 SILENT ERROR SWALLOWING (pass in except blocks)

| File | Line | Context | Risk |
|------|------|---------|------|
| `somabrain/services/outbox_sync.py:107` | `except Exception: pass` | Metric reporting | LOW |
| `somabrain/services/feature_flags_service.py:53` | `except Exception: pass` | Metric registration | LOW |
| `somabrain/services/ann.py:150` | `except Exception: pass` | ef_search setting | MEDIUM |
| `somabrain/services/learner_online.py:136` | `except Exception: pass` | DLQ recording | HIGH |
| `somabrain/services/entry.py:132` | `except Exception: pass` | Signal handling | LOW |
| `somabrain/services/retrieval_cache.py:52,70,88` | `except Exception: pass` | Cache operations | MEDIUM |
| `somabrain/services/recall_service.py:133,173,288` | `except Exception: pass` | Recall operations | HIGH |
| `somabrain/services/cognitive_loop_service.py:121,175` | `except Exception: pass` | Metrics/traits | MEDIUM |
| `somabrain/services/integrator_hub_triplet.py:263,299,381` | `except Exception: pass` | Integration | HIGH |
| `somabrain/services/orchestrator_service.py:148,176,206,225,269,285` | `except Exception: pass` | Orchestration | HIGH |
| `somabrain/services/planning_service.py:36,73` | `except Exception: pass` | Planning metrics | LOW |
| `somabrain/spectral_cache.py:93` | `except Exception: pass` | File cleanup | LOW |
| `somabrain/exec_controller.py:159` | `except Exception: pass` | Metrics | LOW |
| `somabrain/monitoring/drift_detector.py:116,129` | `except Exception: pass` | Drift detection | MEDIUM |
| `somabrain/quantum.py:336` | `except Exception: pass` | Metrics | LOW |
| `somabrain/amygdala.py:146` | `except Exception: pass` | Metrics | LOW |
| `somabrain/jobs/milvus_reconciliation.py:65` | `except Exception: pass` | Runtime setup | MEDIUM |
| `somabrain/mt_wm.py:96,111,133,151` | `except Exception: pass` | WM metrics | MEDIUM |
| `somabrain/services/segmentation_service.py:203,208` | `except Exception: pass` | Segmentation | MEDIUM |
| `somabrain/workers/outbox_publisher.py:336,439` | `except Exception: pass` | Outbox | HIGH |
| `somabrain/db/outbox.py:261,310` | `except Exception: pass` | DB operations | HIGH |
| `somabrain/db/outbox_clean.py:213,262` | `except Exception: pass` | DB cleanup | HIGH |
| `somabrain/api/memory_api.py:67,575,702,758,883,899` | `except Exception: pass` | Memory API | HIGH |

#### 2.1.7 DEPRECATED CODE STILL IN USE

| File | Line | Deprecated Item | Replacement |
|------|------|-----------------|-------------|
| `common/config/settings/__init__.py:124` | `SOMABRAIN_FORCE_FULL_STACK` | `SOMABRAIN_MODE` |
| `somabrain/infrastructure/__init__.py:179` | `getenv` pattern | Settings attribute |
| `somabrain/api/dependencies/auth.py:28,71,79,93` | Multiple deprecated functions | TenantManager |
| `somabrain/api/routers/features.py:21` | Overrides deprecated | Centralized flags |
| `somabrain/metrics_original.py:856` | Queued write metric | Removed |
| `migrations/versions/20231015_*.py` | Entire file | Remove |

#### 2.1.8 DIRECT os.environ ACCESS (Should Use Settings)

| File | Line | Variable | Action |
|------|------|----------|--------|
| `somabrain/app.py:918` | `os.environ.get("SPHINX_BUILD")` | Move to Settings |
| `somabrain/cli.py:68-69` | `os.environ.get("HOST")`, `os.environ.get("PORT")` | Move to Settings |
| `scripts/check_memory_endpoint.py:11` | `os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"]` | Use Settings |
| `scripts/sb_precheck.py:13-15` | `os.environ.get("KAFKA_PORT")` etc. | Use Settings |
| `scripts/verify_deployment.py:138,173` | `os.environ["SOMABRAIN_JWT_SECRET"]` | Use Settings |
| `scripts/constitution_sign.py:58,62` | `os.environ["SOMABRAIN_POSTGRES_DSN"]` | Use Settings |
| `benchmarks/run_stress.py:105` | `os.environ.get("SOMABRAIN_METRICS_SINK")` | Use Settings |
| `benchmarks/eval_learning_speed.py:138,141` | `os.environ.get("SOMABRAIN_BASE")` | Use Settings |
| `benchmarks/diffusion_predictor_bench.py:77` | `os.environ["SOMA_HEAT_METHOD"]` | Use Settings |
| `conftest.py:12-29` | Multiple `os.environ.setdefault` | Use Settings |
| `tests/unit/test_outbox_sync.py:23` | `os.environ.get("SOMABRAIN_MEMORY_URL")` | Use Settings |
| `tests/integration/*.py` | Multiple `os.environ.get` | Use Settings |

#### 2.1.11 IMPORTLIB LAZY LOADING (Circular Dependency Workarounds)

| File | Line | Pattern | Risk |
|------|------|---------|------|
| `somabrain/app.py:2083-2091` | `importlib.util.spec_from_file_location` | HIGH - runtime module loading |
| `somabrain/hippocampus.py:55-57` | `import_module("somabrain.runtime_module")` | HIGH - circular dep |
| `somabrain/libs/__init__.py:15` | `importlib.import_module(f"libs.{sub}")` | MEDIUM |
| `somabrain/libs/kafka_cog/__init__.py:13-25` | Multiple `importlib.import_module` | MEDIUM |
| `scripts/check_memory_endpoint.py:21` | `importlib.import_module("somabrain.app")` | LOW - script |
| `scripts/initialize_runtime.py:122-137` | `importlib.util` module loading | LOW - script |
| `jwt/__init__.py:22-28` | `importlib.util.spec_from_file_location` | MEDIUM |
| `jwt/exceptions.py:16-22` | `importlib.util.spec_from_file_location` | MEDIUM |

#### 2.1.12 ADDITIONAL DUPLICATE IMPLEMENTATIONS

| Pattern | Locations | Canonical Location |
|---------|-----------|-------------------|
| `np.linalg.norm` normalization | 25+ locations | `somabrain/math/normalize.py` |
| Vector normalization | `app.py`, `wm.py`, `agent_memory.py`, `seed.py`, `embeddings.py`, `schemas.py` | `somabrain/math/normalize.py` |
| Cosine similarity | `benchmarks/nulling_bench.py:52`, `tests/benchmarks/nulling_test.py:34`, `benchmarks/run_stress.py:56` | `somabrain/math/similarity.py` |

#### 2.1.13 TEST FILE VIOLATIONS

| File | Issue | Action |
|------|-------|--------|
| `tests/unit/test_outbox_sync.py:23` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_outbox_durability.py:16-17` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_recall_quality.py:20-22` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_milvus_health.py:67-69` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_e2e_real.py:33-40` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_latency_slo.py:16-18` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/integration/test_memory_workbench.py:11-12` | Direct `os.environ.get` | Use conftest fixtures |
| `tests/conftest.py:18-20` | Direct `os.environ.get` | Use Settings |
| `tests/oak/test_thread.py:21` | Direct `os.environ.get` | Use conftest fixtures |

#### 2.1.9 MISSING DOCSTRINGS (Functions Without Documentation)

| File | Function | Priority |
|------|----------|----------|
| `somabrain/services/orchestrator_service.py:156` | `do_GET` | LOW |
| `somabrain/services/agent_predictor.py:52` | `__init__` | MEDIUM |
| `somabrain/services/segmentation_service.py:52` | `__init__` | MEDIUM |
| `somabrain/services/integrator_hub.py:48` | `__init__` | MEDIUM |
| `somabrain/services/entry.py:124` | `_sig_handler` | LOW |
| `somabrain/services/action_predictor.py:52` | `__init__` | MEDIUM |
| `somabrain/services/recall_service.py:216` | `cos` | LOW |
| `somabrain/exec_controller.py:70` | `__init__` | MEDIUM |
| `somabrain/jobs/milvus_reconciliation.py:38` | `_memory_pool` | MEDIUM |
| `somabrain/quantum.py:74` | `__init__` | HIGH |
| `somabrain/quotas.py:67,79` | `__init__`, `_get_tenant_manager` | MEDIUM |
| `somabrain/api/memory_api.py:344,367,374,381` | Multiple helpers | MEDIUM |

#### 2.1.10 ARCHITECTURAL VIOLATIONS SUMMARY

| Category | Count | Severity |
|----------|-------|----------|
| Circular Import Risks | 9+ modules | HIGH |
| Duplicate Cosine Similarity | 9 implementations | HIGH |
| Duplicate Vector Normalization | 25+ locations | HIGH |
| Hardcoded Magic Numbers | 17+ values | MEDIUM |
| Global State Variables | 20+ variables | HIGH |
| Silent Error Swallowing | 40+ blocks | HIGH |
| Deprecated Code Patterns | 6+ patterns | MEDIUM |
| Missing Docstrings | 15+ functions | LOW |
| Direct os.environ Access | 30+ locations | MEDIUM |
| Importlib Lazy Loading | 8+ locations | HIGH |
| Test File Violations | 9+ files | LOW |

**TOTAL VIOLATIONS: 180+**

---

## 3. Requirements

### Requirement 1: Application Core Decomposition

**User Story:** As a developer, I want the application core to be modular and well-organized, so that I can understand, maintain, and extend the system efficiently.

#### Acceptance Criteria

1. WHEN the application starts THEN the System SHALL load components from discrete, single-responsibility modules with clear dependency injection
2. WHEN a developer examines `somabrain/app.py` THEN the System SHALL present a file under 500 lines containing only FastAPI application setup and router registration
3. WHEN middleware is required THEN the System SHALL load middleware from `somabrain/middleware/` directory with each middleware in its own file
4. WHEN scoring functions are needed THEN the System SHALL import them from `somabrain/scoring/` module hierarchy
5. WHEN bootstrap logic executes THEN the System SHALL delegate to `somabrain/bootstrap/` module for singleton initialization

### Requirement 2: Memory System Consolidation

**User Story:** As a system architect, I want a unified memory system with clear interfaces, so that memory operations are consistent, testable, and maintainable.

#### Acceptance Criteria

1. WHEN memory operations are performed THEN the System SHALL route all operations through a single `MemoryGateway` interface
2. WHEN the memory client is instantiated THEN the System SHALL separate HTTP transport, caching, and business logic into distinct classes
3. WHEN memory payloads are serialized THEN the System SHALL use a dedicated serializer with round-trip verification capability
4. WHEN memory payloads are deserialized THEN the System SHALL use the same serializer ensuring `deserialize(serialize(x)) == x`
5. WHEN working memory and long-term memory interact THEN the System SHALL use explicit interfaces defined in `somabrain/interfaces/memory.py`
6. IF the memory service is unavailable THEN the System SHALL activate circuit breaker and queue operations for replay

### Requirement 3: Configuration System Unification

**User Story:** As an operator, I want a single source of truth for configuration, so that I can reliably configure and deploy the system.

#### Acceptance Criteria

1. WHEN configuration is accessed THEN the System SHALL retrieve values exclusively through the `Settings` singleton
2. WHEN environment variables are read THEN the System SHALL use typed accessor methods (`_int_env`, `_bool_env`, `_float_env`, `_str_env`)
3. WHEN deprecated configuration patterns are detected THEN the System SHALL emit deprecation warnings with migration guidance
4. WHEN configuration is validated THEN the System SHALL verify all required values at startup before accepting requests
5. IF configuration validation fails THEN the System SHALL refuse to start and provide clear error messages

### Requirement 4: Mathematical Component Isolation

**User Story:** As a mathematician/developer, I want mathematical components isolated with formal correctness properties, so that cognitive computations are verifiable and maintainable.

#### Acceptance Criteria

1. WHEN HRR operations are performed THEN the System SHALL execute them through `somabrain/math/hrr.py` with unit-norm invariant preservation
2. WHEN SDR encoding is performed THEN the System SHALL use `somabrain/math/sdr.py` with sparsity guarantees
3. WHEN vector operations are performed THEN the System SHALL maintain numerical stability with explicit dtype enforcement
4. WHEN mathematical functions are tested THEN the System SHALL verify round-trip properties for all encoding/decoding operations
5. WHEN cosine similarity is computed THEN the System SHALL handle zero-norm vectors gracefully returning 0.0

### Requirement 5: Service Layer Architecture

**User Story:** As a developer, I want services to follow clean architecture principles, so that business logic is separated from infrastructure concerns.

#### Acceptance Criteria

1. WHEN a service is created THEN the System SHALL inject dependencies through constructor parameters
2. WHEN services communicate THEN the System SHALL use defined interfaces rather than concrete implementations
3. WHEN a service fails THEN the System SHALL propagate errors with full context and recovery suggestions
4. WHEN services are tested THEN the System SHALL support dependency injection without requiring mocks
5. WHEN circuit breakers activate THEN the System SHALL record metrics and provide health status

### Requirement 6: Cognitive Component Organization

**User Story:** As a cognitive systems developer, I want brain-inspired components organized by function, so that the cognitive architecture is clear and extensible.

#### Acceptance Criteria

1. WHEN the hippocampus component is used THEN the System SHALL handle memory consolidation through `somabrain/cognitive/hippocampus/`
2. WHEN the amygdala component is used THEN the System SHALL compute salience through `somabrain/cognitive/amygdala/`
3. WHEN the thalamus component is used THEN the System SHALL route and filter inputs through `somabrain/cognitive/thalamus/`
4. WHEN the prefrontal component is used THEN the System SHALL provide executive control through `somabrain/cognitive/prefrontal/`
5. WHEN neuromodulators are adjusted THEN the System SHALL maintain state through `somabrain/cognitive/neuromodulators/`

### Requirement 7: API Layer Restructuring

**User Story:** As an API consumer, I want well-organized, documented endpoints, so that I can integrate with the system reliably.

#### Acceptance Criteria

1. WHEN API routes are defined THEN the System SHALL organize them in `somabrain/api/routes/` by domain
2. WHEN request validation fails THEN the System SHALL return structured error responses with field-level details
3. WHEN API documentation is generated THEN the System SHALL produce complete OpenAPI specifications
4. WHEN authentication is required THEN the System SHALL delegate to `somabrain/api/auth/` module
5. WHEN rate limiting is applied THEN the System SHALL use `somabrain/api/middleware/ratelimit.py`

### Requirement 8: Legacy Code Removal

**User Story:** As a maintainer, I want legacy code removed, so that the codebase is clean and free of technical debt.

#### Acceptance Criteria

1. WHEN deprecated functions are identified THEN the System SHALL remove them after migration period
2. WHEN `metrics_original.py` is referenced THEN the System SHALL redirect to `somabrain/metrics/` module
3. WHEN duplicate implementations exist THEN the System SHALL consolidate to single canonical implementation
4. WHEN unused imports are detected THEN the System SHALL remove them
5. WHEN dead code paths are identified THEN the System SHALL remove them with git history preservation

### Requirement 9: Testing Infrastructure

**User Story:** As a QA engineer, I want comprehensive testing infrastructure, so that I can verify system correctness with confidence.

#### Acceptance Criteria

1. WHEN property-based tests are written THEN the System SHALL use Hypothesis framework with minimum 100 iterations
2. WHEN serialization is tested THEN the System SHALL verify round-trip properties
3. WHEN mathematical operations are tested THEN the System SHALL verify invariants (unit-norm, sparsity, bounds)
4. WHEN integration tests run THEN the System SHALL use real backends without mocks
5. WHEN tests fail THEN the System SHALL provide clear failure messages with reproduction steps

### Requirement 10: Observability and Metrics

**User Story:** As an operator, I want comprehensive observability, so that I can monitor and debug the system in production.

#### Acceptance Criteria

1. WHEN metrics are recorded THEN the System SHALL use Prometheus-compatible format through `somabrain/metrics/`
2. WHEN requests are traced THEN the System SHALL propagate trace context through all service calls
3. WHEN errors occur THEN the System SHALL log structured error information with request context
4. WHEN health checks are performed THEN the System SHALL verify all critical dependencies
5. WHEN circuit breakers change state THEN the System SHALL emit metrics and log events

### Requirement 11: Duplicate Code Elimination

**User Story:** As a developer, I want a single canonical implementation for common utilities, so that behavior is consistent and maintenance is simplified.

#### Acceptance Criteria

1. WHEN cosine similarity is computed THEN the System SHALL use the canonical implementation in `somabrain/math/similarity.py`
2. WHEN duplicate implementations are found THEN the System SHALL remove them and redirect to canonical location
3. WHEN utility functions are needed THEN the System SHALL import from `somabrain/core/utils/`
4. WHEN mathematical operations are performed THEN the System SHALL use `somabrain/math/` module hierarchy
5. WHEN code duplication is detected by linting THEN the System SHALL fail the build

### Requirement 12: Global State Elimination

**User Story:** As a developer, I want explicit dependency injection instead of global state, so that code is testable and behavior is predictable.

#### Acceptance Criteria

1. WHEN singletons are required THEN the System SHALL use a dependency injection container in `somabrain/core/container.py`
2. WHEN module-level state is detected THEN the System SHALL refactor to instance-level state with explicit lifecycle
3. WHEN caches are needed THEN the System SHALL use explicit cache instances passed via dependency injection
4. WHEN loggers are configured THEN the System SHALL use structured logging with explicit logger injection
5. WHEN global state is detected by linting THEN the System SHALL emit warnings

### Requirement 13: Error Handling Standardization

**User Story:** As a developer, I want consistent error handling patterns, so that failures are visible and recoverable.

#### Acceptance Criteria

1. WHEN exceptions are caught THEN the System SHALL log the error with full context before any recovery action
2. WHEN `except Exception: pass` patterns are detected THEN the System SHALL replace with explicit error handling
3. WHEN errors occur in background tasks THEN the System SHALL emit metrics and structured logs
4. WHEN circuit breakers trip THEN the System SHALL provide clear error messages with recovery guidance
5. WHEN validation fails THEN the System SHALL return structured error responses with field-level details

### Requirement 14: Configuration Centralization

**User Story:** As an operator, I want all configuration in one place with validation, so that deployment is reliable and errors are caught early.

#### Acceptance Criteria

1. WHEN magic numbers are detected in code THEN the System SHALL move them to Settings with typed accessors
2. WHEN `os.environ` or `os.getenv` is used directly THEN the System SHALL replace with Settings attributes
3. WHEN configuration is loaded THEN the System SHALL validate all required values at startup
4. WHEN deprecated configuration patterns are used THEN the System SHALL emit deprecation warnings
5. WHEN configuration changes THEN the System SHALL support hot-reload where safe

### Requirement 15: Circular Dependency Resolution

**User Story:** As a developer, I want clean import graphs without cycles, so that the codebase is maintainable and startup is predictable.

#### Acceptance Criteria

1. WHEN lazy imports are detected THEN the System SHALL refactor to eliminate the circular dependency
2. WHEN metrics are needed THEN the System SHALL use a metrics interface that can be imported without cycles
3. WHEN runtime singletons are accessed THEN the System SHALL use dependency injection instead of module imports
4. WHEN import cycles are detected by tooling THEN the System SHALL fail the build
5. WHEN modules are loaded THEN the System SHALL complete without deferred imports

---

## 4. Proposed Architecture

### 4.1 Module Hierarchy

```
somabrain/
├── api/                    # API layer
│   ├── routes/            # Route handlers by domain
│   ├── middleware/        # Request/response middleware
│   ├── auth/              # Authentication/authorization
│   └── schemas/           # Request/response schemas
├── bootstrap/             # Application initialization
├── cognitive/             # Brain-inspired components
│   ├── amygdala/         # Salience computation
│   ├── hippocampus/      # Memory consolidation
│   ├── prefrontal/       # Executive control
│   ├── thalamus/         # Input routing/filtering
│   └── neuromodulators/  # State modulation
├── core/                  # Core utilities
│   ├── config/           # Configuration management
│   ├── logging/          # Logging setup
│   └── validation/       # Input validation
├── infrastructure/        # External service integration
│   ├── circuit_breaker/  # Fault tolerance
│   ├── http/             # HTTP client utilities
│   └── messaging/        # Kafka/event handling
├── math/                  # Mathematical operations
│   ├── hrr/              # Holographic representations
│   ├── sdr/              # Sparse distributed representations
│   └── numerics/         # Numerical utilities
├── memory/               # Memory system
│   ├── gateway/          # Unified memory interface
│   ├── working/          # Working memory
│   ├── longterm/         # Long-term memory
│   └── serialization/    # Payload serialization
├── metrics/              # Observability
├── services/             # Business logic services
└── testing/              # Test utilities
```

### 4.2 Dependency Flow

```
API Layer → Services → Memory/Cognitive → Math → Core
              ↓
        Infrastructure
```

---

## 5. Migration Strategy

### 5.1 Phase 1: Foundation (Weeks 1-2)
- Extract configuration to unified Settings
- Create interface definitions
- Set up new module structure

### 5.2 Phase 2: Core Decomposition (Weeks 3-4)
- Decompose `app.py` into modules
- Extract middleware to dedicated files
- Separate bootstrap logic

### 5.3 Phase 3: Memory Consolidation (Weeks 5-6)
- Create MemoryGateway interface
- Refactor MemoryClient into components
- Implement serialization with round-trip tests

### 5.4 Phase 4: Cognitive Organization (Weeks 7-8)
- Reorganize brain-inspired components
- Standardize interfaces
- Add property-based tests

### 5.5 Phase 5: Legacy Removal (Weeks 9-10)
- Remove deprecated code
- Consolidate duplicates
- Final cleanup and documentation

---

## 6. Success Criteria

1. No file exceeds 500 lines of code
2. All VIBE Coding Rules violations resolved
3. 100% of serialization operations have round-trip tests
4. All deprecated functions removed
5. Configuration accessed only through Settings singleton
6. Property-based tests for all mathematical operations
7. Clear module boundaries with no circular imports
8. Complete OpenAPI documentation
9. All integration tests pass with real backends
10. Metrics coverage for all critical paths

---

## 7. Appendix: VIBE Coding Rules Summary

The refactoring must adhere to these principles:

1. **NO BULLSHIT**: No lies, guesses, invented APIs, mocks, placeholders, stubs, or TODOs
2. **CHECK FIRST, CODE SECOND**: Review existing architecture before writing code
3. **NO UNNECESSARY FILES**: Modify existing files unless new file is unavoidable
4. **REAL IMPLEMENTATIONS ONLY**: Production-grade code, no fake returns
5. **DOCUMENTATION = TRUTH**: Read and cite documentation proactively
6. **COMPLETE CONTEXT REQUIRED**: Understand full data flow before modifications
7. **REAL DATA & SERVERS ONLY**: Use real data structures and verify APIs

---

*Document prepared following ISO-style structure for clarity and professional documentation standards.*
