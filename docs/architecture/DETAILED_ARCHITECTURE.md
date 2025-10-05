## 11. Math Brain: Core Mathematical Functions (Code Reality)

This version reflects only what exists in the current codebase. Planned or aspirational items are explicitly marked.

### 11.1 Vector Embedding & Normalization
- Embedding Generation (Implemented): `QuantumLayer.encode_text` creates deterministic Gaussian unit vectors. Default dimension from config (`cfg.hrr_dim`, typically 2048). 8192 is supported but not a hard-coded canonical size.
- Normalization (Implemented): `normalize_array` (robust mode) enforces unit norm; padding/truncation only occurs in its compatibility path. No global auto-padding layer.

### 11.2 Similarity & Retrieval
- Cosine Similarity (Implemented): `QuantumLayer.cosine` and builder helpers handle zero norms by returning 0.
- Recall Weighting (Implemented): Softmax weighting over combined semantic cosine + optional `graph_score` + temporal decay (`ContextBuilder._compute_weights`). No separate recall probability function.
- Composite Recall Ranking (Implemented): `/recall` applies a zero-config scoring blend that combines lexical token overlap, working-memory reinforcement, `quality_score` weighting, recency decay, and math-domain detection. Enabled by default via `lexical_boost_enabled` in `config.yaml`; disabling the flag reverts to backend ordering.

### 11.3 Hyperdimensional Computing (HRR / QuantumLayer)
- Superposition (Implemented): Summation + renorm.
- Binding (Implemented): FFT circular convolution (`QuantumLayer.bind`).
- Unbinding (Implemented): `unbind`, `unbind_exact`, `unbind_exact_unitary`, and `unbind_wiener` paths.
- Permutation (Implemented): Fixed permutation and inverse (`permute`).
- Cleanup (Partial): `cleanup` scores anchors by cosine; optionally mixes density matrix score. No persistent NN index.
- Invertibility: Approximate (unitary role roundtrips), not strict algebraic for arbitrary vectors.

### 11.4 Utility, Reward, Adaptation
- Utility Scoring (Simplified): Candidate scoring combines context gain, length penalty, memory count penalty (see `context/planner.py`). No log-prob form.
- Adaptation (Implemented): `AdaptationEngine` updates `(lambda_, mu, nu, alpha, gamma)` with rollback & constraints. Beta and tau not updated.
- Constraints (Implemented): `_constrain` + `UtilityWeights.clamp` enforce bounds.

### 11.5 Invariants & Consistency
- Unit Norm (Best‑Effort): Applied after most quantum operations; external vectors assumed correct.
- Dimension (Config-Driven): No enforced canonical 8192; dimension set by runtime config. Only `normalize_array` compat path pads/truncates.
- Robustness: Tiny-floor logic, NaN guards, spectral regularization present.

### 11.6 Testing & Validation
- Unit Tests: Density matrix, Sinkhorn, bridge, hybrid quantum, adaptation.
- Property-Based Tests: Planned (none active).
- Benchmarks: Scripts under `benchmarks/`; not automated gates.

### 11.7 Density Matrix Cleanup
- Implementation: `memory/density.py` + optional use in `QuantumLayer.cleanup`.
- Tests: PSD and trace=1 assertions only.

### 11.8 Bridge / Transport Primitives
- Heat Kernel / Bridge: `transport/bridge.py` (Schrödinger bridge + expm multiply).
- Sinkhorn: `somabrain/math/sinkhorn.py`; embedding bridge helper in `somabrain/math/bridge.py`.
- Duplication: Two bridge-style modules; consolidation recommended.

### 11.9 Planned (Not Implemented)
- FRGO transport learning (conductance updates).
- Memory integrity reconciliation worker (cross-store drift).
- Sparse memory ops.
- Dynamic memory allocation.
- Property-based invariants.
- Audit JSON schema validation.

---
## 1. Service Topology (Code Reality)
- Brain API: `somabrain/app.py`.
- Memory Service: External HTTP service only (default port 9595). The brain keeps a small in‑process mirror for read-your-writes visibility, persists failures to an outbox, and now mirrors every link operation through both sync `link()` and async `alink()` helpers so FastAPI handlers stay non-blocking. There is still no full local memory backend.
- OPA: Optional middleware; full Rego policies not bundled.
- Background Workers: Outbox + circuit breaker loop only.
- Constitution Engine: `somabrain/constitution/__init__.py` (no `cloud.py`). Multi-sig verify partial.

## 2. Data & Messaging
- Kafka: Optional. Audit producer falls back to JSONL. No schema enforcement.
- Redis / Postgres / Vector store: Referenced via adapters; some external infra assumed.

## 3. Request Lifecycle Adjustments
- Audit: No runtime schema validation despite earlier claims.
- Context: `ContextBuilder` combines embeddings + supplied metadata (graph scores external).
- Reasoning: Lightweight prompt candidate ranking, not iterative planning.

## 4. Data Model Notes
| Domain | Current Implementation | Gaps |
|--------|------------------------|------|
| Audit events | Kafka/JSONL producer | No schema validation |
| Constitution | Redis load + checksum + optional signatures | Rotation & threshold workflows minimal |
| Memories | Multi-tenant memory pool | No reconciliation worker |
| Token usage | Referenced in code | Schema/detail not reviewed here |

## 5. Scaling / Ops
Conceptual scaling strategies; autoscaling logic resides outside repo (Kubernetes/IaC assumed).

## 6. Security & Identity
Basic auth & middleware; SPIFFE/Vault integration placeholders (config-driven, not enforced pipeline).

## 7. Configuration
`load_config` + optional truth budget merging. Feature flags: `hybrid_math_enabled`, etc.

## 8. Testing & Benchmarks
Math & adaptation unit tests present; lacks coverage for FRGO (nonexistent) and integrity worker (nonexistent).
- **Chaos tests** – orchestrated via chaos tooling; must confirm auto-recovery and state
  correctness.
- **Metrics exposure** – Prometheus endpoints remain available for scraping, but no bundled UI or dashboard assets are shipped with SomaBrain.

## 9. Future / Roadmap (Explicitly Unimplemented)
- FRGO conductance updates
- Integrity reconciliation worker
- Differential privacy / k-anonymity
- Formal verification pipeline
- Calibration metrics (effective resistance, Brier/ECE)

## 10. Immediate Code-Focused Improvements
1. Add JSON schema validation for audit events (fail-open).
2. Introduce property-based tests for norms, invertibility, determinism, permutation group property.
3. Consolidate bridge modules (single canonical API + compatibility wrapper).
4. Create FRGO transport stub defining conductance update interface.
5. Implement integrity worker skeleton (consume memory events, log drift).
6. Replace placeholder reconstruction metric zero with actual cosine in unbinding paths.
7. Provide fallback/placeholder graph centrality computation if metadata lacks `graph_score`.
8. Add deterministic embedding & permutation invertibility tests.

This document intentionally matches current code state; update only after code changes land.

### 1.1 Control Plane
- **Envoy Ingress** – terminates mTLS, enforces WAF/rate limits, authenticates JWT/OIDC tokens.
- **Brain API (FastAPI/uvicorn)** – primary entry point; exposes REST/gRPC endpoints for agent
  requests, memory operations, and health checks. Auto-discovers host ports via `scripts/dev_up.sh`
  during local deploys and via config maps in production.
- **Memory Service** – External HTTP service on port 9595 (see `tests/support/memory_service.py`). No in‑process fallback backend; the brain keeps a process‑global mirror (for read‑your‑writes) and an outbox to replay queued writes if the service is temporarily unavailable.
- **OPA Stub Service** – Simple allow-all policy service on port 8181 (see `tests/support/opa_stub.py`). **[Note: Full Rego policy engine not yet implemented]**
- **Background Workers** – Outbox processing and circuit-breaker recovery via `start_background_workers()` in app.py
- **Constitution Engine** – `somabrain/constitution/cloud.py` orchestrates reads/writes to managed
  Redis (primary), Postgres (history), and object storage (immutable snapshots). Threshold signature
  verification happens here.

### 1.2 Data & Messaging Plane
- **Kafka/KRaft Cluster** – 3–5 brokers, TLS/SASL enabled. Topics:
  - `soma.audit` (immutable, replicate=3)
  - `soma.constitution.revisions` (immutable)
  - `soma.memory.events` (source-of-truth for memory operations)
  - `soma.telemetry` (high-volume metrics/trace exports)
- **Redis Cluster** – in-memory cache for constitution hot copy, hot memories, rate limiting, and
  audit buffer.
- **Postgres HA** – stores constitution metadata, token ledgers, tenant config, reward records, graph
  adjacency, and time-series metrics (Timescale extension).
- **Vector Store (Qdrant or PGVector)** – sharded, replicated vector search for memory embeddings.
- **Object Storage (S3/GCS)** – stores signed constitution snapshots, audit archives, benchmark
  outputs, and release artefacts.

### 1.3 Compute & Memory Pipeline
- **Agent SLM clients (external)** – agents (and test harnesses) run their own SLM inference
  stacks. SomaBrain prepares the governed context bundles and metrics those agents need. The
  repository retains lightweight client shims and contract tests but does not run inference
  workloads itself.
- **Memory Integrity Worker** – background service consuming `soma.memory.events`, verifying that
  Redis/Qdrant/Postgres remain in sync.
- **Reward Gate Worker** – Kafka consumer that correlates audit outcomes with agent reward signals.
- **Benchmark & Chaos Runners** – scheduled workloads that stress-test throughput and failure modes.
- **Working Memory Cache** – Redis-backed ring buffer retaining per-conversation scratchpads so the
  agent receives a bounded "residual stream" analogue alongside curated memories.

## 2. LLM/SLM Abstraction Layer

SomaBrain emulates core LLM functions while remaining a lightweight orchestrator:

- **Representation Fusion** – `somabrain/context/state.py` maintains HRR-compressed embeddings,
  graph metadata, and governance scalars that together form an LLM-like latent state.
- **Multi-View Attention** – `somabrain/context/builder.py` computes retrieval weights across
  semantic similarity, graph centrality, and temporal decay, mirroring transformer heads.
- **Reasoning Loop** – `somabrain/planner.py` generates prompt hypotheses, evaluates utility, and
  returns the optimal plan for agent-side SLM execution.
- **Adaptive Parameters** – `somabrain/learning/adaptation.py` performs online convex optimisation on
  utility/retrieval weights and records updates in Postgres/Redis so the brain fine-tunes itself
  without touching model weights.
- **Evaluate/Feedback API** – `/context/evaluate` and `/context/feedback` expose the orchestrated
  bundle and collect agent outcomes. Feedback persists to Postgres (`feedback_events`,
  `token_usage`) and streams audit entries (`context.feedback`) for compliance.
- **Governance Coupling** – policy outputs from `somabrain/constitution` inject penalties and tags
  into every bundle, guaranteeing constitutional compliance at scale.

## 3. Request Lifecycle

1. **Ingress** – Agent sends request with signed headers. Envoy validates cert/JWT and sleeps the
   request only if thresholds are exceeded.
2. **Governance** – FastAPI handler loads constitution (cached in Redis) and verifies latest
  signature. OPA evaluated; decision and metadata captured. Readiness in `/health` reflects OPA posture via `opa_ok` (boolean) and `opa_required` (boolean). Setting `SOMA_OPA_FAIL_CLOSED=1` gates readiness on OPA.
3. **Audit** – `somabrain/audit.publish_event` produces a transactional record to Kafka with schema
   validation, capturing constitution hash, signature, request metadata, and trace ID. Redis Stream
   fallback buffers events if Kafka unreachable.
4. **Context Synthesis** – `somabrain/context/builder` fuses redis hot state, vector store results,
   and graph neighbours, producing weighted memories plus an HRR-compressed residual stream.
5. **Reasoning Loop** – `somabrain/planner` generates and scores prompt variants using the utility
   function; the best-ranked plan is attached to the response. No SLM inference happens inside the
   brain.
6. **Response** – Brain returns a `ContextBundle` (memories, residual vector, recommended prompt,
   governance directives) with trace/audit IDs for the agent to consume when calling its SLM.
7. **Feedback & Learning** – Agent invokes `/feedback` with results; SomaBrain records audit events,
   updates memory salience, and adjusts utility/retrieval weights via online optimisation.
8. **Observability** – Traces, metrics, and logs shipped to OTEL collector and stored in Prometheus/
   Loki/Tempo for dashboards and alerting.

### 3.1 Memory Retrieval Endpoints (Current API)

- `POST /recall` – Semantic retrieval. Accepts `{query, top_k, universe?}` and returns working‑memory hits and long‑term memory payloads. Multi‑tenant via `X-Tenant-ID`.
- `POST /link` – Graph edge creation accepts coordinates or keys. The router calls `MemoryService.alink`, which delegates to the async HTTP client and still mirrors edges into the local graph cache so stubs and tests observe fresh links immediately.

## 4. Data Models & Storage

| Data Domain | Storage | Notes |
|-------------|---------|-------|
| Constitution documents | Redis JSON (active), Postgres (`constitution_versions`), S3 (`constitution/` bucket) | Stored with SHA3-512 hash, Ed25519 signatures, rotation metadata. |
| Audit events | Kafka topic `soma.audit` (immutable), S3 mirror | Enforced schema (`audit_event_v2.json`), includes trace ID, constitution hash, request metadata, decision. |
| Memories | Redis (`mem:<tenant>:<key>`), Qdrant vectors (`vector_id`), Postgres adjacency (`memory_edges`, `memory_payloads`) | All writes emit Kafka events with checksums; background worker reconciles discrepancies. |
| Token ledger | Postgres table (`token_usage`) | Aggregated per tenant, model, day. Snapshots to S3 daily. |
| Metrics & traces | Prometheus, Tempo, Loki via OTEL collector | Exported metrics include agent-side SLM latency (reported via feedback), audit fallback, constitution verification, cache hit rates. |

## 5. Scaling Strategies

- **API layer** – Horizontal Pod Autoscaler (CPU + queue length). Stateless pods capped by rate
  limiters in Redis to prevent noisy-neighbour tenants.
- **Kafka** – Partition topics to balance load; enable tiered storage if retention requirements grow.
- **Redis** – Use cluster mode with hash slots; for global deployments add geo-replicated read-only
  replicas.
- **Postgres** – Managed service with synchronous replicas for HA, read replicas for analytics,
  and Timescale compression for telemetry.
- **Vector store** – Partition by tenant/universe; replicate across AZs; incremental backups.

## 6. Security & Identity

- **Identity** – SPIFFE/SPIRE issues workload certificates; enforced by Envoy and services.
- **Secrets** – Vault or cloud secret manager rotates credentials; secrets injected via CSI driver.
- **API auth** – Bearer/JWT tokens validated with optional HS/RS keys; default tenant allowlist enforced on Evaluate/Feedback routes.
- **Network Policies** – Kubernetes policies restrict pod-to-pod traffic; service meshes (e.g., Istio
  or Linkerd) optional for additional policy enforcement.
- **Auditability** – Audit topic + object storage snapshots + Postgres indexes ensure every action is
  traceable. Alerts fire on audit fallback or schema violations.

## 7. Configuration Management

- All runtime configuration flows through environment variables documented in
  `docs/CONFIGURATION.md`. Sensitive overrides supplied by secret store.
- `scripts/dev_up.sh` inspects the host for occupied ports and writes `.env.local` and `ports.json`
  so developers and tests can target the correct addresses.
- Kubernetes deployments source config from ConfigMaps/Secrets generated by IaC.

## 8. Testing & Benchmarks

- **Unit tests** – run on every PR; focus on constitution, memory math, audit schema.
- **Integration tests** – executed against canonical compose stack in CI (`pytest -m integration`).
- **Load & benchmark tests** – `benchmarks/scale/` scripts produce RL throughput, latency, and
  resource usage metrics; results stored in object storage and compared against SLOs.
- **Chaos tests** – orchestrated via chaos tooling; must confirm auto-recovery and state
  correctness.
- **Metrics exposure** – Prometheus endpoints remain available for scraping, but no bundled UI or dashboard assets are shipped with SomaBrain.

## 9. Deployment & Operations

- **CI/CD** – GitHub Actions pipelines lint, test, build Docker images, apply Terraform/Helm (via
  Argo CD or Flux). Releases require manual approval once health checks pass.
- **Release Strategy** – Blue/Green or canary depending on environment; automated rollback triggers
  when error rate > 1% or SLO breached for 5 minutes.
- **Runbooks** – Maintained alongside this file (see `docs/DEVELOPMENT_SETUP.md` and upcoming
  `ops/runbooks/`). Each critical component has a playbook.

## 10. Future Extensions

- Multi-region active/active deployments with global load balancing.
- Differential privacy and k-anonymity layers for sensitive memory payloads.
- Formal verification for end-to-end pipelines (beyond constitution & reward gate).

## 11. Upgrades & Enhancements

### 11.1 Core Math Enhancements (2023)
- **Robust Division:** Improved handling of zero and near-zero norms in `unbind` via additive
  smoothing.
- **Tikhonov Regularization:** Added to unbinding for improved noise robustness.
- **Inverse Binding Cleanup:** Enhanced with iterative refinement and outlier rejection.

### 11.2 Memory & Transport Upgrades (2024)
- **Sparse Memory Support:** Efficient handling of sparse vectors in HRR operations.
- **Transport Layer Security:** End-to-end encryption and authentication for memory transport.
- **Dynamic Memory Allocation:** On-the-fly adjustment of memory resources based on load.

### 11.3 Density Matrix (ρ) Cleanup & Scoring (2025)
- **Purpose:** Improves recall and calibration under high superposition by maintaining a second-order memory (density matrix) over filler vectors.
- **Update:**
  - ρ is updated as an EMA over outer products of fillers:  \( \rho \leftarrow (1-\lambda)\,\rho + \lambda\sum_j w_j f_j f_j^\top \), then projected to PSD and normalized to trace 1.
  - Candidates are scored by \( s_k = \hat f^\top \rho f_k \), optionally mixed with cosine.
- **Implementation:** See `memory/density.py` (root directory) and `QuantumLayer.cleanup` in `somabrain/quantum.py`.
- **Testing:** Property-based tests ensure PSD, trace=1, and recall improvement in `tests/test_*density*.py`.

### 11.4 FRGO Transport Learning (2025)
- **Purpose:** Learns efficient, robust memory graph transport by updating edge conductances based on batch flows.
- **Update:**
  - After each batch, solve Kirchhoff flows and update conductances:  \( C_e \leftarrow \mathrm{clip}(C_e + \eta(|Q_e|^{\alpha} - \lambda L_e C_e), C_{min}, C_{max}) \).
- **Implementation:** See `somabrain/math/graph_heat.py` and adaptation engine batch step. **[Note: Full FRGO transport not yet implemented]**
- **Testing:** Tests check effective resistance, cost, and robustness in `tests/test_*transport*.py`.

### 11.5 Bridge Planning (Heat Kernel/Sinkhorn) (2025)
- **Purpose:** Probabilistic planning and recommendation using sum-over-paths (heat kernel) and Sinkhorn scaling.
- **Update:**
  - Compute heat kernel \( K=\exp(-\beta\mathcal{L}) \) and use Sinkhorn scaling to get node marginals and reach probabilities.
- **Implementation:** See `somabrain/math/bridge.py` and `somabrain/math/sinkhorn.py`.
- **Testing:** Tests validate reachability, calibration, and detour rates in `tests/test_*bridge*.py`.

### 11.6 Invariants & Monitoring
- All new math is float64, clamped, and batched for stability.
- Monitored metrics: effective resistance, ρ trace, recall, calibration (Brier/ECE).

---

**See also:**
- `docs/CONFIGURATION.md` for runtime toggles and integration notes.
- `tests/test_*density*.py`, `tests/test_*sinkhorn*.py`, `tests/test_*bridge*.py` for property-based and regression tests.
- `somabrain/math/` directory for actual mathematical implementations.
- `memory/density.py` (root level) for density matrix operations.

This document is living; update it whenever architecture decisions are made or components change.

## 12. Recent Infrastructure Updates (2025)

- **Full dev stack restart**: `scripts/dev_up.sh` now builds and starts the complete Docker compose stack (Somabrain API, Redis, Kafka, Prometheus, Postgres, external memory service, OPA stub). It writes `.env.local` and `ports.json` for test harnesses and waits for `/health` before completing.
- **Python environment**: The project now uses **uv** for dependency management and command execution (`uv pip install -e .[dev]`, `uv run ruff`, `uv run black`, `uv run pytest`). This speeds up installs and ensures reproducible builds.
- **CI workflow**: `.github/workflows/ci.yml` has been modernised to run on **Python 3.13**, install dependencies with `uv`, execute linting (`ruff`), formatting (`black`), the full test suite (`pytest`), build the Docker image, and perform a health‑check smoke test against the running container.
- **Docstring coverage**: Comprehensive one‑line and parameter docstrings have been added to many functions across the `somabrain` package (e.g., `memory_service.py`, helpers in `app.py`). Remaining gaps are tracked in the todo list.
- **Health endpoints**: `/health` now reports component readiness, predictor provider, strict-real mode, embedder details, and memory item counts, matching the updated configuration documentation.
- **Visualization policy**: SomaBrain publishes metrics for external scraping but intentionally omits embedded dashboards or UI bundles; operators can point external tools (Grafana, etc.) if needed.

These changes bring the repository to a production‑ready state with full stack verification, reproducible builds, and tighter CI enforcement.
