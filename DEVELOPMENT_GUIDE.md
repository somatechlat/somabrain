> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

## Dynamic Port Discovery and Usage

SomaBrain now supports dynamic port assignment for all major services (Kafka, Redis, Prometheus, etc.).

- The startup script (`scripts/dev_up.sh`) will detect free ports and write them to `.env.local` and `ports.json`.
- All code and scripts use the following environment variables to connect to services:
	- `SOMABRAIN_REDIS_HOST` / `SOMABRAIN_REDIS_PORT`
	- `SOMABRAIN_KAFKA_HOST` / `SOMABRAIN_KAFKA_PORT`
	- `SOMABRAIN_PROMETHEUS_HOST` / `SOMABRAIN_PROMETHEUS_PORT`
	- etc.
- If you run the stack with dynamic ports, always check `.env.local` or `ports.json` for the actual host/port mappings.
- You can override these variables manually if needed.

**Example:**

```sh
export SOMABRAIN_REDIS_HOST=127.0.0.1
export SOMABRAIN_REDIS_PORT=6380
python somabrain/app.py
```

All code, scripts, and documentation have been updated to use this pattern.
# DEVELOPMENT_GUIDE.md

## Overview
This guide provides canonical, up-to-date instructions for developing, building, and running the SomaBrain platform. It is updated live as the codebase evolves.

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

To run the full stack in DEV_FULL mode (all services):

```sh
./scripts/dev_up.sh DEV_FULL
```

- This script brings up all required services (API, memory, DB, Kafka, etc.)
- **Dynamic port mapping:** If a default port (e.g., 9092 for Kafka) is already in use, Docker will automatically assign a free host port. You can find the mapped port using `docker ps` or `docker compose ps`.
- Update your client or environment variables to use the dynamically assigned host port if needed.

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
| FFT Epsilon | `HRR_FFT_EPSILON=1e-6` (float32 path) | Stable unbinding without oversmoothing |
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
