# Implementation Tasks: Unified Planning Kernel

## Overview

This implementation plan eliminates VIBE violations and wires existing infrastructure. All tasks use REAL implementations - NO stubs, NO mocks, NO hardcoded returns.

## Task Dependency Graph

```
Task 1 (Metrics) ──────────────────────────────────────────────┐
                                                               │
Task 2 (Settings) ─────────────────────────────────────────────┤
                                                               │
Task 3 (Fix Settings Mismatch) ← Task 2 ───────────────────────┤
                                                               │
Task 4 (BFS Planner) ← Task 1, Task 2 ─────────────────────────┤
                                                               │
Task 5 (RWR Planner) ← Task 1, Task 2, Task 3 ─────────────────┤
                                                               │
Task 6 (FocusState) ← Task 1 ──────────────────────────────────┤
                                                               │
Task 7 (PlanEngine) ← Task 4, Task 5 ──────────────────────────┤
                                                               │
Task 8 (Fix Predictor Bug) ← Task 1, Task 6 ───────────────────┤
                                                               │
Task 9 (Integration) ← Task 7, Task 8 ─────────────────────────┤
                                                               │
Task 10 (VIBE Cleanup) ← ALL ──────────────────────────────────┘
```

---

## Phase 1: Foundation

- [x] 1. Create Planning Metrics Module
  - Create `somabrain/somabrain/metrics/planning.py`
  - Define `PLAN_LATENCY` histogram with backend label
  - Define `PLAN_EMPTY` counter with reason label
  - Define `PLAN_GRAPH_UNAVAILABLE` counter
  - Define `FOCUS_UPDATE_LATENCY` histogram
  - Define `FOCUS_PERSIST` counter
  - Define `PREDICT_COMPARE_MISSING_PREV` counter
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 2. Add Missing Planner Settings
  - Modify `somabrain/common/config/settings/cognitive.py`
  - Add `use_planner` (default: False)
  - Add `use_focus_state` (default: True)
  - Add `plan_max_steps` (default: 5)
  - Add `planner_backend` (default: "bfs")
  - Add `plan_time_budget_ms` (default: 50)
  - Add `plan_max_options` (default: 10)
  - Add `plan_rel_types` (default: "")
  - Add `focus_decay_gamma` (default: 0.90)
  - Add `focus_persist` (default: False)
  - Add `focus_links` (default: False)
  - Add `focus_admit_top_n` (default: 4)
  - _Requirements: 5.1-5.11_

- [x] 3. Fix Settings Mismatch in Planning Service
  - Modify `somabrain/somabrain/services/planning_service.py`
  - Line 77: Change `cfg.rwr_steps` to `cfg.planner_rwr_steps`
  - Line 78: Change `cfg.rwr_restart` to `cfg.planner_rwr_restart`
  - _Requirements: 4.1, 4.2_

---

## Phase 2: Eliminate Planner Stubs (CRITICAL)

- [x] 4. Replace BFS Planner Stub with Real Implementation
  - REPLACE `somabrain/somabrain/planner.py` entirely
  - REMOVE the `return []` stub
  - REMOVE the FALSE documentation claiming "endpoints don't exist"
  - Import and use EXISTING `GraphClient` from `somabrain/somabrain/memory/graph_client.py`
  - Implement `plan_from_graph()` using `GraphClient.get_neighbors()`
  - Add helper `_coord_to_str()` for coordinate string conversion
  - Add helper `_extract_task_from_neighbor()` for task extraction
  - Respect `plan_max_steps` limit
  - Filter by `rel_types` when specified
  - Use deterministic ordering (sort by strength desc, then coord string)
  - Increment `PLAN_GRAPH_UNAVAILABLE` metric when GraphClient unavailable
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 4.1 Write property test for BFS planner determinism
  - **Property 5: Deterministic Ordering**
  - Test that same neighbors produce same ordering across runs
  - **Validates: Requirement 1.5**

- [x] 5. Replace RWR Planner Stub with Real Implementation
  - REPLACE `somabrain/somabrain/planner_rwr.py` entirely
  - REMOVE the `return []` stub
  - REMOVE the FALSE documentation claiming "endpoints don't exist"
  - Import and use EXISTING `GraphClient` from `somabrain/somabrain/memory/graph_client.py`
  - Implement `rwr_plan()` using `GraphClient.get_neighbors()`
  - Add helper `_build_local_subgraph()` using GraphClient
  - Add helper `_build_transition_matrix()` for RWR
  - Use `planner_rwr_steps` for iteration count
  - Use `planner_rwr_restart` for restart probability
  - Use deterministic tie-breaking (sort by probability desc, then coord string)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 5.1 Write property test for RWR planner determinism
  - **Property 5: Deterministic Ordering**
  - Test that same graph produces same ranking across runs
  - **Validates: Requirement 2.4**

---

## Phase 3: FocusState

- [x] 6. Create FocusState Module
  - Create `somabrain/somabrain/focus_state.py`
  - Create `FocusState` class that WRAPS existing `HRRContext` (composition)
  - Implement `update(task_vec, recall_hits, timestamp)` method
  - Store `previous_focus_vec` before updating
  - Admit task embedding as primary anchor via `HRRContext.admit()`
  - Admit top-N recall hits deterministically (sorted by ID)
  - Implement `_compute_digest(vec)` for deterministic hash
  - Expose `current_focus_vec`, `previous_focus_vec`, `focus_digest` properties
  - Implement `novelty(vec)` via `HRRContext.novelty()`
  - Implement `persist_snapshot()` for focus persistence
  - Implement `create_links()` using EXISTING `GraphClient`
  - _Requirements: 7.1-7.7, 8.1-8.5, 9.1-9.5_

- [x] 6.1 Write property test for FocusState digest determinism
  - **Property 7: Focus Digest Determinism**
  - Test that same inputs produce identical focus_digest
  - **Validates: Requirement 7.7**

---

## Phase 4: PlanEngine and Bug Fixes

- [x] 7. Create PlanEngine
  - Create `somabrain/somabrain/services/plan_engine.py`
  - Create `PlanRequestContext` dataclass
  - Create `CompositePlan` dataclass with `to_legacy_steps()` method
  - Create `PlanEngine` class
  - Implement `plan(ctx)` with time budget enforcement
  - Use BFS or RWR based on `planner_backend` setting
  - Record latency and empty plan metrics
  - Continue on strategy failure (fail-soft)
  - _Requirements: 6.1-6.5_

- [x] 8. Fix Predictor Self-Comparison Bug
  - Modify `somabrain/somabrain/services/cognitive_loop_service.py`
  - Add `previous_focus_vec: Optional[np.ndarray]` parameter to `eval_step()`
  - Replace line 137: `predictor.predict_and_compare(wm_vec, wm_vec)` with proper comparison
  - When `previous_focus_vec` is None, set `result["no_prev_focus"] = True` and use zero error
  - When `previous_focus_vec` exists, compare `previous_focus_vec` against `wm_vec`
  - Increment `PREDICT_COMPARE_MISSING_PREV` metric for missing previous focus
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 8.1 Write property test for predictor comparison correctness
  - **Property 3: Predictor Comparison Correctness**
  - Test that different vectors produce nonzero prediction error
  - **Validates: Requirement 3.3**

---

## Phase 5: Integration

- [x] 9. Integrate into Cognitive Router
  - Modify `somabrain/somabrain/routers/cognitive.py`
  - Import FocusState and PlanEngine
  - In `/act` endpoint, create/get FocusState for session
  - Call `focus_state.update()` with task_vec and recall hits
  - Pass `focus_state.previous_focus_vec` to `eval_step()`
  - In `/plan/suggest`, use PlanEngine when `use_planner` is True
  - Return `CompositePlan.to_legacy_steps()` for backward compatibility
  - When `use_focus_state` is False, use existing `wm_vec` behavior
  - When `use_planner` is False, return empty plan (not error)
  - _Requirements: 10.1-10.4_

---

## Phase 6: VIBE Compliance Verification

- [x] 10. Remove All VIBE Violations
  - Verify `planner.py` has ZERO `return []` stub code
  - Verify `planner_rwr.py` has ZERO `return []` stub code
  - Verify ALL FALSE documentation claiming "endpoints don't exist" is removed
  - Search and remove any TODO/FIXME comments in planning modules
  - Search and remove any `rwr_steps`/`rwr_restart` references (use `planner_rwr_*`)
  - Verify ALL planning uses EXISTING GraphClient (no new HTTP clients)
  - Run grep to confirm: `grep -r "return \[\]" somabrain/somabrain/planner*.py` returns nothing
  - _Requirements: 12.1-12.6_

---

## Execution Order

### Batch 1 (Foundation) - ~30 minutes
- Task 1: Create metrics module
- Task 2: Add settings
- Task 3: Fix settings mismatch

### Batch 2 (Planners) - ~1 hour
- Task 4: Replace BFS planner stub
- Task 5: Replace RWR planner stub

### Batch 3 (FocusState) - ~45 minutes
- Task 6: Create FocusState module

### Batch 4 (Engine & Bug Fix) - ~45 minutes
- Task 7: Create PlanEngine
- Task 8: Fix predictor bug

### Batch 5 (Integration) - ~30 minutes
- Task 9: Integrate into cognitive router

### Batch 6 (Verification) - ~15 minutes
- Task 10: VIBE compliance verification

**Total Estimated Time**: ~4 hours

---

## Success Criteria

1. `grep -r "return \[\]" somabrain/somabrain/planner*.py` returns NOTHING
2. `grep -r "does not exist" somabrain/somabrain/planner*.py` returns NOTHING
3. `/plan/suggest` returns real plans from graph traversal (not empty)
4. Prediction error is nonzero when focus changes between steps
5. All settings use correct names (`planner_rwr_steps`, not `rwr_steps`)
6. All tests pass with REAL infrastructure (no mocks)
