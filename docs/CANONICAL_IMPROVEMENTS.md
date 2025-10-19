# CANONICAL IMPROVEMENTS – SomaBrain

This report captures the hardening and documentation work completed so far and highlights remaining opportunities that keep SomaBrain powerful while simplifying configuration.

---

## Completed Improvements

### Documentation (docs/user-manual/)
- Rebuilt every user-facing guide with real request/response samples drawn from the running API.
- Installation now documents the mandatory external memory service, verification commands, and failure recovery (`installation.md`).
- Quick Start tutorial exercises `/remember → /recall → /context/feedback` with genuine JSON payloads and troubleshooting tips (`quick-start-tutorial.md`).
- Feature pages map directly to the backing modules:
  - Memory operations (`features/memory-operations.md`) ↔ `somabrain/app.py`, `somabrain/schemas.py`.
  - Cognitive reasoning (`features/cognitive-reasoning.md`) ↔ `somabrain/context`, `somabrain/learning`, `somabrain/api/context_route.py`.
  - API integration (`features/api-integration.md`) ↔ endpoint catalogue with headers, auth, metrics.
  - Multi-tenant operation (`features/multi-tenant-usage.md`) ↔ `somabrain/tenant.py`, `somabrain/quotas.py`, `somabrain/ratelimit.py`.
- FAQ now answers questions using the actual handler behaviour, not marketing copy (`faq.md`).

### Configuration Surfaces
- Adaptation engine gains and constraints no longer hardcode deltas; they load from shared settings or `SOMABRAIN_LEARNING_GAIN_*` / `SOMABRAIN_LEARNING_BOUNDS_*` environment variables (`somabrain/learning/adaptation.py`).
- Context builder tau and density heuristics are configurable via config/env (`somabrain/context/builder.py`).
- Planner penalties accept overrides (`somabrain/context/planner.py`).
- Unified scorer now honours `scorer_*` config/env overrides and exposes active/default weights via diagnostics (`somabrain/scoring.py`).
- Adaptation state endpoint returns configured gains/bounds and metrics emit them for observability (`somabrain/api/context_route.py`, `somabrain/metrics.py`).
- Superposed trace cleanup distinguishes “no anchors” from “low similarity” and logs misses (`somabrain/memory/superposed_trace.py`).
- Tau diversity adjustments scale with the observed duplicate ratio instead of fixed steps (`somabrain/context/builder.py`).
- Memory service reports queued writes via Prometheus and memory client uses narrower exception handling (`somabrain/app.py`, `somabrain/memory_client.py`).

### Code Quality
- `/remember` continues to journal queued writes and exposes breaker state when the memory service is unavailable (`somabrain/app.py:2497-2700`).
- Unified scorer clamps weights and records metrics when limits are reached (`somabrain/scoring.py`).
- Superposed trace maintains deterministic rotations and cleanup behaviour with validated configs (`somabrain/memory/superposed_trace.py`).

---

## Recommended Next Actions

| Area | Description | Files / Modules |
|------|-------------|-----------------|
| Scorer configuration | Load default weights/τ from config/env; expose active values via `/metrics` or `stats()` output. | `somabrain/scoring.py` |
| Cleanup diagnostics | Emit metrics/logs when `_cleanup` fails to find anchors and return explicit `None` instead of empty strings. | `somabrain/memory/superposed_trace.py` |
| Tau step adaptation | Make `_compute_weights` adjust τ proportionally to duplicate ratio rather than fixed ± increments. | `somabrain/context/builder.py` |
| Memory client telemetry | Narrow broad `except` clauses and count journal replay events so outages are observable. | `somabrain/memory_client.py`, `somabrain/services/memory_service.py` |
| Adaptation introspection | Surface configured gains/constraints through `/context/adaptation/state` or Prometheus for runtime verification. | `somabrain/api/context_route.py`, `somabrain/learning/adaptation.py` |

---

## Guiding Principle

**Simplify interfaces and configuration without reducing capability**—BHDC maths, semantic retrieval, and adaptive learning remain intact or stronger once these follow-up items land.
