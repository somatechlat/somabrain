# Production Roadmap

This file is the canonical roadmap for Somabrain production readiness. It focuses on numerics hardening, observability, determinism, testing, benchmarking, and CI. The content below is derived directly from the source code and recent audit.

## Numerics Roadmap (consolidated)

Phases:

- P0 — Safety & reproducible baseline
  - Fix typing/call-site for `compute_tiny_floor`.
  - Add deterministic tests for role reproducibility, tiny->spectral conversion, and dtype boundary checks.
  - Acceptance: P0 tests pass locally.

- P1 — Numeric correctness & robust unbinds
  - Standardize spectral arithmetic: float64 power arrays, complex128 spectral numerators, denom in float64, NaN/Inf guards.
  - Centralize tiny->spectral conversion in `spectral_floor_from_tiny`.
  - Add tests for unbind strategies (SNR sweep) and unitary isometry.
  - Acceptance: tests pass and Wiener shows robustness at low SNR.

- P2 — Benchmarks & capacity experiments
  - Add `benchmarks/numerics_workbench.py` sweeping D, tiny_amp, SNR, seeds.
  - Produce JSON and PNG artifacts; record capacity N where cosine < 0.9.
  - Immediate experiments (recommended order):
    - Stress tests: small-D (D ∈ {128,256}), extreme SNRs (down to -30 dB), impulsive spectral nulls and correlated fillers to demonstrate clear failure modes for exact deconvolution and highlight where Wiener/Tikhonov helps.
      - Artifacts: JSON `benchmarks/results_numerics.json`, plots in `benchmarks/plots/` (e.g. `mse_D128.png`, `cosine_D128.png`).
      - Estimated runtime: 20–40 minutes (local venv), reproducible via `PYTHONPATH=. ./venv/bin/python benchmarks/numerics_workbench.py --stress`.
    - Capacity curve: measure recall cosine vs N (number of superposed items) for D ∈ {256,1024} and identify N where mean cosine < 0.9.
      - Artifacts: `benchmarks/workbench_numerics_results.json` and summary CSV/PNG.
      - Estimated runtime: 20–40 minutes.
    - Task demo (optional): small FastAPI demo or quick-start script (`examples/soma_quickstart.py`) that exercises binding/unbinding in a short pipeline and records numeric stability.
    - Run everything: full sweep combining stress + capacity + SNR sweep for publication-quality figures (longer run; 1–3 hours depending on seeds and D grid).

- P3 — Observability & telemetry
  - Add metrics: unbind.path_total, spectral_bins_clamped_total, eps_used histogram, reconstruction_cosine.
  - Add debug logs for robust fallback usage.

- P4 — Docs & reproducibility
  - Add `docs/source/numerics.rst` documenting tiny-floor, dtype policy, RNG seed guidance, strict_math behavior.
  - Ensure Sphinx builds.

- P5 — CI & pinning
  - Add CI to run lint, tests, docs build, bench smoke and pin numpy/pocketfft versions.

Notes:
- Keep `strict_math` as a configuration gate to preserve exact algebraic behavior for research.
- Use deterministic RNG (`np.random.default_rng(seed)`) for role/filler generation.


## Status & Next Steps
- P0: Implemented (typing fix + P0 tests added and passed).
 - P1: Numeric correctness & robust unbinds
   - Standardized spectral patterns partially enforced in `somabrain/quantum.py` for `unbind` and `unbind_exact`.
   - Centralized tiny->spectral conversion in `spectral_floor_from_tiny` (in `somabrain/numerics.py`).
   - Tests: SNR sweep and unbind strategy tests added and run for a focused set of cases.
   - Acceptance criteria: unit tests pass and a focused bench shows Wiener improves stability in stressed settings.

 - P2: Benchmarks & capacity experiments — In progress
   - Stress bench script and plotting helper added. Example artifacts present in `benchmarks/` (JSON + PNGs).
   - Next: run the stress-suite (D=128,256, extreme SNRs) and store canonical artifacts.

 - P3: Observability — Partial
   - Metric labels and counters were added in code paths but need final names, histograms, and bench sink wiring.

 - P4: Docs & reproducibility — Partial
   - Sphinx build smoke tested; add `docs/source/numerics.rst` and reproducibility how-to (commands to reproduce bench/plots).

 - P5: CI & pinning — Pending
   - Add GitHub Actions workflow for lint/test/docs/bench-smoke and pin numeric deps in `pyproject.toml`/`requirements-dev.txt`.

## Artifacts produced so far (local paths)
- `benchmarks/results_numerics.json` — extended bench results (SNR sweep)
- `benchmarks/workbench_numerics_results.json` — workbench runs (capacity-style experiments)
- `benchmarks/plots/` — PNGs: `cosine_D512.png`, `mse_D512.png`, `cosine_D1024.png`, `mse_D1024.png`
- Tests added: `tests/test_role_reproducible.py`, `tests/test_tiny_floor_power_conversion.py`, `tests/test_numerics_dtype_boundaries.py` (P0 acceptance tests)

## Next recommended actions (pick one)
1. Run stress bench (recommended): produces strong examples where Wiener helps. Command (local):

   PYTHONPATH=. ./venv/bin/python benchmarks/numerics_workbench.py --stress --out benchmarks/results_numerics.json

2. Run capacity curves: measure recall vs N and record N where mean cosine < 0.9.
3. Wire metrics sink and re-run bench to collect metrics JSON.
4. Add `docs/source/numerics.rst` and a short reproducibility section; rebuild Sphinx.

If you want, I can run option 1 (stress bench) now and commit the canonical artifacts and update the docs with a short how-to.

## RAG Roadmap (hybrid retrieval, graph, rerank)

Scope: strengthen first‑stage recall, improve precision via calibrated fusion and reranking, and make retrieval explainable with graph links — while keeping latency predictable.

- Retrieval backends
  - Add BM25 lexical retriever (replace naive lexical). Use `rank_bm25` locally; expose as `retriever=lexical`. File: `somabrain/services/retrievers.py`.
  - Qdrant adapter as optional vector backend (in addition to HTTP SFM). Add `memory_mode: qdrant` with client methods: `remember/recall/payloads_for_coords/link/k_hop`. File: `somabrain/memory_client.py`.
  - Keep SFM graph strengths and payloads‑by‑coords; allow mixed modes (vectors in Qdrant + graph in SFM) behind config.

- Fusion & calibration
  - Weighted RRF over retrievers with score normalization (z‑score or min–max per retriever) before fusion. File: `somabrain/services/rag_pipeline.py`.
  - Observability: per‑retriever latency/hit counts; fusion inputs/outputs; dedupe stats; trace IDs.

- Reranking
  - Optional cross‑encoder reranker (e.g., `bge-reranker-large`, `msmarco-MiniLM-L-6-v2`) over top‑N (50→10). Config gate `reranker_provider`, latency budget in ms. File: `somabrain/services/rag_pipeline.py`.
  - Keep HRR‑based rerank for low‑latency path; margin‑aware rerank when enabled.

- Graph RAG
  - Extract typed entity‑relation links on ingest/reflect; persist via `MemoryService.link` with types/weights. Files: `somabrain/services/memory_service.py`, `somabrain/semgraph.py`.
  - Retrieval: prefer `rag_session -> retrieved_with` traversal; fallback BFS with type filters and path‑aware scoring (hop penalty, edge weights, path frequency). File: `somabrain/services/retrievers.py`.

- Expansion
  - Multi‑query expansion: generate 3–5 paraphrases and fuse results (cap budget). File: `somabrain/services/rag_pipeline.py` (pre‑retrieval hook).
  - Document expansion (doc2query‑style) offline; store synthetic queries in payloads to benefit BM25.

- Evaluation
  - Add `benchmarks/rag_eval.py`: Recall@k, MRR, NDCG; latency P50/P95/P99 per stage; ablations by retriever/fusion/rerank. Persist JSON + plots under `benchmarks/`.

Latency targets (defaults): first‑stage recall ≤ 80 ms; rerank ≤ 120 ms; graph traversal bounded by `graph_hops`/`graph_limit`.

## HRR/Math Enhancements

- Adaptive Wiener floor
  - Estimate superposition count k and scale floor by k and mean spectral power; add colored‑noise‑aware whitening. File: `somabrain/quantum.py` (`unbind_wiener`).

- Exact/unitary rigor
  - Persist role spectra and checksums (disk cache); migration tool to precompute for seeds/tokens. Files: `somabrain/quantum.py`, `somabrain/spectral_cache.py`.
  - Strict‑math mode tests: epsilon budgets, determinism across machines; fail fast on contract violations.

- Capacity & robustness benches
  - Capacity curves (cosine vs k) for multiple D and dtypes; adversarial spectral nulls; 1/f exponents. Files: `benchmarks/*` (extend existing harnesses).

- Invariants & guards
  - Enforce norm‑preservation post‑ops; assert no NaN/Inf; unify tiny‑floor semantics across paths. File: `somabrain/numerics.py`.

## Operational Defaults (runtime)

- Ports and services
  - SomaBrain dev/prod: `9696` and `9797` (`scripts/start_somabrain_http.sh`).
  - SFM HTTP memory: `9595` (FastAPI `/health`, `/docs`).
  - Optional infra commonly used: Redis `6379`, Qdrant `6333`.
  - Configure SomaBrain → SFM via `SOMABRAIN_MEMORY_MODE=http` and `SOMABRAIN_HTTP__ENDPOINT=http://127.0.0.1:9595` or via `config.yaml`.

## Milestones

- M1 (1–2 weeks)
  - BM25 retriever; weighted RRF with normalization; per‑retriever metrics; initial RAG eval harness.

- M2 (2–3 weeks)
  - Cross‑encoder reranker; query/doc expansion; graph typed links + path scoring; publish RAG eval results.

- M3 (2–3 weeks)
  - Adaptive Wiener floor; capacity curves; spectral cache persistence; strict‑math tests; numerics report.

- Continuous
  - Qdrant adapter; caching/batching; dashboards (Prometheus/Grafana) with KPIs.
