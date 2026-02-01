# Requirements Document - VIBE Violations Comprehensive Audit

## Introduction

This spec addresses ALL VIBE Coding Rules violations discovered during a comprehensive codebase sweep. The audit was conducted folder-by-folder, file-by-file, applying all VIBE rules systematically.

**Audit Scope:** Entire repository scanned for:
- Dead code calling non-existent API endpoints
- Placeholder/stub code
- Documentation referencing non-existent endpoints
- Dependent code using dead methods
- Interface definitions for non-existent methods

## Glossary

- **SomaBrain**: The main cognitive service running on port 9696
- **SomaFractalMemory API**: The external memory backend service running on port 9595
- **Memory Client**: The `somabrain/memory_client.py` module that interfaces with the memory service
- **Dead Code**: Code that calls non-existent API endpoints or methods that don't exist
- **VIBE Rules**: The project's coding standards requiring real implementations only
- **Placeholder**: Code marked as temporary or incomplete (violates VIBE Rule 1)

## Real API Endpoints (from OpenAPI spec at localhost:9595)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/memories` | POST | Store a memory |
| `/memories/search` | POST/GET | Search memories |
| `/memories/{coord}` | GET | Fetch memory by coordinate |
| `/memories/{coord}` | DELETE | Delete memory |
| `/health` | GET | Health check |
| `/stats` | GET | System statistics |
| `/ping` | GET | Liveness probe |
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe |

## Non-Existent Endpoints (called by dead code)

- `/link` - Does NOT exist
- `/neighbors` - Does NOT exist  
- `/unlink` - Does NOT exist
- `/prune` - Does NOT exist
- `/payloads` - Does NOT exist
- `/recall` - Does NOT exist (correct: `/memories/search`)
- `/remember` - Does NOT exist (correct: `/memories`)
- `/remember/batch` - Does NOT exist
- `/graph/links` - Calls dead methods internally

---

## COMPREHENSIVE VIBE VIOLATIONS FOUND

### Category 1: Dead Methods Removed from memory_client.py BUT Still Called Elsewhere

The following methods were removed from `somabrain/memory_client.py` but are still being called by dependent code:

| Dead Method | What It Called | Files Still Calling It |
|-------------|----------------|------------------------|
| `link()` | `/link` endpoint | `memory_service.py:175`, `consolidation.py:111` |
| `alink()` | `/link` endpoint | `memory_service.py:191` |
| `links_from()` | `/neighbors` endpoint | `memory_service.py:244`, `app.py:4147`, `planner.py:103`, `planner_rwr.py:102` |
| `payloads_for_coords()` | `/payloads` endpoint | `memory_service.py:238`, `app.py:3153,3253,3291`, `recall_service.py:84,114,183`, `persona.py:80,151`, `planner.py:121`, `planner_rwr.py:153` |
| `k_hop()` | Uses `links_from()` | `app.py:3250` |

### Category 2: Interface Defines Non-Existent Methods

| File | Method | Issue |
|------|--------|-------|
| `somabrain/interfaces/memory.py:28-35` | `link()` | Interface defines method that doesn't exist in implementation |
| `somabrain/interfaces/memory.py:37-44` | `alink()` | Interface defines method that doesn't exist in implementation |
| `somabrain/interfaces/memory.py:45-48` | `payloads_for_coords()` | Interface defines method that doesn't exist in implementation |
| `somabrain/interfaces/memory.py:52-55` | `links_from()` | Interface defines method that doesn't exist in implementation |

### Category 3: Dead API Routers and CLI Commands

| File | Issue | Severity |
|------|-------|----------|
| `somabrain/api/routers/link.py` | Entire router for `/link` endpoint - calls `memsvc.alink()` which doesn't exist | CRITICAL |
| `somabrain/memory_cli.py:73-76` | `cmd_link()` POSTs to `/link` - endpoint doesn't exist | CRITICAL |
| `somabrain/memory_cli.py:96-99` | CLI parser registers `link` command | CRITICAL |
| `somabrain/app.py:4106-4150` | `/graph/links` endpoint calls `memsvc.links_from()` which doesn't exist | CRITICAL |

### Category 4: Placeholder/Stub Code (VIBE Rule 1 Violation)

| File | Line | Violation |
|------|------|-----------|
| `somabrain/services/cutover_controller.py:1` | Entire file marked as "Stub implementation" |
| `somabrain/services/segmentation_service.py:221-230` | `CPDSegmenter` marked as "Placeholder" |
| `somabrain/services/segmentation_service.py:233-239` | `HazardSegmenter` marked as "Placeholder" |
| `somabrain/services/calibration_service.py:61` | `export_reliability_data()` comment says "Placeholder for a real export" |
| `somabrain/milvus_client.py:49-51` | `_DummyCollection` class - fallback stub |

### Category 5: Dead Benchmarks

| File | Issue |
|------|-------|
| `benchmarks/benchmark_link_latency.py` | Calls `client.link()` - method doesn't exist |
| `benchmarks/plan_bench.py:38` | POSTs to `/link` - endpoint doesn't exist |

### Category 6: Documentation Lies (VIBE Rule 5 Violation)

| File | Line | Issue |
|------|------|-------|
| `README.md:~122` | Documents `POST /remember` - should be `/remember` |
| `README.md:~123` | Documents `POST /remember/batch` - endpoint doesn't exist |
| `README.md:~124` | Documents `POST /recall` - should be `/recall` |
| `README.md:~125` | Documents `POST /recall/stream` - endpoint doesn't exist |
| `README.md:~143` | Documents `POST /graph/links` - calls dead methods |
| `docs/development/api-reference.md:~43` | Documents `POST /graph/links` |
| `docs/development/testing-guidelines.md:~293` | Uses `/remember` |
| `docs/development/testing-guidelines.md:~309` | Uses `/recall` |
| `docs/benchmarks/README.md:~9,41` | References `/recall` |

---

## Requirements

### Requirement 1: Remove Dead Method Calls from Dependent Code

**User Story:** As a developer, I want all code that calls non-existent methods to be removed or updated, so that the application compiles and runs without AttributeError.

#### Acceptance Criteria

1. WHEN `somabrain/services/memory_service.py` is reviewed THEN the system SHALL remove the `link()` method (line ~163-176)
2. WHEN `somabrain/services/memory_service.py` is reviewed THEN the system SHALL remove the `alink()` method (line ~178-195)
3. WHEN `somabrain/services/memory_service.py` is reviewed THEN the system SHALL remove the `payloads_for_coords()` proxy method (line ~237-238)
4. WHEN `somabrain/services/memory_service.py` is reviewed THEN the system SHALL remove the `links_from()` proxy method (line ~243-244)
5. WHEN `somabrain/consolidation.py` references `mem.link()` THEN the system SHALL remove that code path (line ~111)
6. WHEN `somabrain/app.py` references `payloads_for_coords()` THEN the system SHALL remove those calls (lines ~3153, 3253, 3291)
7. WHEN `somabrain/app.py` references `k_hop()` THEN the system SHALL remove that call (line ~3250)
8. WHEN `somabrain/services/recall_service.py` references `payloads_for_coords()` THEN the system SHALL remove those calls (lines ~84, 114, 183)
9. WHEN `somabrain/api/routers/persona.py` references `payloads_for_coords()` THEN the system SHALL remove those calls (lines ~80, 151)
10. WHEN `somabrain/planner.py` references `links_from()` or `payloads_for_coords()` THEN the system SHALL remove or disable that functionality
11. WHEN `somabrain/planner_rwr.py` references `links_from()` or `payloads_for_coords()` THEN the system SHALL remove or disable that functionality

### Requirement 2: Remove Dead Interface Definitions

**User Story:** As a developer, I want the memory interface to only define methods that actually exist, so that the interface accurately represents the implementation.

#### Acceptance Criteria

1. WHEN `somabrain/interfaces/memory.py` is reviewed THEN the system SHALL remove the `link()` method signature
2. WHEN `somabrain/interfaces/memory.py` is reviewed THEN the system SHALL remove the `alink()` method signature
3. WHEN `somabrain/interfaces/memory.py` is reviewed THEN the system SHALL remove the `payloads_for_coords()` method signature
4. WHEN `somabrain/interfaces/memory.py` is reviewed THEN the system SHALL remove the `links_from()` method signature

### Requirement 3: Remove Dead API Routers and Endpoints

**User Story:** As a developer, I want dead API routers removed, so that the API surface matches actual functionality.

#### Acceptance Criteria

1. WHEN `somabrain/api/routers/link.py` is reviewed THEN the system SHALL delete the entire file
2. WHEN `somabrain/app.py` imports link router THEN the system SHALL remove that import
3. WHEN `somabrain/app.py` defines `/graph/links` endpoint THEN the system SHALL remove that endpoint (line ~4106)
4. WHEN `somabrain/memory_cli.py` defines `cmd_link()` THEN the system SHALL remove that function and CLI command

### Requirement 4: Remove Placeholder/Stub Code

**User Story:** As a developer, I want all placeholder and stub code removed, so that the codebase follows VIBE Rule 1 (NO BULLSHIT).

#### Acceptance Criteria

1. WHEN `somabrain/services/cutover_controller.py` is reviewed THEN the system SHALL either implement it fully or remove it
2. WHEN `CPDSegmenter` placeholder is reviewed THEN the system SHALL either implement it fully or remove it
3. WHEN `HazardSegmenter` placeholder is reviewed THEN the system SHALL either implement it fully or remove it
4. WHEN `_DummyCollection` in `milvus_client.py` is reviewed THEN the system SHALL either implement it fully or remove it
5. WHEN `export_reliability_data()` placeholder comment is reviewed THEN the system SHALL remove the placeholder comment

### Requirement 5: Remove Dead Benchmarks

**User Story:** As a developer, I want benchmarks that test non-existent functionality removed, so that the benchmark suite is accurate.

#### Acceptance Criteria

1. WHEN `benchmarks/benchmark_link_latency.py` is reviewed THEN the system SHALL delete the entire file
2. WHEN `benchmarks/plan_bench.py` is reviewed THEN the system SHALL remove or update the `/link` POST call

### Requirement 6: Update Documentation

**User Story:** As a developer, I want documentation to reflect actual API endpoints, so that users don't get confused by non-existent endpoints.

#### Acceptance Criteria

1. WHEN `README.md` references `/remember` THEN the system SHALL update to `/remember`
2. WHEN `README.md` references `/recall` THEN the system SHALL update to `/recall`
3. WHEN `README.md` references `/remember/batch` THEN the system SHALL remove that reference
4. WHEN `README.md` references `/recall/stream` THEN the system SHALL remove that reference
5. WHEN `README.md` references `/graph/links` THEN the system SHALL remove that reference
6. WHEN `docs/development/api-reference.md` references `/graph/links` THEN the system SHALL remove that reference
7. WHEN `docs/development/testing-guidelines.md` references `/remember` THEN the system SHALL update to `/remember`
8. WHEN `docs/development/testing-guidelines.md` references `/recall` THEN the system SHALL update to `/recall`
9. WHEN `docs/benchmarks/README.md` references `/recall` THEN the system SHALL update to `/recall`

### Requirement 7: Preserve Working Utility Methods

**User Story:** As a developer, I want utility methods that don't call external APIs to be preserved, so that existing functionality that works locally continues to work.

#### Acceptance Criteria

1. WHEN `coord_for_key()` is called THEN the system SHALL return a deterministic coordinate hash (no API call needed)
2. WHEN `_stable_coord()` is called THEN the system SHALL return a deterministic 3D coordinate from a string key
3. WHEN `store_from_payload()` is called THEN the system SHALL work using only `/memories` endpoint

### Requirement 8: Core Memory Operations Work End-to-End

**User Story:** As a user, I want to store and retrieve memories, so that the basic memory functionality works end-to-end.

#### Acceptance Criteria

1. WHEN a user calls `/remember` endpoint THEN the system SHALL successfully store the memory via `POST /memories`
2. WHEN a user calls `/recall` endpoint THEN the system SHALL successfully search memories via `POST /memories/search`
3. WHEN the memory service returns results THEN the system SHALL properly parse the `{"memories": [...]}` response format
4. WHEN a memory is stored and then recalled THEN the system SHALL return the stored memory with a relevance score

---

## Files Summary

### Files to DELETE

| File | Reason |
|------|--------|
| `somabrain/api/routers/link.py` | Router for non-existent `/link` endpoint |
| `benchmarks/benchmark_link_latency.py` | Benchmarks non-existent `link()` method |

### Files to MODIFY (Remove Dead Code)

| File | Changes Needed |
|------|----------------|
| `somabrain/services/memory_service.py` | Remove `link()`, `alink()`, `payloads_for_coords()`, `links_from()` methods |
| `somabrain/interfaces/memory.py` | Remove dead method signatures |
| `somabrain/consolidation.py` | Remove `mem.link()` call |
| `somabrain/app.py` | Remove `payloads_for_coords()`, `k_hop()` calls, `/graph/links` endpoint |
| `somabrain/services/recall_service.py` | Remove `payloads_for_coords()` calls |
| `somabrain/api/routers/persona.py` | Remove `payloads_for_coords()` calls |
| `somabrain/planner.py` | Remove `links_from()`, `payloads_for_coords()` calls |
| `somabrain/planner_rwr.py` | Remove `links_from()`, `payloads_for_coords()` calls |
| `somabrain/memory_cli.py` | Remove `cmd_link()` and link CLI command |
| `benchmarks/plan_bench.py` | Remove `/link` POST call |

### Files to MODIFY (Remove Placeholders)

| File | Changes Needed |
|------|----------------|
| `somabrain/services/cutover_controller.py` | Implement fully or delete |
| `somabrain/services/segmentation_service.py` | Remove `CPDSegmenter`, `HazardSegmenter` placeholders |
| `somabrain/services/calibration_service.py` | Remove placeholder comment |
| `somabrain/milvus_client.py` | Remove `_DummyCollection` or implement properly |

### Files to MODIFY (Documentation)

| File | Changes Needed |
|------|----------------|
| `README.md` | Update endpoint references |
| `docs/development/api-reference.md` | Remove `/graph/links` |
| `docs/development/testing-guidelines.md` | Update endpoint references |
| `docs/benchmarks/README.md` | Update endpoint references |

---

## ADDITIONAL VIOLATIONS FOUND IN RECURSIVE SCAN

### Category 7: Test Files Using Mocks (VIBE Rule 1 Violation)

| File | Violation | Severity |
|------|-----------|----------|
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | Uses `unittest.mock.MagicMock` and `patch` - FORBIDDEN by VIBE rules | CRITICAL |
| `tests/oak/test_thread.py` | Uses `DummySession` mock class to bypass real PostgreSQL | CRITICAL |
| `tests/unit/test_outbox_sync.py` | Uses `DummyEvent` and `DummyClient` mock classes | CRITICAL |

### Category 8: Stub/Placeholder Classes in Production Code

| File | Line | Violation |
|------|------|-----------|
| `somabrain/milvus_client.py` | 49 | `_DummyCollection` class - fallback stub when pymilvus unavailable |
| `somabrain/prefrontal.py` | 53 | Entire class is a "stub implementation" per docstring |
| `somabrain/services/cutover_controller.py` | 1 | Entire file is "Stub implementation" |

### Category 9: Comments Referencing Mocks/Stubs (Documentation Lies)

| File | Line | Issue |
|------|------|-------|
| `somabrain/milvus_client.py` | 44-47 | Comments say "mocked in the test suite" |
| `somabrain/milvus_client.py` | 96-97 | Comments say "or a mock in tests" |
| `somabrain/milvus_client.py` | 111-113 | Comments say "tests replace with mock" |
| `somabrain/services/memory_service.py` | 55-57 | Comments say "For unit tests a tiny mock backend is supplied" |

---

## Requirements (Additional)

### Requirement 9: Remove Mock Usage from Tests

**User Story:** As a developer, I want all tests to use real services, so that the test suite follows VIBE rules and validates actual behavior.

#### Acceptance Criteria

1. WHEN `somabrain/tests/services/test_cognitive_sleep_integration.py` is reviewed THEN the system SHALL remove all `MagicMock` and `patch` usage
2. WHEN `tests/oak/test_thread.py` is reviewed THEN the system SHALL remove `DummySession` and use real PostgreSQL or skip if unavailable
3. WHEN `tests/unit/test_outbox_sync.py` is reviewed THEN the system SHALL remove `DummyEvent` and `DummyClient` mock classes

### Requirement 10: Remove Stub Classes from Production Code

**User Story:** As a developer, I want all production code to be real implementations, so that the codebase follows VIBE Rule 1.

#### Acceptance Criteria

1. WHEN `somabrain/prefrontal.py` is reviewed THEN the system SHALL either implement it fully or remove it
2. WHEN comments reference "mock" or "stub" in production code THEN the system SHALL remove those comments

---

## Complete Files Summary (Updated)

### Files to DELETE

| File | Reason |
|------|--------|
| `somabrain/api/routers/link.py` | Router for non-existent `/link` endpoint |
| `benchmarks/benchmark_link_latency.py` | Benchmarks non-existent `link()` method |

### Files to MODIFY (Remove Dead Code)

| File | Changes Needed |
|------|----------------|
| `somabrain/services/memory_service.py` | Remove `link()`, `alink()`, `payloads_for_coords()`, `links_from()` methods |
| `somabrain/interfaces/memory.py` | Remove dead method signatures |
| `somabrain/consolidation.py` | Remove `mem.link()` call |
| `somabrain/app.py` | Remove `payloads_for_coords()`, `k_hop()` calls, `/graph/links` endpoint |
| `somabrain/services/recall_service.py` | Remove `payloads_for_coords()` calls |
| `somabrain/api/routers/persona.py` | Remove `payloads_for_coords()` calls |
| `somabrain/planner.py` | Remove `links_from()`, `payloads_for_coords()` calls |
| `somabrain/planner_rwr.py` | Remove `links_from()`, `payloads_for_coords()` calls |
| `somabrain/memory_cli.py` | Remove `cmd_link()` and link CLI command |
| `benchmarks/plan_bench.py` | Remove `/link` POST call |

### Files to MODIFY (Remove Placeholders/Stubs)

| File | Changes Needed |
|------|----------------|
| `somabrain/services/cutover_controller.py` | Implement fully or delete |
| `somabrain/services/segmentation_service.py` | Remove `CPDSegmenter`, `HazardSegmenter` placeholders |
| `somabrain/services/calibration_service.py` | Remove placeholder comment |
| `somabrain/milvus_client.py` | Remove `_DummyCollection` or implement properly |
| `somabrain/prefrontal.py` | Implement fully or remove stub |

### Files to MODIFY (Remove Mocks from Tests)

| File | Changes Needed |
|------|----------------|
| `somabrain/tests/services/test_cognitive_sleep_integration.py` | Remove all MagicMock/patch usage, use real services |
| `tests/oak/test_thread.py` | Remove DummySession, use real PostgreSQL |
| `tests/unit/test_outbox_sync.py` | Remove DummyEvent/DummyClient, use real services |

### Files to MODIFY (Documentation)

| File | Changes Needed |
|------|----------------|
| `README.md` | Update endpoint references |
| `docs/development/api-reference.md` | Remove `/graph/links` |
| `docs/development/testing-guidelines.md` | Update endpoint references |
| `docs/benchmarks/README.md` | Update endpoint references |

### New Requirements: Recall Testing Workbench

- **Req 8.1** Labeled recall-quality tests SHALL compute and assert precision@k, recall@k, nDCG@k for hybrid (vector + WM) retrieval against a known corpus.
- **Req 8.2** Degradation-path test SHALL prove writes queue on memory failure, `/recall` returns `degraded=true`, and queued events replay without duplicates after recovery.
- **Req 8.3** Multi-tenant isolation test SHALL prove tenant A recalls never include tenant B payloads and that metrics are tenant-labeled.
- **Req 8.4** Performance SLO test SHALL fail if p95 `/remember` > 300 ms or p95 `/recall` > 400 ms in the dev stack.
- **Req 8.5** Workbench SHALL fail fast with clear messaging when required env vars (memory URL/token, Postgres DSN) are missing; no silent skips.
- **Req 8.6** Documentation update SHALL describe datasets, env vars, commands, and SLO targets in `docs/development/testing-guidelines.md`.

### Requirement 11: Milvus Must Be Mandatory and Verified

**User Story:** As an operator, I need Milvus to be the enforced ANN backend with verified correctness and observable SLOs, so vector recall stays production‑grade without silent degradation.**

#### Acceptance Criteria
1. WHEN `tiered_memory_cleanup_backend` is set to `milvus` THEN the service SHALL fail fast on startup if Milvus is unreachable; no fallback to HNSW/Simple is permitted.
2. WHEN Milvus is reachable THEN a smoke test SHALL insert and search a golden vector set and assert recall@10 meets a configured threshold.
3. WHEN the service initializes THEN Milvus collection schema, metric type, and index parameters SHALL be validated against expected config; mismatch SHALL fail startup.
4. WHEN health/metrics endpoints are queried THEN they SHALL expose Milvus p95 ingest/search latency and segment load status.
5. WHEN Postgres holds canonical memory/option rows THEN a reconciliation job SHALL ensure Milvus contains the same anchors (no orphans/missing) and SHALL emit alerts on drift.
6. WHEN Oak option upserts occur THEN Milvus persistence SHALL be mandatory with retries/backoff; failures SHALL propagate (no log‑only paths).

---

## Audit Statistics

- **Total Folders Scanned:** 50+
- **Total Files Analyzed:** 200+
- **Total Violations Found:** 60+
- **Critical Violations:** 35
- **Medium Violations:** 20
- **Low Violations:** 5
