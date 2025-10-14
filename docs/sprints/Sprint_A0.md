# Sprint A0 – Dependency Cleanup (Weeks 1-2)

> Canonical log for SomaBrain 3.0, Epic A (Foundations & Infrastructure)

## Objective
Raise the baseline for reproducible builds and shared configuration so every downstream epic can rely on stable tooling and dependency hygiene.

- Lock Python/UV environments and ensure deterministic dependency resolution.
- Audit `pyproject.toml`, Dockerfile, and Make targets for redundant or conflicting configuration.
- Unify configuration loading (`load_config`) to a single code path with clear overrides.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Inventory current dependency graph (`pyproject`, `requirements-dev.txt`, Docker) | Platform | In progress | Pyproject core deps (FastAPI, numpy, sql stack), dev req pins (pytest 8.4.2, black 25.1.0, numpy 1.26.4), Docker installs confluent-kafka, pydantic-settings. Next: capture Makefile/tooling extras. |
| Establish reproducible `uv` lockfile and document bootstrap steps | Platform | In progress | Existing `uv.lock` present (revision 3); verify alignment with pyproject/requirements and document refresh workflow (`uv pip compile` → commit). |
| Normalize `load_config` usage across modules | Platform | In progress | Added cached `get_config()` / `reload_config()` helpers; next step is migrating call-sites to use shared accessor. |
| Draft ADR for environment parity & configuration | Architecture | Planned | Outline lockfile strategy + config loader; to file under `docs/adr/`. |
| Update developer quickstart (`DEVELOPMENT_GUIDE.md`) | Docs | Planned | Include lockfile install command, config loader notes. |
| Baseline monitoring of dependency build times | Observability | Planned | Add metric from CI during lockfile adoption. |

## Deliverables
- Dependency audit report
- `uv.lock` (or equivalent) committed
- ADR: "Unified Config Loading"
- Updated developer guide with new setup flow
- Dashboard panel capturing dependency install duration

## Dependency Inventory Notes (2025-10-13)

- `pyproject.toml` runtime deps: FastAPI, uvicorn, numpy >=1.24, Prometheus client, httpx/requests, cachetools, Redis, Kafka-python, SQLAlchemy + psycopg (both new `psycopg[binary]` and legacy `psycopg2-binary`), cryptography, PyJWT.
- Dev extras pinned via `requirements-dev.txt`: formatting (black 25.1.0, isort 6.0.1), linting (ruff 0.13.0), testing (pytest 8.4.2, pytest-asyncio 0.23), docs (Sphinx 7.2.6, myst-parser), profiling (pyinstrument 5.1.1, scalene 1.5, py-spy 0.3.14), numpy pinned to 1.26.4 for CI compatibility.
- Docker runtime installs wheel, PyJWT[crypto], confluent-kafka (with librdkafka-dev) and pydantic-settings; ensures non-root user and copies shared `common/` package.
- Makefile still exposes dev/test targets, no direct pin drift observed yet; confirm once lockfile strategy set.
- `load_config` used in ~19 modules (app, services, routers, math helpers, CLI); upcoming audit will add shared helper to avoid repeated YAML loads.
- `uv.lock` already in repo (revision 3) targeting Python >=3.10; requires verification that runtime/dev pins match pyproject + requirements before finalizing workflow docs.

## Risks & Mitigations
- **Legacy scripts bypassing new config loader** → Flag via code search, add docs.
- **CI image drift** → Update container build pipeline once lockfile lands.

## Exit Criteria
- CI builds and local bootstrap verified using new lockfile
- `load_config` calls route through shared helper exclusively
- Documentation updated and reviewed by architecture + platform leads

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint A0 canonical log. |
| 2025-10-13 | AI assistant | Added dependency inventory notes and introduced cached config helpers. |

---

_Keep this document synchronized throughout the sprint. Update status columns and log material changes in the Change Log section._
