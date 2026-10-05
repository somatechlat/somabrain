# SOMA-BR-ARCH-TRUTH-001 — Architecture Truth Document

> **Derived exclusively from code.** Aspirational documents (`docs/SOMABRAIN_ARCHITECTURE.md`,
> `docs/SomabrainGMD.md`, `SOMABRAIN_CODEBASE_DOCUMENTATION.md`, `docs/iso/SOMA-BR-ARCH-001.md`)
> are treated as claims to be verified, not as sources of truth. Where code and a document
> disagree, the code wins (THE-SOMA-COVENANT Title V).

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Architecture Truth Document |
| Document Identifier | SOMA-BR-ARCH-TRUTH-001 |
| Version | 1.0.0 |
| Date | 2026-10-04 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO/IEC 42010:2011 structure only (not certified) |
| Next Review | 2027-01-04 |
| Source of truth | Repository code at commit-time of writing |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-04 | SomaTech Engineering | Initial issue. Code-derived architecture truth: live/dead map, integrations, dual-implementation register, claims-vs-code table. |

---

## 1. System Purpose (what the CODE does)

SomaBrain is a Django + Django Ninja HTTP service that embeds task text into vectors, keeps a
per-tenant in-process working memory, routes durable memory reads/writes to an external memory
HTTP service (SomaFractalMemory or compatible), runs a synchronous per-request "cognitive step"
(prediction error → neuromodulator state → salience → store/act gates) on `POST /cognitive/act`,
optionally plans via a graph engine, adapts retrieval/utility weights from feedback endpoints,
and runs a separate Kafka-based tripartite predictor/integrator pipeline as sidecar processes.
It depends on external PostgreSQL, Redis, Kafka, OPA, and (optionally) Milvus; a PyO3 Rust
extension (`somabrain_rs`) accelerates some math when present, with Python fallbacks.

Evidence: API surface `somabrain/api/v1.py:18-155`, URL mount `somabrain/config/urls.py:461-475`,
runtime singletons `somabrain/runtime/manager.py:72-91`, cognitive step
`somabrain/services/cognitive_loop_service.py:116-273`, integrator sidecar
`somabrain/services/integrator_hub_triplet.py:86-418` and `infra/standalone/docker-compose.yml:1068`,
adaptation `somabrain/learning/adaptation/engine.py:53-348`, Rust module `rust_core/src/lib.rs:31-96`.

---

## 2. Component Map (major packages / roles)

| Package / module | Role | Status |
|---|---|---|
| `somabrain/config/urls.py` | Django URLconf: health probes, metrics, mounts Ninja API at `/api/` and root | IMPLEMENTED (`urls.py:461-475`) |
| `somabrain/api/v1.py` | Central `NinjaAPI`; registers all routers always-on | IMPLEMENTED (`v1.py:18-155`) |
| `somabrain/api/endpoints/*` | HTTP handlers (cognitive, memory, health, config, sleep, neuromod, …) | IMPLEMENTED |
| `somabrain/api/endpoints/cognitive.py` | `/cognitive/act`, `/cognitive/plan/suggest`, personality, micro diag | IMPLEMENTED (`cognitive.py:108-344`) |
| `somabrain/bootstrap/singletons.py` | Factories: predictor, amygdala, per-tenant neuromods, personality | IMPLEMENTED (`singletons.py:31-289`) |
| `somabrain/bootstrap/core_singletons.py` | Factories for WM, HRR ctx, hippocampus, supervisor, exec, drift, SDR, UnifiedBrainCore, FNOM | MIXED — many factories never invoked on live path (see §3) |
| `somabrain/bootstrap/runtime_init.py` | `register_singletons`, `create_mt_memory`, backend-enforcement helper | IMPLEMENTED but partially orphaned (see §3) |
| `somabrain/runtime/manager.py` | `RuntimeManager`: lazy embedder + `MultiTenantWM` + `MultiTenantMemory` | IMPLEMENTED (`manager.py:52-224`) |
| `somabrain/services/cognitive_loop_service.py` | `eval_step`: sleep → predictor error → neuromod → salience → gates | IMPLEMENTED (`cognitive_loop_service.py:116-273`) |
| `somabrain/services/memory_service.py` | Memory façade + circuit-breaker + degradation journal | IMPLEMENTED (referenced `memory.py:39`) |
| `somabrain/services/retrieval_pipeline.py` | `run_retrieval_pipeline` helper | DEAD (no callers; see §3) |
| `somabrain/services/integrator_hub_triplet.py` | Kafka consumer/producer tripartite integrator sidecar | IMPLEMENTED as separate process (`integrator_hub_triplet.py:428-450`, compose `:1068`) |
| `somabrain/services/integrator_hub.py` | Re-export of triplet + test-only `SoftmaxIntegrator` | TRIVIAL re-export (`integrator_hub.py:14`) |
| `somabrain/services/state_predictor.py` / `agent_predictor.py` / `action_predictor.py` | Kafka domain predictor workers | IMPLEMENTED as supervisord processes (`infra/standalone/ops/supervisor/supervisord.conf:25,38,51`) |
| `somabrain/services/entry.py` | In-process orchestrator for cog threads | BROKEN if run (`entry.py:45` calls `hub.run_forever()`; hub only has `run()` at `integrator_hub_triplet.py:384`) |
| `somabrain/memory/wm/core.py` | `WorkingMemory` buffer: admit/recall/novelty, eviction, promotion hooks | IMPLEMENTED (`wm/core.py:84-187`) |
| `somabrain/memory/scoring.py` | Recall scoring helpers (`rank_hits`, `rescore_and_rank_hits`) | DEAD export (see §3) |
| `somabrain/memory/client/ranking.py` | Live reranking used by memory client search | IMPLEMENTED |
| `somabrain/admin/core/learning/scoring.py` | `UnifiedScorer` used by WM / retrieval / memory pool | IMPLEMENTED |
| `somabrain/admin/core/learning/prediction.py` | Python `MahalanobisPredictor`, `BudgetedPredictor`, `LLMPredictor`, `SlowPredictor` | IMPLEMENTED (live predictor path) |
| `somabrain/predictors/base.py` + `predictors/{agent,action,state}_predictor.py` | Heat-diffusion predictors (`HeatDiffusionPredictor`) | DEAD (package never imported; see §3) |
| `somabrain/runtime/neuromodulators.py` | `NeuromodState`, `Neuromodulators`, `PerTenantNeuromodulators`, adaptive variants | IMPLEMENTED (live: `singletons.py:278-282`) |
| `somabrain/admin/brain/neuromodulators.py` | Near-duplicate neuromodulator tree | DUPLICATE (see §6) |
| `somabrain/admin/brain/unified_core.py` | `UnifiedBrainCore.process_memory` / `retrieve_memory` | DEAD on live path (only factory `create_unified_brain`, never called) |
| `somabrain/admin/cognitive/basal_ganglia.py` | `BasalGangliaPolicy` | DEAD (never imported) |
| `somabrain/runtime/supervisor.py` | `Supervisor.free_energy` / `adjust` | DEAD on `/act` path (see §3, §7) |
| `somabrain/learning/adaptation/engine.py` | Online weight adaptation (retrieval αβγτ, utility λμν) | IMPLEMENTED (live via `/context/*`, `api/endpoints/context.py:73-217`) |
| `somabrain/lifecycle/startup.py` | Startup handlers (Kafka/OPA enforce, outbox sync, Milvus reconcile, …) | DEAD (never registered; `admin/core/apps.py:26-33` `ready()` is side-effect free) |
| `somabrain/settings/` (`infra.py`, `cognitive.py`, `django_core.py`, …) | Env-backed configuration | IMPLEMENTED |
| `rust_core/src/{lib,neuro,mathcore,adaptation,prediction,bhdc}.rs` | PyO3 `somabrain_rs` math/neuro/prediction/adaptation | IMPLEMENTED (optional; Python fallbacks exist) |
| `somabrain/math/bhdc_encoder.py` | BHDC encoder + permutation binder with Rust/Python dual backends | IMPLEMENTED (dual; see §6) |
| `somabrain/admin/core/quantum.py` | `QuantumLayer` BHDC operations (bind/unbind/cleanup) | IMPLEMENTED |
| `somabrain/admin/core/integrator_hub.py` | Claims to re-export triplet hub | BROKEN (`admin/core/integrator_hub.py:20` imports `.services.integrator_hub_triplet`; `somabrain/admin/core/services/` does not exist) |

---

## 3. LIVE vs DEAD Path Table

Legend:
- **LIVE** — reachable from an HTTP request path or a documented process entrypoint that is actually launched.
- **TEST-ONLY** — only imported/constructed from `tests/`.
- **DEAD** — defined and exported but no production caller found.
- **BROKEN** — would fail if invoked (bad import, missing method, wrong arity).
- **TRIVIAL** — thin re-export / no independent logic.

| Class / function | Path role | Evidence (file:line) | Status |
|---|---|---|---|
| `urls.urlpatterns` → `api.urls` | HTTP entry | `somabrain/config/urls.py:461-475` | LIVE |
| `act_endpoint` (`POST /cognitive/act`) | Main cognitive request | `somabrain/api/endpoints/cognitive.py:171-293` | LIVE |
| `plan_suggest` (`POST /cognitive/plan/suggest`) | Planner | `cognitive.py:108-168` | LIVE (gated `SOMABRAIN_USE_PLANNER`, default False `settings/cognitive.py:293`) |
| `get_predictor` / `make_predictor` | Predictor singleton | `somabrain/bootstrap/singletons.py:31-92,266-268`; used `cognitive.py:187` | LIVE |
| `MahalanobisPredictor` (Python) | Default predictor base | `singletons.py:69-70`; impl `somabrain/admin/core/learning/prediction.py:247-347` | LIVE |
| `get_neuromodulators` → `PerTenantNeuromodulators` | Neuromod state | `singletons.py:278-282`; used `cognitive.py:188` | LIVE |
| `get_amygdala` → `AmygdalaSalience` | Salience + gates | `singletons.py:271-275`; used `cognitive.py:190` | LIVE |
| `get_personality_store` | Traits modulation | `singletons.py:285-289`; used `cognitive.py:189` | LIVE |
| `eval_step` | Cognitive step | `somabrain/services/cognitive_loop_service.py:116-273`; called `cognitive.py:209-220` | LIVE |
| `RuntimeManager.initialize_runtime` | Embedder/WM/memory pool | `somabrain/runtime/manager.py:72-91`; triggered `cognitive.py:52-57` | LIVE |
| `MemoryService` remember/recall | LTM HTTP path | `somabrain/api/endpoints/memory.py:235-269`; `api/memory/recall.py:170-258` | LIVE |
| `FocusState` update/persist | Session focus | `cognitive.py:193-243` | LIVE (gated `SOMABRAIN_USE_FOCUS_STATE` default True `settings/cognitive.py:294`) |
| `IntegratorHub.run` | Kafka integrator loop | `somabrain/services/integrator_hub_triplet.py:384-418`; process entry `:428-450`; compose `infra/standalone/docker-compose.yml:1068` | LIVE (sidecar process) |
| `StatePredictorService` / `AgentPredictorService` / `ActionPredictorService` | Kafka domain predictors | `somabrain/services/state_predictor.py:239-240`; `agent_predictor.py:271`; `action_predictor.py:298`; launched `infra/standalone/ops/supervisor/supervisord.conf:25,38,51` | LIVE (sidecar processes) |
| `AdaptationEngine.apply_feedback` | Weight learning | `somabrain/learning/adaptation/engine.py:322-348`; used `somabrain/api/endpoints/context.py:101-106` | LIVE |
| `create_supervisor` / `Supervisor` | Free-energy supervisor | Factory `somabrain/bootstrap/core_singletons.py:165-184`; **never called**; `/act` passes `supervisor=None` (`cognitive.py:216`) | DEAD |
| `Supervisor.free_energy` / `adjust` | Free energy F | `somabrain/runtime/supervisor.py:88-134` | DEAD on request path |
| `BasalGangliaPolicy` | BG selection / store-act policy | `somabrain/admin/cognitive/basal_ganglia.py:45`; **zero imports** in `somabrain/` | DEAD |
| `UnifiedBrainCore.process_memory` / `retrieve_memory` | Unified math core | `somabrain/admin/brain/unified_core.py:23-56`; only factory `core_singletons.py:273-289` (never invoked) | DEAD |
| `AdaptiveNeuromodulators` / `AdaptivePerTenantNeuromodulators` | Performance-adaptive neurochem | `somabrain/runtime/neuromodulators.py:241-422`; `admin/brain/neuromodulators.py:239-420`; tests `tests/proofs/category_d/test_state_isolation.py:149-280` | TEST-ONLY |
| `run_retrieval_pipeline` | Retrieval pipeline | `somabrain/services/retrieval_pipeline.py:98-211`; **no callers** (recall uses `MemoryService.arecall` / `perform_recall`) | DEAD |
| `somabrain.memory.scoring.rank_hits` / `rescore_and_rank_hits` / `apply_weighting_to_hits` | Scoring helpers | `somabrain/memory/scoring.py:227,269,349`; exported `memory/__init__.py:50-59` but **never imported**; live twin is `memory/client/ranking.py:_rank_hits/_rescore_and_rank_hits` used by `memory/client/search.py:68,138` | DEAD |
| `HeatDiffusionPredictor` + `build_predictor_from_env` + domain wrappers | Graph-heat predictors | `somabrain/predictors/base.py:56-269`, `predictors/agent_predictor.py:42`, etc.; package **never imported** outside itself | DEAD |
| `somabrain.predictors` domain services equivalents in `services/*_predictor.py` use Python `MahalanobisPredictor` instead | — | `services/state_predictor.py:55` | (contrast only) |
| `lifecycle.startup.*` (banner, constitution, Kafka/OPA enforce, outbox sync, Milvus reconcile, observability) | Boot handlers | `somabrain/lifecycle/startup.py:22-333`; exports `lifecycle/__init__.py:10-32`; `AppConfig.ready()` does nothing (`admin/core/apps.py:26-33`); docstring says register in `app.py` (`startup.py:7-8`) but `app.py` is gone | DEAD |
| `bootstrap/runtime_init.register_singletons` | Dual DI registration | `runtime_init.py:106-183`; no production caller found (only `create_fractal_memory` used in tests `tests/proofs/category_e/test_memory_e2e.py:40`) | TEST-ONLY / orphan |
| `create_fnom_memory` / `create_fractal_memory` | FNOM + fractal adapters | `core_singletons.py:297-379`; not called from runtime manager | DEAD on live path |
| `admin/core/integrator_hub.py` re-export | Facade | `somabrain/admin/core/integrator_hub.py:20` — import target `somabrain.admin.core.services.integrator_hub_triplet` **does not exist** | BROKEN |
| `services/entry.py:_run_integrator` | Orchestrator | `entry.py:45` calls `hub.run_forever()`; `IntegratorHub` exposes `run()` only (`integrator_hub_triplet.py:384`) | BROKEN if launched |
| Rust `MahalanobisPredictor` | Rust predictor | `rust_core/src/prediction.rs:66-94`; never constructed from Python (Python uses `admin/core/learning/prediction.py`) | DEAD (from Python) |
| Rust TD API (`compute_td_error`, `compute_td_return`, `compute_n_step_return`, `decay_eligibility`) | Sutton TD | Registered `rust_core/src/lib.rs:90-93`; no Python importers of these symbols | DEAD (from Python) |
| Rust `Neuromodulators` sync | Rust neurochem mirror | Used by both Python trees via `rust_bridge` (`runtime/neuromodulators.py:126-155`) | LIVE (optional) |
| `lib.rs` unit tests `test_bayesian_memory_snr`, `test_capacity_estimation` | Rust tests | Rewritten in W4 against the live API (`BayesianMemory::new(dimension, eta, lambda_reg)`, `compute_snr_at_lag`, `estimate_horizon`) | GREEN (W4) |

---

## 4. End-to-End Data Flow — `POST /cognitive/act`

Numbered steps as implemented:

1. **URL dispatch** — request matches Ninja API mounted at both `/api/` and root:
   `somabrain/config/urls.py:471-474` → `somabrain/api/v1.py:18-24`.
2. **Router** — cognitive router registered at prefix `/cognitive/`:
   `somabrain/api/v1.py:66-68`.
3. **Auth + tenant** — `act_endpoint` resolves tenant and enforces auth:
   `somabrain/api/endpoints/cognitive.py:177-178` (`get_tenant_sync`, `require_auth`).
4. **Singletons** — predictor, per-tenant neuromodulators, personality store, amygdala:
   `cognitive.py:180-190` → `somabrain/bootstrap/singletons.py:266-289`.
   Predictor construction: `make_predictor` (`singletons.py:31-92`) wraps
   `MahalanobisPredictor(alpha=0.01)` in `BudgetedPredictor`
   (`admin/core/learning/prediction.py:247-347`).
5. **Embed task** — `embedder.embed(body.task)`:
   `cognitive.py:191`. Embedder is a `RuntimeManager` singleton
   (`runtime/manager.py:122-140`, factory `admin/core/embeddings.make_embedder`).
6. **Focus state** — session-scoped `FocusState` from TTL cache; previous focus vector captured:
   `cognitive.py:192-197`, `_get_or_create_focus_state` `cognitive.py:70-93`.
7. **Cognitive step** — `eval_step(...)`:
   `cognitive.py:209-220` → `somabrain/services/cognitive_loop_service.py:116-273`:
   1. Sleep state from Django ORM with 5s TTL: `cognitive_loop_service.py:61-96,148`.
   2. If `SleepState.FREEZE` → zeroed result: `cognitive_loop_service.py:153-165`.
   3. Prediction error via `predictor.predict_and_compare(previous_focus_vec, wm_vec)`:
      `cognitive_loop_service.py:185`; if no previous focus, error forced 0:
      `cognitive_loop_service.py:172-181`.
   4. Neuromod state + optional personality modulation:
      `cognitive_loop_service.py:196-211`.
   5. Supervisor adjustment — **`supervisor=None` on this path**, so free energy `F`
      stays `None`: `cognitive.py:216`, `cognitive_loop_service.py:212-223,267`.
   6. Salience `amygdala.score(...)` and gates `amygdala.gates(s, nm)`:
      `cognitive_loop_service.py:225-231`; trait uplift forces `s = 1.0`:
      `cognitive_loop_service.py:226-228`.
   7. Optional Kafka `BeliefUpdatePublisher` telemetry:
      `cognitive_loop_service.py:236-258`.
8. **Act step payload** assembled from gates/salience:
   `cognitive.py:222-234`.
9. **Focus snapshot persist** (if `store_gate`):
   `cognitive.py:236-243` → `FocusState.persist_snapshot`.
10. **Optional plan** if `USE_PLANNER`:
    `cognitive.py:245-273` (`PlanEngine`, default off `settings/cognitive.py:480`).
11. **Response** `ActResponse`:
    `cognitive.py:288-293`.

Background (not on the HTTP request path): Kafka domain predictors
(`supervisord.conf:25,38,51`) publish `cog.*.updates`; `IntegratorHub.run`
(`integrator_hub_triplet.py:384-418`) selects a leader by precision-weighted softmax
(`_select_leader` `:239-261`) and publishes `GlobalFrame` (`_publish_global` `:263-353`).

---

## 5. Integration Points (from settings / infra)

| Dependency | Config surface | Real usage | Evidence |
|---|---|---|---|
| **PostgreSQL** | `SOMABRAIN_POSTGRES_DSN` | Django ORM (sleep state, brain settings, outbox); FNOM KV factory requires DSN | `settings/infra.py:127`, `settings/django_core.py:226-229`, `cognitive_loop_service.py:70-78`, `core_singletons.py:342-351` |
| **Redis** | `SOMABRAIN_REDIS_URL` / `SOMABRAIN_REDIS_HOST/PORT` | Django cache (health/readyz), adaptation state persistence, integrator global-frame cache | `settings/infra.py:153-157`, `config/urls.py:53-60,143-157`, `learning/adaptation/engine.py:105,465-491`, `integrator_hub_triplet.py:152-160,324-327` |
| **Kafka** | `KAFKA_BOOTSTRAP_SERVERS` / `SOMABRAIN_KAFKA_URL` | Domain predictor workers + IntegratorHub consume/produce; BeliefUpdate publisher; outbox sync | `settings/infra.py:209-227`, `integrator_hub_triplet.py:117-148`, `supervisord.conf:25,38,51`, `cognitive_loop_service.py:46-54` |
| **OPA** | `SOMABRAIN_OPA_URL` / `OPA_URL` | Health check `GET {url}/health`; integrator leader veto `POST .../v1/data/soma/policy/integrator`; strict fail-closed policy flag | `settings/infra.py:234-258`, `config/urls.py:198-213`, `integrator_hub_triplet.py:336-351,355-382`, `lifecycle/startup.py:49` (comment: always fail-closed) |
| **Milvus** | `SOMABRAIN_MILVUS_HOST/PORT/COLLECTION` | Optional OAK path (`ENABLE_OAK`); FNOM vector store factory; reconciliation job (if wired) | `settings/infra.py:164-168`, `config/urls.py:176-195`, `core_singletons.py:353-372`, `lifecycle/startup.py:219-250` (handler itself DEAD) |
| **Memory HTTP (SFM)** | `SOMABRAIN_MEMORY_HTTP_ENDPOINT`, `SOMABRAIN_MEMORY_HTTP_TOKEN` | All LTM remember/recall via `MemoryClient` → HTTP transport | `settings/infra.py:265-277`, `settings/cognitive.py:61-81`, `core_singletons.py:297-322`, `api/endpoints/memory.py:235-269` |
| **SomaFractalMemory health** | `SOMA_FRACTAL_MEMORY_URL` (alias of memory endpoint) | `/health` aggregator probe `GET {url}/healthz` | `settings/infra.py:269`, `config/urls.py:270-283` |
| **MinIO / Schema Registry / Keycloak** | `MINIO_ENDPOINT`, `SCHEMA_REGISTRY_URL`, `KEYCLOAK_URL` | Health-only probes in `/health` aggregator | `config/urls.py:215-267` |
| **Vault (secrets bootstrap)** | via `settings/infra.py` resolution | DSN/token resolution before Django settings finalize | `settings/infra.py:92-103,274-277` |
| **Prometheus** | `somabrain/metrics` | Neuromod gauges, integrator counters, constitution metrics | `runtime/neuromodulators.py:177-185`, `integrator_hub_triplet.py:63-83`, `lifecycle/startup.py:94-120` |

---

## 6. Dual-Implementation Register

| Domain | Implementation A | Implementation B | Divergence / risk | Evidence |
|---|---|---|---|---|
| **Neuromodulators tree** | `somabrain/runtime/neuromodulators.py` (live; lazy adaptive registry `:425-442`) | `somabrain/admin/brain/neuromodulators.py` (module-level `adaptive_per_tenant_neuromods` `:424`) | Near-identical duplicated module (~420 lines). Live `/act` uses **runtime** tree (`bootstrap/singletons.py:280`). Adaptation engine dopamine lookup uses **admin** tree (`learning/adaptation/engine.py:435-437`). Tests import admin tree. Two mutable global registries can diverge. | `runtime/neuromodulators.py:1-449` vs `admin/brain/neuromodulators.py:1-424` |
| **Binder algebra** | Rust `PermutationBinder` (`rust_core/src/bhdc.rs` via `math/bhdc_encoder.py:231-235`) | Python `_PythonPermutationBinder` fallback (`math/bhdc_encoder.py:83+,237-239`) | Dual backend chosen at runtime by `is_rust_available()`. GMD doc states binding is pure element-wise multiply (`docs/SomabrainGMD.md:69-73`); code is **permute-then-multiply** (`math/bhdc_encoder.py:242`). Math claim ≠ implementation. | `math/bhdc_encoder.py:213-249`, `admin/core/quantum.py:130-140` |
| **Scoring / ranking copies** | `somabrain/memory/scoring.py` (`rank_hits` `:227`, `rescore_and_rank_hits` `:349`) — DEAD | `somabrain/memory/client/ranking.py` (`_rank_hits` `:180`, `_rescore_and_rank_hits` `:381`) — LIVE via `memory/client/search.py:68,138` | Two parallel scoring utilities with overlapping names. Only the `client/ranking.py` copy is on the recall path. `memory/scoring.py` is exported (`memory/__init__.py:50-59`) but never imported. | see file:line |
| **UnifiedScorer vs memory scoring** | `admin/core/learning/scoring.py:41` `UnifiedScorer` (WM + memory pool + retrieval) | `memory/scoring.py` hit ranking utilities | Different layers, but both named "scoring"; risk of wrong import. | `bootstrap/singletons.py:230-240`, `runtime/manager.py:167-174` |
| **Mahalanobis predictor** | Python `admin/core/learning/prediction.py:247-347` — diagonal variance-normalized distance `_mahal_bounded` `:299-318`, blend `0.8*cos + 0.2*surprise` `:344` | Rust `rust_core/src/prediction.rs:66-94` — EWMA mean + **L2 distance** (`distance()` `:90-93`); `covariance` field is `#[allow(dead_code)]` `:68-69` | Rust type is named Mahalanobis but does **not** use covariance → not Mahalanobis distance. Python version is the live one (`bootstrap/singletons.py:70`). Rust version unused from Python. | cited |
| **Adaptation engine** | Python `learning/adaptation/engine.py:53-610` (live via `/context/*`) | Rust `rust_core/src/adaptation.rs:81+` wrapped by `learning/rust_engine.py:14-108` | Two engines with same names. Live API path uses Python (`api/context_state.py:17,60`). Rust engine is a separate wrapper, not swapped in. | cited |
| **Integrator hub facades** | `services/integrator_hub_triplet.py` (real) | `services/integrator_hub.py:14` re-export + `admin/core/integrator_hub.py:20` broken re-export | Latter claims "single source of truth" but imports a non-existent path. | `admin/core/integrator_hub.py:20` |
| **Neuromod state backend** | Python dataclass `NeuromodState` | Rust `Neuromodulators` mirror synced get/set | Optional acceleration; state is dual-written when Rust present. | `runtime/neuromodulators.py:126-155` |

---

## 7. Claimed in Old Docs but NOT Implemented (truth table)

| Claim (source) | What the code actually does | Verdict | Evidence |
|---|---|---|---|
| **Free energy minimization on `/act`**: "supervisor.adjust() modulates the neuromod state and returns free-energy/magnitude" (`docs/SOMABRAIN_ARCHITECTURE.md` §6.1 step 6) | `/act` passes `supervisor=None` (`cognitive.py:216`). `eval_step` only calls `supervisor.adjust` if supervisor is not None (`cognitive_loop_service.py:214-223`). Result key `free_energy` is therefore always `None` on the live path (`cognitive_loop_service.py:267`). `Supervisor.free_energy` is a weighted sum proxy (`runtime/supervisor.py:88-110`), and `create_supervisor` is never invoked. | **NOT IMPLEMENTED on live path** | cited |
| **BG selection / basal ganglia policy** — documented cognitive component (`SOMABRAIN_CODEBASE_DOCUMENTATION.md` implies full brain stack; `basal_ganglia.py` docstring "Policy decision making based on store/act gates") | `BasalGangliaPolicy` (`admin/cognitive/basal_ganglia.py:45`) has **zero importers** in production code. Store/act gates come from `AmygdalaSalience.gates` instead (`cognitive_loop_service.py:231`). | **DEAD code** | grep: no `from somabrain.admin.cognitive.basal_ganglia` / `BasalGangliaPolicy(` outside its module |
| **RPE (reward prediction error)** — dopamine "reward prediction errors" (`admin/brain/neuromodulators.py:325`, `runtime/neuromodulators.py:327`) | `_calculate_dopamine_feedback` returns `success_rate + bias + optional boost` (`runtime/neuromodulators.py:324-338`) — no temporal-difference / RPE term. Rust exposes `compute_td_error` / `compute_td_return` (`rust_core/src/lib.rs:90-93`) but nothing in Python calls them. Adaptive path itself is TEST-ONLY (§3). | **NOT IMPLEMENTED** (label only) | cited |
| **Mahalanobis in Rust** — GMD/ARCH treat Rust as the math runtime (`docs/SomabrainGMD.md:29` "Implementation Target: Deterministic Rust Runtime") | Live predictor is Python `MahalanobisPredictor` (`bootstrap/singletons.py:70`). Rust `MahalanobisPredictor.distance` is L2-to-mean, covariance unused (`rust_core/src/prediction.rs:66-93`) — **not** a Mahalanobis distance. Never constructed from Python. | **MISNAMED / UNUSED** | cited |
| **GMD binding `b = k ⊙ v`** (`docs/SomabrainGMD.md:69-73`, `docs/SOMABRAIN_ARCHITECTURE.md` §2.2) | Production binder is permutation + element-wise multiply: "Bind two vectors: permute b, then elementwise multiply" (`math/bhdc_encoder.py:242`). `QuantumLayer` uses `PermutationBinder` (`admin/core/quantum.py:140`). | **MATH CLAIM ≠ CODE** | cited |
| **Memory update / SNR horizon as the governing runtime** (`SomabrainGMD.md` §0.4, Theorem 2) | Rust `BayesianMemory` implements the rule (`mathcore.rs:386-455`). No Python caller wires `BayesianMemory` into WM/LTM request path. WM uses cosine/salience eviction (`memory/wm/core.py`). | **IMPLEMENTED IN RUST ONLY; not on live request path** | `mathcore.rs:352-470`; WM path `wm/core.py:84+` |
| **`run_retrieval_pipeline` as "recall API" engine** (module docstring `retrieval_pipeline.py:1-2`) | Recall endpoints call `MemoryService.arecall` / `perform_recall` (`api/endpoints/memory.py:269`, `api/memory/recall.py:250`). `run_retrieval_pipeline` has no callers. | **DEAD** | grep: sole definition `retrieval_pipeline.py:98` |
| **Lifecycle startup enforcement** (Kafka/OPA required, outbox sync, Milvus reconcile — `lifecycle/startup.py:124-250`) | Handlers exist but are never registered. `AppConfig.ready()` is intentionally side-effect free (`admin/core/apps.py:26-33`). Module docstring says register in `app.py` (`startup.py:7-8`); `somabrain/app.py` does not exist. | **DEAD** | cited |
| **`services/entry.py` as orchestrator** (`SOMABRAIN_CODEBASE_DOCUMENTATION.md` §2.2) | Would crash on integrator start: `hub.run_forever()` (`entry.py:45`) vs `IntegratorHub.run()` (`integrator_hub_triplet.py:384`). Compose launches triplet module directly instead (`docker-compose.yml:1068`). | **BROKEN / unused** | cited |
| **AAAS routers conditional on INSTALLED_APPS** (`SOMABRAIN_ARCHITECTURE.md` §5, `SOMABRAIN_CODEBASE_DOCUMENTATION.md` §2.1) | `v1.py` loads cognitive/memory/config/… routers unconditionally (`v1.py:41-155`). Comment states commerce overlay removed (`v1.py:6-9`). AAAS conditional block is not present in `v1.py`. | **PARTIALLY OBSOLETE** | `api/v1.py:1-155` |
| **`UnifiedBrainCore` as "unified mathematical core replacing complex component interactions"** (`unified_core.py:12`) | Only constructed via `create_unified_brain` (`core_singletons.py:273-289`), which has no callers. Not on `/act` or memory paths. | **DEAD** | grep: only factory + adapters/tests |
| **Rust unit tests as proof of Theorems 1–4** (`lib.rs` test module) | W4: tests rewritten against the live API. `compute_optimal_p` (false "Theorem 1") is deleted; `test_wiener_lambda_theorem3` pins `λ* = Δ²/(12p(1−p))`; `test_fwht_*`, `test_bayesian_memory_snr`, `test_capacity_estimation` assert real values. `cargo test` 14/14 green. | **GREEN tests (W4)** | cited |

---

## 8. Status Labels (summary)

| Component | Label |
|---|---|
| Django Ninja API + URLconf | IMPLEMENTED |
| `/cognitive/act` + `eval_step` | IMPLEMENTED |
| Memory HTTP client path (`MemoryService` → SFM) | IMPLEMENTED |
| Working memory (`WorkingMemory` / `MultiTenantWM`) | IMPLEMENTED |
| Python Mahalanobis predictor + budget wrapper | IMPLEMENTED |
| Per-tenant neuromodulators (runtime tree) | IMPLEMENTED |
| Amygdala salience/gates | IMPLEMENTED |
| AdaptationEngine (Python, `/context/*`) | IMPLEMENTED |
| Kafka predictors + IntegratorHub sidecar | IMPLEMENTED (separate processes) |
| BHDC QuantumLayer + dual binder backend | IMPLEMENTED |
| Rust `somabrain_rs` math core (FWHT, quantize, Wiener, BayesianMemory) | IMPLEMENTED (optional; partial live use) |
| `retrieval_pipeline.run_retrieval_pipeline` | DEAD |
| `memory/scoring.py` ranking helpers | DEAD |
| `somabrain/predictors/*` heat-diffusion stack | DEAD |
| `lifecycle/startup.py` handlers | DEAD |
| `BasalGangliaPolicy` | DEAD |
| `Supervisor` / free energy on `/act` | DEAD |
| `UnifiedBrainCore` | DEAD |
| `AdaptiveNeuromodulators` | TEST-ONLY |
| `admin/core/integrator_hub.py` | BROKEN |
| `services/entry.py` integrator start | BROKEN |
| Rust `MahalanobisPredictor` / TD API (from Python) | DEAD |
| `lib.rs` incomplete unit tests | BROKEN |

---

## 9. Residual Risk / Open Points (not invented; stated as unknowns)

1. Whether any out-of-repo deployment script registers `lifecycle/startup.py` handlers is **not
   visible in this repository**. In-repo evidence shows they are unregistered.
2. Whether `somabrain_rs` is built in a given deployment is environment-dependent
   (`somabrain/core/rust_bridge.py:8-23` falls back to Python). Dual backends can therefore
   produce different binder/predictor numerics across environments.
3. `bootstrap/runtime_init.load_runtime_module` expects a `somabrain/runtime.py` **file**
   (`runtime_init.py:46-48`). The package is `somabrain/runtime/`. If `register_singletons` is
   ever invoked, that load path must be re-verified; today it is unused on the live path.

---

*End of document — SOMA-BR-ARCH-TRUTH-001 v1.0.0*
