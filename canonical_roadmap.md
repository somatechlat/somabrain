# SomaBrain Canonical Roadmap (VIBE‑compliant)

This is the single source of truth for the current Somabrain implementation plan. It removes all stubs/fallbacks/shims, completes the Sutton + Karpathy learning loop, and introduces the tripartite predictor architecture with an integrator hub. All items below are grounded in files that already exist in the repo; no speculative features.

## Goals
- Zero stubs, mocks, placeholders, or silent fallbacks in runtime code.
- Real learner, planner, embedder, and tenant handling.
- Unified configuration (Settings/Config/Runtime) with hot‑swap safety.
- Tripartite predictors (state/agent/action) + integrator hub built on existing diffusion code.
- Segmentation upgraded with a formal HMM wrapper.
- Observable, test‑backed learning loop: entropy caps, τ annealing, metrics.

## Phased Implementation (sprint‑sized)

### Phase 0 — Stub/Fallback Purge & Safety (1 sprint)
- Remove placeholder `memory/__init__.py`; fail fast when backend missing.
- Replace `somabrain/services/learner_online.py` stub with real loop (Kafka consumer/producer required; no dummy gauge).
- Replace placeholder expansion/termination in `somabrain/cognitive/planning.py` with real actions/evaluation.
- Block or implement real FDE provider in `somabrain/embeddings.py`; no tiny fallback when `provider="fde"`.
- Fix `somabrain/schemas.py:PersonalityState` (typed traits) or disable persona endpoint in `somabrain/app.py`.
- Drop sync tenant `"public"` fallback in `somabrain/tenant.py` (or gate behind an explicit dev flag).
- CI guardrails: extend `scripts/ci/forbid_stubs.sh` to catch `placeholder|Dummy|no-op` in runtime code.

### Phase 1 — Learning Loop Hardening (Sutton/Karpathy) (1–2 sprints)
- Enforce `entropy_cap` and τ annealing schedule in `somabrain/autonomous/learning.py` and `somabrain/context/builder.py`; expose config keys in `somabrain/runtime/config.py` + `config.yaml`.
- Metrics: add τ/entropy/entropy_cap_hits to `somabrain/metrics/__init__.py`; surface via `/health`.
- Input safety: validate and rate-limit `/context/feedback` payloads (`somabrain/app.py`, `somabrain/services/reward.py`).
- Tests: TD weight bounds, softmax correctness, entropy-cap behavior (new `tests/learning/...`).

### Phase 2 — Tripartite Predictors + Integrator Hub (2 sprints, parallelizable)
- Implement `state_predictor`, `agent_predictor`, `action_predictor` services using `somabrain/math/graph_heat.py` & `somabrain/math/lanczos_chebyshev.py` via `somabrain/controls/feature_flags.py` heat factory.
- Emit `PredictorUpdate` (salience, observed vector, error) to Kafka with Avro schema.
- Implement `integrator_hub` service: consume updates, weight = exp(-α·error), pick leader, emit `GlobalFrame` Avro.
- Metrics: `somabrain_predictor_error{domain}`, `somabrain_integrator_leader_total{leader}`; tests on toy graphs (compare to `scipy.linalg.expm`).

### Phase 3 — Segmentation HMM Wrapper (1 sprint)
- Wrap existing gradient-threshold output in a 2‑state HMM (or CPD) inside `somabrain/controls/segmenter.py`; feature flag to select `hmm` vs `threshold`.
- Metrics: `somabrain_segment_hmm_boundary_total`; tests on synthetic series.

### Phase 4 — Config Unification & Hot‑Swap (1–2 sprints)
- Make `common/config/settings.py` the only env reader; strip stray `os.getenv` from runtime code.
- Cache `get_config()`; keep cognitive defaults solely in `somabrain/config.py`.
- Turn `somabrain/runtime_config.py` into a shim over `somabrain/runtime/config_runtime.py`; add `live_config` facade + safety validator for runtime changes.
- Centralize feature flags into `somabrain/feature_flags.py`; refactor gates.
- `/health` must assert `stub_counts == 0`, expose diffusion method, τ, entropy_cap status.

### Phase 5 — Observability, Benchmarks, Docs (1 sprint)
- Benchmark `feedback → leader selection` latency (`benchmarks/learning_latency.py`).
- Update docs: concise Sutton ↔ Karpathy ↔ diffusion map and new predictor/integrator flows (`docs/developer-manual/learning.md`).
- Dashboards/alerts for τ, entropy, predictor errors, segment HMM boundaries, config change metrics.

## File/Module Touch List (scope control)
- `somabrain/services/learner_online.py`
- `somabrain/cognitive/planning.py`
- `somabrain/embeddings.py`, `somabrain/config.py`, `config.yaml`
- `somabrain/schemas.py`, `somabrain/app.py` (persona, feedback)
- `somabrain/tenant.py`
- `somabrain/autonomous/learning.py`, `somabrain/context/builder.py`, `somabrain/services/reward.py`
- `somabrain/metrics/__init__.py`
- `somabrain/runtime/config.py`, `somabrain/runtime/config_runtime.py`, `somabrain/feature_flags.py`
- `somabrain/math/graph_heat.py`, `somabrain/math/lanczos_chebyshev.py`, `somabrain/controls/feature_flags.py`, `somabrain/controls/segmenter.py`
- New schemas (Avro) for PredictorUpdate/GlobalFrame; predictor/integrator services
- Tests under `tests/learning/`, `tests/predictors/`, `tests/segmenter/`

## Acceptance Criteria
- No runtime stubs/placeholders/fallbacks; CI blocks new ones.
- Learner, planner, embedder, tenant resolution all real and fail-fast on missing deps.
- τ annealing and entropy caps enforced; metrics and tests cover edge cases.
- Tripartite predictors + integrator hub emit GlobalFrame with metrics and schema coverage.
- Segmentation offers HMM mode with metrics; default remains deterministic if flag off.
- Config is single-sourced (Settings/Config/Runtime) with hot-swap safety and health reporting.

## Status Tracking
- Phase 0: NOT STARTED (in progress after this consolidation)
- Phase 1: NOT STARTED
- Phase 2: NOT STARTED
- Phase 3: NOT STARTED
- Phase 4: NOT STARTED
- Phase 5: NOT STARTED

## Sprint Parallelization Notes
- Phase 0 can run in parallel with Phase 1 (entropy/τ) but must finish before prod cut.
- Phase 2 predictor/integrator work can start once Phase 0 removes stubs and Phase 1 exposes τ/entropy metrics.
- Phase 3 segmentation can run alongside Phase 2 (shared metrics only).
- Phase 4 config unification should start after Phase 0 (to avoid chasing moving env reads).
- Phase 5 depends on metrics being in place (Phase 1/2/3).

## VIBE Compliance
- Real implementations only; fail fast on missing deps.
- No shims, no silent fallbacks, no hardcoded magic numbers in hot path.
- Tests required for every new behavior; metrics for every new critical variable.
