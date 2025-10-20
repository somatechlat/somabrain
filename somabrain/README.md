somabrain + somafractalmemory

Overview
- The `somafractalmemory` library is a dependency (installed via pip), not part of this repo.
- A minimal example is available at `examples/soma_quickstart.py:1` that stores and recalls a memory using the in‑memory vector backend.

SomaBrain docs
- See `docs/SomaBrain.md:1` for a full, nicely formatted project summary, MVP scope, and roadmap.
- Architecture: `docs/Architecture.md:1` details the biology‑first design and HRR/superposition plan.
- Progress Log: `PROGRESS.md:1` tracks milestones, decisions, and next steps.
- Use Cases + UML: `docs/UseCases.md:1` shows core flows and Mermaid diagrams.
 - Index Profiles: `docs/INDEX_PROFILES.md:1` explains vector index/compression profiles and knobs.
 - MUVERA FDE: `docs/MUVERA_FDE.md:1` outlines the single‑vector retrieval plan and config placeholders.

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
 - Optional bench: `PYTHONPATH=. python scripts/bench_recall.py` (prints p50/p95 ms)
 - Optional ablation: `PYTHONPATH=. python scripts/ablate_hrr.py` (compares HRR-first off/on/gated)

Profiles
- Copy `config.example.yaml` to `config.yaml` to enable the Balanced profile (HRR‑first gated, diversity MMR, Mahalanobis predictor, adaptive salience). Adjust for Low‑Latency or High‑Recall using the commented presets.

Notes
- ON_DEMAND mode defaults to an in‑memory vector store; no external services needed.
- If you enable Qdrant/Redis backends, configure them via `config` or environment; see the Somafractalmemory docs (CONFIGURATION.md in its repo).

Run API
- `source .venv/bin/activate`
- `uvicorn somabrain.app:app --reload`

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

Anatomy Aliases
- Use biological names without changing internals: `somabrain/anatomy.py` (e.g., `PrefrontalWM`, `CerebellumPredictor`, `HippocampusEpisodic`, `CortexSemantic`).

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
