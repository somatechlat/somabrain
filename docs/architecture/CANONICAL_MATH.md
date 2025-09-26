# SomaBrain Canonical Mathematics

This document captures the mathematical constructs underpinning SomaBrain. It defines the utility
function, memory representations, similarity metrics, audit and reward gating invariants, and the
cryptographic primitives used for constitutional governance. Each section references the modules
where the math is implemented or will be implemented during upcoming sprints.

## 1. Utility & Decision Theory

**Objective:** ensure each agent action delivers positive utility while respecting cost, latency, and
policy constraints.

- **Utility Function**: `U(r) = λ · log p(r) − μ · c(r) − ν · ℓ(r)`
  - `λ`, `μ`, `ν` are scalar weights stored in the constitution JSON.
  - `p(r)` is the model confidence (probability assigned to the response).
  - `c(r)` represents cost (e.g., tokens consumed, provider charges).
  - `ℓ(r)` represents latency or risk penalty.
  - Implemented in `somabrain/api/dependencies/utility_guard.py` (see `compute_utility`).
  - Negative utility triggers policy denial and increments Prometheus metrics
    (`soma_utility_negative_total`, `soma_utility_value`).

- **Parameter Updates:** Modelled as constrained optimization:
  - After each batch, adjust `(λ, μ, ν)` via gradient-free updates to maintain `U(r) > 0` target.
  - Future work (S8) will implement a projected gradient/descent mechanism ensuring constraints.

## 2. Memory & Embedding Mathematics

SomaBrain maintains a multi-tier memory system with vector, graph, and temporal dimensions.

- **Coordinate Derivation:** Keys hashed using BLAKE2b to produce deterministic 3D coordinates in
  `[-1, 1]^3` (see `_stable_coord` in `somabrain/memory_client.py`). The hash is BLAKE2b with
  12-byte digest, split into three 32-bit unsigned ints scaled to the target range.

- **Embedding Similarity:**
  - Current: cosine similarity on embedding vectors for retrieval (via vector store).
  - Planned enhancement (S8): geodesic metrics leveraging spherical embeddings to better model
    high-dimensional semantics.

- **Multi-View Attention Weights:** When constructing the context bundle the brain computes
  
  \[
  w_i = \operatorname{softmax}\left(\frac{\alpha\,\cos(q, m_i) + \beta\,g_i + \gamma\,d_i}{\tau}\right)
  \]

  where `cos` is semantic similarity, `g_i` is graph centrality (degree/PageRank), `d_i` is temporal
  decay, and `(α, β, γ, τ)` are adaptive parameters updated via online optimisation. The weights
  normalise across the top-K candidates so the fused residual stream mirrors transformer attention.

- **Hyperdimensional Encoding:** Quantum-inspired HRR operations in `somabrain/quantum.py` provide
  binding/unbinding, superposition, and deterministic text encodings using seeded Gaussian vectors.
  Core primitives:
  - `QuantumLayer.random_vector()` – unit-norm Gaussian vectors.
  - `QuantumLayer.bind(a, b)` – circular convolution via unitary FFT (see `somabrain/numerics.py`
    for `rfft_norm` / `irfft_norm`).
  - `QuantumLayer.unbind(a, b)` / `unbind_exact` – circular correlation with Tikhonov-style
    regularization using `compute_tiny_floor` and `spectral_floor_from_tiny`.
  - `QuantumLayer.make_unitary_role(token)` – generates unitary role vectors (|FFT| = 1) for
    lossless binding operations.
  - Tests in `tests/test_math_stability.py` guarantee HRR vectors stay finite and maintain non-zero
    norms across bind/unbind sequences.

- **Memory Graph:** Postgres adjacency matrix representing memory relationships. Graph algorithms
  (shortest path, degree centrality) assist in retrieval; future modules will compute PageRank or
  attention weights.

- **Integrity Checks:** Embedding checksum (SHA256) stored alongside each vector; background worker
  recalculates and alerts on mismatches.

## 3. Audit, Rewards, & Policy Invariants

- **Audit Events:** Each decision emits audit records with schema fields:
  `event_id`, `request_id`, `tenant_id`, `allowed`, `violated_article`, `constitution_sha`, etc.
  Schema enforced through JSON Schema/Avro in Kafka.

- **Reward Gating:** Reward is `1` only if governance allowed the action. Equivalent to enforcing
  `if audit.allowed(request_id) == False then reward(request_id) = 0`.
  - Implemented via Kafka consumer reading audit stream (S4).
  - Formalized in documentation as an invariant; future TLA+/Coq proofs ensure compliance.

## 4. Constitution Integrity & Cryptography

- **Checksums:** SHA3-512 applied to constitution JSON to produce stable version ID.
- **Signatures:** Ed25519 with threshold scheme (t-of-n) to require multiple operators for updates.
  Implementation in `somabrain/constitution/cloud.py` (S1).
- **Merkle Trees:** Optionally used for verifying constitution history; each snapshot appended to an
  append-only ledger stored in Postgres/Postgres.
- **Verification Metrics:** `somabrain_constitution_verified` gauge (1 when signatures validate).

## 5. Learning & Adaptation

- **Utility weight updates:** SomaBrain adjusts `θ = (λ, μ, ν)` using an online convex optimisation
  step and stores every update in Postgres (`learning_weights` table) for auditability:

  \[
  θ_{t+1} = \Pi_{\mathcal{C}}(θ_t - η_t \, \hat{\nabla} L_t)
  \]

  where `Π` projects onto constraint set `𝒞` (non-negative weights, upper bounds), `η_t` is an
  adaptive learning rate, and `\hat{∇} L_t` is the estimated gradient from observed utility and
  feedback. Implementation target: `somabrain/learning/adaptation.py`.

- **Retrieval parameter tuning:** The multi-view weights `(α, β, γ, τ)` are updated via Thompson
  sampling/Bayesian bandits. Reward signals derive from agent feedback and audit outcomes; updates
  persist to Postgres and Redis, with guardrails enforced by the constitution (min/max bounds and
  rollback thresholds).

- **Working memory decay:** Redis-backed scratchpads apply exponential decay `s_t = γ s_{t-1} +
  (1-γ) x_t` ensuring bounded contribution from old context.

## 6. Memory Retrieval Analytics

Planned algorithms (S3+):
- **Latent Semantic Mapping:** maintain low rank approximation of memory embeddings for fast updates.
- **Graph-based retrieval:** blend vector similarity with graph centrality to select context.
- **Temporal weighting:** apply exponential decay to memory relevance.

## 7. Observability & Statistical Monitoring

- Use statistical process control (SPC) charts (EWMA, CUSUM) on metrics such as utility, audit
  fallback, and SLM latency.
- Anomaly detection triggers when metrics deviate beyond configured sigma thresholds.

## 8. Benchmarks & Performance Targets

- Latency quintiles (p50/p95/p99) tracked for governance, memory retrieval, and SLM inference.
- Throughput measured in requests/sec; load tests combine heavy-tailed distributions to simulate
  real usage.
- Benchmarks compare actual vs. predicted utility, memory consistency, and audit coverage.

## 9. Formal Verification Plans

- Constitution update process specified in TLA+ (S8) to ensure only threshold-signed updates are
  accepted.
- Reward gating modelled in Coq or another proof assistant to enforce the reward invariant.
- Integration with CI ensures proofs run before merge.

## 10. Advanced Memory & Transport Math (2025)

### 10.1 Density Matrix (ρ) Cleanup
- Maintains a PSD density matrix ρ as an EMA over filler outer products.
- Scoring:  \( s_k = \hat f^\top \rho f_k \), optionally mixed with cosine.
- Ensures better recall/calibration under superposition. See `memory/density.py`.

### 10.2 FRGO Transport Learning
- Updates edge conductances in the memory graph using batch flows:  \( C_e \leftarrow \mathrm{clip}(C_e + \eta(|Q_e|^{\alpha} - \lambda L_e C_e), C_{min}, C_{max}) \).
- Reduces global resistance, prunes unused edges, and adapts to usage. See `transport/flow_opt.py`.

### 10.3 Bridge Planning (Heat Kernel/Sinkhorn)
- Computes heat kernel  \( K=\exp(-\beta\mathcal{L}) \) and uses Sinkhorn scaling for probabilistic planning.
- Ranks candidates by bridge reach probability, supporting robust, short-time recommendations. See `transport/bridge.py`.

All new math is float64, clamped, and batched. Property-based tests and benchmarks validate invariants and performance.

## References
- Code references: `somabrain/constitution/`, `somabrain/api/dependencies/`,
  `somabrain/memory_client.py`, `somabrain/audit.py`.
- Roadmap references: `docs/architecture/CANONICAL_ROADMAP.md` (S1–S10 tasks).

Update this document whenever mathematical definitions change or new models are introduced.
