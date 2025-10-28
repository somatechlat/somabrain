# SomaBrain Benchmarks

This folder contains a mix of pure numerics/micro-benchmarks and live end-to-end (E2E) benchmarks. Use the E2E ones to validate real behavior against a running stack; use micro-benches to profile inner loops and algorithms.

## Quick map

- Live/E2E (real IO)
  - `recall_latency_bench.py` — Remember/recall latency (requests to running API). Outputs p50/p95 for writes/reads.
  - `rag_live_bench.py` — End-to-end RAG: seeds a small corpus via `/remember`, queries `/rag/retrieve`, computes hit-rate@k, scrapes `/metrics`.
  - `http_bench.py` — Simple concurrent HTTP load harness for any endpoint (async httpx). Good for latency percentiles.
  - `eval_rag_precision.py` — Measures precision for RAG retrieval against labeled pairs via live API.
  - `eval_learning_speed.py` — Measures adaptation/learning progression via live API.
  - `db_bench.py` — Direct DB insert/select cycles via project SQLAlchemy engine (real DB IO).
  - Scale utilities under `scale/` — Load/soak/spike, chaos experiments, and large remember/recall runs (require live stack).
  - `showcase_suite.py` — Composable suite that can run RAG latency and collect metrics; supports `--dry-run` for CI.

- Micro / pure numerics (no IO)
  - `cognition_core_bench.py` — Core HRR/quantum numerics: recovery quality and unbind latency (numpy only).
  - `worker_bench.py` — Synthetic RAG pipeline path without network IO (NOT E2E).
  - `bench_numerics.py`, `numerics_bench.py`, `numerics_bench_multi.py`, `numerics_workbench.py` — algorithmic kernels.
  - `nulling_bench.py`, `nulling_test.py`, `colored_noise_bench.py`, `capacity_curves.py`, etc. — algorithmic/mathematical experiments.

## When to use what

- Proving end-to-end claims: prefer `rag_live_bench.py`, `recall_latency_bench.py`, and `http_bench.py` against a running stack.
- Profiling algorithms and inner loops: use `cognition_core_bench.py` and other numerics benches.
- Database throughput sanity: `db_bench.py`.
- Scale/stress: scripts under `benchmarks/scale/`.

## How to run (dev stack)

1) Start the stack (from repo root):
- Use Docker Compose per the deployment docs, ensuring API is reachable (e.g., http://127.0.0.1:9696 or :9999 depending on your profile).

2) Live/E2E examples:
- Recall latency (defaults to http://127.0.0.1:9999):
  - SOMA_API_URL=http://127.0.0.1:9999 python benchmarks/recall_latency_bench.py
- RAG live bench (defaults to http://127.0.0.1:9696):
  - SOMABRAIN_API_URL=http://127.0.0.1:9696 python benchmarks/rag_live_bench.py --output benchmarks/outputs/rag_live_results.json
- HTTP harness (choose endpoint):
  - python benchmarks/http_bench.py --url http://127.0.0.1:9696/rag/retrieve --concurrency 8 --requests 200

3) Micro-benches:
- Cognition core:
  - PYTHONPATH=. python benchmarks/cognition_core_bench.py --dim 8192 --dtype float32
- Worker synthetic pipeline:
  - PYTHONPATH=. python benchmarks/worker_bench.py --iterations 500

## Environment variables

- API base URLs:
  - `SOMA_API_URL` for `recall_latency_bench.py` (default: http://127.0.0.1:9999)
  - `SOMABRAIN_API_URL` for `rag_live_bench.py` (default: http://127.0.0.1:9696)
- Tenancy (when applicable): `SOMA_TENANT`, `SOMA_NAMESPACE`
- DB DSN for DB bench (optional): `SOMABRAIN_POSTGRES_DSN`

## Notes and guarantees

- Files labeled "micro" or "numerics" do not perform network IO and are not suitable for substantiating live system claims.
- Live/E2E benches will fail fast if the API is not reachable; ensure the stack is up and healthy (`/health` returns ok).
- Some large-scale scripts in `scale/` are designed for stress testing and may generate heavy load.

## Artifacts

- Many scripts write results under `benchmarks/` or `benchmarks/outputs/` (CSV, JSON, plots). See each script's usage for details.
