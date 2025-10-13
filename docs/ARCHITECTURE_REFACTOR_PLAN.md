> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Architecture Refactor Plan

## 1. Architecture Vision
- Replace the monolithic `somabrain/app.py` with a layered architecture: API routers, service orchestration, domain core, adapters, and shared utilities.
- Eliminate the singleton registry in `somabrain/runtime.py` by adopting dependency injection (FastAPI `Depends`, provider container) and explicit lifecycle management.
- Segregate external integrations (Kafka, Redis, Postgres, Memory API) into typed gateways with retry/circuit-breaker policies, accompanied by contract tests.
- Normalize configuration through Pydantic settings packages per environment, loaded during process startup to prevent runtime mutation.
- Introduce a streaming/event bus abstraction to decouple command/query processing from transports, enabling comprehensive integration testing without mocks.
- Establish observability foundations: structured logging adapters, OpenTelemetry tracing, and RED metrics for every service boundary.

## 2. Prerequisite Work
- Catalog all endpoints, background jobs, and cron triggers; document ownership, SLAs, and dependencies in `docs/`.
- Assemble golden data sets for Redis/Postgres/Memory to anchor integration tests that avoid mocking.
- Define and enforce coding standards (lint/mypy settings) via pre-commit; expand Ruff rules for async pitfalls, complexity, and unsafe patterns.
- Provision a staging namespace mirroring prod ingress/TLS, including blue/green deployment scripts for refactor rollout.
- Inventory secrets/config maps and migrate to sealed secrets or SOPS with automated rotation runbooks.
- Create Architectural Decision Records (ADRs) capturing legacy choices, desired transitions, and risk acceptance.

## 3. Refactor Phases
1. **Phase 0 – Stabilize**
   - Freeze feature work, add failing regression tests for memory recall, and enforce CI gates (`ruff`, `mypy`, `pytest`, integration smoke tests).
2. **Phase 1 – Decouple API**
   - Extract router modules (`somabrain/api/memory.py`, `somabrain/api/runtime.py`), replace dummy runtime patches with dependency providers, and rework startup sequencing.
3. **Phase 2 – Domain Core**
   - Move cognitive logic into `somabrain/core/`, introduce a service layer for persistence/cache/message flows, and define explicit interfaces.
4. **Phase 3 – Infrastructure Adapters**
   - Build isolated clients for Redis/Postgres/Kafka/Memory with resilience patterns and update services to consume these interfaces.
5. **Phase 4 – Cross-Cutting Concerns**
   - Implement structured logging, metrics, tracing, feature flags, and configuration versioning.
6. **Phase 5 – Hardening**
   - Run load/stress benchmarks, remediate bottlenecks, and finalize runbooks plus disaster recovery drills.

## 4. Sprint Roadmap (2-week cadence)
- **Sprint 1**
  - Enforce CI gates, add ownership documentation, capture golden datasets, write failing memory recall tests, draft ADRs for DI adoption.
  - Deliverables: Passing CI, `docs/ownership.md`, `/remember`↔`/recall` regression tests, ADR-001.
- **Sprint 2**
  - Extract API routers, implement the DI container skeleton, migrate health endpoints, and refactor tests to new structure.
  - Deliverables: `somabrain/api/` package, `somabrain/container.py`, passing integration suite, updated runbook.
- **Sprint 3**
  - Move domain logic into `somabrain/core/`, introduce service layer interfaces, scaffold adapters for memory and Redis clients.
  - Deliverables: `core/memory_service.py`, `adapters/memory_client.py`, contract tests against live services, ADR-002.
- **Sprint 4**
  - Complete adapter refactors (Postgres, Kafka), wire resilience patterns, update background jobs to use new services.
  - Deliverables: Adapter suite, chaos test scripts, updated cron/job manifests.
- **Sprint 5**
  - Implement observability stack (OpenTelemetry, RED metrics), enhance logging, integrate tracing dashboards.
  - Deliverables: Grafana dashboards, tracing configuration, logging style guide.
- **Sprint 6**
  - Performance hardening, execute load tests, automate blue/green deploys, finalize DR and rollback runbooks.
  - Deliverables: `scripts/deploy_blue_green.sh`, load test reports, DR checklist.

## 5. Immediate Next Steps
1. Approve the roadmap scope and sprint cadence.
2. Assign owners for Phase 0 tasks and kick off Sprint 1 backlog grooming.
3. Schedule an architecture review to validate the dependency injection/container design before Sprint 2 execution.
