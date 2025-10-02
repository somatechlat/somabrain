# SomaBrain — Math, Evaluation & Benchmark Plan

Last updated: 2025-09-27

This document is the canonical reference for the mathematics behind the core
algorithms used by SomaBrain (HRR, vector normalization, fusion/rerank), and a
practical, reproducible evaluation plan for correctness, learning-speed, RAG
accuracy, and performance benchmarking.

Use this file as the authoritative source for designing, running, and
interpreting the benchmarks defined in the `benchmarks/` directory.

## 1. Mathematical foundations

### 1.1 High-level primitives
- Vectors: floating point arrays of fixed dimension $D$ (see `somabrain.nano_profile.HRR_DIM`).
- Normalization: L2 normalization to unit norm (implemented by `normalize_array`).
- Tiny floor: amplitude floor returned by `compute_tiny_floor(D, dtype)` used to
  avoid division by zero and numeric instability in normalization and FFT-based
  transforms.

Notation:
- $x \in \mathbb{R}^D$ is a vector.
- $\|x\|_2 = \sqrt{\sum_i x_i^2}$ is the L2 norm.

### 1.2 Normalization invariant
Goal: after calling normalize_array(x), each normalized vector $\hat x$ should satisfy
$$\|\hat x\|_2 \approx 1$$
subject to numeric tiny-floor handling for near-zero vectors. The implementation:

1. computes energy $E = \sum_i x_i^2$ (float64 for stability),
2. computes denom $= \sqrt{E + tiny^2}$ where $tiny$ is amplitude floor,
3. returns $x / denom$ and applies deterministic baseline vectors for subtiny slices
   when needed.

This guarantees finite results and deterministic fallback behavior for subtiny norms.

### 1.3 HRR and spectral transforms
SomaBrain uses unitary real FFT (rfft/irfft with norm='ortho') via wrappers
`rfft_norm` and `irfft_norm`. Parseval's theorem and the unitary normalization
imply energy preservation across domains; when converting amplitude tiny floors
to spectral power floors, use
$$p_{floor} = \frac{tiny^2}{D}$$
as implemented in `spectral_floor_from_tiny`.

### 1.4 Retrieval, fusion, and rerank (as implemented)
- Retrieval returns candidate documents with retriever-specific raw scores $s_{r,i}$.
- Per-retriever normalization: compute mean $\mu_r$ and std $\sigma_r$ for scores,
  form z-scores: $z_{r,i} = (s_{r,i} - \mu_r)/\sigma_r$ (fallback to identity when \sigma=0).
- RRF-style fusion (weighted reciprocal rank): for a candidate with rank $rank_{r,i}$,
  contribution is $\alpha \cdot w_r \cdot \frac{1}{k + rank_{r,i}}$ plus
  $\beta \cdot w_r \cdot z_{r,i}$ when available. Constants in code: $k=60$, $\alpha=1.0$, $\beta=0.5$.

Rationale: RRF term ensures rank-safety (top candidates from any retriever get
credit) and the z-score term introduces magnitude information from retriever
scores. Retriever weights $w_r$ are configurable via runtime config (vector, wm, graph, lexical).

### 1.5 Reranking options
- `mmr`: Maximal Marginal Relevance implemented by `diversify_payloads` using
  embeddings and lambda parameter; measures diversity vs relevance tradeoff.
- `hrr`: HRR cosine-based rerank using quantum-like HRR encoding (if `quantum` present).
- `ce`: Cross-encoder reranking (sentence-transformers) or fallback cosine via embedder.

Tradeoffs:
- Cross-encoders are accurate but CPU-heavy (per candidate expensive). Use only on
  top-N candidates (configurable `reranker_top_n`) and batch size tuning is important.
- HRR-based rerank is numerically cheap but depends on HRR design choices and seed stability.

## 2. Evaluation goals & metrics

This project requires two orthogonal evaluation suites:

1. Correctness & learning evaluation (does the Brain learn and retrieve correct information?)
2. Performance evaluation (latency, throughput, resource cost)

Each test below includes the formal metric, the instrumentation to capture it,
and the statistical analysis recommended.

### 2.1 Correctness & learning metrics
- Precision@K: fraction of top-K results that are relevant.
- Recall@K: fraction of ground-truth relevant docs recovered in top-K.
- MRR (mean reciprocal rank): measures expected rank of first relevant result.
- nDCG@K: graded relevance ranking quality.

Learning-speed metric (primary experimental quantity):
- Setup: present a sequence of training items (memory writes) to the system.
- Metric: precision@1 and recall@K measured at checkpoints after N writes (e.g., N=10, 100, 1k, 10k).
- Plot: accuracy vs. number of training examples (learning curve). Fit an appropriate
  learning-rate model (e.g., power-law: accuracy(N) = a - b N^{-c}) to quantify learning speed.

Statistical rigor:
- Run each configuration with at least 5 independent seeds (randomization of data order,
  random embedding seeds) and report mean & 95% bootstrap confidence intervals.
- Use paired tests (paired t-test or Wilcoxon signed-rank for non-normal) when comparing
  two systems (baseline vs optimized) on per-query metrics.

### 2.2 RAG accuracy bench
- Create a dataset of queries with ground-truth relevant doc IDs (can be synthetic
  or human-annotated). For each query, compute precision@K, recall@K, MRR, nDCG.
- Aggregation: report macro averages and percentiles; for critical queries, report per-query results.

### 2.3 End-to-end performance
- Latency (p50/p90/p95/p99), throughput (RPS) under a workload mix representative of
  expected production traffic (read: retrieval-heavy; mix in writes/persists).
- Resource usage: CPU-seconds per request, memory footprint, DB latency and IOPS.
- Stress tests: step-load up to saturation and report knee point where p95 crosses SLA.

## 3. Test protocols (detailed)

All tests must be reproducible: scripts, seeds, and environment variables are recorded.

### 3.1 Learning-speed protocol (detailed)

1. Dataset: a collection of (key, payload) items — for synthetic tests use templated facts:
   e.g., "Author of Book X is Y" for 10k books.
2. Procedure:
   - Start from an empty backend (drop memory store / named volume) or reproducible snapshot.
   - For i in checkpoints (10, 100, 1k, 10k):
       * Write items 1..i using the same insertion API (HTTP /remember or memory client).
       * After a short stabilization delay (e.g., 1–5s, or until write pipeline processes), run the
         evaluation queries: the set of queries maps to items seen so far and a holdout set.
       * Record precision@1, recall@K, MRR for the seen items and holdout.
   - Repeat for 5 seeds (shuffle order, random payload variants) and compute mean & CI.

3. Hypothesis test:
   - Null: learning curve of optimized system equals baseline.
   - Use paired metric differences at each checkpoint; report p-values and effect sizes.

### 3.2 RAG precision@K protocol

1. Dataset: queries Q, each with a set of relevant doc IDs R_q.
2. Procedure:
   - For each query, call `/rag/retrieve` and record the returned candidate IDs.
   - Compute precision@K and recall@K.
   - Aggregate across queries; compute 95% bootstrap CI.

3. Reranker experiments:
   - Evaluate both pre-rerank and post-rerank: compute delta precision@1 and statistical significance.

### 3.3 End-to-end perf protocol

1. Warm-up: run 10–20% of target load for 5–10 minutes.
2. Steady-state run: run for at least 5 minutes; capture Prometheus metrics and process-level stats.
3. Spike tests: run sudden 10x burst and measure recovery.

Notes on environment:
- Record CPU, number of cores, memory, disk type (SSD/HDD), Docker host OS.
- For local testing use a single-node, reproducible Docker Compose; for scale runs, use a dedicated host or cloud instances with pinned CPUs.

### 3.4 Live cognition verification (strict real mode)

Goal: demonstrate that the deployed brain updates memory, feedback stores, and session history when driven through public endpoints.

1. Prepare connectivity via `kubectl port-forward`:
  - `somabrain-test` → `127.0.0.1:9797`
  - `somamemory` → `127.0.0.1:9595`
  - `sb-redis` → `127.0.0.1:6379`
  - `postgres` → `127.0.0.1:55432`
2. Export live endpoint variables (pytest skips automatically if any health probe fails):

  ```bash
  export SOMA_API_URL=http://127.0.0.1:9797
  export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
  export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
  export SOMABRAIN_POSTGRES_LOCAL_PORT=55432
  ```

3. Execute the cognition suite:

  ```bash
  pytest -vv tests/test_cognition_learning.py
  ```

Success criteria:
- Memory `/health` reports an increased `items` count after `/remember`, and `/recall` returns at least one entry.
- `/context/feedback` writes rows into `feedback_events` and `token_usage` in Postgres (validated via SQL queries inside the test).
- Session `working_memory` lengths grow monotonically across repeated evaluate/feedback cycles.

If any assertion fails, re-check the forwards (`pgrep -fl "kubectl.*port-forward"`), inspect `/tmp/pf-*.log`, and only rerun once each `/health` endpoint returns `{"ok": true}`.

## 4. Numerics correctness & tests

Tests to assert invariants (implement as unit tests / property tests):

1. Normalization stability
   - Property: for random input vectors x, normalized y = normalize_array(x) satisfies |\|y\|_2 - 1| < 1e-6 for non-subtiny inputs.
   - For subtiny inputs (zero or near-zero), ensure result is finite, deterministic, and not NaN.

2. Tiny-floor rounding invariants
   - For D in {64, 256, 1024}, dtype float32/float64, compute tiny via compute_tiny_floor and assert tiny >= machine epsilon lower bounds and tiny > 0.

3. HRR spectral conversions
   - Round-trip rfft->irfft reproduces origin vector up to numeric tolerance under unitary norm.

## 5. Sample-size guidance

For per-query binary metrics (precision@K), determining required number of queries to estimate a difference:

- Use standard binomial sample-size approximations. For baseline precision p0 and desired detectable difference d at power=0.8 and alpha=0.05, compute n using normal approximation:
  $$n \approx \frac{(Z_{1-\alpha/2}\sqrt{2p(1-p)} + Z_{power}\sqrt{p_0(1-p_0)+p_1(1-p_1)})^2}{d^2}$$
  where p=(p0+p1)/2. In practice, run at least 200–1000 queries for stable precision estimates.

For learning curves: run multiple randomized seeds (≥5) to estimate variance and compute bootstrap CIs.

## 6. Concrete artifacts to implement (immediate)

I will implement the following project artifacts (next steps):

1. Seeder script: `scripts/seed_bench_data.py` — reproducible data seeding into the memory backend (supports HTTP or direct memory client modes).
2. Extended instrumentation: stage-level Prometheus histograms added to `somabrain/services/rag_pipeline.py` (labels: namespace, stage), and expose metrics if needed.
3. Benchmark harness enhancements: add support for varied query templates, warm-up, and CSV/JSON outputs.
4. Report generator: small script to aggregate results, compute precision@K, MRR, nDCG, and produce plots (requires matplotlib optional dependency).

## 7. Reporting format

All benchmark runs will produce a JSON artifact with fields:

```
{
  "run_id": "2025-09-27T...",
  "env": { "cpu": 8, "mem_gb": 32, "docker_compose": "Docker_Canonical.yml", ...},
  "benchmarks": {
     "http": { "p50": ..., "p95": ..., "requests": ..., "errors": ...},
     "learning_curve": [{"n":10,"precision@1":...}, ...]
  },
  "profiles": { "py_spy": "profile.svg" }
}
```

These artifacts will be archived under `artifacts/benchmarks/` by default.

## 8. Prioritized immediate actions (short sprint)

1. Implement seeder script and run the Learning-speed & RAG precision@K tests on a small dataset (1k items) to validate harness.
2. Add stage-level histograms in `rag_pipeline.py` (if not already present) and confirm Prometheus scrape exposes them.
3. Run worker-bench and http-bench under warm-up + steady-state and collect baseline artifacts.
4. Analyze profiler output and propose top-3 code fixes (numerics vectorization, DB pooling, reranker batching).

## 9. Contact & provenance

This document was generated and added to the repository by the development assistant as the canonical plan for evaluation and benchmarking. If you want I can now:

- Implement the seeder (`scripts/seed_bench_data.py`) and run the first two tests (learning-speed and RAG precision@K) against the dev stack and upload the raw JSON artifacts.
- Or implement Postgres/SQLAlchemy engine tuning and show DB benchmark before/after.

Tell me which of the two immediate actions to perform now and I will start implementing and running them.
