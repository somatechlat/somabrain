# Implementation Plan - Monolithic File Decomposition

## Phase 1: app.py Decomposition (Priority: High)

- [x] 1. Extract Health and Diagnostics Router
  - [x] 1.1 Create `somabrain/routers/health.py` with health endpoints
    - Move `health()`, `healthz()`, `diagnostics()`, `metrics()` endpoints
    - Move `health_memory()`, `health_oak()`, `health_metrics()` endpoints
    - Move `_milvus_metrics_for_tenant()` helper
    - _Requirements: 1.2_
  - [x] 1.2 Update `somabrain/app.py` to import health router
    - Add `app.include_router(health_router)`
    - Remove extracted endpoint definitions
    - _Requirements: 1.1_
  - [ ]* 1.3 Write property test for route preservation
    - **Property 2: API Route Preservation**
    - **Validates: Requirements 1.2**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Extract Memory Operations Router
  - [x] 3.1 Create `somabrain/routers/memory_ops.py` with memory endpoints
    - Move `remember()`, `recall()`, `delete_memory()`, `recall_delete()` endpoints
    - Move scoring helpers: `_score_memory_candidate()`, `_apply_diversity_reranking()`
    - Move payload helpers: `_extract_text_from_candidate()`, `_normalize_payload_timestamps()`
    - _Requirements: 1.2, 1.3_
  - [x] 3.2 Update `somabrain/app.py` to import memory_ops router
    - Add `app.include_router(memory_ops_router)`
    - Remove extracted endpoint definitions
    - _Requirements: 1.1_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Extract Cognitive Router
  - [x] 5.1 Create `somabrain/routers/cognitive.py` with cognitive endpoints
    - Move `plan_suggest()`, `act_endpoint()` endpoints
    - Move `get_neuromodulators()`, `set_neuromodulators()` endpoints
    - Move `set_personality()` endpoint
    - _Requirements: 1.2_
  - [x] 5.2 Update `somabrain/app.py` to import cognitive router
    - Add `app.include_router(cognitive_router)`
    - Remove extracted endpoint definitions
    - _Requirements: 1.1_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Extract OAK Router
  - [ ] 7.1 Create `somabrain/routers/oak.py` with OAK endpoints
    - Move `oak_option_create()`, `oak_option_update()`, `oak_plan()` endpoints
    - _Requirements: 1.2_
  - [ ] 7.2 Update `somabrain/app.py` to import oak router
    - Add `app.include_router(oak_router)`
    - Remove extracted endpoint definitions
    - _Requirements: 1.1_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Extract Service Classes
  - [ ] 9.1 Create `somabrain/services/unified_brain.py`
    - Move `UnifiedBrainCore` class
    - Update imports in app.py
    - _Requirements: 1.4_
  - [ ] 9.2 Create `somabrain/services/complexity_detector.py`
    - Move `ComplexityDetector` class
    - Update imports in app.py
    - _Requirements: 1.4_
  - [ ] 9.3 Create `somabrain/services/fractal_intelligence.py`
    - Move `AutoScalingFractalIntelligence` class
    - Update imports in app.py
    - _Requirements: 1.4_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Extract Lifecycle Functions
  - [ ] 11.1 Create `somabrain/lifecycle/__init__.py` with exports
    - _Requirements: 1.5_
  - [ ] 11.2 Create `somabrain/lifecycle/startup.py`
    - Move `_startup_mode_banner()`, `_init_constitution()`, `_init_tenant_manager()`
    - Move `_enforce_kafka_required()`, `_enforce_opa_postgres_required()`
    - Move `_start_outbox_sync()`, `_init_health_watchdog()`
    - _Requirements: 1.5_
  - [ ] 11.3 Create `somabrain/lifecycle/watchdog.py`
    - Move `_health_watchdog_coroutine()`, `_start_memory_watchdog()`, `_stop_memory_watchdog()`
    - _Requirements: 1.5_
  - [ ] 11.4 Update `somabrain/app.py` to import lifecycle functions
    - _Requirements: 1.1_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Extract Helper Modules
  - [ ] 13.1 Create `somabrain/helpers/__init__.py` with exports
    - _Requirements: 1.3_
  - [ ] 13.2 Create `somabrain/helpers/wm_support.py`
    - Move `_build_wm_support_index()`, `_collect_candidate_keys()`
    - _Requirements: 1.3_
  - [ ] 13.3 Update `somabrain/app.py` to import helpers
    - _Requirements: 1.1_

- [ ] 14. Final app.py Cleanup
  - [ ] 14.1 Verify app.py is under 800 lines
    - Run `wc -l somabrain/app.py`
    - Document final line count
    - _Requirements: 1.1_
  - [ ] 14.2 Verify all imports work correctly
    - Test `import somabrain.app`
    - Test all router imports
    - _Requirements: 1.4_

- [ ] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: memory_client.py Decomposition (Priority: High)

- [ ] 16. Create Memory Module Structure
  - [ ] 16.1 Create `somabrain/memory/__init__.py`
    - Re-export `MemoryClient`, `RecallHit`, `MemoryHTTPTransport`
    - _Requirements: 2.3_
  - [ ] 16.2 Create `somabrain/memory/types.py`
    - Move `RecallHit` dataclass
    - _Requirements: 2.3_

- [ ] 17. Extract Transport Layer
  - [ ] 17.1 Create `somabrain/memory/transport.py`
    - Move `MemoryHTTPTransport` class
    - Move `_http_setting()` helper
    - _Requirements: 2.2_
  - [ ] 17.2 Update `somabrain/memory_client.py` to import transport
    - _Requirements: 2.1_

- [ ] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Extract Normalization and Filtering
  - [ ] 19.1 Create `somabrain/memory/normalization.py`
    - Move `_stable_coord()`, `_parse_coord_string()`
    - _Requirements: 2.3_
  - [ ] 19.2 Create `somabrain/memory/filtering.py`
    - Move `_filter_payloads_by_keyword()`, `_extract_memory_coord()`
    - _Requirements: 2.3_
  - [ ] 19.3 Update `somabrain/memory_client.py` to import helpers
    - _Requirements: 2.1_

- [ ] 20. Refactor MemoryClient
  - [ ] 20.1 Create `somabrain/memory/client.py`
    - Move `MemoryClient` class
    - Update imports to use extracted modules
    - _Requirements: 2.3_
  - [ ] 20.2 Update `somabrain/memory_client.py` as compatibility shim
    - Re-export from `somabrain/memory/client.py`
    - Keep file under 50 lines
    - _Requirements: 2.1_

- [ ] 21. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: metrics_original.py Decomposition (Priority: Medium)

- [ ] 22. Create Metrics Module Structure
  - [ ] 22.1 Create `somabrain/metrics/core.py`
    - Move `_MetricProtocol`, `_counter()`, `_gauge()`, `_histogram()`, `_summary()`
    - Move `get_counter()`, `get_gauge()`, `get_histogram()`
    - _Requirements: 3.2_
  - [ ] 22.2 Update `somabrain/metrics/__init__.py` to import core
    - _Requirements: 3.4_

- [ ] 23. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 24. Extract Domain-Specific Metrics
  - [ ] 24.1 Create `somabrain/metrics/learning.py`
    - Move all `update_learning_*`, `record_learning_*` functions
    - Move learning-related metric definitions
    - _Requirements: 3.2, 3.3_
  - [ ] 24.2 Create `somabrain/metrics/memory_metrics.py`
    - Move `record_memory_snapshot()`, `observe_recall_latency()`, `observe_ann_latency()`
    - Move memory-related metric definitions
    - _Requirements: 3.2, 3.3_
  - [ ] 24.3 Create `somabrain/metrics/outbox_metrics.py`
    - Move `report_outbox_pending()`, `report_outbox_processed()`, `report_outbox_replayed()`
    - Move `report_circuit_state()`
    - _Requirements: 3.2, 3.3_
  - [ ] 24.4 Create `somabrain/metrics/middleware.py`
    - Move `metrics_endpoint()`, `timing_middleware()`
    - _Requirements: 3.2_

- [ ] 25. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 26. Refactor metrics_original.py
  - [ ] 26.1 Update `somabrain/metrics_original.py` as compatibility shim
    - Re-export all metrics from domain modules
    - Keep file under 100 lines
    - _Requirements: 3.1_
  - [ ] 26.2 Update `somabrain/metrics/__init__.py`
    - Re-export all public metrics for backward compatibility
    - _Requirements: 3.4_

- [ ] 27. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Secondary Files Decomposition (Priority: Medium)

- [ ] 28. Decompose api/memory_api.py
  - [ ] 28.1 Create `somabrain/api/memory/models.py`
    - Move all Pydantic models (MemoryWriteRequest, MemoryRecallRequest, etc.)
    - _Requirements: 6.1_
  - [ ] 28.2 Create `somabrain/api/memory/helpers.py`
    - Move `_compose_memory_payload()`, `_serialize_coord()`, `_resolve_namespace()`
    - Move `_get_embedder()`, `_get_wm()`, `_get_memory_pool()`
    - _Requirements: 6.1_
  - [ ] 28.3 Refactor `somabrain/api/memory_api.py`
    - Import models and helpers from extracted modules
    - Keep only router and endpoint handlers
    - Target: <500 lines
    - _Requirements: 6.1_

- [ ] 29. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 30. Decompose learning/adaptation.py
  - [ ] 30.1 Create `somabrain/learning/config.py`
    - Move `AdaptationConfig` and related dataclasses
    - _Requirements: 6.2_
  - [ ] 30.2 Create `somabrain/learning/feedback.py`
    - Move feedback processing logic
    - _Requirements: 6.2_
  - [ ] 30.3 Refactor `somabrain/learning/adaptation.py`
    - Import from extracted modules
    - Keep `AdaptationEngine` class
    - Target: <500 lines
    - _Requirements: 6.2_

- [ ] 31. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 32. Decompose schemas.py
  - [ ] 32.1 Create `somabrain/schemas/memory.py`
    - Move memory-related schemas
    - _Requirements: 6.3_
  - [ ] 32.2 Create `somabrain/schemas/cognitive.py`
    - Move cognitive/planning schemas
    - _Requirements: 6.3_
  - [ ] 32.3 Create `somabrain/schemas/health.py`
    - Move health/diagnostic schemas
    - _Requirements: 6.3_
  - [ ] 32.4 Refactor `somabrain/schemas.py`
    - Re-export all schemas for backward compatibility
    - Target: <200 lines
    - _Requirements: 6.3_

- [ ] 33. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Final Verification

- [ ] 34. Line Count Verification
  - [ ] 34.1 Verify all target files meet line count requirements
    - `somabrain/app.py` < 800 lines
    - `somabrain/memory_client.py` < 100 lines (shim)
    - `somabrain/metrics_original.py` < 100 lines (shim)
    - `somabrain/api/memory_api.py` < 500 lines
    - `somabrain/learning/adaptation.py` < 500 lines
    - `somabrain/schemas.py` < 200 lines (shim)
    - _Requirements: 1.1, 2.1, 3.1, 6.1-6.4_

- [ ] 35. Import Compatibility Verification
  - [ ] 35.1 Verify all existing imports still work
    - Test `from somabrain.app import *`
    - Test `from somabrain.memory_client import MemoryClient`
    - Test `from somabrain.metrics import *`
    - Test `from somabrain.schemas import *`
    - _Requirements: 1.4, 2.3, 3.4_
  - [ ]* 35.2 Write property test for import backward compatibility
    - **Property 1: Import Backward Compatibility**
    - **Validates: Requirements 1.4, 2.3, 3.4**

- [ ] 36. Final Checkpoint - All tests pass
  - Ensure all tests pass, ask the user if questions arise.
