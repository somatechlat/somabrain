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
| **Observability Built-In** | `/health`, `/metrics`, structured logs, and journaling. Queued writes and adaptation behaviour emit explicit metrics so you can see when the brain deviates. |
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
- **Neuromodulators** (`somabrain/neuromodulators.py`) supply dopamine/serotonin/noradrenaline/acetylcholine levels that can modulate learning rate (enable with `SOMABRAIN_LEARNING_RATE_DYNAMIC`).
- **Metrics** (`somabrain/metrics.py`) track per-tenant weights, effective LR, configured gains/bounds, feedback counts, and queue health (`somabrain_ltm_store_queued_total`).

---

## Runtime Topology

```
HTTP Client
   │  /remember /recall /context/evaluate /context/feedback …
   ▼
FastAPI Runtime (somabrain/app.py)
   │   ├─ Authentication & tenancy guards
   │   ├─ ContextBuilder / Planner / AdaptationEngine
   │   ├─ MemoryService (HTTP + journaling)
   │   └─ Prometheus metrics, structured logs
   ▼
Working Memory (MultiTenantWM) ──► Redis
Long-Term Memory ───────────────► External memory HTTP service
OPA Policy Engine ──────────────► Authorization decisions
Kafka ──────────────────────────► Audit & streaming
Postgres ───────────────────────► Config & metadata
Prometheus ─────────────────────► Metrics export
```

Docker Compose (`docker-compose.yml`) starts the API plus Redis, Kafka, OPA, Postgres, Prometheus, and exporters. For local dev we reserve the 301xx host port range to avoid conflicts and keep things predictable:

- API: host 9999 -> container 9696
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

Note: Kafka’s advertised listener is internal to the Docker network by default. For host-side consumers, run your clients inside the Compose network or add a dual-listener config. For WSL2 or remote clients, set the EXTERNAL listener host before running dev scripts:

```bash
KAFKA_EXTERNAL_HOST=192.168.1.10 ./scripts/dev_up.sh
```

### Kubernetes external ports (NodePort)

Kubernetes defaults to ClusterIP internally. If you need host access without an ingress/controller, enable NodePorts in the Helm chart using a centralized 30200+ range:

- API: 30200 → 9696
- Integrator health: 30201 → 8091
- Segmentation health: 30202 → 8092
- Predictor-State health: 30203 → 8093
- Predictor-Agent health: 30204 → 8094
- Predictor-Action health: 30205 → 8095
- Reward Producer (optional): 30206 → 8083
- Learner Online (optional): 30207 → 8084

How to enable (values):
- `.Values.expose.apiNodePort=true` → sets API service type to NodePort at `.Values.ports.apiNodePort`
- `.Values.expose.healthNodePorts=true` → exposes all cog-thread health services at their respective NodePorts
- `.Values.expose.learnerNodePorts=true` → exposes learner services at NodePorts

All NodePort numbers are centralized in `infra/helm/charts/soma-apps/values.yaml` under `.Values.ports.*`. Container and target ports remain internal and unchanged.

---

## API Overview

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Checks Redis, Postgres, Kafka, OPA, memory backend, and embedder.
| `POST /remember` | Store a memory (accepts legacy inline fields or `{"payload": {...}}`). Journals if the backend is unavailable and sets `breaker_open`/`queued` flags.
| `POST /remember/batch` | Bulk ingestion with per-item success/failure counts.
| `POST /recall` | Retrieves working-memory and long-term matches with scores from `UnifiedScorer`.
| `POST /context/evaluate` | Builds a prompt, returns weighted memories, residual vector, and working-memory snapshot.
| `POST /context/feedback` | Updates tenant-specific retrieval/utility weights; emits gain/bound metrics.
| `GET /context/adaptation/state` | Inspect current weights, effective learning rate, configured gains, and bounds.
| `POST /plan/suggest`, `POST /act` | Planner/agent assist (enabled when full stack is running).
| `POST /sleep/run` | Trigger NREM/REM consolidation cycles.
| `GET/POST /neuromodulators` | Read or set neuromodulator levels (dopamine, serotonin, etc.).

All endpoints require a Bearer token unless you set `SOMABRAIN_DISABLE_AUTH=1` for local experiments, and every call can be scoped with `X-Tenant-ID`.

---

## Quick Start

```bash
# Clone and launch the full stack
$ git clone https://github.com/somatechlat/somabrain.git
$ cd somabrain
$ docker compose up -d
# Ensure your memory backend is accessible at http://localhost:9595
$ curl -s http://localhost:9999/health | jq
```

Store and recall a memory:

```bash
$ curl -s http://localhost:9999/remember \
    -H "Content-Type: application/json" \
    -d '{"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}}'

$ curl -s http://localhost:9999/recall \
    -H "Content-Type: application/json" \
    -d '{"query": "capital of France", "top_k": 3}' | jq '.results'
```

Close the loop with feedback:

```bash
$ curl -s http://localhost:9999/context/feedback \
    -H "Content-Type: application/json" \
    -d '`
{"session_id":"demo","query":"capital of France","prompt":"Summarise the capital of France.","response_text":"Paris is the capital of France.","utility":0.9,"reward":0.9}
`
'
```

Inspect tenant learning state:

```bash
$ curl -s http://localhost:9999/context/adaptation/state | jq
```

Metrics are available at `http://localhost:9999/metrics`; queued writes appear under `somabrain_ltm_store_queued_total`, and adaptation gains/bounds under `somabrain_learning_gain` / `somabrain_learning_bound`.

Journaling and durability: writes are journaled to `/var/lib/somabrain/journal` when external backends are unavailable. The Compose stack mounts a persistent volume (`somabrain_journal_data`) at that path so journaled events survive container restarts. You can replay journals into your memory backend with `scripts/migrate_journal_to_backend.py` or `scripts/journal_to_outbox.py`.

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
curl -fsS http://127.0.0.1:9999/health | jq .
curl -fsS http://127.0.0.1:9999/metrics | head -n 20
```

For common queries, see the PromQL cheat sheet at the top of the monitoring guide.

Alertmanager playbooks and escalation examples: see `docs/monitoring/alertmanager-playbooks.md`.

---

## Cognitive Threads (Predictors, Integrator, Segmentation)

Predictors are diffusion-backed and enabled by default so they’re always available unless explicitly disabled. Each service emits BeliefUpdate messages that IntegratorHub can consume to produce a GlobalFrame.

- Always-on defaults: `SOMABRAIN_FF_PREDICTOR_STATE=1`, `SOMABRAIN_FF_PREDICTOR_AGENT=1`, `SOMABRAIN_FF_PREDICTOR_ACTION=1`
- Heat diffusion method via `SOMA_HEAT_METHOD=chebyshev|lanczos`; tune `SOMABRAIN_DIFFUSION_T`, `SOMABRAIN_CONF_ALPHA`, `SOMABRAIN_CHEB_K`, `SOMABRAIN_LANCZOS_M`.
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

## Documentation & Roadmap

- **User Manual** – Installation, quick start, feature guides, FAQ (`docs/user-manual/`).
- **Technical Manual** – Architecture, deployment, monitoring, runbooks, security (`docs/technical-manual/`).
- **Development Manual** – Repository layout, coding standards, testing strategy, contribution workflow (`docs/development-manual/`).
- **Onboarding Manual** – Project context, code walkthroughs, checklists (`docs/onboarding-manual/`).
- **Canonical Improvements** – Living record of all hardening and transparency work (`docs/CANONICAL_IMPROVEMENTS.md`).
- **Cognitive-Thread Configuration** – Feature flags, environment variables, and Helm overrides for the predictor, segmentation, and integrator services (`docs/cog-threads/configuration.md`).
- **Predictor Service API** – Health probe behaviour and Kafka emission contract for the predictor services (`docs/cog-threads/predictor-api.md`).

---

## Contributing & Next Steps

1. Read the [Development Manual](docs/development-manual/index.md) and follow the local setup + testing instructions (`pytest`, `ruff`, `mypy`).
2. Extend the cognitive stack: plug in your own memory service, add new retrieval strategies, or integrate additional planning heuristics via `somabrain/planner`.
3. Capture benchmarks with the scripts under `benchmarks/` (e.g., `adaptation_learning_bench.py`) to measure model retention and learning speed. The old interactive notebook has been removed in favor of script-based, reproducible runs that operate against real services.
4. File issues or update `docs/CANONICAL_IMPROVEMENTS.md` whenever you add a new capability or harden an assumption.

**SomaBrain’s guiding philosophy is simple: make high-order memory and reasoning practical without relaxing the math. If something looks magical, you can find the code, metrics, and documentation that make it real.**
