# Benchmarks Quickstart

This guide shows how to run SomaBrain’s benchmarks locally in “developer prod” with real backends, plus a tiny CI smoke.

## Prerequisites

- Stack up and healthy. Confirm the API port:
  - Fixed profile: http://127.0.0.1:9999
  - Dynamic/dev profile: http://127.0.0.1:9696
- External memory backend reachable at http://127.0.0.1:9595 (containers use host.docker.internal)
- Python 3.11 with project deps installed:

```
python -m pip install -U pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Live/E2E benches

- Recall latency (prints JSON p50/p95):

```
SOMA_API_URL=http://127.0.0.1:9696 BENCH_N=200 BENCH_Q=50 BENCH_TOPK=3 \
python benchmarks/recall_latency_bench.py
```

- Live recall (writes JSON artifact):

```
python benchmarks/recall_live_bench.py \
  --api-url http://127.0.0.1:9696 \
  --output benchmarks/outputs/recall_live_results.json
```

- Generic HTTP harness (latency percentiles):

```
python benchmarks/http_bench.py --url http://127.0.0.1:9696/recall --concurrency 8 --requests 200
```

- Multi-pass runner (artifacts + plots + metrics deltas):

```
python benchmarks/run_live_benchmarks.py \
  --recall-api-url http://127.0.0.1:9696 \
  --start 100 --end 1000 --passes 5 --q 50 --topk 3 \
  --out-dir benchmarks/outputs/live_runs
```

Artifacts land under `benchmarks/outputs/` with JSON summaries and plots. If matplotlib isn’t installed, plots are skipped gracefully.

## Micro/algorithmic benches

- Cognition core (quality and latency gates):

```
PYTHONPATH=. python benchmarks/cognition_core_bench.py --dim 8192 --dtype float32
```

- Diffusion predictors (Chebyshev/Lanczos; accuracy/runtime sweeps):

```
python benchmarks/diffusion_predictor_bench.py
```

- FD sketch, nulling, colored noise, capacity curves:

```
python benchmarks/fd_benchmark.py
python benchmarks/nulling_bench.py --out benchmarks/nulling_results.json
python benchmarks/colored_noise_bench.py --out benchmarks/colored_noise_results.json
python benchmarks/capacity_curves.py
```

## Tips

- Ports vary by profile. Prefer 9696 unless you intentionally run the 9999 profile. Verify with `/health`.
- Hit-rate depends on payload fields. Using `content` in addition to `task` generally improves retrieval quality for live benches.
- Persistence effects may need a short delay (~0.5–1.0s) for the external indexer to catch up.
- Evidence of “no mocks”: use `benchmarks/run_live_benchmarks.py` to capture `/metrics` deltas for /remember and /recall and health snapshots.

## Where results go

- `benchmarks/outputs/recall_latency.json`
- `benchmarks/outputs/recall_live_results.json`
- `benchmarks/outputs/live_runs/<timestamp>/*` (summaries, plots, metrics_deltas.json, report.md)