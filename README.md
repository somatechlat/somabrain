SomaBrain — Brain‑Inspired Memory & Planning for Agents

[![CI](https://github.com/somatechlat/somaBrain/actions/workflows/ci.yml/badge.svg)](https://github.com/somatechlat/somaBrain/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://somatechlat.github.io/somaBrain/)
[![Tag](https://img.shields.io/github/v/tag/somatechlat/somaBrain?sort=semver)](https://github.com/somatechlat/somaBrain/tags)
[![Container](https://img.shields.io/badge/container-ghcr.io%2Fsomatechlat%2FsomaBrain-0A66C2?logo=docker)](https://github.com/somatechlat/somaBrain/pkgs/container/somaBrain)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Elegant, verifiable mathematics meets practical engineering. SomaBrain gives agents a stable, observable memory and planning layer powered by HRR numerics (unitary roles, exact and Wiener unbinding), typed graph links, multi‑tenant semantics, and a clean FastAPI surface.

Human × AI collaboration, by design. Declarative HTTP contracts and tiny SDKs make it easy for humans to guide the system, while Prometheus metrics make behavior visible and tunable. Small, composable “brain modules” (thalamus, amygdala, hippocampus, prefrontal) provide understandable control loops instead of opaque magic.

Why SomaBrain stands out
- Single memory gateway (ADR‑0002) to SomaFractalMemory (modes: stub | local | http)
- Hardened math: sqrt(D) tiny‑floor, deterministic unitary roles, float64 divisions, Wiener/MAP for superpositions
- Observable by default: Prometheus metrics for HTTP, recall stages, HRR paths, microcircuits, predictors, consolidation

Docs & Tutorials
- Quickstart API: `docs/source/api_quickstart.md` • Full API: `docs/source/api.md`
- Configure & deploy: `docs/ops/configuration.md`, `docs/OPERATION.md`
- Security hardening: `docs/ops/security.md`
- Metrics & dashboards: `docs/ops/metrics.md`, `docs/ops/grafana.md`
- Architecture overview: `docs/architecture/brain_modules.md`, `docs/architecture/executive_controller.md`

Project status: Beta — stable core, evolving APIs and docs.

Overview
- The `somafractalmemory` library is a dependency (installed via pip), not part of this repo.
- A minimal example is available at `examples/soma_quickstart.py:1` that stores and recalls a memory using the in‑memory vector backend.

Why SomaBrain (at a glance)
- Cognitive memory API with hardened math (HRR, unitary roles, exact + Wiener unbind)
- Multi‑tenant by default; observability via Prometheus `/metrics`
- Graph links + planning; quotas, rate‑limits, and auth hooks
- Single Docker run to try; copy‑paste API curls and micro‑clients

 SomaBrain docs
- Docs landing: `docs/index.md`
- Architecture: `docs/architecture/brain_modules.md`, `docs/architecture/executive_controller.md`
- API Reference: `docs/source/api.md` • Quickstart: `docs/source/api_quickstart.md`
- Ops: `docs/ops/configuration.md`, `docs/ops/metrics.md`, `docs/ops/security.md`
 - Grafana: `docs/ops/grafana.md` and dashboard JSON `docs/ops/grafana_dashboard.json`
 - Collaboration: `docs/HUMAN_AI_COLLABORATION.md`
- Observability panels: `docs/observability/metrics_dashboard.md`
- Roadmap: `docs/ROADMAP.md`
- Key Decision (ADR‑0002): `docs/architecture/adr/0002-single-memory-gateway.md`

Math Core (Hardened)
- Canonical numerics: single-source tiny-floor with sqrt(D) scaling and safe normalization (`somabrain/numerics.py`).
- Unitary roles: deterministic, isometric role vectors (random phase in rFFT) preserve norms under bind.
- Exact unbind: float64 spectral division for unitary roles for precise recovery.
- Wiener unbinding: MAP filter with SNR parameterization for Gaussian roles; robust Tikhonov fallback remains.
- Deterministic seeding: 64-bit seed mixing ensures reproducible vectors and roles.

Setup
- Create venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps:
  - `python -m pip install -U pip setuptools wheel`
  - `python -m pip install somafractalmemory`
  - `python -m pip install numpy redis fakeredis qdrant-client networkx prometheus-client fastapi uvicorn httpx`
  - Optional extras: `transformers cryptography scikit-learn Pillow torchaudio`

Run the example
- `source .venv/bin/activate`
- `python examples/soma_quickstart.py`
 - See `docs/source/api_quickstart.md` for canonical curl examples for the API endpoints.
 - Optional bench: `PYTHONPATH=. python scripts/bench_recall.py` (prints p50/p95 ms)
 - Optional ablation: `PYTHONPATH=. python scripts/ablate_hrr.py` (compares HRR-first off/on/gated)
 - Cognition core bench: `make bench` (quality + latency CSV/plots saved under `benchmarks/`)

Profiles
- Copy `config.example.yaml` to `config.yaml` to enable the Balanced profile (HRR‑first gated, diversity MMR, Mahalanobis predictor, adaptive salience). Adjust for Low‑Latency or High‑Recall using the commented presets.

Notes
- ON_DEMAND mode defaults to an in‑memory vector store; no external services needed.
- If you enable Qdrant/Redis backends, configure them via `config` or environment; see the Somafractalmemory docs (CONFIGURATION.md in its repo).

Run API
- `source .venv/bin/activate`
- `uvicorn somabrain.app:app --reload` (default port 9696)
- To run a second instance on port 9697: `uvicorn somabrain.app:app --port 9697`

Ops tuning (math)
- Unitary roles and exact unbind are on by default. For superposed working memory, you can tune Wiener/MAP parameters via env:
  - `SOMABRAIN_WIENER_SNR_DB` (float, default ~35–40): maps to `floor_snr = 1/SNR`.
  - `SOMABRAIN_WIENER_ALPHA` (float, default 1e-3): scales adaptive floor with `k_est · mean(|B|^2)`.
  - `SOMABRAIN_WIENER_WHITEN` (bool): enable spectral whitening (recommended when k>1).
  - Optional cleanup is typically handled at the caller (snap to nearest anchor after unbind) — use it when evaluating multi-item superpositions.
- Metrics (Prometheus):
  - `somabrain_unbind_path_total{path}` — counts unbind paths (robust|exact|exact_unitary|wiener)
  - `somabrain_unbind_wiener_floor` — current floor value used
  - `somabrain_unbind_k_est` — estimated k used by Wiener

Math docs
- See `docs/COGNITION_MATH_WHITEPAPER.md` for the production-cut whitepaper.

Configuration
- Env vars (Dynaconf `SOMABRAIN_` prefix) or `config.yaml`:
  - `SOMABRAIN_USE_HRR` (bool): enable HRR QuantumLayer and tenant HRR context.
  - `SOMABRAIN_USE_HRR_CLEANUP` (bool): include HRR cleanup signal in `/recall` and metrics.
  - `SOMABRAIN_WM_SIZE`, `SOMABRAIN_EMBED_DIM`: working memory capacity and embedding dim (default 64, 256).
  - `SOMABRAIN_RATE_RPS`, `SOMABRAIN_RATE_BURST`: per‑tenant rate limiter.
  - `SOMABRAIN_WRITE_DAILY_LIMIT`: per‑tenant daily write quota.
  - Reflection: `SOMABRAIN_REFLECT_SIMILARITY_THRESHOLD` (default 0.35), `SOMABRAIN_REFLECT_MIN_CLUSTER_SIZE` (2), `SOMABRAIN_REFLECT_MAX_SUMMARIES` (5).
  - Memory backend: `SOMABRAIN_MEMORY_MODE` = `local` | `http` | `stub`; HTTP endpoint/token via `SOMABRAIN_MEMORY_HTTP_ENDPOINT`, `SOMABRAIN_MEMORY_HTTP_TOKEN`.
  - Index profiles (backend): `SOMABRAIN_INDEX_PROFILE` (low_latency|balanced|high_recall), `SOMABRAIN_PQ_M`, `SOMABRAIN_PQ_BITS`, `SOMABRAIN_OPQ_ENABLED`, `SOMABRAIN_ANISOTROPIC_ENABLED`, `SOMABRAIN_IMI_CELLS`, `SOMABRAIN_HNSW_M`, `SOMABRAIN_HNSW_EFC`, `SOMABRAIN_HNSW_EFS`.
  - Predictor: `SOMABRAIN_PREDICTOR_PROVIDER` (stub|slow), `SOMABRAIN_PREDICTOR_TIMEOUT_MS`, `SOMABRAIN_PREDICTOR_FAIL_DEGRADE`.
  - Predictor (providers): now also supports `mahal` (Mahalanobis surprise blended with cosine residuals).
  - Predictor (LLM provider): `SOMABRAIN_PREDICTOR_PROVIDER=llm`, `SOMABRAIN_PREDICTOR_LLM_ENDPOINT`, `SOMABRAIN_PREDICTOR_LLM_TOKEN`.
  - Auth: `SOMABRAIN_API_TOKEN` for exact match token; `SOMABRAIN_AUTH_REQUIRED=true` to require any bearer token.
  - Executive/Soft Salience: `SOMABRAIN_USE_SOFT_SALIENCE`, `SOMABRAIN_SOFT_SALIENCE_TEMPERATURE`, `SOMABRAIN_USE_META_BRAIN`, `SOMABRAIN_META_GAIN`, `SOMABRAIN_META_LIMIT`, `SOMABRAIN_USE_EXEC_CONTROLLER`, `SOMABRAIN_EXEC_WINDOW`, `SOMABRAIN_EXEC_CONFLICT_THRESHOLD`, `SOMABRAIN_EXEC_EXPLORE_BOOST_K`.
  - Executive bandits (optional): `SOMABRAIN_EXEC_USE_BANDITS` (bool), `SOMABRAIN_EXEC_BANDIT_EPS`.
  - Adaptive Salience (optional): `SOMABRAIN_USE_ADAPTIVE_SALIENCE` (bool), `SOMABRAIN_SALIENCE_TARGET_STORE_RATE`, `SOMABRAIN_SALIENCE_TARGET_ACT_RATE`, `SOMABRAIN_SALIENCE_ADJUST_STEP`.
  - Planner: `SOMABRAIN_USE_PLANNER`, `SOMABRAIN_PLAN_MAX_STEPS`, `SOMABRAIN_PLAN_REL_TYPES`, `SOMABRAIN_PLANNER_BACKEND` (bfs|rwr), `SOMABRAIN_RWR_RESTART`, `SOMABRAIN_RWR_STEPS`.
  - Microcircuits: `SOMABRAIN_USE_MICROCIRCUITS`, `SOMABRAIN_MICRO_CIRCUITS`, `SOMABRAIN_MICRO_VOTE_TEMPERATURE`.
  - Embeddings: `SOMABRAIN_EMBED_PROVIDER` (tiny|hrr|fde|transformer), `SOMABRAIN_EMBED_MODEL` (e.g., sentence-transformers/all-MiniLM-L6-v2), `SOMABRAIN_EMBED_DIM_TARGET_K` (JL projection target dim), `SOMABRAIN_EMBED_CACHE_SIZE`.
  - FDE (MUVERA placeholders): `SOMABRAIN_FDE_ENABLED` (bool), `SOMABRAIN_FDE_POOLING` (gated_max|attention), `SOMABRAIN_FDE_MARGIN_THRESHOLD`.
  - Memory HTTP (async): HTTP mode now uses async client paths within FastAPI routes for better concurrency; local and stub modes remain synchronous.

HRR Cleanup (optional)
- Enable `SOMABRAIN_USE_HRR=true` and `SOMABRAIN_USE_HRR_CLEANUP=true` to compute a top‑1 cleanup against tenant anchors.
- `/recall` response includes `hrr_cleanup: { anchor_id, score }` and metrics emit:
  - `somabrain_hrr_cleanup_used_total`
  - `somabrain_hrr_cleanup_score`

Reflection v2
- `/reflect` clusters recent episodics by cosine similarity over BoW vectors and writes semantic summaries (up to `reflect_max_summaries`).
- Tuned via reflection config keys above.

Memory Gateway (ADR‑0002)
- Single gateway `somabrain/memory_client.py` handles all long‑term memory I/O (modes: stub | local | http).
- No other module imports `somafractalmemory.*` directly (enforced by tests).

Testing
- Quick smoke scripts (no pytest needed):
  - `PYTHONPATH=. .venv/bin/python tests/test_endpoints_basic.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_hrr_cleanup.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_memory_client.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_reflection_v2.py`
- These cover core endpoints, HRR cleanup signal, memory client behavior, and reflection clustering.

Migration
- Export: `POST /migrate/export { include_wm, wm_limit }` returns `{ manifest, memories, wm }` with `manifest.version` and `api_version`.
- Import: `POST /migrate/import { manifest, memories, wm }` validates manifest, warms WM, and returns counts with `warnings` if any.

Consolidation & Sleep Cycle
- NREM replay: re-activate top-importance episodics to create semantic summaries and reinforce links between items.
- REM recombination: synthesize creative semantic memories from unrelated episodics; stored with `phase: "REM"`.
- Config:
  - `SOMABRAIN_CONSOLIDATION_ENABLED`
  - `SOMABRAIN_SLEEP_INTERVAL_SECONDS`
  - `SOMABRAIN_NREM_BATCH_SIZE`
  - `SOMABRAIN_REM_RECOMB_RATE`
  - `SOMABRAIN_MAX_SUMMARIES_PER_CYCLE`
- Metrics:
  - `somabrain_consolidation_runs_total{phase="NREM|REM"}`
  - `somabrain_consolidation_replay_strength`
  - `somabrain_consolidation_rem_synthesized_total`
- CLI (module): `python -m somabrain.consolidation sleep --tenant public --nrem --rem`

Background Sleep Scheduler
- Enable with `SOMABRAIN_CONSOLIDATION_ENABLED=true` and set `SOMABRAIN_SLEEP_INTERVAL_SECONDS` (>0) to run NREM+REM periodically per tenant seen in WM.
- Admin trigger: `POST /sleep/run { nrem: true, rem: true }` runs a cycle for the current tenant.

Docker
- Build and run:
  - `docker build -t somabrain .`
  - `docker run -p 8000:8000 -e SOMABRAIN_MEMORY_MODE=local somabrain`
- Or with compose: `docker compose up --build`

Project Goals
- Cognitive layer over SomaFractalMemory with working memory, recall, prediction, salience, and reflection.
- Biology-first architecture: modules mirror brain anatomy and neurochemistry.
- Multi-tenant API with strong observability, quotas, and configurable backends.
- Roadmap: HRR cleanup → Reflection v2 → Graph reasoning → Personality → Predictor providers → Ops/Packaging → Multi-agent.

Multi‑tenancy
- Pass `X-Tenant-ID` header to isolate working memory and long‑term namespace per tenant.
- Default fallback tenant is `public` when no header/token is provided.

Auth & Quotas
- Optional bearer token: set `SOMABRAIN_API_TOKEN` (or in `config.yaml` as `api_token`); then include `Authorization: Bearer <token>` on requests.
- Per-tenant rate limiting (token bucket): defaults `rate_rps=50`, `rate_burst=100`.
- Per-tenant daily write quota: `write_daily_limit` (default 10000) enforced on `/remember` and gated writes in `/act`.
Note: By default, no auth is required. Enable auth later by setting `SOMABRAIN_API_TOKEN` or `SOMABRAIN_AUTH_REQUIRED=true`.
Semantic Graph (typed relations)
- Create typed links: `POST /link { from_key|from_coord, to_key|to_coord, type: causes|contrasts|part_of|depends_on|motivates|related }`.
- Query links: `POST /graph/links { from_key|from_coord, type?, limit? }`.
- Event tuple fields: `/remember` enriches `who/did/what/where/when/why` heuristically when possible.

Planner (optional)
- When `SOMABRAIN_USE_PLANNER=true`, `/act` returns a `plan: []` derived from neighbors in the semantic graph (bounded breadth‑first).
- Tune with `SOMABRAIN_PLAN_REL_TYPES` and `SOMABRAIN_PLAN_MAX_STEPS`.

Executive Controller (optional)
- Conflict‑aware policy adjusts `top_k`, toggles graph augmentation, and can inhibit act/store under high conflict.
- Metrics: `somabrain_exec_conflict`, `somabrain_exec_use_graph_total`.

Microcircuits WM (optional)
- Shards WM into K columns; per‑column recall + softmax vote aggregation for stability and diversity.
- Enable with `SOMABRAIN_USE_MICROCIRCUITS=true` and set `SOMABRAIN_MICRO_CIRCUITS`.
 - Diagnostics: `GET /micro/diag` returns per-tenant per-column item counts when enabled; metrics include `somabrain_micro_vote_entropy`, `somabrain_micro_column_admit_total`, `somabrain_micro_column_best_total`.
Providers and Async I/O
- Embeddings: `SOMABRAIN_EMBED_PROVIDER=tiny|hrr|transformer` with optional JL projection (`SOMABRAIN_EMBED_DIM_TARGET_K`) and LRU cache (`SOMABRAIN_EMBED_CACHE_SIZE`). Metrics: `somabrain_embed_latency_seconds{provider}`, `somabrain_embed_cache_hit_total{provider}`.
- Predictors: `SOMABRAIN_PREDICTOR_PROVIDER=stub|mahal|slow` with budgets; metrics include `somabrain_predictor_latency_seconds{provider}` and fallbacks.
- Memory HTTP: in HTTP mode, routes use async HTTP client for better concurrency; local/stub remain synchronous.

Quick smoke (providers)
- Tiny embeddings + stub predictor (default):
  - `uvicorn somabrain.app:app --reload`
  - POST `/recall {"query":"hello","top_k":3}` then check `/metrics` for embed/predictor metrics.
- HRR embeddings (feature flag):
  - `export SOMABRAIN_USE_HRR=true && export SOMABRAIN_EMBED_PROVIDER=hrr`
  - Restart and call `/recall`; verify HRR metrics and behavior.
- Mahalanobis predictor:
  - `export SOMABRAIN_PREDICTOR_PROVIDER=mahal`
  - Call `/act`; verify non‑zero error distribution and predictor latency by provider.
HRR-first rerank (WM + LTM)
- When `SOMABRAIN_USE_HRR=true` and `SOMABRAIN_USE_HRR_FIRST=true`, the system blends HRR similarity into ranking.
- WM hits: blend `combined = (1-α)*cosine + α*HRR_cosine`.
- LTM: when scores aren’t available from the backend, use HRR cosine to rerank payloads (best‑effort); metric `somabrain_hrr_rerank_ltm_applied_total`.
  - HRR-first gating: `SOMABRAIN_HRR_RERANK_ONLY_LOW_MARGIN` (bool), `SOMABRAIN_RERANK_MARGIN_THRESHOLD`.
  - Diversity rerank (optional): `SOMABRAIN_USE_DIVERSITY` (bool), `SOMABRAIN_DIVERSITY_METHOD` (mmr|facility), `SOMABRAIN_DIVERSITY_K`, `SOMABRAIN_DIVERSITY_LAMBDA`.

Canonical docs (legacy pointers)
- Legacy planning files have been reorganized under docs/. See `docs/index.md` for the new structure.

Removed experimental modules
- Legacy/experimental modules (advanced/fractal/FNOM/transformer provider/anatomy facades) have been removed to reduce surface area and improve maintainability. Demo endpoints remain guarded and inert by default.

API Surface (minimal vs non‑minimal)
- Minimal (default):
  - `GET /health`, `GET /metrics`
  - `POST /remember`, `POST /recall`
  - `POST /link`, `POST /graph/links`, `POST /plan/suggest`
- Non‑minimal (set `SOMABRAIN_MINIMAL_PUBLIC_API=0`):
  - Sleep ops: `POST /sleep/run`, `GET /sleep/status`, `GET /sleep/status/all`
  - Diagnostics: `GET /metrics/snapshot`, `GET/POST /personality`, `GET /micro/diag`
  - Demo/alt endpoints (must also set flags):
    - `expose_alt_memory_endpoints=true` → `/fnom/*`, `/fractal/*`, `/brain/*` (experimental)
    - `expose_brain_demos=true` (kept off by default in code)

Security note: Keep minimal mode for public exposure; enable non‑minimal and demos only in trusted/internal environments.

Quick Start (Docker)
- Run API in stub mode (no external deps):
  - `docker run --rm -p 9696:9696 -e SOMABRAIN_MEMORY_MODE=stub -e SOMABRAIN_DEMO_SEED=true ghcr.io/somatechlat/somaBrain:latest`
- Health: `curl -s http://127.0.0.1:9696/health`
- Recall: `curl -s -X POST http://127.0.0.1:9696/recall -H 'Content-Type: application/json' -d '{"query":"write docs","top_k":3}'`
- Plan: `curl -s -X POST http://127.0.0.1:9696/plan/suggest -H 'Content-Type: application/json' -d '{"task_key":"write docs"}'`

Python/TS micro-clients
- Python (httpx):
  - `pip install httpx`
  -
    ```python
    import httpx
    base = "http://127.0.0.1:9696"
    headers = {"Content-Type": "application/json"}
    httpx.post(f"{base}/remember", json={"coord": None, "payload": {"task":"hello","importance":1,"memory_type":"episodic"}}, headers=headers)
    r = httpx.post(f"{base}/recall", json={"query":"hello","top_k":3}, headers=headers)
    print(r.json())
    ```
- TypeScript (fetch):
  -
    ```ts
    const base = "http://127.0.0.1:9696";
    await fetch(`${base}/remember`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({coord:null, payload:{task:"hello",importance:1,memory_type:"episodic"}})});
    const res = await fetch(`${base}/recall`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({query:"hello", top_k:3})});
    console.log(await res.json());
    ```

 Clients (ready-made)
- Python: `clients/python/somabrain_client.py`
  -
    ```python
    from clients.python.somabrain_client import SomaBrainClient
    api = SomaBrainClient("http://127.0.0.1:9696", tenant="public")
    api.remember({"task":"hello","importance":1,"memory_type":"episodic"})
    print(api.recall("hello", top_k=3))
    ```
- TypeScript: `clients/typescript/somabrainClient.ts`
  -
    ```ts
    import { SomaBrainClient } from "./clients/typescript/somabrainClient";
    const api = new SomaBrainClient("http://127.0.0.1:9696", { tenant: "public" });
    await api.remember({ task: "hello", importance: 1, memory_type: "episodic" });
    console.log(await api.recall("hello", 3));
    ```

GHCR (CI publish)
- On tag `v*`, a multi-arch image is pushed to `ghcr.io/somatechlat/somaBrain` (see `.github/workflows/docker-publish.yml`).
- Pull latest: `docker pull ghcr.io/somatechlat/somaBrain:latest`

Performance (CPU, D=8192, float32)
- Quality (mean cosine):
  - Unitary+Exact k=1: ≈ 1.000 (PASS gate ≥ 0.70)
  - Gaussian+Wiener − Tikhonov Δcos (raw): k=1 ≈ 0.030 (borderline), k=4 ≈ 0.087, k=16 ≈ 0.052 (PASS ≥ 0.03)
- Unbind latency p99 (ms):
  - Unitary+Exact: ≈ 0.80 ms (PASS ≤ 1.0 ms)
  - Gaussian+Wiener: ≈ 0.72 ms
  - Gaussian+Tikhonov: ≈ 0.80 ms
- Reproduce locally:
  - `PYTHONPATH=. MPLBACKEND=Agg python benchmarks/cognition_core_bench.py`
  - Outputs: `benchmarks/cognition_quality.csv`, `benchmarks/cognition_latency.csv` (and PNGs if matplotlib is available)

Charts
- Recovery vs k: `benchmarks/cognition_cosine.png`
- Unbind latency p99: `benchmarks/cognition_unbind_p99.png`
