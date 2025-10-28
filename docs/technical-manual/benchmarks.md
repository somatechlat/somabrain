# Benchmarks

## Recall Latency Benchmark

A quick, repeatable benchmark to measure remember/recall latency percentiles against a running Somabrain API.

- API: defaults to http://127.0.0.1:9999 (override with `SOMA_API_URL`)
- Memory: expected at 9595 (as configured for dev/prod-like compose)

### How to run

```bash
# Optional: ensure the stack is running
make up-prod-like

# Run with defaults (N=200 remembers, Q=50 recalls, top_k=3)
make bench-recall

# Or customize
SOMA_API_URL=http://127.0.0.1:9999 BENCH_N=500 BENCH_Q=100 BENCH_TOPK=5 make bench-recall
```

### Output

Emits a single JSON object to stdout, for example:

```json
{
  "n_remember": 200,
  "n_recall": 50,
  "p50_remember_ms": 2.8,
  "p95_remember_ms": 5.6,
  "p50_recall_ms": 3.1,
  "p95_recall_ms": 6.2,
  "errors": 0
}
```

Persist results to a file and compare across commits or environments to track performance over time.
