# Implementation Plan - VIBE Violations Comprehensive Cleanup

- [x] 1. Clean up Memory Interface
  - [x] 1.1 Remove dead method signatures from `somabrain/interfaces/memory.py`
    - Remove `link()` method signature (lines 28-35)
    - Remove `alink()` method signature (lines 37-44)
    - Remove `payloads_for_coords()` method signature (lines 45-48)
    - Remove `links_from()` method signature (lines 52-55)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Remove Dead Methods from Memory Service
  - [x] 2.1 Remove dead proxy methods from `somabrain/services/memory_service.py`
    - Remove `link()` method (~lines 163-176)
    - Remove `alink()` method (~lines 178-195)
    - Remove `payloads_for_coords()` proxy method (~line 237-238)
    - Remove `links_from()` proxy method (~line 243-244)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Delete Dead Router Files
  - [x] 3.1 Delete `somabrain/api/routers/link.py`
    - Entire file is a router for non-existent `/link` endpoint
    - _Requirements: 3.1_
  - [x] 3.2 Remove link router import from `somabrain/app.py`
    - Find and remove import statement for link router
    - Remove router registration if present
    - _Requirements: 3.2_

- [x] 4. Remove Dead Endpoints from app.py
  - [x] 4.1 Remove `/graph/links` endpoint from `somabrain/app.py`
    - Remove endpoint definition (~lines 4106-4150)
    - Remove any helper functions used only by this endpoint
    - _Requirements: 3.3_
  - [x] 4.2 Remove `payloads_for_coords()` calls from `somabrain/app.py`
    - Remove calls at lines ~3153, 3253, 3291
    - _Requirements: 1.6_
  - [x] 4.3 Remove `k_hop()` call from `somabrain/app.py`
    - Remove call at line ~3250
    - _Requirements: 1.7_

- [x] 5. Remove Dead CLI Commands
  - [x] 5.1 Remove `cmd_link()` function and CLI command from `somabrain/memory_cli.py`
    - Remove `cmd_link()` function (lines ~73-76)
    - Remove CLI parser registration for `link` command (lines ~96-99)
    - _Requirements: 3.4_

- [x] 6. Checkpoint - Verify core cleanup
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Clean up Dependent Code - Services
  - [x] 7.1 Remove dead method calls from `somabrain/consolidation.py`
    - Remove `mem.link()` call at line ~111
    - _Requirements: 1.5_
  - [x] 7.2 Remove dead method calls from `somabrain/services/recall_service.py`
    - Remove `payloads_for_coords()` calls at lines ~84, 114, 183
    - _Requirements: 1.8_
  - [x] 7.3 Remove dead method calls from `somabrain/api/routers/persona.py`
    - Remove `payloads_for_coords()` calls at lines ~80, 151
    - _Requirements: 1.9_

- [x] 8. Clean up Dependent Code - Planners
  - [x] 8.1 Remove dead method calls from `somabrain/planner.py`
    - Remove `links_from()` call at line ~103
    - Remove `payloads_for_coords()` call at line ~121
    - _Requirements: 1.10_
  - [x] 8.2 Remove dead method calls from `somabrain/planner_rwr.py`
    - Remove `links_from()` call at line ~102
    - Remove `payloads_for_coords()` call at line ~153
    - _Requirements: 1.11_

- [x] 9. Checkpoint - Verify dependent code cleanup
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Remove Placeholder/Stub Code
  - [x] 10.1 Delete or implement `somabrain/services/cutover_controller.py`
    - File is marked as "Stub implementation"
    - Delete if not needed, implement if required
    - _Requirements: 4.1_
  - [x] 10.2 Remove placeholder segmenters from `somabrain/services/segmentation_service.py`
    - Remove `CPDSegmenter` placeholder class (lines ~221-230)
    - Remove `HazardSegmenter` placeholder class (lines ~233-239)
    - _Requirements: 4.2, 4.3_
  - [x] 10.3 Remove `_DummyCollection` from `somabrain/milvus_client.py`
    - Remove stub class at line ~49-51
    - Remove comments referencing mocks (lines ~44-47, 96-97, 111-113)
    - _Requirements: 4.4_
  - [x] 10.4 Remove placeholder comment from `somabrain/services/calibration_service.py`
    - Remove "Placeholder for a real export" comment at line ~61
    - _Requirements: 4.5_
  - [x] 10.5 Evaluate and clean `somabrain/prefrontal.py`
    - Class is marked as "stub implementation" in docstring
    - Either implement fully or remove
    - _Requirements: 10.1_

- [x] 11. Remove Mock Comments from Production Code
  - [x] 11.1 Remove mock/stub references from `somabrain/services/memory_service.py`
    - Remove comment "For unit tests a tiny mock backend is supplied" (lines ~55-57)
    - _Requirements: 10.2_

- [x] 11.2 Write property test for no forbidden terms
  - **Property 3: No Forbidden Terms in Production Code**
  - **Validates: Requirements 4.1-4.5, 10.1, 10.2**

- [x] 12. Checkpoint - Verify placeholder removal
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Clean up Test Files (Remove Mocks)
  - [x] 13.1 Clean `somabrain/tests/services/test_cognitive_sleep_integration.py`
    - Remove all `MagicMock` and `patch` usage
    - Rewrite to use real services or add skip markers
    - _Requirements: 9.1_
  - [x] 13.2 Clean `tests/oak/test_thread.py`
    - Remove `DummySession` mock class
    - Use real PostgreSQL or add skip marker
    - _Requirements: 9.2_
  - [x] 13.3 Clean `tests/unit/test_outbox_sync.py`
    - Remove `DummyEvent` and `DummyClient` mock classes
    - Use real services or add skip markers
    - _Requirements: 9.3_

- [x] 14. Delete Dead Benchmark Files
  - [x] 14.1 Delete `benchmarks/benchmark_link_latency.py`
    - Entire file benchmarks non-existent `link()` method
    - _Requirements: 5.1_
  - [x] 14.2 Update `benchmarks/plan_bench.py`
    - Remove or update the `/link` POST call at line ~38
    - _Requirements: 5.2_

- [x] 15. Update Documentation
  - [x] 15.1 Update `README.md` endpoint references
    - Change `/remember` to `/remember`
    - Change `/recall` to `/recall`
    - Remove `/remember/batch` reference
    - Remove `/recall/stream` reference
    - Remove `/graph/links` reference
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 15.2 Update `docs/development-manual/api-reference.md`
    - Remove `/graph/links` documentation
    - _Requirements: 6.6_
  - [x] 15.3 Update `docs/development-manual/testing-guidelines.md`
    - Change `/remember` to `/remember`
    - Change `/recall` to `/recall`
    - _Requirements: 6.7, 6.8_
  - [x] 15.4 Update `benchmarks/README.md`
    - Change `/recall` to `/recall`
    - _Requirements: 6.9_

- [x] 16. Write Property-Based Tests
  - [x] 16.1 Write property test for deterministic coordinate generation
    - **Property 1: Deterministic Coordinate Generation**
    - **Validates: Requirements 7.1, 7.2**
    - Test that `_stable_coord()` returns same result for same input
    - Test that all coordinates are in [-1, 1] range
  - [x] 16.2 Write property test for memory round-trip
    - **Property 2: Memory Round-Trip Consistency**
    - **Validates: Requirements 8.3, 8.4**
    - Test store then recall returns original data

- [x] 17. Final Checkpoint - Verify all changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Build Recall Testing Workbench (new)
  - [x] 18.1 Add integration suite `tests/integration/test_recall_quality.py`
    - Precision/recall/nDCG on labeled corpus (vector + WM hybrid)
    - Validates degradation flag and circuit state exposure in responses
  - [x] 18.2 Add metrics helper `tests/utils/metrics.py`
    - Compute precision@k, recall@k, nDCG@k
  - [x] 18.3 Add load/SLO check using existing harness (parametrized `benchmarks/recall_latency_bench.py`)
    - Assert p95 latency targets for /remember and /recall (dev stack)
  - [x] 18.4 Add multi-tenant isolation test
    - Tenant A recalls never return Tenant B payloads; metrics labeled per tenant
  - [x] 18.5 Add outbox durability test
    - Force memory 5xx, ensure events queue, replay drains pending to 0, no dupes
  - [x] 18.6 Document workbench in `docs/development-manual/testing-guidelines.md`
    - Env vars, datasets, expected SLOs, how to run locally/CI

- [ ] 19. Milvus Hardening (no fallbacks, full exploitation)
  - [x] 19.1 Remove ANN fallback chain (Milvus → HNSW → Simple) so configured backend is mandatory
  - [x] 19.2 Add live Milvus smoke + golden-set recall@10 test (ensures vector layer correctness)
  - [x] 19.3 Add index-config drift check (schema + metric + index params) and fail on mismatch
  - [x] 19.4 Expose Milvus health/SLO telemetry (p95 search/ingest, segment load) via health/metrics
  - [x] 19.5 Add reconciliation job/tests to ensure Postgres canonical rows exist in Milvus (no orphans)
  - [x] 19.6 Harden Oak option upsert: mandatory Milvus write with retries/backoff and alerting
