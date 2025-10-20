SomaBrain — MUVERA‑style FDE (Single‑Vector Retrieval)

Goal
- Compress multi‑vector (chunk/token) late‑interaction scoring into a single fixed‑dimensional embedding (FDE) per document/query.
- Preserve MaxSim/attention scores while enabling fast MIPS on one vector.

Approach
- Train a small pooling head (gated‑max or attention) to distill the multi‑vector scorer into an FDE.
- Optimize with a ranking loss that matches teacher scores (e.g., margin NLL on MaxSim scores).
- Deploy FDE in ANN index (IMI→HNSW with OPQ/PQ), keep the multi‑vector scorer as an optional reranker on small margins.

Config (placeholders)
- `SOMABRAIN_FDE_ENABLED` (bool): prefer FDE provider in embedding pipeline.
- `SOMABRAIN_FDE_POOLING` (gated_max|attention): pooling head type.
- `SOMABRAIN_FDE_MARGIN_THRESHOLD` (float): trigger multi‑vector rerank only when ANN margins are small.

Implementation Notes
- In this repo, the embedding provider API and JL projection are in place. A future provider can load a trained FDE model.
- Keep stubs fast: default providers remain tiny/hrr; FDE toggles are no‑ops until a model is wired.
- Reranking should only trigger on ambiguous queries (small top‑k margins) to control latency.

Benchmarks
- Target: within 1–2% recall@k of the multi‑vector teacher with 2–5× speedup vs multi‑vector.

