> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

## Direct Port Access

SomaBrain uses standard container ports for direct access:

**Docker Port Scheme (direct container ports)**:
- SomaBrain API: **9696** (direct access via localhost:9696)
- Redis: **6379** (localhost:6379)
- Kafka: **9092** (localhost:9092)
- Kafka Exporter: **9308** (localhost:9308)
- OPA: **8181** (localhost:8181)
- Prometheus: **9090** (localhost:9090)
- Postgres: **5432** (localhost:5432)
- Postgres Exporter: **9187** (localhost:9187)

- All services expose their container ports directly to localhost without offset.
- Internal container-to-container communication uses service hostnames (e.g., `redis://somabrain_redis:6379/0`).

**Example – Local development**:
```sh
# Access directly on standard ports
curl http://localhost:9696/health
redis-cli -h localhost -p 6379
```
# DEVELOPMENT_GUIDE.md

## Overview
This guide provides canonical, up-to-date instructions for developing, building, and running the SomaBrain platform. It is updated live as the codebase evolves.

---

## 0. Quickstart (≈10 minutes)
- Install `uv` 0.8+: `pipx install uv`.
- Sync the project environment deterministically:
    ```sh
    uv pip install --editable .[dev]
    uv pip sync uv.lock
    ```
- Launch the strict-real stack: `./scripts/dev_up.sh --rebuild` (writes `.env.local` + `ports.json`).
- Spot-check health: `curl -fsS http://localhost:9696/health | jq`.
- Run the canonical smoke: `uv run pytest -q` (uses locked dependencies).
- Access configuration exclusively via `somabrain.config.get_config()`; call `reload_config()` after changing YAML files.

This sequence mirrors the CI workflow and guarantees environment parity before deeper development work.

---

## 1. Prerequisites
- Docker and Docker Compose (latest stable)
- Python 3.10+ (for local development)
- [uv](https://github.com/astral-sh/uv) 0.8+ (dependency locking & runner)
- GNU Make (optional, for convenience)
- Recommended: VS Code with Python and Docker extensions

### 1.1 Dependency locking with `uv`

- Install `uv` via `pipx install uv` (or `pip install --user uv`).
- Install editable deps and write the lock file in one command:

    ```sh
    uv pip install --editable .[dev]
    ```

- When dependency metadata changes, regenerate and commit the lock:

    ```sh
    uv pip compile pyproject.toml --extra dev --lockfile uv.lock
    uv pip sync uv.lock
    ```

- `uv pip sync` guarantees CI/local envs resolve exactly to the versions pinned in `uv.lock`.
- See `docs/DEVELOPMENT_SETUP.md` § 1 for the full environment bootstrap walkthrough.

---


## 2. Building the Docker Image

To build the production-grade Docker image:

```sh
docker build -t somabrain:latest .
```

- The build uses a multi-stage Dockerfile for minimal, secure images.
- Only essential files are included in the image (see `.dockerignore`).
- The build will fail if the Python wheel cannot be built or installed.

---

## 3. Running the Stack

To run the full stack with standard port mapping:

```sh
./scripts/assign_ports.sh
docker compose up -d
```

- The `assign_ports.sh` script will create a `.env` file with standard container ports.
- `docker-compose` will use the `.env` file to launch the services with direct port access.
- Services are accessible at `localhost:PORT` (e.g., `localhost:9696` for SomaBrain API).

---

## 4. Development Workflow
- Make code changes in feature branches (unless main-only is required).
- Use `pytest` for tests: `pytest tests/`
- Use `make lint` and `make format` for code quality (if Makefile present).
- Update this guide as you improve the workflow.

---

## 5. Docker Image Hardening
- The Dockerfile uses a builder stage to create a wheel and a slim runtime stage.
- `.dockerignore` excludes tests, examples, build artifacts, and secrets.
- Only `somabrain/`, `scripts/`, `arc_cache.py`, and docs are included in the runtime image.
- Non-root user is used for security.

---

## 6. Troubleshooting
- If the build fails, check for missing dependencies or file bloat in the build context.
- Use `docker build --no-cache .` to force a clean build.
- For issues with services, check logs in `docker-compose` or `docker ps`.

---

## 7. Contributing
- Follow the code style and commit message guidelines.
- All changes should be tested and documented.
- Open PRs against `main` unless otherwise specified.

---

*This guide is updated live as the codebase and workflow evolve.*

---

## 8. Canonical Roadmap: Math Integrity & Production Readiness

This section captures the high-impact, strictly necessary roadmap items to keep the "brain" mathematically sound, simple, and real-world scalable. Only items that materially improve correctness, stability, determinism, or large-scale readiness are listed.

### A. Math Verification (Core Invariants)
| Area | Invariant | Planned Test (real vectors, no mocks) |
|------|-----------|----------------------------------------|
| HRR Roles | Unitary spectrum (|H_k|≈1) & determinism | `test_hrr_invariants.py` role spectrum & seed repeatability |
| Bind/Unbind | Roundtrip cosine ≥ threshold (dim-aware) | Bind→Unbind property test (random vec, token role) |
| Wiener Unbinding | Higher SNR → lower lambda & better cosine | SNR sweep (20,40,60 dB) monotonic assertions |
| Normalization | Idempotent, stable tiny-floor fallback | Zero & subtiny vectors robustness test |
| Tiny Floor Scaling | sqrt strategy: tiny ∝ sqrt(D) | Compare ratios across dims (256,1024,4096) |
| Sinkhorn | Marginal fidelity within tol | Extended transport test (uniform + random marginals) |
| Spectral Heat | Chebyshev ≈ Lanczos exp(-tA)x | SPD test matrix relative error bound |

Execution Order (lean): HRR → Numerics → Determinism → Wiener → Sinkhorn → Spectral.

### B. Production Configuration (Recommended Defaults)
| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| HRR Dim | 8192 (baseline), 16384 for richer semantic density | Balance memory vs binding accuracy |
| Permutation Seed | `HRR_BIND_SEED` aligned with role seed | Deterministic binding/unbinding |
| FD Rank | `FD_SALIENCE_RANK=64` (tune per dim) | Captures ≥90% spectral energy without O(D) cost |
| Wiener SNR Default | 40 dB | Good trade-off robustness vs fidelity |
| Redis | Dedicated instance, maxclients ≥ 10k, latency monitor enabled | Predictable low-latency store |
| Uvicorn/Gunicorn | Gunicorn w/ Uvicorn workers: `workers = 2 * cores`, `--loop uvloop` | Throughput + lower overhead |
| HTTP Keepalive | Enable; idle timeout 30s | Reuse connections for agent swarm traffic |
| Metrics Interval | Prom scrape every 5s | Timely drift + load feedback |
| HRR Role Cache | Persist spectra to disk (mmap) | Avoid recomputation spikes |
| Memory Sharding | Hash by tenant or semantic bucket | Horizontal scalability for millions of agents |

### C. Scaling Strategy (Agents / Millions of Users)
1. Stateless API layer behind L4/L7 load balancer.
2. Shard working memory; promote hot items to in-memory tier; cold pass-through to durable store.
3. Batch embeddings; consider vector DB for long-term recall if LTM size exceeds RAM.
4. Pre-generate frequently used unitary roles at process warm-up.
5. Introduce backpressure: rate limiter ties into neuromodulator signal for graceful degradation.

### D. Guardrails Against Regression
| Risk | Mitigation |
|------|------------|
| Silent norm drift | Property tests + assert unit norm post-normalize |
| Over-regularized unbinding | Track effective epsilon + cosine threshold alerts |
| Role non-determinism | Seed-specified tests fail on drift |
| Marginal mismatch (OT) | Sinkhorn test enforcing marginal L∞ error < 1e-5 |
| Spectral interval misestimate | Lanczos interval containment test |

### E. Minimal Future Enhancements (Optional)
- Expose `(vector, eps_used)` from unbind (optional, not required now) for direct inspection.
- Add a lightweight route to dump current HRR config (read-only) for operational observability.

### F. Acceptance Criteria for "Mathematically Verified" Stamp
All the A-series property tests pass in CI under both default and a high-dimension profile (skipped if CI resources constrain). No NaNs, all cosine thresholds met, marginal / spectral assertions hold.

---

*Edits to this roadmap must preserve: simplicity, determinism, and real numeric execution (no mocks).*
