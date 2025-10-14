# SomaBrain 3.0 — Cognitive Memory Core

> Documentation here is math-first, test-backed, and describes only the software that ships in this repository.

SomaBrain is a hyperdimensional memory and reasoning runtime that couples binary hypervector binding, density-matrix scoring, and transport-aware planning. This repository is the canonical implementation for the SomaBrain 3.0 stack.

---

## 1. Architecture Snapshot

```mermaid
graph TD
    subgraph Client Edge
        Agents[Agents / Tooling]
    end

    Agents -->|HTTPS| API

    subgraph Runtime
        API[SomaBrain FastAPI]
        WM[Working Memory (MultiTenantWM)]
        LTM[MemoryClient + HTTP memory service]
        Scorer[UnifiedScorer + DensityMatrix]
        Quantum[QuantumLayer (BHDC HRR)]
        Control[Neuromodulators & Policy Gates]
    end

    API -->|Recall / Remember| WM
    API -->|Recall / Remember| LTM
    API -->|Scoring| Scorer
    API -->|HRR Encode| Quantum
    API -->|Safety Gates| Control

    subgraph Auxiliary Services
        SMF[SomaFractalMemory Gateway]
        GRPC[gRPC MemoryService]
    end

    LTM -->|Vector IO| SMF
    API -->|Optional Transport| GRPC
```

- `somabrain.app`: FastAPI surface with recall, remember, planning, and introspection endpoints.
- `somabrain/memory_client.py`: HTTP-first memory connector with strict-mode auditing and write mirroring.
- `somabrain/memory/density.py`: Maintains the ρ matrix used by the unified scorer for second-order recall.
- `somabrain/quantum.py`: BHDC binding, permutation roles, and deterministic superposition utilities.
- `services/smf`: Thin gateway to Qdrant-compatible vector backends (SomaFractalMemory).
- `somabrain/grpc_server.py`: Optional gRPC façade layered on top of the memory client.

See `docs/architecture/somabrain-3.0.md` for a full deep dive into the runtime topology.

---

## 2. Quickstart

### 2.1 Docker Compose (recommended)

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

Check status:

- API: http://localhost:9696/health
- Metrics: http://localhost:9696/metrics
- Docs: http://localhost:9696/docs

The bundled compose stack runs Redis, Kafka, Postgres, OPA, Prometheus, and the SomaBrain API. Override host ports through the environment variables defined in `docker-compose.yml` when needed.

### 2.2 Local Python (strict mode)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]

export SOMABRAIN_STRICT_REAL=1
export SOMABRAIN_FORCE_FULL_STACK=1
export SOMABRAIN_REQUIRE_MEMORY=1
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
export SOMABRAIN_DISABLE_AUTH=1

PYTHONPATH=$(pwd) uvicorn somabrain.app:app --host 127.0.0.1 --port 9696
```

Strict-mode flags disable stubs, require backing services, and surface violations as runtime errors. Start Redis, Postgres, and Kafka (via compose or external services) before launching the API.

### 2.3 CLI Utilities

- `scripts/dev_up.sh`: Spins up the compose stack, waits for readiness, writes `ports.json`.
- `scripts/export_openapi.py`: Generates the canonical OpenAPI document under `artifacts/`.
- `run_learning_test.py`: Sanity-checks numerics and memory flows against canonical fixtures.

---

## 3. Runtime Invariants

| Invariant | Description | Enforcement |
| --- | --- | --- |
| Density matrix trace | `abs(trace(ρ) - 1) < 1e-4` | `somabrain/memory/density.py` renormalizes after each update. |
| PSD stability | Negative eigenvalues are clipped so ρ stays PSD | `DensityMatrix.project_psd()` trims the spectrum. |
| Scorer bounds | Component weights stay within configured bounds | `somabrain/scoring.py` clamps weights and exports metrics. |
| Strict-mode audit | Stub usage raises `RuntimeError` | `_audit_stub_usage` inside `somabrain/memory_client.py`. |
| Governance | Rate limits, OPA policy, neuromodulator feedback | Middleware stack inside `somabrain.app` and controls modules. |

Instrumentation for these invariants surfaces through `/metrics`; Prometheus names and dashboard links live in the operations guide.

---

## 4. Feature Highlights

- **BHDC binding**: Deterministic binary hypervectors with permutation roles deliver invertible binding/unbinding.
- **Frequent-Directions salience**: `somabrain.salience.FDSalienceSketch` tracks residual mass for diversity-aware recall.
- **Unified scoring**: Cosine, FD projection, and recency combine with bounded weights to keep rankings stable.
- **Working memory**: `somabrain.mt_wm.MultiTenantWM` feeds real-time recall before long-term memory hits.
- **Transport planning**: Planning endpoints leverage graph-based reasoning in `somabrain/planner.py`.
- **Audit pipeline**: `somabrain.audit` emits structured events and activates Kafka producers when brokers are configured.

---

## 5. Observability & Health

- **HTTP health**: `/health` aggregates readiness across Redis, Postgres, Kafka, policy middleware, and metrics emission; `/healthz` mirrors the same payload.
- **Metrics**: `/metrics` exports Prometheus counters and histograms for recall latency, scorer components, HRR cleanup, and rate limiting.
- **Tracing**: If `observability.provider.init_tracing` is available, startup hooks configure tracing automatically.
- **Logging**: Structured JSON logging can be enabled via `somabrain/logging.yaml`.

Operational dashboards, alert recipes, and runbooks live in `docs/operations/runbook.md`.

---

## 6. Testing & Quality Gates

- **Linting**: `ruff check .`
- **Type checking**: `mypy somabrain`
- **Unit & property tests**: `pytest`

Run the full suite locally before submitting changes:

```bash
ruff check .
mypy somabrain
pytest
```

Property tests assert BHDC binding inverses, density-matrix PSD, scorer stability, and API contracts. CI enforces the same gating.

---

## 7. Documentation Map

- `docs/architecture/somabrain-3.0.md` — runtime topology, recall lifecycle, and invariants.
- `docs/architecture/STRICT_MODE.md` — strict-mode contract, failure modes, and audit rules.
- `docs/architecture/math/bhdc-binding.md` — BHDC binding / cleanup maths.
- `docs/architecture/math/density-matrix.md` — ρ update rule, projections, and metrics.
- `docs/api/rest.md` — REST endpoint table sourced from `somabrain.app`.
- `docs/operations/runbook.md` — deployment, monitoring, and incident procedures.
- `docs/operations/configuration.md` — environment variable reference.
- `docs/releases/changelog.md` — release log tied to commits and test evidence.

All documents remain canonical to this repository. If you spot drift, open an issue or PR with the corrective source.

---

## 8. Quick Integration Snippet

```python
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.salience import FDSalienceSketch
from somabrain.scoring import UnifiedScorer

cfg = HRRConfig(dim=2048, seed=1337, sparsity=0.08)
quantum = QuantumLayer(cfg)
role = quantum.make_unitary_role("route::origin")
encoded = quantum.bind_unitary(quantum.encode_text("payload"), "route::value")

fd = FDSalienceSketch(dim=cfg.dim, rank=64, decay=0.98)
fd.observe(encoded)

scorer = UnifiedScorer(
    w_cosine=0.6,
    w_fd=0.3,
    w_recency=0.1,
    weight_min=0.0,
    weight_max=1.0,
    recency_tau=32.0,
    fd_backend=fd,
)

score = scorer.score(quantum.encode_text("query"), encoded, recency_steps=5)
```

---

## 9. Contributing

- Fork the repository and create a feature branch.
- Keep strict-mode environment variables enabled while developing.
- Run `ruff`, `mypy`, and `pytest` before opening a pull request.
- Update documentation alongside behavioral changes; docs are treated as source code.

SomaBrain is built for mathematical clarity, production-grade observability, and uncompromising strict-mode enforcement—ship changes that keep those pillars intact.
