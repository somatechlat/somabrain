# Benchmark Runbook (Live + Micro)

This runbook explains how to run SomaBrain benchmarks end-to-end (live, real IO) and micro/numerics (no IO), where the artifacts go, and how to interpret results.

## Profiles

- Live/E2E (real HTTP/DB/Kafka):
  - `benchmarks/recall_latency_bench.py` — Remember + recall latency percentiles against a running API.
  - `benchmarks/rag_live_bench.py` — Seeds corpus, queries `/rag/retrieve`, computes hit-rate@k, scrapes `/metrics`.
  - `benchmarks/http_bench.py` — Async HTTP harness for any endpoint to get latency percentiles.
  - `benchmarks/db_bench.py` — Direct DB throughput sanity via SQLAlchemy.
  - `benchmarks/scale/*` — Load/soak/spike, chaos experiments.
  - `benchmarks/showcase_suite.py` — Composable suite; supports `--dry-run` for CI.

- Micro / Numerics (no IO):
  - `benchmarks/cognition_core_bench.py` — Core numerics. Writes CSV + plots.
  - `benchmarks/worker_bench.py` — Synthetic pipeline (NOT E2E, no network IO).

See also: `benchmarks/README.md` for a quick map.

## Prerequisites

- A live stack running, with at least one API endpoint reachable:
  - Recall/Memory API (default): `http://127.0.0.1:9999`
  - RAG API (alt): `http://127.0.0.1:9696` (if not available, use `9999` for RAG as well)
- Optional: `matplotlib` for plots.

Health check:

```sh
curl -s http://127.0.0.1:9999/health | jq .ok
```

## Orchestrated live passes

Use the helper to run multiple passes and produce plots to a timestamped folder:

```sh
PYTHONPATH=. python benchmarks/run_live_benchmarks.py \
  --recall-api-url http://127.0.0.1:9999 \
  --rag-api-url http://127.0.0.1:9999 \
  --start 100 --end 1000 --passes 5 \
  --q 50 --topk 3 \
  --out-dir benchmarks/outputs/live_runs
```

Outputs will be created under `benchmarks/outputs/live_runs/<timestamp>/`, including:
- Per-pass recall JSON summaries: `recall_N<value>.json`
- RAG live results JSON: `rag_live_results.json`
- Plots: `remember_latency_vs_N.png`, `recall_latency_vs_N.png`
- `provenance.json`

Notes:
- If RAG API on `:9696` is unavailable, `:9999` is typically fine (same service profile in dev).
- If plots are missing, install matplotlib: `pip install matplotlib`.

## Manual runs (alternatives)

- Recall latency only:
```sh
SOMA_API_URL=http://127.0.0.1:9999 BENCH_N=300 BENCH_Q=50 BENCH_TOPK=3 \
  PYTHONPATH=. python benchmarks/recall_latency_bench.py | tee recall_300.json
```

- RAG live bench:
```sh
SOMABRAIN_API_URL=http://127.0.0.1:9999 \
  PYTHONPATH=. python benchmarks/rag_live_bench.py --output benchmarks/outputs/rag_live_results.json
```

## Troubleshooting

- Health returns false or curl fails: ensure Docker Compose stack is up; check `docker compose ps` and service logs.
- High error rates in recall: check `kafka_ok` and `postgres_ok` in `/health` and ensure migrations are applied.
- Plots missing: ensure `matplotlib` is installed and that the script sets an offscreen backend (Agg) if running headless.
- Artifacts location: always under `benchmarks/outputs/…`; each orchestration run uses a new timestamped folder.
