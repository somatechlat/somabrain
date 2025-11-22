# SomaBrain Canonical Roadmap (Merged ROAMDP + Sutton/Karpathy, VIBE‑compliant)

This roadmap consolidates the canonical ROAMDP gaps (Phases 5–7), the Sutton/Karpathy learning-loop hardening, and the stub/fallback purge into a single, production-readiness plan. It is grounded only in code and docs that exist in this repo—no speculative features.

## North Star
- Zero stubs, mocks, silent fallbacks, or magic numbers in runtime paths.
- Strict, observable cognitive loop: memory → recall → feedback → learning → predictors → integrator → segmentation.
- Single-source configuration (Settings/Config/Runtime) with feature flags centrally managed.
- CI/ops proof: schema compatibility, Kafka/Redis smokes, health gates, alerting.

## Phases (sprint-sized, ordered by risk reduction)

### Phase 0 — Stub/Fallback Purge & Safety (1 sprint)
- Remove placeholder backends and fail fast: `memory/__init__.py`, any optional local embeds unless explicitly dev-flagged.
- Replace stub `somabrain/services/learner_online.py` with real Kafka consumer/producer loop (no dummy gauges).
- Replace placeholder planning expansions in `somabrain/cognitive/planning.py` with real action evaluation.
- Eliminate implicit tenant defaults (`tenant.py` “public” fallback) unless gated by an explicit dev flag.
- Embedder: block `fde` fallback or implement real provider; no tiny/test vectors in production path.
- Persona safety: fix `schemas.PersonalityState` typing or disable persona endpoint in `app.py`.
- CI: extend `scripts/ci/forbid_stubs.sh` to block `placeholder|Dummy|no-op` in runtime code.

### Phase 1 — Learning Loop Hardening (Sutton) (1–2 sprints)
- Enforce entropy cap and τ annealing in `autonomous/learning.py` and `context/builder.py`; surface config in `common/config/settings.py`, `somabrain/config.py`, `config.yaml`.
- Metrics: τ, entropy, entropy_cap_hits in `somabrain/metrics/__init__.py`; `/health` must expose them.
- Feedback safety: validate + rate-limit `/context/feedback` (`app.py`, `services/reward.py`); reject out-of-range rewards.
- Tests: TD bounds, softmax correctness, entropy-cap behavior under edge inputs (`tests/learning/...`).

### Phase 2 — Tripartite Predictors + Integrator Hub (Karpathy) (2 sprints)
- Predictors (state/agent/action): ensure diffusion heat uses real domain Laplacians (no line-graph fallback) via `math/graph_heat.py` + `lanczos_chebyshev.py`.
- Emit `PredictorUpdate` Avro with `confidence`, `delta_error`, `posterior`; Avro schemas versioned in repo.
- Integrator: weight by precision (1/error) or document chosen policy; emit `GlobalFrame`; cache in Redis.
- Metrics: `somabrain_predictor_error{domain}`, `somabrain_integrator_leader_total{leader}`, leader entropy, τ.
- Tests: toy-graph spectral parity vs `scipy.linalg.expm`; Kafka ingest/publish smokes.
- Feature flags: centralize `ENABLE_COG_THREADS` and per-service flags in `somabrain/feature_flags.py`; align Helm defaults with settings.

### Phase 3 — Segmentation HMM/CPD (1 sprint)
- Harden `services/segmentation_service.py`: default topic preflight, hazard/HMM parameters from settings, validation metrics.
- Metrics: `somabrain_segmentation_boundaries_total{mode}`, entropy spikes; alerts on missing frames.
- Tests: synthetic series for leader-change detection and CPD/HMM correctness (`tests/segmenter/...`).

### Phase 4 — Config Unification & Hot-Swap Safety (1–2 sprints)
- Make `common/config/settings.py` the sole env reader; strip stray `os.getenv` from runtime code.
- Runtime config facade: `runtime/config_runtime.py` with validation; cache `get_config()`.
- `/health` asserts: no stub counts, diffusion method, τ, entropy_cap status.
- Deduplicate ports/topics into `config.yaml` and Helm values; update env templates.

### Phase 5 — Cognitive Threads v2 (ROAMDP Phase 5) (1–2 sprints)
- Unified predictor_update Avro already present—ensure all predictors emit it.
- Integrator hub softmax + optional OPA + Redis cache already present—add CI Kafka/Redis smokes and observability checks.
- Segmentation hardening: thresholds/HMM toggle via ConfigService; ensure `cog.segments` topic preflight.
- Feature flag `ENABLE_COG_THREADS` default OFF (settings + Helm); documented enable sequence.

### Phase 6 — Sleep System (ROAMDP Phase 6) (1 sprint)
- `/api/util/sleep` and `/api/brain/sleep_mode` are implemented with OPA/JWT/rate-limit guards and TTL auto-wake, but `/api/brain/sleep_policy` still needs to be built before the phase can be marked complete.
- Metrics: sleep-state gauge labels on latency/adaptation; counters for calls/toggles.
- Tests: monotonic schedules, TTL expiry, CB-driven FREEZE/LIGHT mapping; Docker/CI smoke.

### Phase 7 — Hardcoded-Value Purge & Settings Unification (ROAMDP Phase 7) (1 sprint)
- Move thresholds/ports/weights for predictors, integrator, segmentation, adaptive modules, neuromodulators into `common/config/settings.py`.
- Add invariant tests to forbid new magic numbers in those modules.
- Deduplicate topic names/ports in env templates and Helm values.

### Phase 8 — Observability, Benchmarks, Docs (1 sprint)
- Benchmarks: `feedback → leader selection` latency; diffusion predictor accuracy vs expm; learning retention.
- Dashboards/alerts: τ, entropy, predictor errors, segment boundaries, config-change metrics.
- Docs: updated Sutton ↔ Karpathy ↔ diffusion map, predictor/integrator/segmentation runbooks, sleep system operations.

## Scope-Control File List (touches)
- Runtime: `somabrain/app.py`, `somabrain/runtime/config*.py`, `somabrain/feature_flags.py`, `common/config/settings.py`, `config.yaml`
- Learning: `autonomous/learning.py`, `context/builder.py`, `services/reward.py`
- Predictors/Integrator/Segmentation: `services/predictor-*.py`, `services/integrator_hub.py`, `services/segmentation_service.py`, `math/graph_heat.py`, `math/lanczos_chebyshev.py`, `controls/segmenter.py`
- Memory/Planner/Auth/Tenant: `services/learner_online.py`, `cognitive/planning.py`, `embeddings.py`, `tenant.py`, `schemas.py`
- Metrics/CI: `metrics/__init__.py`, `scripts/ci/forbid_stubs.sh`, new tests under `tests/learning/`, `tests/predictors/`, `tests/segmenter/`
- Helm/env/templates: `infra/helm/...`, `config/env.example`

## Acceptance Criteria
- No stubs/placeholders/silent fallbacks in production code; CI blocks regressions.
- τ annealing + entropy cap enforced with metrics; `/health` exposes learning params.
- Predictors emit unified schema; integrator selects leader with documented weighting; segmentation emits boundaries; Kafka/Redis smokes pass.
- Sleep APIs enforced with OPA/JWT/rate limits; metrics and tests cover TTL/schedule.
- Config single-sourced; flags centralized; magic-number invariants enforced.
- Dashboards and alerts operational for learning and cognition signals.

## Status (as of 2025‑11‑22)
- Phase 0: PARTIAL (some stub purges pending)
- Phase 1: NOT STARTED (entropy/τ enforcement, feedback validation outstanding)
- Phase 2: PARTIAL (integrator/predictors exist; precision weighting + CI smokes pending)
- Phase 3: PARTIAL (segmentation modes exist; metrics/tests/preflight pending)
- Phase 4: NOT STARTED
- Phase 5: PARTIAL (feature flag default misaligned across settings/Helm; smokes missing)
- Phase 6: PARTIAL (APIs exist; CI/Docker verification and metrics gaps remain)
- Phase 7: IN PROGRESS (some settings migrated; magic-number invariants missing)
- Phase 8: NOT STARTED

## Cleanup & Refactor Plan (VIBE Coding Rules)

The repository has been audited and the following comprehensive cleanup plan will be applied to achieve a perfect, production‑ready code base with no legacy, duplicate, or hard‑coded values.

### 1️⃣ Audit & Inventory
- Search all Python files for imports of `settings` and duplicate imports.
- Identify unused `Settings` fields (`integrator_triplet_health_url`, `segmentation_health_url`, `somabrain_cog_base_url`).
- Locate duplicated helper functions (`_int_env`, `_bool_env`, `_float_env`, health‑check logic, URL construction).
- Scan benchmarks for repeated async client/queue code.
- Find repeated CLI argument parsing.
- Gather all logging configuration occurrences.

### 2️⃣ Consolidate `settings` Imports
- Adopt a single import style: `from common.config.settings import settings`.
- Remove any additional aliases (`_settings`, `_shared`, etc.) across all modules (107 matches).
- Run a linter to ensure no unused imports remain.

### 3️⃣ Remove Legacy / Mock / Test‑Only Files
- Delete all CI‑only scripts (`ci_readiness.py`, `verify_config_update.py`, `sb_precheck.py`, etc.).
- Remove smoke/demo scripts not used in production (`devprod_smoke.py`, `e2e_*_smoke.py`, `verify_roadmap_compliance.py`).
- Remove benchmark helper scripts that duplicate functionality.
- Ensure the `tests/` directory is already removed.

### 4️⃣ Centralise Helper Functions
- Keep `_int_env`, `_bool_env`, `_float_env` only in `common/config/settings.py`.
- Create `common/health.py` with `def check_health(url: str) -> bool` and replace ad‑hoc checks.
- Centralise logging in `common/logging.py` and expose a `logger` object.
- Add `common/cli.py` providing `add_common_args(parser)` for shared CLI flags.
- Add `benchmarks/utils.py` offering reusable async request execution and stats aggregation.

### 5️⃣ Prune Unused Settings Fields
- Verify usage of `integrator_triplet_health_url`, `segmentation_health_url`, `somabrain_cog_base_url`.
- Remove any that are not referenced after legacy script deletion.

### 6️⃣ Standardise Error Handling & Return Types
- Ensure services raise `RuntimeError` with clear messages instead of returning `None`.
- Log errors via the central logger and re‑raise.
- Replace `sys.exit` in scripts with proper exception handling.

### 7️⃣ Run Static Analysis & Formatting
- Execute `ruff`/`flake8` for unused imports, naming, and duplicate code.
- Run `mypy`/`pyright` for type consistency.
- Apply `black` and `isort` for formatting.
- Verify any remaining tests pass (`pytest`).

### 8️⃣ Validate Runtime Behaviour
- Start the Docker compose stack and perform a health‑check using `settings.api_url`.
- Run a simple benchmark via the new utilities.
- Ensure all services start without hard‑coded URLs.

### 9️⃣ Document the New Architecture
- Add `ARCHITECTURE.md` describing the single source of truth (`Settings`), shared utilities, and logging.
- Provide a brief guide for adding new services following the VIBE rules.

### 🔟 Final Deliverable
- Clean repository containing only production code.
- Centralised configuration, utilities, and documentation.
- Consistent style, no duplicated logic, and fully functional service.

*All the above steps will be executed automatically via a series of patches, linting runs, and validation checks to ensure the repository complies with the VIBE coding standards.*
