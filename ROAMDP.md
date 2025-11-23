# SomaBrain ROAMDP (Canonical)

This file is the canonical Somabrain ROAMDP (Roadmap & Action Plan).
It summarizes gaps discovered in the codebase and a prioritized, phased implementation plan for development sprints.

## Summary
- Core platform pieces (DB-backed outbox, publisher worker, metrics, memory facade) are in place.
- Newly identified gaps: cognitive threads v2 (unified predictor schema, integrator softmax/OPA/Redis, segmentation config + metrics), sleep system (utility + cognitive sleep APIs, schedules), and hardcoded-value purge/settings unification.

## Prioritized Implementation Plan (Phases)

### Phase 0 — Safety & Observability (DONE)
- 0.1 Per-tenant circuit-breaker: convert class-level circuit state to per-tenant state in `somabrain/services/memory_service.py`. Ensure `CIRCUIT_STATE` metric is labeled by tenant.
- 0.2 Outbox pending metric wiring: implement `_update_outbox_metric()` and ensure `OUTBOX_PENDING` is updated per tenant by worker/service.
- 0.3 Tenant-aware pending queries: extend `somabrain/db/outbox.py:get_pending_events(limit, tenant_id=None)` and add appropriate DB indices.

### Phase 1 — Idempotency, DB Constraints & Worker Hardening (DONE)
- 1.1 DB constraints & indices: add migration for unique index on `(tenant_id, dedupe_key)` and index on `(status, tenant_id, created_at)`.
- 1.2 Producer keying & headers: publish Kafka messages with stable key (dedupe_key/tenant) and relevant headers.
- 1.3 Per-tenant batch quotas & backpressure: allow worker to process per-tenant batches and enforce quotas.

### Phase 2 — Replay/Recovery & Operational Tooling (DONE)
- 2.1 Admin replay endpoints: add admin API to inspect and replay pending/failed events per tenant.
- 2.2 Optional local journaling: if required, add opt-in local journal and migration script to DB-outbox.

### Phase 3 — Monitoring & Canary Rollout (DONE)
- 3.1 Automated alerts for per-tenant outbox/circuit metrics (Prometheus / alertmanager).
- 3.2 Feature flags & canary rollout for enabling tenant-aware behavior (admin endpoints, CLI tooling).

### Phase 4 — Tests, Docs & CI (DONE)

### Phase 5 — Cognitive Threads v2 (NEW)
- 5.1 Unified predictor_update Avro schema; existing state/agent/action predictors emit it (no new services).
- 5.2 Integrator hub upgrade: softmax leader selection with configurable alpha/temperature; optional OPA veto; Redis cache; Prom metrics.
- 5.3 Segmentation hardening: thresholds/HMM toggle from ConfigService; metrics; topic `cog.segments` ensured in preflight.
- 5.4 Feature flag `ENABLE_COG_THREADS` default on so cognition/learning threads start automatically.
- 5.5 CI: schema compatibility + Kafka/Redis smoke tests; observability checks.
    - Current status: 5.2 implemented (softmax, OPA optional, Redis cache, metrics); 5.1 schema exists; gating removed so integration runs every time.

### Phase 6 — Sleep System (Utility + Cognitive) (NEW)
- 6.1 Implement `/api/util/sleep` (sync/async, OPA/JWT, rate/limits via ConfigService) with metrics/logging.
- 6.2 Implement `/api/brain/sleep_mode` and `/api/brain/sleep_policy` (per-tenant state, TTL auto-wake, wake-on-traffic, CB-driven gating, schedules for K,t,τ,η,B,λ with η=0 in deep/freeze).
- 6.3 Metrics: sleep state labels on latency/adaptation; counters for calls/toggles; tests for monotonic schedules and safety.
- 6.4 Feature flag default off; docs/runbooks and CI coverage.
- 6.5 `/api/brain/sleep_policy` is now live with OPA/JWT/rate-limit gating, tenant-aware TTL auto-wake, circuit-breaker-aware gating, and the expected parameter scheduling (η=0 in deep/freeze).

## Phase 7 — Hardcoded‑Value Purge & Settings Unification (NEW)
### Current Status (IN PROGRESS)
- Settings have been added for many predictor, integrator, and segmentation parameters.
- Remaining modules (adaptive learning, neuromodulators, etc.) still contain hard‑coded defaults and need migration.
- Unit tests for circuit‑breaker and memory‑service are complete; invariant tests are being added.

### Tasks to Complete
1. **Add missing Settings fields** – generate a CSV of every `os.getenv` usage and create a typed `Field` in `common/config/settings.py` (bool, int, float as appropriate).
2. **Replace all direct `os.getenv` calls** with `settings.<field>` across the entire codebase (services, infrastructure helpers, health checks, OPA client, etc.).
3. **Remove duplicated default literals** – ensure defaults live only in `Settings`.
4. **Enforce invariants** – add tests that fail if a module contains a magic number or accesses an undefined env‑var.
5. **Deduplicate topic names & ports** – centralise them in `Settings` and update any reference.
6. **Update CI** – modify `scripts/roadmap_invariant_scanner.py` to scan for stray `os.getenv` and hard‑coded numbers.
7. **Documentation** – reflect the new configuration model in `README.md` and `docs/`.

## Phase 8 — Settings Centralisation & Duplicate Removal (NEW)
**Goal:** Provide a single source‑of‑truth for configuration, eliminate all duplicated imports/flags, and simplify the architecture.

### High‑Level Architecture Changes
| Layer | Target Design |
|-------|----------------|
| **Configuration** | All environment variables are accessed **only** via `common.config.settings.Settings` (singleton `settings`). No direct `os.getenv` anywhere else. |
| **Health** | `common/health.py` reads values from `settings` and provides a FastAPI `/health` endpoint. |
| **Logging** | All modules import the shared logger from `common.logging`. |
| **Feature Flags** | Flags are boolean fields in `Settings`; no raw string checks. |
| **Infrastructure Helpers** | Helpers accept the `settings` singleton; all local `os.getenv` removed. |

### Concrete Refactor Steps (to be executed on the current branch)
1. **Catalogue** – run `grep -R "os.getenv" somabrain/` → CSV of file, line, variable, default.
2. **Settings Expansion** – add a typed `Field` for each entry in `common/config/settings.py` using the existing `_bool_env`, `_int_env`, `_float_env` helpers.
3. **Code Migration** – replace every `os.getenv("VAR")` with `settings.<field>` and delete any duplicated defaults.
4. **Health Service Refactor** – update `common/health.py` and remove duplicate reads in `somabrain/healthchecks.py`.
5. **Logging Consolidation** – ensure all modules import `from common.logging import logger` and remove any custom logger config.
6. **Feature‑Flag Cleanup** – verify each flag exists in `Settings`; delete stale flag logic.
7. **Legacy Removal** – permanently delete CI/e2e scripts and any mock‑only files; clean up `pyproject.toml` references.
8. **Testing** – run the full test suite, add `test_settings_centralisation.py` to assert every env‑var is present in `settings`.
9. **Documentation** – update `README.md`, `docs/`, and this ROAMDP file with the new architecture description.
10. **Merge** – commit the changes directly on the current branch, open a PR, run CI, and merge.

### Acceptance Criteria
- No `os.getenv` calls remain outside `common/config/settings.py`.
- All feature flags accessed via `settings`.
- Single logger instance used throughout.
- Health endpoint returns HTTP 200.
- CI passes with 100 % coverage for configuration code.

---
**Implementation Status**
All previous phases (0‑6) are complete. Phase 7 is in progress, and Phase 8 outlines the next concrete steps to achieve full centralisation and duplicate removal.

**Last Updated:** November 22, 2025

## Concrete files to change (examples)
- `somabrain/services/memory_service.py` — per-tenant circuit state and metric wiring.
- `somabrain/db/outbox.py` & `somabrain/db/models/outbox.py` — tenant-aware queries and DB indices.
- `somabrain/workers/outbox_publisher.py` — message keying, tenant batching, and headers.
- `somabrain/metrics.py` — ensure per-tenant metrics are registered once and used consistently.
- `migrations/` — add Alembic migration to create unique index on `(tenant_id, dedupe_key)` and pending-event index.

## Acceptance Criteria (high level)
- Existing: circuit breaker isolation per tenant; idempotent outbox; replay tooling; per-tenant dashboards.
- New Phase 5: unified predictor schema emitted; integrator softmax+OPA+Redis; segmentation metrics/config; flag off by default; E2E smoke passes.
- New Phase 6: sleep APIs active behind flag; schedules enforced (η=0 in deep/freeze); metrics & tests.
- New Phase 7: no hardcoded literals in predictors/integrator/segmentation/adaptive modules; settings-driven single source of truth; invariant tests pass.

## Implementation Status

### ✅ Phase 0 — Safety & Observability: COMPLETE
- 0.1 ✅ Per-tenant circuit-breaker: Centralized `CircuitBreaker` class in `somabrain/infrastructure/circuit_breaker.py` with complete tenant isolation
- 0.2 ✅ Outbox pending metric wiring: Implemented `_update_outbox_metric()` and `OUTBOX_PENDING` per-tenant metrics
- 0.3 ✅ Tenant-aware pending queries: Enhanced `get_pending_events()` with tenant support and proper DB indices

### ✅ Phase 1 — Idempotency, DB Constraints & Worker Hardening: COMPLETE
- 1.1 ✅ DB constraints & indices: Migration `b5c9f9a3d1ab_outbox_tenant_indices.py` with unique constraint on `(tenant_id, dedupe_key)`
- 1.2 ✅ Producer keying & headers: Enhanced outbox publisher with stable keys and comprehensive headers
- 1.3 ✅ Per-tenant batch quotas & backpressure: `TenantQuotaManager` class with rate limiting and fair processing

### ✅ Phase 3 — Memory Outbox & Write Modes: COMPLETE
- DB-backed outbox migration completed
- Enhanced HTTP headers with tenant context
- Memory write mode configuration implemented
- Tenant isolation fully operational

### ✅ Phase 2 — Replay/Recovery & Operational Tooling: COMPLETE
- 2.1 ✅ Admin replay endpoints: Implemented in `somabrain/app.py` and `somabrain/api/memory_api.py`
  - `POST /admin/outbox/replay` - Replay specific events by ID
  - `POST /admin/outbox/replay/tenant` - Replay events for specific tenant with filtering
  - Full tenant-aware replay with metrics and error handling
- 2.2 ✅ Optional local journaling: Implemented in `somabrain/journal/local_journal.py`
  - Complete LocalJournal class with file-based storage
  - Configurable rotation, retention, and compression
  - Integration with outbox system for redundant persistence
  - Thread-safe operations with JSON serialization

### ✅ Phase 4 — Tests, Docs & CI: COMPLETE

### 🚧 Phase 5 — Cognitive Threads v2: PARTIAL
- Unified predictor and global_frame schemas landed; state/agent/action predictors emit them.
- Integrator hub upgraded (softmax + OPA optional + Redis cache) with metrics; segmentation runtime thresholds + HMM toggle wired via ConfigService.
- Feature flag present; CI Kafka/Redis smoke still pending and flag currently default OFF on paper (enable in env when ready).

### ✅ Phase 6 — Sleep System & Degradation: COMPLETE
- Sleep APIs, schedules, and CB-driven mapping implemented; sleep params centralized in settings; η=0 in deep/freeze.
- `/api/util/sleep`, `/api/brain/sleep_mode`, and `/api/brain/sleep_policy` are live with the same validation pipeline (JWT + OPA, TTL storage, gauge updates), with the policy endpoint adding tenant rate-limiting and explicit circuit-breaker-aware transitions.
- Shared circuit breaker registry; memory degradation mode added: health reports `memory_degraded`, CB drives sleep FREEZE/LIGHT, writes queue to journal when circuit open (configurable), recalls auto-switch to WM-only when degraded. Needs full Docker verification and backlog flush wiring.

### 🚧 Phase 7 — Hardcoded-Value Purge & Settings Unification: IN PROGRESS
- Settings added for predictor alpha, segment thresholds, integrator/segment ports; predictors/integrator/segmentation now consume settings. Remaining modules (adaptive/learning/neuromodulators) still contain hardcoded defaults and need migration plus invariant tests.
- 4.1 ✅ Unit tests: CircuitBreaker and MemoryService delegation tests completed
  - `tests/infrastructure/test_circuit_breaker.py` - Comprehensive CircuitBreaker test suite
  - `tests/services/test_memory_service_circuit.py` - MemoryService delegation tests
  - All tests use real implementations (no mocks) following VIBE rules
- 4.2 ✅ Documentation updates: Complete
  - Updated ROAMDP.md with implementation status and examples
  - Added infrastructure module usage examples
  - Documented new CircuitBreaker and tenant utilities

## New Infrastructure Components

### Central Circuit Breaker (`somabrain/infrastructure/circuit_breaker.py`)
```python
from somabrain.infrastructure.circuit_breaker import CircuitBreaker

# Create shared instance
breaker = CircuitBreaker(global_failure_threshold=3, global_reset_interval=60.0)

# Configure per-tenant thresholds
breaker.configure_tenant('tenant1', failure_threshold=5, reset_interval=120.0)

# Record operations
breaker.record_success('tenant1')
breaker.record_failure('tenant1')
is_open = breaker.is_open('tenant1')
state = breaker.get_state('tenant1')
```

### Tenant Utilities (`somabrain/infrastructure/tenant.py`)
```python
from somabrain.infrastructure.tenant import tenant_label, resolve_namespace

# Extract tenant label from namespace
label = tenant_label('org:tenant1')  # Returns 'tenant1'
label = tenant_label('simple_tenant')  # Returns 'simple_tenant'
label = tenant_label('')  # Returns 'default'

# Resolve namespace from label
namespace = resolve_namespace('tenant1')  # Returns 'tenant1'
```

## 🎯 ROAMDP IMPLEMENTATION STATUS

- Phases 0–4: COMPLETE (as previously documented).
- Phase 5: NOT STARTED.
- Phase 6: NOT STARTED.
- Phase 7: IN PROGRESS (settings consolidated; more modules to migrate and tests to add).

**Last Updated:** November 21, 2025  
**Status:** In progress (Phases 5–7 outstanding)
