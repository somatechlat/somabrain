# Requirements Document

## Introduction

This document specifies requirements for the Unified Planning Kernel and FocusState integration in SomaBrain. The goal is to:
1. **ELIMINATE** all stub implementations that violate VIBE CODING RULES
2. **FIX** critical bugs breaking the cognitive loop
3. **WIRE** existing infrastructure that is already built but not connected

**VIBE CODING RULES COMPLIANCE:**
- NO mocks, NO placeholders, NO fake functions, NO stubs, NO TODOs
- NO hardcoded return values (like `return []`)
- REAL implementations ONLY using EXISTING infrastructure
- The GraphClient (`somabrain/somabrain/memory/graph_client.py`) is FULLY IMPLEMENTED
- SomaFractalMemory HAS `/graph/link`, `/graph/neighbors`, `/graph/path` endpoints

**See Also**: `ARCHITECTURE_ANALYSIS.md` for complete system diagrams and flow analysis.

## Current VIBE Violations (MUST FIX)

### VIOLATION 1: Planner Stub with FALSE Documentation
**File**: `somabrain/somabrain/planner.py`
**Line**: 47-49
**Code**: `return []`
**FALSE Claim**: "The memory backend API does not expose graph link endpoints"
**TRUTH**: SFM HAS these endpoints. GraphClient is FULLY IMPLEMENTED.
**Impact**: `/plan/suggest` always returns empty - system has NO planning capability

### VIOLATION 2: RWR Planner Stub with FALSE Documentation  
**File**: `somabrain/somabrain/planner_rwr.py`
**Line**: 47-49
**Code**: `return []`
**FALSE Claim**: "Graph traversal requires /neighbors endpoint which does not exist"
**TRUTH**: SFM HAS `/graph/neighbors`. GraphClient.get_neighbors() works.
**Impact**: RWR planning completely broken

### VIOLATION 3: Predictor Self-Comparison Bug
**File**: `somabrain/somabrain/services/cognitive_loop_service.py`
**Line**: 137
**Code**: `predictor.predict_and_compare(wm_vec, wm_vec)`
**Problem**: Compares vector to ITSELF - prediction error is ALWAYS ~0
**Impact**: Salience gating broken, memories not stored, consolidation fails

### VIOLATION 4: Settings Mismatch
**File**: `somabrain/somabrain/services/planning_service.py`
**Lines**: 77-78
**Code**: Uses `cfg.rwr_steps` instead of `cfg.planner_rwr_steps`
**Impact**: RWR configuration completely ignored

## Glossary

- **FocusState**: Session-scoped working-memory signal wrapping HRRContext
- **PlanEngine**: Single planning entrypoint producing CompositePlan
- **CompositePlan**: Plan output with graph_plan, context_plan, option_plan, action_plan
- **HRRContext**: Holographic Reduced Representation context (EXISTING, WORKING)
- **GraphClient**: Client for SFM graph operations (EXISTING, FULLY IMPLEMENTED)
- **SFM**: SomaFractalMemory - the memory backend service

## Requirements

### Requirement 1: Eliminate Planner Stub - Implement Real BFS

**User Story:** As a cognitive system, I want graph-based planning to use the EXISTING GraphClient so that `/plan/suggest` returns real plans.

#### Acceptance Criteria

1. WHEN `plan_from_graph` is called THEN the system SHALL use `GraphClient.get_neighbors()` (NOT return `[]`)
2. WHEN `plan_from_graph` is called THEN the system SHALL import and use the existing `GraphClient` from `somabrain/somabrain/memory/graph_client.py`
3. WHEN traversing the graph THEN the system SHALL respect `plan_max_steps` configuration limit
4. WHEN `plan_rel_types` is non-empty THEN the system SHALL filter edges by those relationship types
5. WHEN GraphClient returns neighbors THEN the system SHALL use deterministic ordering (sort by strength desc, then coord string)
6. WHEN graph endpoint is unavailable THEN the system SHALL return empty plan with metric increment (graceful degradation, NOT silent `return []`)
7. WHEN implementation is complete THEN the system SHALL have ZERO hardcoded `return []` statements

### Requirement 2: Eliminate RWR Planner Stub - Implement Real RWR

**User Story:** As a cognitive system, I want RWR-based planning to use the EXISTING GraphClient so that probabilistic graph ranking works.

#### Acceptance Criteria

1. WHEN `rwr_plan` is called THEN the system SHALL use `GraphClient.get_neighbors()` to build local subgraph (NOT return `[]`)
2. WHEN RWR runs THEN the system SHALL use `planner_rwr_steps` for iteration count
3. WHEN RWR runs THEN the system SHALL use `planner_rwr_restart` for restart probability
4. WHEN RWR runs THEN the system SHALL use deterministic tie-breaking for reproducibility
5. WHEN implementation is complete THEN the system SHALL have ZERO hardcoded `return []` statements
6. WHEN implementation is complete THEN the system SHALL remove FALSE documentation claiming endpoints don't exist

### Requirement 3: Fix Predictor Self-Comparison Bug

**User Story:** As a cognitive system, I want prediction error to be meaningful so that salience gating works correctly.

#### Acceptance Criteria

1. WHEN the cognitive loop evaluates a step THEN the system SHALL compare previous_focus vector against current_focus vector (NOT wm_vec vs wm_vec)
2. WHEN no previous focus exists for a session THEN the system SHALL record diagnostic `no_prev_focus=true` and use current_focus as baseline
3. WHEN prediction error is computed THEN the system SHALL produce nonzero values when focus changes between steps
4. WHEN predictor comparison fails THEN the system SHALL increment `somabrain_predict_compare_missing_prev_total` metric

### Requirement 4: Fix Settings Mismatch

**User Story:** As a developer, I want planning settings to use correct names so that configuration works as documented.

#### Acceptance Criteria

1. WHEN planning service reads RWR steps THEN the system SHALL use `planner_rwr_steps` setting (NOT `rwr_steps`)
2. WHEN planning service reads RWR restart THEN the system SHALL use `planner_rwr_restart` setting (NOT `rwr_restart`)
3. WHEN legacy setting names are accessed THEN the system SHALL log a deprecation warning

### Requirement 5: Add Missing Planner Settings

**User Story:** As an operator, I want to configure planning behavior via environment variables so that I can tune the system without code changes.

#### Acceptance Criteria

1. WHEN the system starts THEN the system SHALL read `SOMABRAIN_USE_PLANNER` (default: false)
2. WHEN the system starts THEN the system SHALL read `SOMABRAIN_USE_FOCUS_STATE` (default: true)
3. WHEN the system starts THEN the system SHALL read `SOMABRAIN_PLAN_MAX_STEPS` (default: 5)
4. WHEN the system starts THEN the system SHALL read `SOMABRAIN_PLANNER_BACKEND` (default: "bfs")
5. WHEN the system starts THEN the system SHALL read `SOMABRAIN_PLAN_TIME_BUDGET_MS` (default: 50)
6. WHEN the system starts THEN the system SHALL read `SOMABRAIN_PLAN_MAX_OPTIONS` (default: 10)
7. WHEN the system starts THEN the system SHALL read `SOMABRAIN_PLAN_REL_TYPES` (default: "")
8. WHEN the system starts THEN the system SHALL read `SOMABRAIN_FOCUS_DECAY_GAMMA` (default: 0.90)
9. WHEN the system starts THEN the system SHALL read `SOMABRAIN_FOCUS_PERSIST` (default: false)
10. WHEN the system starts THEN the system SHALL read `SOMABRAIN_FOCUS_LINKS` (default: false)
11. WHEN the system starts THEN the system SHALL read `SOMABRAIN_FOCUS_ADMIT_TOP_N` (default: 4)


### Requirement 6: Create PlanEngine

**User Story:** As a developer, I want a single planning entrypoint so that all planning paths share consistent behavior.

#### Acceptance Criteria

1. WHEN PlanEngine.plan is called THEN the system SHALL accept a PlanRequestContext with tenant_id, task_key, task_vec, focus_vec, and budgets
2. WHEN PlanEngine.plan completes THEN the system SHALL return a CompositePlan with optional graph_plan, context_plan, option_plan, action_plan
3. WHEN time budget is exceeded THEN the system SHALL return partial results with diagnostics
4. WHEN any strategy fails THEN the system SHALL continue with remaining strategies (fail-soft)
5. WHEN CompositePlan is returned THEN the system SHALL provide `to_legacy_steps()` method for backward compatibility

### Requirement 7: Create FocusState Module

**User Story:** As a cognitive system, I want FocusState as the canonical working-memory signal so that novelty and salience gating are stable.

**Architecture Note:** FocusState WRAPS (does not replace) the existing HRRContext. HRRContext handles the low-level HRR vector operations (superposition, decay, cleanup). FocusState adds session-scoped state management, previous/current focus tracking, and deterministic digest computation on top of HRRContext.

#### Acceptance Criteria

1. WHEN FocusState is created THEN the system SHALL wrap an HRRContext instance for vector operations (composition, not inheritance)
2. WHEN FocusState is updated THEN the system SHALL admit task embedding as primary anchor via HRRContext.admit()
3. WHEN FocusState is updated THEN the system SHALL admit top-N recall hits (configurable via `focus_admit_top_n`, default 4) deterministically sorted by ID
4. WHEN FocusState is updated THEN the system SHALL delegate exponential decay to HRRContext using `focus_decay_gamma`
5. WHEN FocusState is queried THEN the system SHALL provide current_focus_vec and previous_focus_vec (FocusState tracks both, HRRContext only has current)
6. WHEN FocusState is queried THEN the system SHALL provide novelty score via HRRContext.novelty()
7. WHEN same inputs are provided in same order THEN the system SHALL produce identical focus digest (determinism)

### Requirement 8: FocusState Persistence

**User Story:** As a cognitive system, I want focus snapshots persisted so that I can maintain continuity across sessions.

#### Acceptance Criteria

1. WHEN `focus_persist` is true AND store gate allows THEN the system SHALL persist focus snapshot to memory
2. WHEN focus snapshot is persisted THEN the system SHALL use memory_type "episodic"
3. WHEN focus snapshot is persisted THEN the system SHALL include timestamp, universe, session_id, tick, focus_digest
4. WHEN focus snapshot is persisted THEN the system SHALL NOT include raw user text (privacy-safe)
5. WHEN memory endpoint is unavailable THEN the system SHALL continue without failing the request

### Requirement 9: Focus Pointer Chain

**User Story:** As a cognitive system, I want focus snapshots linked so that I can trace attention history.

#### Acceptance Criteria

1. WHEN `focus_links` is true THEN the system SHALL create "next" edge between consecutive focus snapshots using GraphClient.create_link()
2. WHEN `focus_links` is true THEN the system SHALL create "attends_to" edges to used memory IDs
3. WHEN `focus_links` is true THEN the system SHALL create "used_option" edges to selected option IDs
4. WHEN graph endpoint is unavailable THEN the system SHALL queue link to outbox for retry (GraphClient already does this)
5. WHEN link creation fails THEN the system SHALL NOT fail the request

### Requirement 10: API Compatibility

**User Story:** As an API consumer, I want existing endpoints to work unchanged so that my integration is not broken.

#### Acceptance Criteria

1. WHEN `/plan/suggest` is called THEN the system SHALL return `{plan: [str]}` response format
2. WHEN `/act` is called THEN the system SHALL return ActResponse with task, results, plan, plan_universe
3. WHEN planner is disabled THEN the system SHALL return empty plan (not error)
4. WHEN FocusState is disabled THEN the system SHALL use existing wm_vec behavior

### Requirement 11: Observability

**User Story:** As an operator, I want metrics and logs for planning and focus so that I can debug issues.

#### Acceptance Criteria

1. WHEN planning completes THEN the system SHALL record `somabrain_plan_latency_seconds` histogram
2. WHEN planning produces empty result THEN the system SHALL record reason in `somabrain_plan_empty_total` counter with label
3. WHEN focus is updated THEN the system SHALL record `somabrain_focus_update_latency_seconds` histogram
4. WHEN focus is persisted THEN the system SHALL record `somabrain_focus_persist_total` counter
5. WHEN any operation fails THEN the system SHALL log with request_id, tenant_id, and degrade reason

### Requirement 12: Remove All VIBE Violations

**User Story:** As a developer, I want all VIBE violations removed so that the codebase is clean and production-ready.

#### Acceptance Criteria

1. WHEN implementation is complete THEN `planner.py` SHALL have ZERO `return []` stub code
2. WHEN implementation is complete THEN `planner_rwr.py` SHALL have ZERO `return []` stub code
3. WHEN implementation is complete THEN ALL FALSE documentation claiming "endpoints don't exist" SHALL be removed
4. WHEN implementation is complete THEN the system SHALL have ZERO TODO/FIXME comments in planning modules
5. WHEN implementation is complete THEN ALL hardcoded bypass values SHALL be replaced with real implementations
6. WHEN implementation is complete THEN the system SHALL use ONLY the existing GraphClient for graph operations (no new HTTP clients)
