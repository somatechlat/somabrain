somabrain + somafractalmemory integration

Overview
- The `somafractalmemory` library is cloned locally at `somafractalmemory/` and installed in editable mode into `.venv`.
- A minimal example is available at `examples/soma_quickstart.py:1` that stores and recalls a memory using the in‑memory vector backend.

SomaBrain docs
- See `docs/SomaBrain.md:1` for a full, nicely formatted project summary, MVP scope, and roadmap.
- Architecture: `docs/Architecture.md:1` details the biology‑first design and HRR/superposition plan.
- Progress Log: `PROGRESS.md:1` tracks milestones, decisions, and next steps.
- Use Cases + UML: `docs/UseCases.md:1` shows core flows and Mermaid diagrams.

Setup
- Create venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install package (editable) and deps:
  - `python -m pip install -U pip setuptools wheel`
  - `python -m pip install -e somafractalmemory`
  - `python -m pip install numpy redis fakeredis qdrant-client networkx prometheus-client`
  - Optional extras: `transformers cryptography scikit-learn Pillow torchaudio`

Run the example
- `source .venv/bin/activate`
- `python examples/soma_quickstart.py`

Notes
- ON_DEMAND mode defaults to an in‑memory vector store; no external services needed.
- If you enable Qdrant/Redis backends, configure them via `config` or environment per `somafractalmemory/CONFIGURATION.md:1`.

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
  - Predictor: `SOMABRAIN_PREDICTOR_PROVIDER` (stub|slow), `SOMABRAIN_PREDICTOR_TIMEOUT_MS`, `SOMABRAIN_PREDICTOR_FAIL_DEGRADE`.
  - Auth: `SOMABRAIN_API_TOKEN` for exact match token; `SOMABRAIN_AUTH_REQUIRED=true` to require any bearer token.

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
