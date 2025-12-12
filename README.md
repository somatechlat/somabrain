# SomaBrain

**SomaBrain is an opinionated cognitive memory runtime that gives your AI systems long-term memory, contextual reasoning, and live adaptation—backed by real math, running code, and production-ready infrastructure.**  
It ships as a FastAPI service with a documented REST surface, BHDC hyperdimensional computing under the hood, and a full Docker stack (Redis, Kafka, OPA, Postgres, Prometheus) so you can test the whole brain locally.

---

## Highlights

| Capability | What it actually does |
|------------|------------------------|
| **Binary Hyperdimensional Computing (BHDC)** | 2048‑D permutation binding, superposition, and cleanup with spectral verification (`somabrain/quantum.py`). |
| **Tiered Memory** | Multi-tenant working memory + long-term storage coordinated by `TieredMemory`, powered by governed `SuperposedTrace` vectors and cleanup indexes. |
| **Contextual Reasoning** | `/context/evaluate` builds prompts, weights memories, and returns residuals; `/context/feedback` updates tenant-specific retrieval and utility weights in Redis. |
| **Adaptive Learning** | Decoupled gains and bounds per parameter, configurable via settings/env, surfaced in Prometheus metrics and the adaptation state API. |
| **Observability Built-In** | `/health`, `/metrics`, and structured logs. Adaptation behaviour emits explicit metrics so you can see when the brain deviates. |
| **Hard Tenancy** | Each request resolves a tenant namespace (`somabrain/tenant.py`); quotas and rate limits are enforced before the memory service is called. |
| **Complete Docs** | Four-manual documentation suite (User, Technical, Development, Onboarding) plus a canonical improvement log (`docs/CANONICAL_IMPROVEMENTS.md`). |

---

## Math & Systems at a Glance

### Hyperdimensional Core
- **QuantumLayer** (`somabrain/quantum.py`) implements BHDC operations (bind, unbind, superpose) with deterministic unitary roles and spectral invariants.
- **Numerics** (`somabrain/numerics.py`) normalises vectors safely with dtype-aware tiny floors.
- **SuperposedTrace** (`somabrain/memory/superposed_trace.py`) maintains a governed superposition with decay (\(\eta\)), deterministic rotations, cleanup indexes (cosine or HNSW), and now logs when no anchors match.

### Retrieval & Scoring
- **ContextBuilder** (`somabrain/context/builder.py`) embeds queries, computes per-memory weights, and adjusts the temperature parameter \(\tau\) based on observed duplicate ratios.
- **UnifiedScorer** (`somabrain/scoring.py`) blends cosine, frequent-directions projections, and recency; weights and decay constants can be tuned via `scorer_*` settings and are exposed through diagnostics.
- **TieredMemory** (`somabrain/memory/hierarchical.py`) orchestrates working and long-term traces with configurable promotion policies and safe handling when cleanup finds no anchor.

### Learning & Neuromodulation
- **AdaptationEngine** (`somabrain/learning/adaptation.py`) provides decoupled gains for retrieval (α, β, γ, τ) and utility (λ, μ, ν), driven by tenant-specific feedback. Configured gains/bounds are mirrored in metrics and the adaptation state API.
- **Neuromodulators** (`somabrain/neuromodulators.py`) supply dopamine/serotonin/noradrenaline/acetylcholine levels that can modulate learning rate (enable with `SOMABRAIN_LEARNING_RATE_DYNAMIC`). Tune noradrenaline feedback via `SOMABRAIN_NEURO_LATENCY_SCALE` and the new `SOMABRAIN_NEURO_LATENCY_FLOOR`, keeping the latency-based term finite even if latency drops toward zero.
- **Metrics** (`somabrain/metrics.py`) track per-tenant weights, effective LR, configured gains/bounds, and feedback counts.

---

## Runtime Topology

```
HTTP Client
   │  /memory/remember /memory/recall /context/evaluate /context/feedback …
   ▼
FastAPI Runtime (somabrain/app.py)
   │   ├─ Authentication & tenancy guards
   │   ├─ ContextBuilder / Planner / AdaptationEngine
    │   ├─ MemoryService (HTTP)
   │   └─ Prometheus metrics, structured logs
   ▼
Working Memory (MultiTenantWM) ──► Redis
Long-Term Memory ───────────────► External memory HTTP service
OPA Policy Engine ──────────────► Authorization decisions
Kafka ──────────────────────────► Audit & streaming
Postgres ───────────────────────► Config & metadata
Prometheus ─────────────────────► Metrics export
```

Docker Compose (`docker-compose.yml`) starts the API plus Redis, Kafka, OPA, Postgres, Prometheus, and exporters. The API always binds host port 9696 for consistency:

- API: host 9696 -> container 9696
- Redis: 30100 -> 6379
- Kafka broker: 30102 -> 9092 (internal advertised as somabrain_kafka:9092)
- Kafka exporter: 30103 -> 9308
- OPA: 30104 -> 8181
- Prometheus: 30105 -> 9090
- Postgres: 30106 -> 5432
- Postgres exporter: 30107 -> 9187
- Schema registry: 30108 -> 8081
- Reward producer: 30183 -> 8083
- Learner online: 30184 -> 8084

Memory service: by default the API points to `http://localhost:9595` (`memory_http_endpoint` in `common/config/settings.py`). Override `SOMABRAIN_MEMORY_HTTP_ENDPOINT` and `SOMABRAIN_MEMORY_HTTP_TOKEN` if your memory backend runs elsewhere or requires auth.

**Important:** *SomaBrain never runs an internal memory container.* All agents, services, and tests **must** use the external memory service reachable at `http://localhost:9595`. The service should already be running on the host machine; you can verify it with:

```bash
curl -f http://localhost:9595/health
```

If the health check reports `kv_store:false` or any component flag as false, the stack will refuse to start and the integration tests will fail – this is intentional to enforce the **real‑server‑only** rule.

In production the same endpoint is injected via Kubernetes manifests; for local development we rely on the host‑side service.

Note: Kafka’s advertised listener is internal to the Docker network by default. For host-side consumers, run your clients inside the Compose network or add a dual-listener config. For WSL2 or remote clients, set the EXTERNAL listener host before running dev scripts:

```bash
KAFKA_EXTERNAL_HOST=192.168.1.10 ./scripts/dev_up.sh
```

### Kubernetes external ports (NodePort)

Kubernetes defaults to ClusterIP internally. If you need host access without an ingress/controller, enable NodePorts in the Helm chart using a centralized 30200+ range:

- API: 30200 → 9696
- Integrator health: 30201 → 8091
- Segmentation health: 30202 → 8092
- Unified Predictor health: 30203 → 8093 (Consolidated service)
- Reward Producer (optional): 30206 → 8083
- Learner Online (optional): 30207 → 8084

How to enable (values):
- `.Values.expose.apiNodePort=true` → sets API service type to NodePort at `.Values.ports.apiNodePort`
- `.Values.expose.healthNodePorts=true` → exposes all cog-thread health services at their respective NodePorts
- `.Values.expose.learnerNodePorts=true` → exposes learner services at NodePorts

All NodePort numbers are centralized in `infra/helm/charts/soma-apps/values.yaml` under `.Values.ports.*`. Container and target ports remain internal and unchanged.

---

## API Overview

### Core Memory Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Checks Redis, Postgres, Kafka, OPA, memory backend, embedder, and circuit breaker state.
| `POST /memory/remember` | Store a memory with signals (importance, novelty, ttl), attachments, links, and policy tags. Returns coordinate, WM promotion status, and signal feedback.
| `POST /memory/recall` | Unified retrieval backed by the full retrieval pipeline (vector, wm, graph, lexical retrievers). Supports streaming, session pinning, and tiered memory.
| `GET /memory/context/{session_id}` | Retrieve pinned recall session results.
| `GET /memory/metrics` | Per-tenant memory metrics (WM items, circuit breaker state).

### Context & Adaptation

| Endpoint | Description |
|----------|-------------|
| `POST /context/evaluate` | Builds a prompt, returns weighted memories, residual vector, and working-memory snapshot.
| `POST /context/feedback` | Updates tenant-specific retrieval/utility weights; emits gain/bound metrics.
| `GET /context/adaptation/state` | Inspect current weights, effective learning rate, configured gains, and bounds.

### Planning & Actions

| Endpoint | Description |
|----------|-------------|
| `POST /plan/suggest` | Suggest a plan derived from the semantic graph around a task key.
| `POST /act` | Execute an action/task and return step results with salience scoring.
| `POST /delete` | Delete a memory at the given coordinate.
| `POST /recall/delete` | Delete a memory by coordinate via the recall API.

### Neuromodulation & Sleep

| Endpoint | Description |
|----------|-------------|
| `GET/POST /neuromodulators` | Read or set neuromodulator levels (dopamine, serotonin, noradrenaline, acetylcholine).
| `POST /sleep/run` | Trigger NREM/REM consolidation cycles.
| `GET /sleep/status` | Check sleep/consolidation status for current tenant.
| `GET /sleep/status/all` | Admin view: list sleep status for all known tenants.

### Admin & Operations

| Endpoint | Description |
|----------|-------------|
| `GET /admin/services` | List all cognitive services managed by Supervisor.
| `GET /admin/services/{name}` | Get status of a specific service.
| `POST /admin/services/{name}/start` | Start a cognitive service.
| `POST /admin/services/{name}/stop` | Stop a cognitive service.
| `POST /admin/services/{name}/restart` | Restart a cognitive service.
| `GET /admin/outbox` | List transactional outbox events (pending/failed/sent) with tenant filtering.
| `POST /admin/outbox/replay` | Mark failed outbox events for replay.
| `GET /admin/features` | Get current feature flag status and overrides.
| `POST /admin/features` | Update feature flag overrides (full-local mode only).
| `POST /memory/admin/rebuild-ann` | Rebuild ANN indexes for tiered memory.

All endpoints require a Bearer token (auth may be disabled automatically in dev mode). Every call can be scoped with `X-Tenant-ID`.

### Unified Memory API & Retrieval Pipeline

The `/recall` endpoint is backed by a full retrieval pipeline (`somabrain/services/retrieval_pipeline.py`) that orchestrates:

- **Multiple retrievers**: vector, wm (working memory), graph, lexical
- **Reranking strategies**: auto (HRR → MMR → cosine), mmr, hrr, cosine
- **Session learning**: recall sessions and `retrieved_with` links recorded when `persist=true`
- **Tiered memory**: governed superposition with cleanup indexes (cosine or HNSW)

By default, the recall API runs in full-capacity mode:

- Retrievers: `vector, wm, graph, lexical`
- Rerank: `auto` (prefers HRR → MMR → cosine depending on availability)
- Session learning: enabled (`persist=true`)

Override via environment variables (no code changes required):

- `SOMABRAIN_RECALL_FULL_POWER=1|0` (default 1)
- `SOMABRAIN_RECALL_SIMPLE_DEFAULTS=1` forces conservative mode
- `SOMABRAIN_RECALL_DEFAULT_RERANK=auto|mmr|hrr|cosine`
- `SOMABRAIN_RECALL_DEFAULT_PERSIST=1|0`
- `SOMABRAIN_RECALL_DEFAULT_RETRIEVERS=vector,wm,graph,lexical`

**Working-memory tuning:** adjust microcircuit column sizing and vote noise via `SOMABRAIN_WM_PER_COL_MIN_CAPACITY`, `SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR`, and `SOMABRAIN_WM_VOTE_ENTROPY_EPS` (see `common/config/settings.py` for defaults).

### Tiered Memory

SomaBrain supports governed tiered memory:

- **TieredMemoryRegistry** (`somabrain/services/tiered_memory_registry.py`) maintains per-tenant/namespace superposed traces
- **Outbox Pattern** (`somabrain/db/outbox.py`) ensures transactional event publishing to Kafka

Tip: set `use_hrr=true` in config to enable HRR reranking when `rerank=auto`.

---

## Quick Start

```bash
# Clone and launch the full stack
$ git clone https://github.com/somatechlat/somabrain.git
$ cd somabrain
$ docker compose up -d
# Ensure your memory backend is accessible at http://localhost:9595
$ curl -s http://localhost:9696/health | jq
```

If you run host-side tools (benchmarks, curl) and want convenient access to the memory service URL/token, generate host-friendly exports and source them:

```bash
scripts/export_memory_env.sh && source scripts/.memory.env
```

Store and recall a memory:

```bash
$ curl -s http://localhost:9696/memory/remember \
    -H "Content-Type: application/json" \
    -d '{"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}}'

$ curl -s http://localhost:9696/memory/recall \
    -H "Content-Type: application/json" \
    -d '{"query": "capital of France", "top_k": 3}' | jq '.results'
```

Close the loop with feedback:

```bash
$ curl -s http://localhost:9696/context/feedback \
    -H "Content-Type: application/json" \
    -d '`
{"session_id":"demo","query":"capital of France","prompt":"Summarise the capital of France.","response_text":"Paris is the capital of France.","utility":0.9,"reward":0.9}
`
'
```

Inspect tenant learning state:

```bash
$ curl -s http://localhost:9696/context/adaptation/state | jq
```

Metrics are available at `http://localhost:9696/metrics`; adaptation gains/bounds under `somabrain_learning_gain` / `somabrain_learning_bound`.

---

## Monitoring (no dashboards)

Prometheus metrics and Alertmanager alerts only. See `docs/technical-manual/monitoring.md`.

Quickstart:

```bash
# Generate .env from template
./scripts/generate_global_env.sh

# Start API locally with Compose
docker compose --env-file ./.env -f docker-compose.yml up -d --build somabrain_app

# Check health and scrape metrics
curl -fsS http://127.0.0.1:9696/health | jq .
curl -fsS http://127.0.0.1:9696/metrics | head -n 20
```

For common queries, see the PromQL cheat sheet at the top of the monitoring guide.

Alertmanager playbooks and escalation examples: see `docs/monitoring/alertmanager-playbooks.md`.

## Cognitive Threads (Predictors, Integrator, Segmentation)

Predictors are diffusion-backed and enabled by default so they’re always available unless explicitly disabled. Each service emits BeliefUpdate messages that IntegratorHub can consume to produce a GlobalFrame.

- Always-on defaults: `SOMABRAIN_FF_PREDICTOR_STATE=1`, `SOMABRAIN_FF_PREDICTOR_AGENT=1`, `SOMABRAIN_FF_PREDICTOR_ACTION=1`
- Heat diffusion method via `SOMA_HEAT_METHOD=chebyshev|lanczos`; tune `SOMABRAIN_DIFFUSION_T`, `SOMABRAIN_CONF_ALPHA`, `SOMABRAIN_CHEB_K`, `SOMABRAIN_LANCZOS_M`.
- Adjust the dev/test predictor latency with `SOMABRAIN_SLOW_PREDICTOR_DELAY_MS` so the slow predictor matches real service characteristics without hard-coded sleep values.
- Provide production graph files via `SOMABRAIN_GRAPH_FILE_STATE`, `SOMABRAIN_GRAPH_FILE_AGENT`, `SOMABRAIN_GRAPH_FILE_ACTION` (or `SOMABRAIN_GRAPH_FILE`). Supported JSON formats: adjacency or laplacian matrices.
- Integrator normalization (default ON): `SOMABRAIN_INTEGRATOR_ENFORCE_CONF=1` derives confidence from `delta_error` for cross-domain consistency. Set to `0` only if you must use raw predictor confidences.

See Technical Manual > Predictors for math, config, and tests.

### Benchmarks

Run diffusion predictor benchmarks and generate plots (clean, timestamped artifacts):

```bash
make bench-diffusion
```

Artifacts:
- Results (JSON): `benchmarks/results/diffusion_predictors/<timestamp>/`
- Plots (PNG): `benchmarks/plots/diffusion_predictors/<timestamp>/`
The latest timestamp is recorded in `benchmarks/results/diffusion_predictors/latest.txt`.

For live and adaptation learning benches, see Technical Manual → Benchmarks Quickstart:

- docs/technical-manual/benchmarks-quickstart.md

## Documentation

- **User Manual** – Installation, quick start, feature guides, FAQ (`docs/user-manual/`).
- **Technical Manual** – Architecture, deployment, monitoring, runbooks, security (`docs/technical-manual/`).
- **Development Manual** – Repository layout, coding standards, testing strategy, contribution workflow (`docs/development-manual/`).
- **Onboarding Manual** – Project context, code walkthroughs, checklists (`docs/onboarding-manual/`).
- **Canonical Improvements** – Living record of all hardening and transparency work (`docs/CANONICAL_IMPROVEMENTS.md`).
- **Cognitive-Thread Configuration** – Feature flags, environment variables, and Helm overrides for the predictor, segmentation, and integrator services (`docs/cog-threads/configuration.md`).
- **Predictor Service API** – Health probe behaviour and Kafka emission contract for the predictor services (`docs/cog-threads/predictor-api.md`).

### Drift & Learning Utilities
- **Drift Dump** – Run `make drift-dump` (or `python somabrain/scripts/drift_dump.py`) to print current drift baselines & last drift timestamps. Requires `ENABLE_DRIFT_DETECTION=1` or a persisted file at `SOMABRAIN_DRIFT_STORE`.
- **Tau & Entropy Alignment** – See `docs/technical-manual/tau-entropy-alignment.md` for how tau annealing, context diversity heuristic, and entropy caps co-exist.

---

## Contributing & Next Steps

1. Read the [Development Manual](docs/development-manual/index.md) and follow the local setup + testing instructions (`pytest`, `ruff`, `mypy`).
2. Extend the cognitive stack: plug in your own memory service, add new retrieval strategies, or integrate additional planning heuristics via `somabrain/planner`.
3. Capture benchmarks with the scripts under `benchmarks/` (e.g., `adaptation_learning_bench.py`) to measure model retention and learning speed. The old interactive notebook has been removed in favor of script-based, reproducible runs that operate against real services.
4. File issues or update `docs/CANONICAL_IMPROVEMENTS.md` whenever you add a new capability or harden an assumption.

**SomaBrain’s guiding philosophy is simple: make high-order memory and reasoning practical without relaxing the math. If something looks magical, you can find the code, metrics, and documentation that make it real.**
