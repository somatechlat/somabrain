# Requirements Document - Complete VIBE Compliance Sweep

## Introduction

This specification defines the requirements for a COMPLETE sweep of the SomaBrain codebase to eliminate ALL VIBE rule violations. This includes:
- Legacy API endpoints (`/remember`, `/recall`, `/delete`, `/recall/delete`)
- Fake/Mock/Stub/Dummy classes in production and test code
- Fallback patterns and shims
- Legacy compatibility code
- All references to removed functionality

The goal is HARD DELETE - no legacy code, no mentions, as if it never existed.

## Glossary

- **Legacy Endpoints**: The original `/remember`, `/recall`, `/delete`, `/recall/delete` endpoints in `somabrain/routers/memory.py`
- **Canonical Endpoints**: The new `/memory/remember`, `/memory/recall` endpoints in `somabrain/api/memory_api.py`
- **VIBE Rules**: The project's coding standards requiring no duplicate code, no legacy paths, no dead code, no mocks, no stubs, no placeholders
- **Consumer**: Any code that calls the legacy endpoints (benchmarks, tests, scripts, clients)
- **Fake Class**: Any class prefixed with Fake/Mock/Dummy/Stub that violates VIBE Rule 1

## Current State

### Legacy Endpoints (TO BE REMOVED)
| Endpoint | File | Purpose |
|----------|------|---------|
| `POST /remember` | `somabrain/routers/memory.py` | Store memory (LEGACY) |
| `POST /recall` | `somabrain/routers/memory.py` | Search memories (LEGACY) |
| `POST /delete` | `somabrain/routers/memory.py` | Delete memory (LEGACY) |
| `POST /recall/delete` | `somabrain/routers/memory.py` | Delete via recall API (LEGACY) |

### Canonical Endpoints (TO USE)
| Endpoint | File | Purpose |
|----------|------|---------|
| `POST /memory/remember` | `somabrain/api/memory_api.py` | Store memory |
| `POST /memory/remember/batch` | `somabrain/api/memory_api.py` | Batch store memories |
| `POST /memory/recall` | `somabrain/api/memory_api.py` | Search memories |
| `POST /memory/recall/stream` | `somabrain/api/memory_api.py` | Streaming recall |

## Requirements

### Requirement 1: Remove Legacy Router

**User Story:** As a developer, I want the legacy memory router removed, so that there is only one canonical API surface for memory operations.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN the `somabrain/routers/memory.py` file SHALL be deleted
2. WHEN the router is removed THEN the system SHALL remove all imports of the legacy router from `somabrain/app.py`
3. WHEN the router is removed THEN the system SHALL verify no other files import from `somabrain/routers/memory`

### Requirement 2: Update Benchmark Files

**User Story:** As a developer, I want all benchmarks to use the canonical endpoints, so that benchmarks test the production API surface.

#### Acceptance Criteria

1. WHEN `benchmarks/plan_bench.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
2. WHEN `benchmarks/plan_bench.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
3. WHEN `benchmarks/agent_coding_bench.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
4. WHEN `benchmarks/agent_coding_bench.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
5. WHEN `benchmarks/eval_retrieval_precision.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
6. WHEN `benchmarks/http_bench.py` defaults to `/recall` THEN the system SHALL update to `/memory/recall`
7. WHEN `benchmarks/eval_learning_speed.py` calls `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
8. WHEN `benchmarks/scale/run_remember_recall.py` calls `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
9. WHEN `benchmarks/scale/run_remember_recall_scaled.py` calls `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
10. WHEN `benchmarks/scale/load_soak_spike.py` uses `/recall` THEN the system SHALL update to `/memory/recall`
11. WHEN `benchmarks/scale/scale_bench.py` uses `/recall` THEN the system SHALL update to `/memory/recall`

### Requirement 3: Update Integration Tests

**User Story:** As a developer, I want all integration tests to use the canonical endpoints, so that tests validate the production API.

#### Acceptance Criteria

1. WHEN `tests/integration/test_recall_quality.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
2. WHEN `tests/integration/test_recall_quality.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
3. WHEN `tests/integration/test_memory_workbench.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
4. WHEN `tests/integration/test_memory_workbench.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
5. WHEN `tests/integration/test_latency_slo.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
6. WHEN `tests/integration/test_latency_slo.py` calls `/recall` THEN the system SHALL update to `/memory/recall`
7. WHEN `tests/integration/test_e2e_real.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
8. WHEN `tests/integration/test_e2e_real.py` calls `/recall` THEN the system SHALL update to `/memory/recall`

### Requirement 4: Update Scripts

**User Story:** As a developer, I want all scripts to use the canonical endpoints, so that operational tooling works with the production API.

#### Acceptance Criteria

1. WHEN `scripts/seed_bench_data.py` calls `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
2. WHEN `scripts/devprod_smoke.py` calls `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
3. WHEN any script in `scripts/` calls legacy endpoints THEN the system SHALL update to canonical endpoints

### Requirement 5: Update Python Client

**User Story:** As a developer, I want the Python client to use the canonical endpoints, so that client users interact with the production API.

#### Acceptance Criteria

1. WHEN `clients/python/somabrain_client.py` calls `/remember` THEN the system SHALL update to `/memory/remember`
2. WHEN `clients/python/somabrain_client.py` calls `/recall` THEN the system SHALL update to `/memory/recall`

### Requirement 6: Verify No Remaining Legacy References

**User Story:** As a developer, I want verification that no legacy endpoint references remain, so that the cleanup is complete.

#### Acceptance Criteria

1. WHEN a grep search for `"/remember"` is performed THEN the system SHALL return zero matches in production code (excluding comments explaining the migration)
2. WHEN a grep search for `"/recall"` is performed THEN the system SHALL return zero matches in production code (excluding `/memory/recall` and comments)
3. WHEN the application starts THEN the system SHALL NOT expose `/remember` or `/recall` endpoints

### Requirement 7: Update Documentation

**User Story:** As a developer, I want documentation to reflect only the canonical endpoints, so that users know the correct API surface.

#### Acceptance Criteria

1. WHEN `README.md` references `/remember` THEN the system SHALL update to `/memory/remember`
2. WHEN `README.md` references `/recall` THEN the system SHALL update to `/memory/recall`
3. WHEN `docs/development/testing-guidelines.md` references legacy endpoints THEN the system SHALL update to canonical endpoints
4. WHEN `docs/benchmarks/README.md` references legacy endpoints THEN the system SHALL update to canonical endpoints

### Requirement 8: Remove Fake/Mock/Stub Classes

**User Story:** As a developer, I want all Fake/Mock/Stub classes removed from the codebase, so that tests use real implementations per VIBE Rule 1.

#### Acceptance Criteria

1. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` contains `FakePredictor` THEN the system SHALL delete the class
2. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` contains `FakeNeuromods` THEN the system SHALL delete the class
3. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` contains `FakePersonalityStore` THEN the system SHALL delete the class
4. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` contains `FakeAmygdala` THEN the system SHALL delete the class
5. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` contains `Simple*` classes THEN the system SHALL delete those classes
6. WHEN the test file cannot function without fake classes THEN the system SHALL delete the entire test file

### Requirement 9: Remove Fallback Patterns

**User Story:** As a developer, I want all fallback patterns removed, so that the system fails fast on errors per VIBE rules.

#### Acceptance Criteria

1. WHEN `somabrain/memory/transport.py` contains `_fallback_to_localhost()` THEN the system SHALL remove the method and all calls to it
2. WHEN code contains fallback logic that silently degrades THEN the system SHALL remove it and fail explicitly

### Requirement 10: Remove Legacy Comments and References

**User Story:** As a developer, I want all legacy comments and references removed, so that the codebase appears as if legacy code never existed.

#### Acceptance Criteria

1. WHEN `somabrain/metrics_original.py` docstring contains "Legacy" THEN the system SHALL remove the legacy reference
2. WHEN `somabrain/cli.py` contains "Legacy code expects" THEN the system SHALL remove the comment
3. WHEN `somabrain/quotas.py` contains "Falls back to legacy" THEN the system SHALL remove the comment
4. WHEN `somabrain/common/kafka.py` contains "legacy environment variables" THEN the system SHALL remove the comment
5. WHEN `somabrain/numerics.py` contains "Legacy compatibility" comments THEN the system SHALL remove all such comments
6. WHEN `somabrain/numerics.py` uses `mode: str = "legacy_zero"` THEN the system SHALL change default to "robust"

### Requirement 11: Remove Stub References from Health Schema

**User Story:** As a developer, I want stub references removed from health responses, so that the API reflects reality.

#### Acceptance Criteria

1. WHEN `somabrain/schemas/health.py` contains `stub_counts` field THEN the system SHALL remove the field
2. WHEN `somabrain/routers/health.py` references `stub_counts` THEN the system SHALL remove those references

### Requirement 12: Remove unittest.mock Usage

**User Story:** As a developer, I want unittest.mock removed from tests, so that tests validate real behavior per VIBE rules.

#### Acceptance Criteria

1. WHEN `tests/property/test_settings_properties.py` imports `unittest.mock` THEN the system SHALL remove the import and rewrite tests to use real services

### Requirement 13: Update Internal Middleware References

**User Story:** As a developer, I want internal middleware to reference canonical endpoints, so that validation and policy enforcement work correctly.

#### Acceptance Criteria

1. WHEN `somabrain/middleware/validation_handler.py` references `/remember` or `/recall` THEN the system SHALL update to `/memory/remember` and `/memory/recall`
2. WHEN `somabrain/controls/middleware.py` references `/remember` THEN the system SHALL update to `/memory/remember`
3. WHEN `somabrain/controls/policy.py` references `/remember` THEN the system SHALL update to `/memory/remember`

### Requirement 14: Remove Shim Terminology

**User Story:** As a developer, I want all "shim" terminology removed from the codebase, so that code appears production-grade without compatibility layers.

#### Acceptance Criteria

1. WHEN `somabrain/common/kafka.py` contains `_ProducerShim` THEN the system SHALL rename to `_KafkaProducerAdapter` or similar
2. WHEN `somabrain/adaptive/core.py` contains "Compatibility shim" THEN the system SHALL remove the reference
3. WHEN `somabrain/hippocampus.py` contains "shim" THEN the system SHALL remove the reference
4. WHEN `somabrain/schemas.py` contains "Compatibility Shim" THEN the system SHALL remove the reference

### Requirement 15: Remove Stub Backend from Tests

**User Story:** As a developer, I want stub backends removed from tests, so that tests validate real behavior.

#### Acceptance Criteria

1. WHEN `tests/unit/test_memory_service.py` contains `_StubBackend` THEN the system SHALL remove the class and use real backend
2. WHEN tests cannot function without stubs THEN the system SHALL add skip markers for unavailable services

### Requirement 16: Remove Test Bypass Comments

**User Story:** As a developer, I want test bypass comments removed from production code, so that the codebase appears clean.

#### Acceptance Criteria

1. WHEN `somabrain/app.py` contains "Test environment bypass" THEN the system SHALL remove the comment section
2. WHEN `somabrain/app.py` contains "test-mode bypass" THEN the system SHALL remove the reference

## COMPREHENSIVE VIOLATIONS FOUND

### Category 1: Legacy Endpoints (CRITICAL)

| File | Violation | Action |
|------|-----------|--------|
| `somabrain/routers/memory.py` | Entire legacy router with `/remember`, `/recall`, `/delete` | DELETE FILE |
| `somabrain/routers/__init__.py` | Exports `memory_router` | REMOVE EXPORT |
| `somabrain/app.py` | Imports and registers `memory_router` | REMOVE IMPORT AND REGISTRATION |

### Category 2: Fake/Mock/Stub Classes (VIBE Rule 1 Violation)

| File | Class | Action |
|------|-------|--------|
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `FakePredictor` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `FakeNeuromods` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `FakePersonalityStore` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `FakeAmygdala` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `SimplePredictor` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `SimpleNeuromods` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `SimplePersonalityStore` | DELETE |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | `SimpleAmygdala` | DELETE |

### Category 3: Legacy Endpoint Consumers (Must Update)

| File | Current | Target |
|------|---------|--------|
| `benchmarks/plan_bench.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `benchmarks/agent_coding_bench.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `benchmarks/eval_retrieval_precision.py` | `/recall` | `/memory/recall` |
| `benchmarks/http_bench.py` | `/recall` | `/memory/recall` |
| `benchmarks/eval_learning_speed.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `benchmarks/scale/run_remember_recall.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `benchmarks/scale/run_remember_recall_scaled.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `benchmarks/scale/load_soak_spike.py` | `/recall` | `/memory/recall` |
| `benchmarks/scale/scale_bench.py` | `/recall` | `/memory/recall` |
| `scripts/seed_bench_data.py` | `/remember` | `/memory/remember` |
| `tests/integration/test_recall_quality.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `tests/integration/test_memory_workbench.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `tests/integration/test_latency_slo.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `clients/python/somabrain_client.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `somabrain/memory_cli.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |
| `somabrain/controls/middleware.py` | `/remember` references | `/memory/remember` |
| `somabrain/controls/policy.py` | `/remember` references | `/memory/remember` |
| `somabrain/middleware/validation_handler.py` | `/remember`, `/recall` | `/memory/remember`, `/memory/recall` |

### Category 4: Fallback Patterns (Must Remove)

| File | Pattern | Action |
|------|---------|--------|
| `somabrain/memory/transport.py` | `_fallback_to_localhost()` method | REMOVE - no fallbacks allowed |
| `somabrain/adaptive/core.py` | "Compatibility shim for legacy AdaptiveCore API" | EVALUATE - remove if not needed |
| `somabrain/numerics.py` | `mode: str = "legacy_zero"` | CHANGE to robust mode, remove legacy |

### Category 5: Legacy Comments/References (Must Clean)

| File | Issue | Action |
|------|-------|--------|
| `somabrain/metrics_original.py` | "Legacy Re-export Layer" in docstring | REMOVE legacy reference |
| `somabrain/cli.py` | "Legacy code expects" comment | REMOVE legacy reference |
| `somabrain/quotas.py` | "Falls back to legacy behaviour" comment | REMOVE legacy reference |
| `somabrain/common/kafka.py` | "legacy environment variables" comment | REMOVE legacy reference |
| `somabrain/numerics.py` | Multiple "Legacy compatibility" comments | REMOVE all legacy references |
| `somabrain/schemas/health.py` | `stub_counts` field | REMOVE - no stubs exist |
| `somabrain/routers/health.py` | `stub_counts` references | REMOVE - no stubs exist |

### Category 6: unittest.mock Usage (VIBE Rule 1 Violation)

| File | Usage | Action |
|------|-------|--------|
| `tests/property/test_settings_properties.py` | `from unittest import mock` | REMOVE - use real services |

### Category 7: Shim Classes (VIBE Rule 1 Violation)

| File | Class/Pattern | Action |
|------|---------------|--------|
| `somabrain/common/kafka.py` | `_ProducerShim` class | RENAME to proper name, remove "shim" terminology |
| `somabrain/adaptive/core.py` | "Compatibility shim" in docstring | REMOVE shim reference |
| `somabrain/hippocampus.py` | "shim" in docstring | REMOVE shim reference |
| `somabrain/schemas.py` | "Compatibility Shim" in docstring | REMOVE shim reference |
| `tests/integration/test_milvus_health.py` | "marshmallow compatibility shim" | REMOVE shim reference |

### Category 8: _StubBackend and NoOp Classes (VIBE Rule 1 Violation)

| File | Class | Action |
|------|-------|--------|
| `tests/unit/test_memory_service.py` | `_StubBackend` class | DELETE - use real backend |
| `somabrain/metrics/interface.py` | `_NoOpMetric` class | EVALUATE - may be needed for disabled metrics |

### Category 9: NotImplementedError in Production Code

| File | Location | Action |
|------|----------|--------|
| `somabrain/services/recall_service.py` | `raise NotImplementedError("diversify_payloads supports only method='mmr'")` | IMPLEMENT or REMOVE unsupported code path |

### Category 10: Bypass/Test Environment References

| File | Pattern | Action |
|------|---------|--------|
| `somabrain/app.py` | "Test environment bypass" comment | REMOVE - no test bypasses in production |
| `somabrain/app.py` | "test-mode bypass" comment | REMOVE |
| `tests/support/test_targets.py` | `bypass_lock_checks` field | EVALUATE - may be needed for CI |

## Files Summary

### Files to DELETE

| File | Reason |
|------|--------|
| `somabrain/routers/memory.py` | Legacy router with duplicate endpoints |
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | Contains only Fake classes - rewrite or delete |

### Files to MODIFY (Remove Legacy Router)

| File | Changes Needed |
|------|----------------|
| `somabrain/routers/__init__.py` | Remove `memory_router` import and export |
| `somabrain/app.py` | Remove `memory_router` import and `include_router` call |

### Files to MODIFY (Update Endpoint Paths)

| File | Changes Needed |
|------|----------------|
| `benchmarks/plan_bench.py` | Update `/remember` → `/memory/remember`, `/recall` → `/memory/recall` |
| `benchmarks/agent_coding_bench.py` | Update endpoint paths |
| `benchmarks/eval_retrieval_precision.py` | Update `/recall` → `/memory/recall` |
| `benchmarks/http_bench.py` | Update default URL |
| `benchmarks/eval_learning_speed.py` | Update endpoint paths |
| `benchmarks/scale/run_remember_recall.py` | Update endpoint paths |
| `benchmarks/scale/run_remember_recall_scaled.py` | Update endpoint paths |
| `benchmarks/scale/load_soak_spike.py` | Update endpoint path |
| `benchmarks/scale/scale_bench.py` | Update endpoint path |
| `scripts/seed_bench_data.py` | Update endpoint path |
| `tests/integration/test_recall_quality.py` | Update endpoint paths |
| `tests/integration/test_memory_workbench.py` | Update endpoint paths |
| `tests/integration/test_latency_slo.py` | Update endpoint paths |
| `clients/python/somabrain_client.py` | Update endpoint paths |
| `somabrain/memory_cli.py` | Update endpoint paths |
| `somabrain/controls/middleware.py` | Update endpoint references |
| `somabrain/controls/policy.py` | Update endpoint references |
| `somabrain/middleware/validation_handler.py` | Update endpoint references |

### Files to MODIFY (Remove Legacy/Fallback Code)

| File | Changes Needed |
|------|----------------|
| `somabrain/memory/transport.py` | Remove `_fallback_to_localhost()` method |
| `somabrain/metrics_original.py` | Remove "Legacy" from docstring |
| `somabrain/cli.py` | Remove legacy comment |
| `somabrain/quotas.py` | Remove legacy comment |
| `somabrain/common/kafka.py` | Remove legacy comment |
| `somabrain/numerics.py` | Remove legacy mode and comments |
| `somabrain/schemas/health.py` | Remove `stub_counts` field |
| `somabrain/routers/health.py` | Remove `stub_counts` references |
| `tests/property/test_settings_properties.py` | Remove unittest.mock usage |

### Files to MODIFY (Remove Shim/Stub Terminology)

| File | Changes Needed |
|------|----------------|
| `somabrain/common/kafka.py` | Rename `_ProducerShim` to `_KafkaProducerAdapter` |
| `somabrain/adaptive/core.py` | Remove "Compatibility shim" from docstring |
| `somabrain/hippocampus.py` | Remove "shim" from docstring |
| `somabrain/schemas.py` | Remove "Compatibility Shim" from docstring |
| `tests/unit/test_memory_service.py` | Remove `_StubBackend` class |
| `somabrain/app.py` | Remove "Test environment bypass" comments |

### Files to MODIFY (Documentation)

| File | Changes Needed |
|------|----------------|
| `README.md` | Update endpoint references |
| `docs/development/testing-guidelines.md` | Update endpoint references |
| `docs/benchmarks/README.md` | Update endpoint references |

## Sweep Status

### Folders Swept
- [x] `.kiro/` - Clean (spec files only)
- [x] `benchmarks/` - 11 files need endpoint updates
- [x] `clients/` - 1 file needs endpoint updates
- [x] `common/` - 1 file needs shim rename
- [x] `config/` - Clean
- [x] `docs/` - Documentation updates needed
- [x] `infra/` - Clean
- [x] `libs/` - Clean
- [x] `scripts/` - 1 file needs endpoint updates
- [x] `services/` - Clean
- [x] `somabrain/` - Multiple violations found
- [x] `tests/` - Multiple violations found

### Total Violations Found
- **Files to DELETE**: 2
- **Files to MODIFY**: 35+
- **Legacy endpoint references**: 18 files
- **Fake/Mock/Stub classes**: 9 classes in 2 files
- **Shim terminology**: 5 files
- **Legacy comments**: 6 files
- **Fallback patterns**: 2 files
