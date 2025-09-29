# SomaBrain — Math-Powered Memory & Reasoning Engine (GitHub-ready overview)

**SomaBrain** is a deterministic, float-precision, hyperdimensional memory + transport engine that **learns from use**, **recalls under heavy superposition**, and **routes knowledge like a living network**. It plugs into your apps as a set of small, composable modules.

> Strict Real Mode: The repository enforces a no-mocks contract in CI and production-like flows. See `docs/architecture/STRICT_MODE.md` for enforcement rationale and readiness gating.

---

## 🚀 Headline Features

* **Unit-norm Hyperdimensional Embeddings (HRR)**

  * 8,192-D (configurable), deterministic seeds, FFT binding/unbinding (exact + Wiener).
  * Safe invariants everywhere: pad/truncate → L2-normalize → guard NaNs/zeros.

* **Superposition that Actually Works**

  * Robust recall under many overlapping memories using **Wiener unbinding** + **density-matrix scoring** (ρ).
  * Calibrated confidence scores for ranking and cleanup (better Brier/NLL than cosine-only).

* **Self-Optimizing Memory Graph (Mycelial FRGO)**

  * After serving, SomaBrain solves sparse flows and **reinforces high-use edges** while pruning waste.
  * Outcome: **lean, efficient, robust backbones** (lower effective resistance at lower “material” cost).

* **Sum-Over-Paths Planning (Schrödinger Bridge)**

  * Recs/paths come from **probabilistic fastest routes** (heat-kernel on the graph), not just one shortest path.
  * Fewer detours, higher Success@T; diversity is tunable via entropy.

* **Online Convex Adaptation (Safe by Design)**

  * Utility = λ·log(p_conf) − μ·cost − ν·latency with **bounded**, rollback-safe updates.
  * Precision/attention knobs available; all weights clamped to config ranges.

* **Deterministic, Auditable, Test-First**

  * Float64 in critical numerics; property-based tests for invertibility, unit-norm, stability.
  * Provenance: every edge has conductance $C_e$, flows $Q_e$, and loop rank to explain decisions.

---

## 🧠 What It Does Better (in practice)

* **Recall:** Higher Top-1 under dense superposition; calibrated confidence → fewer wrong high-confidence hits.
* **Recommendation:** Ranks by path reachability (bridge) + evidence (ρ), not just cosine closeness.
* **Prediction:** Accurate steps-to-goal via arrival-time marginals; better cache prefetch.
* **Scale:** Batch updates keep latency low; sparse CG on sharded graphs; clamp + prune for stability.

---

## 🧩 Core Math (clean, production-ready)

* **HRR:** circular convolution/correlation (FFT), exact & Wiener unbinding, unitary roles.

* **Density Matrix ρ:** PSD, trace-normalized memory of co-occurrence:

  $$
  \rho \leftarrow (1-\lambda)\rho + \lambda \sum w_i f_i f_i^\top,\quad \rho\gets \text{Proj}_{\text{PSD}}(\rho)/\text{tr}(\rho)
  $$

  Score: $s(q\!\to\!k)=\hat f^\top \rho\, f_k$.

* **Transport (FRGO):**

  $$
  C_e \leftarrow \mathrm{clip}\!\big(C_e + \eta(|Q_e|^\alpha - \lambda L_e C_e)\big)
  $$

  (flows $Q$ from Laplacian solves; cost edge weight $L_e/C_e$).

* **Planning (Bridge):** heat-kernel $K=\exp(-\beta \mathcal{L})$ with Sinkhorn scaling for start/goal distributions → time-marginals and controls.

---

## 🛠️ Minimal Integration

```python
# 1) HRR recall (Wiener first), then ρ-scoring
f_hat = wiener_unbind(H_superposed, role, lam=1e-3)  # float64 FFT
s_k   = f_hat @ (rho @ candidate_k)                   # density-matrix score
topK  = argsort_desc(s_k)

# 2) After N requests: update graph transport (FRGO)
Q = solve_flows_sparse(C, demands_batch)              # CG on Laplacian
C = clip(C + eta*(abs(Q)**alpha - lam*L*C), Cmin, Cmax)

# 3) Optional: bridge planning for ranking/ETA
P = schrodinger_bridge(Laplacian, mu0, mu1, beta)     # heat-kernel Sinkhorn
eta_pred = expected_arrival_time(P)
```

---

## 📈 What to Measure (A/B checklist)

* **Recall Top-1 vs. superposition K** ↑
* **Calibration:** Brier / ECE ↓
* **Mean effective resistance (graph)** ↓
* **Material cost (edges above threshold)** ↓ with **robustness** ≥ baseline
* **Success@T / detour rate** (bridge) ↑
* **Latency & p50/p95** stable under batching

---

## 🔒 Reliability & Safety

* Deterministic seeds; float64 critical ops; bounded learning rates.
* Clamps: $C_{\min}$, $C_{\max}$; PSD projection for ρ; pruning thresholds.
* Unit tests: invertibility (bind→unbind), unit-norm, no NaNs, stability under load.

---

## 📦 Modules (drop-in)

* `embeddings.py` – TinyDeterministicEmbedder (unit-norm)
* `quantum.py` – HRR/QuantumLayer (FFT bind/unbind, Wiener)
* `memory/density.py` – ρ update + scoring (PSD/trace)
* `transport/flow_opt.py` – sparse CG + FRGO updater
* `transport/bridge.py` – heat-kernel Sinkhorn (Krylov expm-v)
* `adaptation.py` – bounded OCO (λ, μ, ν, …)
* `tests/` – property tests + benchmarks

---

## 📚 Why it’s different

SomaBrain doesn’t just **store vectors**—it **shapes the space** they move through. Usage induces flows; flows re-shape routes; second-order evidence calibrates memory; planning sums over paths. The result is a brain that **learns from its own traffic**, stays **lean** as it grows, and **explains** the choices it makes.

```bash
# Create a local venv and install dev deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Launch canonical stack (auto-selects free ports and writes ports.json)
./scripts/dev_up.sh

# 3. Run integration tests (NO_MOCKS)
pytest -m integration -q

# 4. Tail metrics / logs
open http://localhost:$(jq -r '.SOMABRAIN_HOST_PORT' ports.json)/metrics

# (Optional) run schema migrations for Postgres-backed stores
alembic upgrade head

# 5. Export OpenAPI (optional)
./scripts/export_openapi.py
```

### 🚀 Fast Strict-Dev Quickstart (Realism, No Stubs)

```bash
export SOMABRAIN_STRICT_REAL=1
export SOMABRAIN_PREDICTOR_PROVIDER=mahal
uvicorn somabrain.app:app --host 0.0.0.0 --port 9696
curl -s localhost:9696/health | jq
```

If running the test harness (integration tests) a dedicated port `9797` is used to avoid collisions. Production containers still expose internal port `9696`.

### 🔍 Health & Readiness Sample

```json
{
  "ok": true,
  "components": {"memory": {"http": false}, "wm_items": "tenant-scoped", "api_version": "v1"},
  "namespace": "sandbox",
  "predictor_provider": "mahal",
  "strict_real": true,
  "embedder": {"provider": "tiny", "dim": 256},
  "stub_counts": {},
  "ready": true,
  "memory_items": 12
}
```
`ready=false` under strict mode indicates: (a) predictor still stub, or (b) no memory backend and no in-process payloads yet, or (c) embedder missing.

### 🔁 Recall Path Resolution
1. HTTP memory service (if endpoint configured & healthy)
2. Deterministic in-process similarity (real embeddings) if HTTP not available and local payloads exist
3. Strict mode: raise instead of falling back to stub when neither path can serve

### 🧪 Mode Overview

| Mode | Strict | Predictor Default | Recall Strategy | Primary Use |
|------|--------|-------------------|-----------------|-------------|
| dev | Off | stub | in-process recent | Rapid prototyping |
| strict-dev | On | mahal | HTTP → in-process | CI / pre-prod validation |
| staging | On | mahal | HTTP → in-process | Dress rehearsal |
| prod | On | dynamic (mahal/llm) | HTTP → in-process | Live traffic |
| bench | On | mahal | in-process deterministic | Deterministic perf |

Full variable list and precedence rules: `docs/CONFIGURATION.md`.

The canonical stack automatically detects occupied host ports and allocates alternatives; the
POC `ports.json` file records the assignments so CLI tooling and tests can hydrate the correct
endpoints.

## Full‑stack Kubernetes deployment

- **API service** – `somabrain` listening on **port 9696** (ClusterIP). For external testing a **NodePort 30979** is exposed.
- **Memory service** – `somamemory` listening on **port 9595** (ClusterIP).
- **Redis** – `sb-redis` on **6379**.
- **OPA** – `sb-opa` on **8181**.
- Persistent volume claim `somabrain-outbox-pvc` stores outbox artifacts for the API.

The stack can be started with:
```bash
kubectl apply -f k8s/full-stack.yaml
```

A quick health‑check:
```bash
curl http://<node-ip>:30979/health   # API
curl http://<node-ip>:9595/health    # Memory service
```
Both should return `{"ok": true, ...}` and report `ready: true`.

For CI you can run the integration test `tests/test_full_stack_k8s.py` which performs port‑forwarding, queries the health endpoints and verifies the PVC is bound.

## Contributing

1. Each sprint deliverable is tracked in `docs/architecture/CANONICAL_ROADMAP.md`.
2. Infrastructure changes must ship via Terraform/Helm manifests under code review.
3. All code paths require tests (unit + integration). Benchmarks in `benchmarks/` are executed
   before release and must meet the published SLOs.
4. Follow the coding standards documented in `docs/DEVELOPMENT_SETUP.md` (formatter, lints, hooks).


## 📊 Performance & Chaos Testing (S9)

## 🚦 Launch, DR & Runbooks (S10)

**Disaster Recovery & Automation:**
- Automated backups and multi-region replication for Redis, Kafka, and Postgres. Constitution restore workflow documented in `ops/runbooks/DR_and_Restore.md`.

**Runbooks:**
- Constitution rotation, Kafka upgrade, memory integrity incident, agent SLM rollback, and onboarding runbooks in `ops/runbooks/Runbooks.md`.

**Release Process & Health Gating:**
- Blue/green or canary release process, health checks, and rollback documented in `ops/runbooks/Release_and_Health_Gating.md`.

**Compliance & Proofs:**
- Pen test results, formal proof scripts, and SLO/benchmark/chaos results in `ops/runbooks/Compliance_and_Proofs.md`.

All S10 artefacts are production-ready and validated. See `ops/runbooks/` for details.

**Benchmarking & Load Testing:**
- `benchmarks/scale/scale_bench.py`: Simulates 1M requests/day, captures p50/p95/p99 latency, error rate, and throughput.
- `benchmarks/scale/load_soak_spike.py`: Runs load (steady), soak (long duration), and spike (burst) tests to identify bottlenecks.
- Results: System sustains target throughput with <1% error rate; p95 latency meets SLOs under all tested patterns.

**Chaos Experiments:**
- `benchmarks/scale/chaos_experiment.py`: Coordinates health checks before/during/after manual chaos (Kafka, Redis, agent SLM outage). Verifies auto-recovery and data integrity.
- Results: All core services recover automatically; no data loss or integrity issues observed.

**Profiling & Optimization:**
- `benchmarks/scale/profile_harness.py`: Profiles CPU/memory for any benchmark, outputs bottleneck analysis.
- Optimizations: Connection pooling, batch operations, and config tuning applied where needed. No major bottlenecks remain at current scale.

All scripts and configs are documented in `benchmarks/scale/` and referenced in the canonical roadmap.

---
## Roadmap & Status

The fine-grained roadmap lives in `docs/architecture/CANONICAL_ROADMAP.md`. Status updates happen at
the end of every sprint (two-week cadence) along with release notes and exemplar metrics.

## CLI Example

```bash
cd clients/python
python cli.py "Hello Soma" --session sandbox-cli
```

---
Additional architecture, strict mode, and scaling docs:

* `docs/CONFIGURATION.md` – canonical environment + mode matrix
* `docs/architecture/STRICT_MODE.md` – no-stub enforcement details
* `docs/developer/PRODUCTION_CONFIG.md` – high-impact prod knobs
* `docs/developer/PERFORMANCE_SCALING.md` – performance levers
* `docs/developer/MATH_VERIFICATION_REPORT.md` – invariant coverage
