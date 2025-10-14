# Dependency Inventory – Sprint A0

> Canonical snapshot of SomaBrain runtime and tooling dependencies as of Sprint A0 (2025-10-13).

## 1. Python Runtime Packages

| Scope | Name | Version / Constraint | Source | Notes |
|-------|------|----------------------|--------|-------|
| Runtime | fastapi | `==0.115.*` (via `pyproject.toml`) | PyPI | Public API surface. |
| Runtime | uvicorn[standard] | `>=0.30,<0.31` | PyPI | ASGI server (multiprocess via Gunicorn in prod). |
| Runtime | numpy | `>=1.24` | PyPI | Numeric kernels, HRR operations. |
| Runtime | scipy | `>=1.14` | PyPI | Numerical routines (flow optimisation, bridge tests). |
| Runtime | prometheus-client | `>=0.20` | PyPI | Metrics exposition. |
| Runtime | httpx | `>=0.27` | PyPI | Outbound HTTP clients. |
| Runtime | requests | `>=2.32` | PyPI | Legacy HTTP usage; slated for consolidation into httpx. |
| Runtime | cachetools | `>=5.3` | PyPI | In-memory TTL caches. |
| Runtime | redis | `>=5.0` | PyPI | Redis client (strict-real requires real Redis). |
| Runtime | kafka-python | `>=2.0` | PyPI | Kafka/Redpanda producer + consumer. |
| Runtime | grpcio | `>=1.75` | PyPI | gRPC server transport for SA01 service. |
| Runtime | SQLAlchemy | `>=2.0` | PyPI | ORM/persistence layer. |
| Runtime | psycopg[binary] | `>=3.1` | PyPI | Modern Postgres driver. |
| Runtime | psycopg2-binary | `>=2.9` | PyPI | Transitional driver for legacy paths. |
| Runtime | cryptography | `>=43` | PyPI | JWT + secrets tooling. |
| Runtime | PyJWT | `>=2.9` | PyPI | Token signing/validation. |
| Runtime | pydantic-settings | `>=2.5` | PyPI | Loading strongly typed config objects. |
| Runtime | python-dotenv | `>=1.1` | PyPI | Optional `.env` parsing via pydantic-settings. |
| Runtime | python-json-logger | `>=2.0` | PyPI | Structured logging.

## 2. Developer Extras (`.[dev]`)

| Category | Package | Version / Constraint | Purpose |
|----------|---------|----------------------|---------|
| Test | pytest | `==8.4.2` | Canonical unit/integration test runner. |
| Test | pytest-asyncio | `==0.23.8` | Async FastAPI test helpers. |
| Lint | ruff | `==0.13.0` | Lint + format (supersedes black/isort for most paths). |
| Format | black | `==25.1.0` | Historical formatter, still used for selected modules. |
| Type | mypy | `==1.11.2` | Static type checking. |
| Docs | sphinx | `==7.2.6` | Documentation build system. |
| Docs | myst-parser | `==3.0.1` | Markdown support in Sphinx. |
| Profiling | pyinstrument | `==5.1.1` | CPU sampling profiler. |
| Profiling | scalene | `==1.5.27` | CPU + memory profiler. |
| Profiling | py-spy | `==0.3.14` | Lightweight sampling profiler for production snapshots. |
| QA | coverage | `==7.6.1` | Coverage reporting (integrated via pytest). |

> Jupyter stack intentionally excluded (strict-real prohibits notebook-driven simulations in CI).

## 3. System-Level Dependencies (Docker Image)

| Layer | Package | Notes |
|-------|---------|-------|
| Base Image | `python:3.13-slim` | Aligns with CI/runtime environment. |
| Build Tools | `build-essential`, `gcc`, `libpq-dev` | Required for compiling wheels (psycopg, numpy). |
| Kafka | `librdkafka-dev` | Backing library for `confluent-kafka` (legacy ingestion path). |
| Runtime Tools | `curl`, `jq` | Health + debugging inside container. |
| User | `somabrain` non-root | Security posture. |

## 4. Makefile & Toolchain Targets

| Target | Dependency Surface | Lockfile Strategy |
|--------|--------------------|-------------------|
| `make install` | Virtualenv + editable install (`pip install -e .`) | To be replaced with `uv pip install -e .` (tracked). |
| `make dev` | Editable install with dev extras | Mirrors `uv` workflow; bridging target retained for backwards compatibility. |
| `make lint` | Relies on `ruff` | Covered by `uv` extras. |
| `make typecheck` | `mypy` | Covered by `uv` extras. |
| `make docs` | `sphinx-build` | Provided via dev extras. |
| `make dev-up` | `scripts/dev_up.sh` | Requires Docker, Compose, Redis, Kafka binaries available in stack. |
| `make bench` | `benchmarks/cognition_core_bench.py` | Uses numpy + internal modules; no additional packages. |

## 5. Observability & Metrics

| Metric | Source | Notes |
|--------|--------|-------|
| `dependency_install_duration_seconds` | `scripts/ci/record_dependency_install_metrics.py` | Captured during CI `uv pip sync`. |
| `dependency_install_package_total` | Same as above | Counts resolved wheels in `uv.lock`. |
| Grafana Panel | `observability/dependency_install_panel.json` | Ready-to-import panel (baseline alert: install time > 120s). |

## 6. Action Items & Drift Watch

- **Remove duplicate PostgreSQL drivers** once all call-sites migrate to `psycopg`. Track under Sprint B1.
- **Enforce `uv` flow in Makefile** after one sprint of coexistence period. Replace `pip` commands with `uv pip` while retaining venv compatibility for external users.
- **Monitor confluent-kafka usage**; remove from image if ingestion strategy moves entirely to `kafka-python`.
- **Quarterly audit**: rerun this inventory each quarter or when major dependency changes ship.

---

_Last updated: 2025-10-13 (Sprint A0 close-out)._