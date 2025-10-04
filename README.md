# SomaBrain — Math-Powered Memory & Reasoning Engine (GitHub-ready overview)

**SomaBrain** is a deterministic, float-precision, hyperdimensional memory + transport engine that **learns from use**, **recalls under heavy superposition**, and **routes knowledge like a living network**. It plugs into your apps as a set of small, composable modules.

> Strict Real Mode: The repository enforces a no-mocks contract in CI and production-like flows. See `docs/architecture/STRICT_MODE.md` for enforcement rationale and readiness gating.

---

## 🚀 Quickstart (container)

```bash
docker run --rm \
  -p 8000:9696 \
  -e SOMABRAIN_DISABLE_AUTH=true \
  ghcr.io/somatechlat/somabrain:latest
```

Then open:
- Health: http://localhost:8000/health
- OpenAPI: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

### 🔐 Auth & Tenancy
Enable token auth (recommended for non-local):

```bash
docker run --rm \
  -p 8000:9696 \
  -e SOMABRAIN_DISABLE_AUTH=false \
  -e SOMABRAIN_API_TOKEN=yourtoken \
  ghcr.io/somatechlat/somabrain:latest
  
# Call with:
#   -H "Authorization: Bearer yourtoken"
# Multi-tenant isolation header:
#   -H "X-Tenant-ID: demo"

# Call with:
### ⚖️ OPA Posture (fail-open vs fail-closed)

By default, policy checks via OPA are fail-open, meaning requests are allowed if OPA is unreachable. For production, you can enable fail-closed to deny requests when OPA is unavailable:

- Set SOMA_OPA_FAIL_CLOSED=1 to require OPA for allow/deny decisions.
- The health endpoint exposes opa_ok and opa_required. When fail-closed is on, readiness requires opa_ok=true.

Example:

```bash
docker run --rm \
  -p 8000:9696 \
  -e SOMABRAIN_DISABLE_AUTH=false \
  -e SOMA_OPA_URL=http://sb_opa:8181 \
  -e SOMA_OPA_FAIL_CLOSED=1 \
  ghcr.io/somatechlat/somabrain:latest
```

Health payload fields:
- opa_required: true when SOMA_OPA_FAIL_CLOSED is enabled
- opa_ok: true when OPA /health responds 200 within timeout

#   -H "Authorization: Bearer yourtoken"
# Multi-tenant isolation header:
#   -H "X-Tenant-ID: demo"
```

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

* `somabrain/embeddings.py` – TinyDeterministicEmbedder (unit-norm)
* `somabrain/quantum.py` – HRR/QuantumLayer (FFT bind/unbind, Wiener)
* `memory/density.py` – ρ update + scoring (PSD/trace) *[root directory]*
* `somabrain/math/bridge.py` – heat-kernel Sinkhorn planning
* `somabrain/math/sinkhorn.py` – Sinkhorn scaling operations  
* `somabrain/math/graph_heat.py` – graph heat kernel operations
* `somabrain/learning/adaptation.py` – bounded OCO (λ, μ, ν, …)
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

If running the integration harness a dedicated port `9797` is used to avoid collisions. Production containers still expose internal port `9696`.

### ✅ Live Cognition Verification (real services)

When the Kubernetes stack is port-forwarded back to localhost, run the cognition suite to prove the brain learns from real interactions:

```bash
export SOMA_API_URL=http://127.0.0.1:9797
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
export SOMABRAIN_POSTGRES_LOCAL_PORT=55432
pytest -vv tests/test_cognition_learning.py
```

The tests confirm three signals:

* `/remember` increases the memory item count and `/recall` returns live entries.
* `/context/feedback` writes new rows into `feedback_events` and `token_usage` via Postgres.
* Session working-memory history grows monotonically across evaluate/feedback loops.

If any check fails, inspect the port-forward logs (e.g. `/tmp/pf-*.log`) and re-run once the services return `{"ok": true}` from their `/health` probes.

### Kubernetes Test Port (9797)
The full-stack manifest includes an additional ClusterIP service `somabrain-test` exposing port **9797** mapped to the primary pod container port 9696. This lets you:

- Isolate test / load / learning verification traffic
- Keep dashboards and alert routes pointed at the canonical `somabrain` service on 9696

Port-forward for local validation and run a quick learning probe directly from the repo:

```bash
kubectl -n somabrain-prod port-forward svc/somabrain-test 9797:9797
export SOMA_API_URL=http://127.0.0.1:9797
python - <<'PY'
import os
import time
import requests

BASE = os.getenv("SOMA_API_URL", "http://127.0.0.1:9797")
SESSION = "doc-check"
HEADERS = {"X-Model-Confidence": "2.0"}

task = {"coord": None, "payload": {"task": "alpha waves and cognitive resonance"}}
requests.post(f"{BASE}/remember", json=task, headers=HEADERS, timeout=10).raise_for_status()

before = requests.get(f"{BASE}/context/adaptation/state", timeout=10).json()
for _ in range(3):
    ev = requests.post(
        f"{BASE}/context/evaluate",
        json={"session_id": SESSION, "query": "neural reward modulation", "top_k": 5},
        headers=HEADERS,
        timeout=10,
    )
    ev.raise_for_status()
    prompt = ev.json()["prompt"]
    fb = requests.post(
        f"{BASE}/context/feedback",
        json={
            "session_id": SESSION,
            "query": "neural reward modulation",
            "prompt": prompt,
            "response_text": "ok",
            "utility": 0.8,
            "reward": 0.8,
        },
        headers=HEADERS,
        timeout=10,
    )
    fb.raise_for_status()
    time.sleep(0.05)

after = requests.get(f"{BASE}/context/adaptation/state", timeout=10).json()
print({
    "alpha_delta": after["retrieval"]["alpha"] - before["retrieval"]["alpha"],
    "lambda_delta": after["utility"]["lambda_"] - before["utility"]["lambda_"],
})
PY
```

You should observe positive deltas for `alpha` and `lambda_`, confirming adaptation is active. Any HTTP 4xx/5xx indicates the stack is not fully wired.
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

- **API service** – `somabrain` (ClusterIP) exposing container port **9696**. A sibling service,
  `somabrain-test`, maps **9797 → 9696** for load or soak tests without touching dashboards.
- **Memory service** – `somamemory` (ClusterIP) on **9595**. The API points at the DNS name
  `http://somamemory.somabrain-prod.svc.cluster.local:9595` by default.
- **Redis** – `sb-redis` on **6379** and **OPA** – `sb-opa` on **8181**.
- Persistent volume claim `somabrain-outbox-pvc` stores the API outbox artifacts.
- Authentication is disabled by default via `SOMABRAIN_DISABLE_AUTH=1` in the `somabrain-env`
  ConfigMap so you can hit endpoints immediately. Remove the flag and populate the JWT secret to
  re-enable auth (see `docs/CONFIGURATION.md`).

Apply the stack:
```bash
kubectl apply -f k8s/full-stack.yaml
```

Port‑forward the services for local validation:
```bash
kubectl -n somabrain-prod port-forward svc/somabrain 9696:9696   # primary API
kubectl -n somabrain-prod port-forward svc/somabrain-test 9797:9797   # optional test port
kubectl -n somabrain-prod port-forward svc/somamemory 9595:9595  # memory service (optional)
kubectl -n somabrain-prod port-forward svc/postgres 55432:5432   # Postgres (feedback + token ledger)
```

Need the forwards to survive a shell restart? Run them in the background and log to `/tmp`:

```bash
nohup kubectl -n somabrain-prod port-forward svc/somabrain 9696:9696         > /tmp/pf-somabrain.log      2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/somabrain-test 9797:9797   > /tmp/pf-somabrain-test.log 2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/somamemory 9595:9595       > /tmp/pf-somamemory.log     2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/sb-redis 6379:6379         > /tmp/pf-redis.log          2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/postgres 55432:5432        > /tmp/pf-postgres.log        2>&1 &
```
Tail the corresponding log file if a forward drops unexpectedly. When finished, clean them up with
`pkill -f "kubectl -n somabrain-prod port-forward"`.

Health probes:
```bash
curl http://127.0.0.1:9696/health
curl http://127.0.0.1:9797/health  # same pod, test service
curl http://127.0.0.1:9595/health  # memory service
PGPASSWORD=somabrain-dev-password psql "host=127.0.0.1 port=55432 user=somabrain dbname=somabrain" -c 'select 1;'
```
All should report `{"ok": true, ...}` with `ready: true` once memory and Redis are reachable.

To verify in-cluster learning, run the lightweight end-to-end script that stores 10 memories and
checks recall:
```bash
python benchmarks/agent_coding_bench.py --base http://127.0.0.1:9696 --tenant benchdev
```
Or reuse the existing pytest scenario that encodes and recalls a memory via the agent memory
module:
```bash
pytest tests/test_agent_memory_module.py::test_encode_and_recall_happy -q
```
Both commands fail fast if encode/recall plumbing is broken.

After forwarding the test service (`somabrain-test`), you can force the pytest run to hit the
forwarded address explicitly:

```bash
SOMA_API_URL=http://127.0.0.1:9797 .venv/bin/pytest \
  tests/test_agent_memory_module.py::test_encode_and_recall_happy -q
```

The test prints `[pytest_configure] STRICT REAL MODE enabled` and reports a single `.` when the
live stack (API + Redis + memory) is wired correctly.

For CI you can run the integration test `tests/test_full_stack_k8s.py`; it performs the same
port‑forwarding, queries health endpoints, and verifies the PVC is bound before exercising the API.

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
