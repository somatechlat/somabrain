# SomaBrain Architecture — How the Brain Works

> **Document type:** Technical architecture overview  
> **Scope:** Full-stack SomaBrain: mathematical foundations, runtime, memory plane, cognitive loop, API, security, and standalone deployment  
> **As-of date:** 2026-06-14  
> **Authoritative sources:** `docs/SomabrainGMD.md`, `docs/ONBOARDING.md`, `ARCHITECTURE_AUDIT_STANDALONE_2026-02-03.md`, `somabrain/runtime/manager.py`, `somabrain/services/memory_service.py`, `somabrain/memory`, `somabrain/services/cognitive_loop_service.py`, `somabrain/api`, `infra/standalone/docker-compose.yml`

---

## 1. What SomaBrain Is

SomaBrain is a **cognitive memory platform** for AI agents. It is not a plain vector database; it is a brain-like memory stack that combines:

- **Hyperdimensional / sparse vector mathematics** for memory encoding and recall.
- **Working memory** for fast, in-process, context-bound recall.
- **Long-term memory (LTM)** persisted through an external memory service (SomaFractalMemory, or SFM).
- **A cognitive loop** that predicts, evaluates prediction error, modulates "neurochemical" state, and decides what to store or act on.
- **Multi-tenant isolation** of memory, quotas, and configuration.
- **Strict-real-mode operation**: production code uses real backends, no stubs, no silent fallbacks.

The project is implemented as a **Django + Django Ninja** monolith with background Python services and a Kafka-based cognitive pipeline.

---

## 2. Mathematical Foundation: Governing Memory Dynamics (GMD)

The core theory is documented in `docs/SomabrainGMD.md`.

### 2.1 Sparse standardized representation

Raw sparse vectors `s ∈ {0,1}^D` (sparsity `p`, typically `p = 0.1`) are standardized to zero mean and unit variance:

```text
x = (s − p) / sqrt(p(1 − p))
```

This removes scale dependence from sparsity. Similarity is then a normalized dot product:

```text
sim(x, y) = (1/D) x^T y
```

This behaves like cosine similarity but is cheaper and deterministic.

### 2.2 Binding and unbinding

Binding is element-wise multiplication on the standardized vectors:

```text
b = k ⊙ v
```

Unbinding uses the same operator. The system therefore supports associative storage of key/value pairs in superposed traces.

### 2.3 Memory update rule

Memory evolves by exponential decay:

```text
m_t = (1 − η) m_{t−1} + η b_t
```

The weight of an item inserted at lag `L` is `w_L = η (1 − η)^L`. The usable recall horizon is determined by an age-dependent signal-to-noise ratio rather than a fixed capacity.

### 2.4 Quantization-aware unbinding

For 8-bit quantized storage, the optimal ridge regularizer is:

```text
λ* = σ_ε² / σ_v²
```

where `σ_ε²` is quantization noise variance and `σ_v²` is value variance. Unbinding becomes:

```text
v̂ = (Q(b) ⊙ k) / (k² + λ*)
```

### 2.5 Fast Walsh–Hadamard Transform (FWHT)

FWHT applies an exact orthogonal rotation in `O(D log D)` operations. For `D = 2048` this is ~24k operations versus ~4M for a dense matrix multiply. This provides deterministic orthogonal mixing without the cost of dense rotation.

### 2.6 Recommended production parameters

| Parameter | Value | Role |
|---|---|---|
| Dimension `D` | 2048 | Similarity concentration / distinguishability |
| Sparsity `p` | 0.1 | Compute and quantization stability |
| Decay `η` | 0.05–0.08 | Memory horizon |
| Regularizer `λ` | `σ_ε² / σ_v²` | Quantization ridge |
| Mixing | FWHT | Deterministic orthogonalization |

---

## 3. High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│  External clients (HTTP / gRPC / Kafka)                              │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Django + Django Ninja API layer                                     │
│  somabrain/api/v1.py, somabrain/config/urls.py                       │
│  /api/memory/*, /api/cognitive/*, /api/sleep/*, /api/admin/*, ...    │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Runtime singletons (somabrain/runtime/manager.py)                   │
│  • embedder        → text → dense vector                             │
│  • mt_wm           → MultiTenantWM (in-process working memory)       │
│  • mt_memory       → MultiTenantMemory → MemoryClient → SFM HTTP     │
└──────────┬──────────────────────┬───────────────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐    ┌──────────────────────────────────────────┐
│ Cognitive loop   │    │ Memory plane                             │
│ services         │    │ • Working memory (wm)                    │
│ • predictors     │    │ • Long-term memory (ltm) via SFM         │
│ • integrator     │    │ • Graph links                            │
│ • supervisor     │    │ • Local journal (degradation fallback)   │
│ • neuromodulators│    │ • Outbox → Kafka                         │
└──────────┬───────┘    └──────────────┬───────────────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────┐    ┌──────────────────────────────────────────┐
│ Kafka topics     │    │ External backends                        │
│ cog.*.updates    │    │ • SomaFractalMemory (memory + vectors)   │
│ cog.global.frame │    │ • PostgreSQL (Django ORM + outbox)       │
│ cog.config.updates│   │ • Redis (cache, registry, WM backing)    │
│ soma.audit       │    │ • Kafka (event bus)                      │
└──────────────────┘    │ • OPA (policy engine)                    │
                        │ • Vault (secrets bootstrap)              │
                        └──────────────────────────────────────────┘
```

### 3.1 Runtime is the center of gravity

`somabrain/runtime/manager.py` (`RuntimeManager`, lines 52–222) owns three lazy-initialized singletons:

1. **Embedder** — created by `make_embedder(_SettingsAdapter(settings))` (line 92–110).
2. **Working memory** — `MultiTenantWM(dim=settings.SOMABRAIN_EMBED_DIM)` (line 112–125).
3. **Memory pool** — `MultiTenantMemory(cfg=settings)` (line 127–139).

All three are created under a thread lock on first access, or eagerly by `initialize_runtime()`. The API layer does not create these objects directly; it asks the runtime for them.

---

## 4. Memory Plane

The memory plane is the most exercised part of the system. It has four layers:

| Layer | Location | Persistence | Latency | Use case |
|---|---|---|---|---|
| **Working memory (WM)** | `somabrain/memory/wm/mt_wm.py`, `wm/core.py` | In-process, per tenant | Sub-millisecond | Immediate context, recent items |
| **Long-term memory (LTM)** | `somabrain/memory/client`, `somabrain/memory/pool.py` | SomaFractalMemory via HTTP | Tens of ms | Durable episodic/semantic memory |
| **Hierarchical / HRR trace** | `somabrain/memory/hierarchical.py`, `superposed_trace.py` | In-process + SFM | Variable | Superposed associative traces |
| **Local journal / outbox** | `somabrain/journal`, `somabrain/db/outbox.py` | Disk JSONL + Postgres | Durable | Degradation replay, audit |

### 4.1 LTM backend: MemoryClient → SFM

`MultiTenantMemory.for_namespace(namespace)` (`somabrain/memory/pool.py:34`) returns a `MemoryClient` per namespace. `MemoryClient` (`somabrain/memory/client/core.py:16`) is composed of mixins:

- `TransportMixin` — builds `MemoryHTTPTransport` pointing at `SOMABRAIN_MEMORY_HTTP_ENDPOINT`.
- `WriteMixin` — `remember`, `aremember`, `remember_bulk`, `aremember_bulk`.
- `ReadMixin` — `recall`, `arecall`, `payloads_for_coords`.
- `SearchMixin` — backend search + keyword filtering + reranking.
- `GraphOpsMixin` — `create_link`, `get_neighbors`, `find_path`.

The SFM HTTP contract used by the client:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/memories` | Store a memory |
| POST | `/memories/search` | Vector/text search |
| GET | `/memories/{coord}` | Fetch by coordinate |
| POST | `/payloads` | Bulk payload fetch |
| POST/GET | `/graph/link`, `/graph/neighbors`, `/graph/path` | Graph operations |

### 4.2 Working memory lifecycle

`MultiTenantWM.admit(tenant_id, vec, payload)` (`somabrain/memory/wm/mt_wm.py:121`):

1. Ensures a tenant-scoped `WorkingMemory` instance.
2. Normalizes and unit-normalizes the vector.
3. Checks for duplicates by cosine similarity.
4. Appends a `WMItem` with recency/tick tracking.
5. If over capacity, evicts the lowest-salience item (`wm/core.py:336`, `wm_eviction.py:33`).

`MultiTenantWM.recall(tenant_id, query_vec, top_k)` scores items by cosine similarity with density/recency adjustments and returns ranked payloads.

### 4.3 MemoryService: façade + circuit breaker + degradation

`somabrain/services/memory_service.py:44` wraps the backend pool with:

- Per-tenant circuit breaker from `somabrain/infrastructure/cb_registry.py:get_cb()`.
- Degradation queue to a local journal when the circuit is open.
- Success/failure recording.

The remember/recall flow:

```text
API endpoint
    → MemoryService(pool, namespace)
        → _reset_circuit_if_needed()
        → if circuit open → _queue_degraded() → LocalJournal
        → else → backend.remember()/recall()
            → on success → _mark_success()
            → on failure → _mark_failure() → raise
```

The circuit breaker itself (`somabrain/infrastructure/circuit_breaker.py:27`) maintains per-tenant `TenantCircuitState` with CLOSED/OPEN/HALF-OPEN states and exposes `is_open`, `allow_request`, `record_success`, `record_failure`, `reset`, `get_stats`.

### 4.4 Promotion from WM to LTM

`somabrain/memory/promotion.py:206` (`WMLTMPromoter`) promotes salient WM items to LTM by calling `MemoryClient.aremember` with `promoted_from_wm=true`. On failure it queues to the outbox for later replay.

---

## 5. API Layer

`somabrain/api/v1.py` registers the central NinjaAPI instance. Routers include:

| Router | File | Purpose |
|---|---|---|
| `/memory` | `somabrain/api/endpoints/memory.py`, `memory_remember.py` | Remember / recall |
| `/cognitive` | `somabrain/api/endpoints/cognitive.py` | `/act`, `/plan/suggest`, personality |
| `/sleep` | `somabrain/api/endpoints/sleep.py` | Sleep-state transitions |
| `/context` | `somabrain/api/endpoints/context.py` | Context evaluation / feedback |
| `/neuromod` | `somabrain/api/endpoints/neuromod.py` | Neuromodulator read/adjust |
| `/health` | `somabrain/api/endpoints/health.py` | Ninja health routes |
| AAAS routers | `somabrain/api/v1.py` | Auth, tenants, billing, admin (conditional on `INSTALLED_APPS`) |

### 5.1 Memory endpoints

- `POST /api/memory/remember` — `remember_memory_async()` (`somabrain/api/endpoints/memory_remember.py:73`). Composes payload, calls `MemoryService.aremember()`, embeds seed text, admits to WM.
- `POST /api/memory/remember/batch` — `remember_memory_batch()` (line 188).
- `POST /api/memory/recall` — `recall_memory()` (`somabrain/api/endpoints/memory.py:73`). Queries LTM via `MemoryService.arecall()` and WM via `wm.items()`, merges and ranks.

### 5.2 Authentication

`somabrain/api/auth.py:30` dispatches auth:

- If `SOMABRAIN_DEFAULT_TENANT == "standalone"` → `StandaloneAPIKeyAuth` validates the bearer token against `SOMABRAIN_MEMORY_HTTP_TOKEN`.
- Otherwise → AAAS `APIKeyAuth` validates `sbk_*` keys against the `aaas_api_keys` table.

Tenant resolution is handled by `somabrain/tenant.py:get_tenant()` / `get_tenant_sync()`, with priority:

1. `X-Tenant-ID` header.
2. First 16 characters of the bearer token.
3. Default tenant (`standalone` or `public`).

---

## 6. Cognitive Loop — How the Brain "Thinks"

The cognitive subsystem has a synchronous HTTP path and a background Kafka path.

### 6.1 Synchronous path: `POST /api/cognitive/act`

`somabrain/api/endpoints/cognitive.py:189` → `act_endpoint()`:

1. Embeds the task string.
2. Creates or reuses a per-session `FocusState` (`somabrain/admin/brain/focus_state.py:31`).
3. `FocusState.update()` pushes the task vector and top recall hits into an `HRRContext`.
4. Calls `eval_step()` from `somabrain/services/cognitive_loop_service.py:116`.

Inside `eval_step()`:

1. Loads the tenant's latest `SleepState` from the Django ORM with a 5-second TTL cache.
2. If `SleepState.FREEZE`, returns a zeroed result.
3. `predictor.predict_and_compare(previous_focus_vec, wm_vec)` computes prediction error.
4. Fetches neuromodulator state (`dopamine`, `serotonin`, `noradrenaline`, `acetylcholine`).
5. Optionally modulates neuromods by personality traits.
6. `supervisor.adjust()` modulates the neuromod state and returns free-energy/magnitude.
7. `amygdala.score()` computes salience; `amygdala.gates()` returns `store_gate` / `act_gate`.
8. If enabled, `BeliefUpdatePublisher.publish()` emits a `BeliefUpdate` to Kafka.

If `store_gate` is open, `FocusState.persist_snapshot()` stores the focus vector and payload to memory.

### 6.2 Background Kafka path

Three predictor services consume and produce Kafka topics:

| Service | Input topic | Output topic | File |
|---|---|---|---|
| `StatePredictorService` | `cog.global.frame` | `cog.state.updates` | `somabrain/services/state_predictor.py:50` |
| `AgentPredictorService` | `cog.global.frame` | `cog.agent.updates` | `somabrain/services/agent_predictor.py:50` |
| `ActionPredictorService` | `cog.next_event` | `cog.action.updates` | `somabrain/services/action_predictor.py:46` |

`IntegratorHub` (`somabrain/services/integrator_hub_triplet.py:86`) consumes the three `.updates` topics, computes domain confidence as `exp(-alpha * error)`, selects a leader via precision-weighted softmax, and publishes a `GlobalFrame` back to `cog.global.frame`.

```text
              ┌─────────────────────┐
cog.global.frame → StatePredictor → cog.state.updates
              │                     │
              │   AgentPredictor → cog.agent.updates ─┐
              │                     │                 │
              │  ActionPredictor → cog.action.updates─┤
              │                                       ▼
              │                           IntegratorHub.run()
              │                             _select_leader()
              │                             _publish_global()
              │                                       │
              └────────────◄────────────── cog.global.frame
```

### 6.3 Neuromodulators

`somabrain/admin/brain/neuromodulators.py` and `somabrain/runtime/neuromodulators.py` implement a four-chemical state model:

- **Dopamine** — prediction-error / reward signal.
- **Serotonin** — confidence / stability.
- **Noradrenaline** — arousal / urgency.
- **Acetylcholine** — attention / memory encoding bias.

`AdaptiveNeuromodulators` update these based on performance feedback (`adapt_from_performance`).

### 6.4 Sleep / consolidation

`somabrain/api/endpoints/sleep.py` manages sleep-state transitions. `SleepStateManager.compute_parameters` returns parameters such as `eta` (memory decay). During sleep/consolidation, WM items can be promoted or consolidated into LTM.

---

## 7. Security & Multi-Tenancy (AAAS)

The **AAAS** (Agent-as-a-Service) subsystem lives under `somabrain/aaas/`.

### 7.1 Authentication

- `APIKeyAuth` validates `sbk_live_*` / `sbk_test_*` tokens against `aaas_api_keys`.
- `JWTAuth` validates Keycloak-issued JWTs against JWKS.
- `GoogleOAuth` handles Google OAuth2 flows.
- `StandaloneAPIKeyAuth` is the single-tenant pre-shared-token fallback.

### 7.2 Authorization

- `somabrain/aaas/granular.py:43` defines `PlatformRole` (9 roles) and `Permission` (65+ resource:action permissions).
- `require_permission("resource:action")` checks the static permission matrix.
- `require_scope(...)` checks API-key scopes.

### 7.3 Tenant registry

- `TenantRegistry` (`somabrain/aaas/logic/tenant_registry.py:36`) is Redis-backed.
- `TenantManager` (`somabrain/aaas/logic/tenant_manager.py:25`) is the high-level async facade.
- `get_tenant()` resolves tenant context per request.

### 7.4 Rate limiting and quotas

- `TokenBucketRateLimiter` (`somabrain/aaas/rate_limit.py:69`) — cache-backed token bucket.
- `QuotaManager` (`somabrain/aaas/governance/quotas.py:80`) — daily/monthly write and API-call quotas.
- `RateLimitMiddleware` is defined but **not registered by default** in `django_core.py`.

### 7.5 Audit

`somabrain/core/security/audit.py:37` publishes audit events to the DB outbox for Kafka topic `soma.audit`.

---

## 8. Runtime Modes & Feature Flags

`somabrain/runtime/modes.py` canonicalizes deployment mode:

| Mode | Env var | Behavior |
|---|---|---|
| `full-local` | `SOMA_DEPLOY_MODE=FULL_LOCAL` or `SOMABRAIN_MODE=full-local` | All features available; `data/feature_overrides.json` honored |
| `ci` | `SOMABRAIN_MODE=ci` | CI-specific gating |
| `prod` | `SOMABRAIN_MODE=prod` | Production strictness |

`feature_enabled(name)` gates cognitive features. `SOMABRAIN_FEATURE_OVERRIDES` points to `data/feature_overrides.json`, which is only honored in `full-local`.

`somabrain/core/mode.py` also defines `DeploymentMode` (`dev/staging/production`) controlling auth, OPA strictness, required backends, and minimum replicas. The two mode systems overlap and can be confusing.

---

## 9. Standalone Deployment Architecture

The standalone stack is defined in `infra/standalone/docker-compose.yml`. It is **Vault-first**: a `vault_init` container seeds secrets, and the web entrypoints load them before Django settings are evaluated.

### 9.1 Services in standalone

1. `somabrain_standalone_redis`
2. `somabrain_standalone_kafka`
3. `somabrain_standalone_kafka_exporter`
4. `somabrain_standalone_schema_registry`
5. `somabrain_standalone_opa`
6. `somabrain_standalone_prometheus`
7. `somabrain_standalone_jaeger`
8. `somabrain_standalone_postgres`
9. `somabrain_standalone_vault`
10. `somabrain_standalone_vault_init`
11. `somabrain_standalone_db_migrate` (dev profile)
12. `somabrain_standalone_postgres_exporter`
13. `somabrain_standalone_app`
14. `somabrain_standalone_cog`
15. `somabrain_standalone_outbox_publisher`
16. `somabrain_standalone_etcd`
17. `somabrain_standalone_minio`
18. `somabrain_standalone_milvus`
19. `somabrain_standalone_integrator_triplet`

### 9.2 Secret bootstrap flow

Only the WSGI/ASGI entry points call the Vault bootstrap helpers:

- `somabrain/config/wsgi.py:14` calls `configure_vault_secrets()` and `configure_infra_secrets()` before `get_wsgi_application()`.
- `somabrain/config/asgi.py:14` does the same.

These helpers (`somabrain/settings/django_core.py`) read Vault and write into `os.environ`:

- `SOMABRAIN_JWT_SECRET` / `SECRET_KEY`
- `SOMABRAIN_MEMORY_HTTP_TOKEN`
- `SOMABRAIN_POSTGRES_DSN`
- `SOMA_API_TOKEN` / `SOMABRAIN_API_TOKEN`

### 9.3 Critical bootstrap gap

Worker/cognitive entry points (`somabrain/workers/outbox_publisher.py`, `somabrain/services/integrator_hub_triplet.py`, supervisor programs in the `cog` container) do **not** call the Vault bootstrap helpers before importing Django settings. They therefore crash on startup unless the secrets are injected as plain environment variables.

---

## 10. Data Flow Summary

### 10.1 Remember

```text
HTTP POST /api/memory/remember
    │
    ▼
somabrain/api/endpoints/memory_remember.py:73
    │
    ├─► _get_memory_pool() → RuntimeManager.mt_memory → MultiTenantMemory
    ├─► _get_wm()          → RuntimeManager.mt_wm   → MultiTenantWM
    ├─► _get_embedder()    → RuntimeManager.embedder
    │
    ▼
_resolve_namespace(tenant, namespace)
    │
    ▼
MemoryService(pool, namespace)
    │
    ├─► _reset_circuit_if_needed()
    ├─► if circuit open → _queue_degraded() → JournalEvent → LocalJournal
    │
    └─► memsvc.aremember(payload.key, stored_payload)
            │
            ▼
        MultiTenantMemory.for_namespace(ns).aremember()
            │
            ▼
        MemoryClient.aremember()
            │
            ├─► _compat_enrich_payload()
            ├─► _stable_coord() → deterministic 3D coordinate
            └─► POST /memories → SFM
                    │
                    ▼
                _extract_memory_coord(response) → coordinate
    │
    ├─► embed seed_text → vector
    └─► wm.admit(tenant, vector, stored_payload)
```

### 10.2 Recall

```text
HTTP POST /api/memory/recall
    │
    ▼
somabrain/api/endpoints/memory.py:73
    │
    ▼
_get_memory_pool() → MemoryService(pool, namespace)
    │
    ├─► LTM: memsvc.arecall(query, top_k, universe)
    │       │
    │       ▼
    │   MemoryClient.SearchMixin._memories_search_async()
    │       │
    │       ├─► POST /memories/search (fetch_limit = max(top_k*5, 50))
    │       ├─► _normalize_recall_hits()
    │       ├─► filter by universe
    │       ├─► keyword filter, deduplicate, rerank
    │       └─► top-k RecallHit[]
    │
    └─► WM: wm.items(tenant_id)
            │
            ▼
        WorkingMemory.recall(query_vec, top_k)
            │
            ▼
        cosine-ranked payloads
    │
    ▼
merge LTM + WM hits, sort by score, return top_k
```

### 10.3 Cognitive act

```text
HTTP POST /api/cognitive/act
    │
    ▼
somabrain/api/endpoints/cognitive.py:189
    │
    ├─► embed task → vector
    ├─► FocusState.update(task_vec, recall_hits)
    │
    ▼
eval_step(previous_focus_vec, wm_vec, ...)
    │
    ├─► SleepState check
    ├─► predictor.predict_and_compare() → prediction error
    ├─► neuromods.get_state()
    ├─► supervisor.adjust() → modulated neuromods + free energy
    ├─► amygdala.score() → salience
    ├─► amygdala.gates() → store_gate, act_gate
    └─► optionally BeliefUpdatePublisher.publish() → Kafka
    │
    ▼
if store_gate: FocusState.persist_snapshot() → MemoryClient
    │
    ▼
ActResponse
```

---

## 11. Current Operational State (as of 2026-06-14)

This section records the real state observed in the running standalone deployment.

### 11.1 What is healthy

- PostgreSQL, Redis, Kafka, Schema Registry, OPA, MinIO, Prometheus, Jaeger, Vault, and SomaFractalMemory are all up and healthy.
- The SomaFractalMemory API responds on `localhost:10101` with `healthy: true` and all stores (`kv_store`, `vector_store`, `graph_store`) up.
- The brain app container initializes its runtime successfully (`embedder: True`, `working_memory: True`, `memory_pool: True`).

### 11.2 What is broken

1. **`/api/memory/remember` returns 500.**
   - Root cause: `MemoryService._reset_circuit_if_needed()` calls `CircuitBreaker.should_attempt_reset(tenant)`, which does not exist on `somabrain/infrastructure/circuit_breaker.py`.
   - Same mismatch affects `get_circuit_state()` (`get_state` missing) and `configure_tenant_thresholds()` (`configure_tenant` missing).

2. **Cognitive containers crash on startup.**
   - `somabrain_standalone_cog`, `somabrain_standalone_outbox_publisher`, and `somabrain_standalone_integrator_triplet` are in restart loops.
   - Root cause: they import Django settings without first calling `configure_vault_secrets()` / `configure_infra_secrets()`. Settings validation fails because `SOMABRAIN_JWT_SECRET` and `SOMABRAIN_MEMORY_HTTP_TOKEN` are never loaded from Vault.

3. **Health endpoint reports misleading Milvus status.**
   - The health aggregator instantiates `MilvusClient` and tries `localhost:19530`. In standalone the brain has no local Milvus; it uses SFM's Milvus. The `connected: false` flag is expected but architecturally misleading.

4. **Several code-level mismatches exist** (non-blocking but documented by sub-agents):
   - `MemoryService` reads lowercase settings names (`memory_degrade_readonly`, `memory_degrade_topic`) while settings export uppercase names.
   - `somabrain/api/memory/helpers.py` lowercases recall env vars, causing overrides to be ignored.
   - `somabrain/api/endpoints/cognitive.py` imports `somabrain.app`, which does not exist.
   - `BeliefUpdatePublisher` emits Avro-ish payloads while `IntegratorHub` JSON-decodes the same topics.
   - `FocusState.persist_snapshot()` calls `MemoryClient.store()` with wrong kwargs.
   - `entry.py` calls `IntegratorHub.run_forever()`, which does not exist (the method is `run()`).
   - `somabrain/bootstrap/runtime_init.py` looks for `somabrain/runtime.py`, but the runtime is a package.

---

## 12. Key Configuration Variables

| Variable | Default | Meaning |
|---|---|---|
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | `http://host.docker.internal:10101` | External memory service URL |
| `SOMABRAIN_MEMORY_HTTP_TOKEN` | `sfm-api-token-123` | Bearer token for memory service and standalone API auth |
| `SOMABRAIN_JWT_SECRET` / `SECRET_KEY` | loaded from Vault | Django/crypto secret |
| `SOMABRAIN_POSTGRES_DSN` | loaded from Vault | Postgres connection |
| `SOMABRAIN_REDIS_URL` | `redis://...:6379/0` | Redis connection |
| `SOMABRAIN_KAFKA_URL` | `kafka://...:9092` | Kafka bootstrap |
| `SOMABRAIN_OPA_URL` | `http://...:8181` | OPA policy endpoint |
| `SOMABRAIN_EMBED_DIM` | `256` | Embedding / WM dimension |
| `SOMABRAIN_WM_SIZE` | `64` | Working-memory capacity |
| `SOMABRAIN_WM_ALPHA/BETA/GAMMA` | `0.6/0.3/0.1` | Salience weights |
| `SOMABRAIN_MODE` / `SOMA_DEPLOY_MODE` | `full-local` | Runtime mode |
| `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | `1` | Fail if backends unreachable |
| `SOMABRAIN_REQUIRE_MEMORY` | `1` | Fail if memory service unavailable |

---

## 13. Files That Define the Architecture

| Concern | File |
|---|---|
| Mathematical model | `docs/SomabrainGMD.md` |
| Runtime singletons | `somabrain/runtime/manager.py` |
| Mode / feature flags | `somabrain/runtime/modes.py`, `somabrain/core/mode.py` |
| API routing | `somabrain/api/v1.py`, `somabrain/config/urls.py` |
| Auth dispatch | `somabrain/api/auth.py`, `somabrain/api/standalone_auth.py` |
| Memory façade | `somabrain/services/memory_service.py` |
| Memory client / transport | `somabrain/memory/client`, `somabrain/memory/transport.py` |
| Memory pool | `somabrain/memory/pool.py` |
| Working memory | `somabrain/memory/wm/mt_wm.py`, `somabrain/memory/wm/core.py` |
| Cognitive loop | `somabrain/services/cognitive_loop_service.py` |
| Cognitive endpoints | `somabrain/api/endpoints/cognitive.py` |
| Predictors / integrator | `somabrain/services/state_predictor.py`, `agent_predictor.py`, `action_predictor.py`, `integrator_hub_triplet.py` |
| Neuromodulators | `somabrain/admin/brain/neuromodulators.py`, `somabrain/runtime/neuromodulators.py` |
| Focus state | `somabrain/admin/brain/focus_state.py` |
| Sleep | `somabrain/api/endpoints/sleep.py` |
| Settings / bootstrap | `somabrain/settings/django_core.py`, `somabrain/settings/infra.py`, `somabrain/settings/standalone.py` |
| Vault client | `somabrain/core/security/vault_client.py` |
| AAAS | `somabrain/aaas/auth`, `somabrain/aaas/logic`, `somabrain/aaas/granular.py` |
| Standalone deployment | `infra/standalone/docker-compose.yml`, `infra/standalone/docker-entrypoint.sh` |

---

## 14. Summary

SomaBrain is a **Django-based cognitive memory server** built around three runtime singletons:

1. An **embedder** that turns text into dense vectors.
2. A **multi-tenant working memory** buffer for fast in-process recall.
3. A **multi-tenant memory pool** that proxies LTM operations to SomaFractalMemory over HTTP.

On top of these, a **cognitive loop** (`eval_step`) predicts the next state, computes prediction error, updates neuromodulator-like chemicals, and decides whether to store a focus snapshot. A background **Kafka pipeline** of predictors and an integrator hub produces a global belief frame that feeds back into the loop.

The architecture is intentionally **strict-real**: real services, real backends, no stubs. This surfaces integration problems immediately — as is currently the case with the missing `CircuitBreaker.should_attempt_reset` method and the worker Vault-bootstrap gap.

The next engineering steps to make the system fully operational are:

1. Reconcile `MemoryService` with the real `CircuitBreaker` API.
2. Add Vault/bootstrap calls to all worker and cognitive service entry points, or inject the resolved secrets into their compose environments.
3. Clean up the documented interface mismatches in the cognitive pipeline and health endpoints.
