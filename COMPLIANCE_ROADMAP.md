> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Compliance Roadmap

**Goal:** Transform the current SomaBrain code‑base into a **first‑class
service** that runs on the shared‑infra platform (auth, OPA, Redis, Etcd,
Kafka, OpenTelemetry, Helm, CI). All changes use **real services** – no mocks or
stubs – and are organized into **parallel sprints** that can be executed
simultaneously.

---

## Sprint Overview

| Sprint | Focus | Key Deliverables | Approx. Effort |
|-------|-------|------------------|----------------|
| **Sprint 0 – Foundations** | Project scaffolding | • Create `common` package (`__init__`, `utils` sub‑package)\n• Add `common/config/settings.py` (already present)\n• Add CI helper scripts (`scripts/run_integration.sh`) | 1 day |
| **Sprint 1 – Centralised Configuration** | Migrate all env‑var accesses to `Settings` | • Replace every `os.getenv` with `settings.<field>`\n• Update `somabrain/storage/db.py` to use `settings.postgres_dsn`\n• Add import `from common.config.settings import settings` where needed | 2 days |
| **Sprint 2 – gRPC‑only Memory Service** | Expose memory via gRPC on port 50052 | • Generate stubs from `memory.proto`\n• Add a gRPC server entry‑point (`grpc_server.py`)\n• Remove the HTTP memory endpoint (`/memory/*`)\n• Update clients to call the gRPC stub | 3 days |
| **Sprint 3 – Real Cache & Feature‑Flag Layer** | Add Redis cache wrapper & Etcd flag client | • `common/utils/cache.py` (TTL cache around redis)\n• `common/utils/etcd_client.py` (get/put for flags)\n• Update `memory_client.py` to use cache first and flags via Etcd | 3 days |
| **Sprint 4 – Auth & OPA Integration** | Delegate auth to central service & enforce OPA | • `common/utils/auth_client.py` (HTTP call to `auth.soma‑infra.svc.cluster.local:8080`)\n• Refactor `somabrain/auth.py` to use the client\n• Ensure OPA middleware points at side‑car (`http://localhost:8181/v1/data/sb/policy`) | 2 days |
| **Sprint 5 – Observability, Health & Readiness** | OpenTelemetry, metrics, probes | • Add `common/utils/trace.py` (OTEL init with service name `sb`)\n• Add `/healthz` (DB, Redis, Kafka) and `/ready` (migration check) endpoints\n• Expose shared `/metrics` endpoint (Prometheus) | 2 days |
| **Sprint 6 – Dockerfile & Helm Chart** | Production‑ready image & deployment | • Update `Dockerfile` to `python:3.11‑slim`, expose 50052 & 8080, add OCI labels, build‑arg `VERSION`\n• Entry‑point runs `alembic upgrade head` then starts gRPC server\n• Create Helm sub‑chart `helm/charts/sb/` with OPA side‑car, Vault init, probes, ConfigMap/Secret mounts | 4 days |
| **Sprint 7 – CI/CD Extensions** | Automated integration testing | • Extend `.github/workflows/ci.yml` to spin up a Kind cluster, install shared‑infra chart, then install `sb` chart\n• Run real integration tests (no mocks) against gRPC endpoint\n• Add Trivy scan, push image with tag `sha-${{ github.sha }}` | 3 days |

---

## Parallel Execution Strategy

Sprints **2, 3, and 4** can run concurrently because they touch separate
concerns (configuration, cache/flags, auth).  Sprints **5** and **6** depend on
the outputs of the earlier sprints, and **Sprint 7** depends on the final Helm
chart and Docker image.

### Suggested workflow

1. **Create feature branches** for each sprint (e.g. `sprint-1-config`,
   `sprint-2-grpc`, `sprint-3-cache`).
2. Open pull‑requests; CI runs on each branch independently.
3. Merge the branches in any order once CI passes – the changes are orthogonal,
   so merge conflicts are unlikely.
4. After **Sprint 5** is merged, open a PR for **Sprint 6** (Docker & Helm).
5. Finally, open the **CI/CD** PR (**Sprint 7**) which references the new
   Helm chart.

---

## Acceptance Criteria (per sprint)

All tests must pass against the **real stack** (Docker Compose or Kind).

| Sprint | Success Indicator |
|-------|-------------------|
| 0 | Scaffold files exist; CI can lint them |
| 1 | No `os.getenv` calls remain; `settings` is used everywhere |
| 2 | `grpc_server.py` starts on port 50052 and memory calls succeed |
| 3 | Cache hits are recorded; Etcd flag reads reflect actual keys |
| 4 | Auth requests are validated by the external service; OPA denies when policy says so |
| 5 | `/healthz` returns 200 with DB/Redis/Kafka checks; `/ready` only after migrations |
| 6 | Docker image builds, runs migrations, starts gRPC server; Helm chart installs cleanly |
| 7 | CI pipeline creates a Kind cluster, installs infra, runs integration tests, pushes image, and fails on Trivy critical CVEs |

---

**Next immediate step:**
1. Create the branch `compliance‑roadmap`.
2. Push this file so the team can start the parallel sprints.

*Prepared by the AI‑assisted development assistant.*
