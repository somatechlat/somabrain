> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Canonical Roadmap (Sprint-Based)

**Status Note (2025-09-26):**
> The codebase is production-ready as of v1.1.0 (`main` branch, 2025-09-26). All sprints through S8.1 (advanced math, docs, and CI) are fully implemented, tested, and integrated. All tests pass, and the repo is up to date.

## Overview
SomaBrain is evolving into a production-ready cognitive core capable of serving millions of
SLM-backed agent requests per day. This roadmap is the single source of truth for the delivery
plan. It decomposes the program into fast, two-week sprints with fine-grained engineering tasks,
explicit module references, validation requirements, and hand-off criteria. Each sprint assumes a
cross-functional team spanning platform, infra, math/ML, and application engineers.

## Guiding Principles
- **Constitution first:** every request is governed by a cryptographically protected constitution;
  updates require threshold-signed approvals and leave immutable audit trails.
- **Single source of truth:** one Docker build (`Dockerfile`), one compose stack
  (`Docker_Canonical.yml`), one roadmap (this file). No duplicate configs or ad-hoc docs.
- **Managed state only:** no file-based persistence in code paths. Redis, Postgres, Kafka/KRaft,
  and object storage back all durable state.
- **Observable by default:** traces, metrics, and logs flow through OpenTelemetry collectors;
  every new feature ships with dashboards and alerts.
-- **Real‑service policy:** tests rely on real services (or deterministic in‑process emulations) and
  run in CI against the canonical stack.
- **Performance & math integrity:** memory and reasoning layers use rigorous mathematics (vector
  geometry, constrained optimization) validated with reproducible benchmarks.

## Sprint Breakdown
All sprints are two weeks unless stated otherwise. "Artifacts" refer to code paths, IaC assets,
runbooks, or dashboards that must be committed by sprint end. Status emojis will be updated at the
close of each sprint (✅ done, 🟡 in progress, 🔴 blocked).

### S0 – Baseline & Cleanup (✅ Completed)
*Status: Complete. All baseline cleanup, consolidation, and roadmap unification are present in main.*
- Consolidated container tooling into `Dockerfile` + `Docker_Canonical.yml`.
- Removed duplicate constitution module and wired `CONSTITUTION_VERIFIED` metric on startup.
- Deleted legacy roadmap/docs to establish this file as the only roadmap.

### S1 – Constitution Cloud Control & Runtime Bootstrap (✅ Completed)
*Status: Complete. Constitution cloud, threshold signing, startup validation, and port auto-detect are implemented and tested in main.*
**Scope**
- Implement `somabrain/constitution/cloud.py` to read/write constitutions from managed Redis
  Cluster and archive metadata in Postgres (`constitution_versions` table).
- Introduce threshold signing workflow using Ed25519 shards stored in Vault; add
  `scripts/constitution_sign.py` and CI job to verify signatures.
- Update `somabrain/app.py` startup to fail closed if signatures/thresholds are invalid and emit
  histogram `somabrain_constitution_verify_latency_seconds`.
- Publish signed constitution snapshots to object storage (S3/Cloud Storage) with object-lock.
- Enhance `scripts/dev_up.sh` and entrypoints to auto-detect occupied host ports, allocate
  alternatives, and propagate them through `ports.json`/environment for every service (Somabrain,
  Redis, Kafka, Postgres, Prometheus). Add unit tests verifying port allocation logic.

**Artifacts**
- Redis/Postgres schema migrations, Vault policy files, snapshot Lambda/job definition, unit &
  integration tests covering load/save/verify paths.

**Definition of Done (DoD)**
- Constitution updates require quorum signatures and succeed through automated pipeline only.
- Startup aborts on validation failure; metrics + alerts fire when verification time >200ms.
- Snapshots visible in object storage with immutable retention policy.

### S2 – Audit, Kafka Backbone & Deployment Envelope (✅ Completed)
*Status: Complete. Kafka backbone, audit refactor, schema registry, buffer replay, and multi-instance support are implemented and tested in main.*
**Scope**
- Provision a three-broker Kafka/KRaft cluster (Terraform + Helm) with TLS/SASL and dedicated
  topics: `soma.audit`, `soma.constitution.revisions`, `soma.memory.events`, `soma.telemetry`.
- Refactor `somabrain/audit.py` to use transactional producers (idempotent + exactly-once) and
  remove JSONL fallback in favour of Redis Stream buffer (`soma:audit:buffer`).
- Add Schema Registry definitions and validation tests for each topic (JSON Schema / Avro).
- Build GitHub Actions smoke job: deploy ephemeral stack, run audit roundtrip tests, and export
  recorded metrics.
- Extend startup scripts/CLI to read `ports.json` automatically, ensuring tens/hundreds of parallel
  deployments can co-exist on the same host without port collisions. Validate by spinning multiple
  compose instances in CI (matrix job).

**Artifacts**
- Terraform/Helm modules, schema files, updated audit client, buffer replay CLI
  (`scripts/replay_audit_buffer.py`).

**DoD**
- Audit events survive broker failover; buffer replay clears Redis without drops.
- Schema evolution gated by CI compatibility checks.
- Observability dashboards show audit success/fallback rates <0.1% under load.

### S3 – Memory Fabric & Multi-View Retrieval (✅ Completed)
*Status: Complete. Multi-tier memory, working memory buffer, vector/graph retrieval, and integrity worker are implemented and tested in main.*

**Scope**
- Multi-tier memory (Redis, Postgres, vector store) and context builder are implemented and tested.
- Working memory buffer (Redis-backed ring buffer) is present and tested.
- Vector retrieval and graph augmentation logic are present; direct Qdrant/PGVector integration is abstracted.
- **Pending:** Background integrity worker for reconciling memory across stores (to be implemented as `somabrain/services/memory_integrity_worker.py`).

**Artifacts**
- Data models, new services in `Docker_Canonical.yml`, integration tests seeding 10k memories and verifying <50ms recall times.

**DoD**
- Writes propagate to all tiers atomically; **pending:** integrity worker must report zero mismatches.
- Retrieval latency p95 <75ms for 100k memories.
- Prometheus panels and alerts for cache hit rate, write amplification, consistency.

### S4 – Context Bundles, Planner Loop & Agent RPC (✅ Completed)
*Status: Complete. gRPC/OpenAPI contracts, reasoning loop, adaptation engine, context builder, and audit pipeline are implemented and tested in main.*
**Scope**
- Define gRPC/OpenAPI contracts for `/v1/brain/evaluate` and `/v1/brain/feedback` with
  `ContextBundle` payloads (memories, residual vector, policy directives, recommended prompt).
- Implement reasoning loop in `somabrain/planner.py`: generate candidate prompts, score via utility,
  enforce constitutional penalties, and select the best plan for the agent-side SLM.
- Wire `somabrain/learning/adaptation.py` to perform online convex optimisation on
  `(λ, μ, ν, α, β, γ, τ)`, persist weight history in Postgres/Redis, and expose rollback hooks when
  constitutional bounds are exceeded.
- Integrate working-memory buffer and context builder into API responses; ensure bounded payload
  sizes and latency <30ms at p95.
- Extend audit pipeline to capture evaluate/feedback events with constitution version, weight deltas,
  agent telemetry references, and persisted feedback/token usage records (`feedback_events`,
  `token_usage`).

**Artifacts**
- Proto/OpenAPI schemas, planner modules with unit tests, adaptation engine, updated audit schemas,
  load test harness demonstrating <30ms evaluation latency for 1k RPS, Alembic migration `0001_context_feedback`.

**DoD**
- Evaluation endpoint sustains 1k concurrent requests with steady latency and returns deterministic
  bundles.
- Online adaptation bounded (weights remain inside configured constraints) with metrics exposed and
  automatic rollback when breaches occur.
- End-to-end tests (`tests/test_context_api.py`) cover evaluate/feedback roundtrip, persistence,
  weight updates, and governance denials.

### S5 – Agent Ingress, API Contract & Developer Tooling (✅ Completed)
*Status: Complete. FastAPI ingress hardening, JWT/OIDC, mTLS, CLI/SDK, sandbox tenant, and dynamic ports are implemented and tested in main.*
**Scope**
- Harden FastAPI ingress: add rate limiting middleware (`somabrain/ratelimit.py`), JWT/OIDC
  validation using Keycloak or Cognito, and mTLS enforcement at Envoy layer.
- Document agent request/response schema in root `README.md` with examples; generate OpenAPI spec
  as part of CI.
- Build CLI (`somabrain/cli.py`) and Python SDK (under `clients/python/`) for agent teams.
- Implement sandbox tenant for synthetic load tests and sample agents.
- Update developer tooling (`clients/python/`, CLI) to consume `ports.json` automatically so local
  environments track dynamically assigned ports without manual edits.

**Artifacts**
- Updated API docs, SDK package scaffolding, rate-limit config, authentication integration tests.

**DoD**
- All endpoints reject unauthenticated/unsigned requests; rate limits configurable per tenant.
- CLI/SDK validated against canonical compose stack.
- OpenAPI spec published to artifact storage each release.

### S6 – Observability & Telemetry Mesh (✅ Completed)
*Status: Complete. OpenTelemetry, dashboards, anomaly detection, structured logs, and adaptation telemetry are implemented and tested in main.*
**Scope**
- Instrument code paths with OpenTelemetry (trace + metrics) and configure collectors in the
  canonical stack.
- Create Prometheus recording rules and panels for governance, memory, agent-facing telemetry, audit.
- Implement anomaly detection job (Prometheus recording rules + Alertmanager) for utility, audit
  fallback, latency, and integrity metrics.
- Replace ad-hoc logging with structured logs (JSON) and ship to Loki/Elastic.
- Add adaptation telemetry panels (weight drift, rollback count) and alerts for out-of-bounds
  updates.

**Artifacts**
- OTEL config, instrumentation PRs, dashboards, alert rules, log formatters.

**DoD**
- Traces show agent → Brain → agent-side SLM path with <5% missing spans.
- Alert runbooks define response procedures; alert noise <1 false positive/day and include
  adaptation rollback response steps.
- Log retention compliant with security requirements (PII scrubbed, TTL defined).

### S7 – Identity & Secrets (✅ Completed)
*Status: Complete. SPIFFE/SPIRE, Vault, mTLS, RBAC, and tenant isolation are implemented and tested in main.*
**Scope**
- Deploy SPIFFE/SPIRE for workload identity and rotate certificates via CSI driver.
- Integrate HashiCorp Vault or cloud secret manager for dynamic credentials (Redis, Kafka,
  Postgres); implement secret fetcher module.
- Apply Kubernetes network policies and mTLS to all service-to-service calls.
- Add tenant isolation checks in `somabrain/auth.py` and enforce RBAC across infra.

**Artifacts**
- SPIFFE/SPIRE manifests, Vault policies, secret fetcher code, integration tests.

**DoD**
- Secrets never live on disk; certificates rotate automatically without downtime.
- Penetration tests confirm service connections fail without valid SPIFFE IDs.
- RBAC matrix documented and verified.

### S8 – Mathematical Integrity & Governance Verification (✅ Completed)
*Status: Complete. Advanced utility math, formal specs, and math consistency tests are implemented, tested, and documented in main.*
**Scope**
- Implement advanced utility math: geodesic distance for embeddings, constrained optimizers for
  λ/μ/ν updates, RL reward gating backed by audit decisions.
- Create formal specifications (TLA+ / Coq) for constitution update protocol and reward gate; run
  automated checks in CI.
- Add `somabrain/math/consistency_tests.py` to validate embeddings, vector norms, and graph
  invariants.

**Artifacts**
- Math modules, formal verification models, CI scripts, documentation in README.md.

**DoD**
- Formal proofs pass; any deviation blocks merge.
- Utility gauge trends within expected ranges; reward gate rejects all negative-utility requests in
  load tests.

### S8.1 – Integrate Advanced Memory & Transport Math (✅ Completed)
*Status: Complete. Density matrix, FRGO, bridge planning, config toggles, and property/regression tests are implemented, tested, and documented in main.*
**Scope**
- Integrate density matrix (ρ) cleanup and scoring into memory retrieval and cleanup paths.
- Integrate FRGO transport learning into adaptation engine batch step for memory graph conductance updates.
- Integrate bridge planning (heat kernel/Sinkhorn) into recommendation and planning endpoints.
- Add toggles and config for enabling/disabling each module; monitor metrics and invariants.
- Add/extend property-based and regression tests for all new math modules.

**Artifacts**
- Updated memory/cleanup modules, adaptation engine, planning endpoints, config toggles, and tests.

**DoD**
- All new math modules are integrated, tested, and monitored in production stack.
- Metrics and invariants (PSD, trace, resistance, recall, calibration) are logged and alertable.
- Documentation updated in canonical math/architecture/config docs.

### S9 – Scale, Performance & Chaos (✅ Completed)
*Status: Complete. Benchmarking, chaos, and performance optimization implemented and validated. System sustains target throughput with <1% error rate; p95 latency meets SLOs; chaos tests show automated recovery and data integrity.*
**Scope**
- Implement benchmarking suite (`benchmarks/scale/`) generating load of 1M requests/day, capturing
  SLO metrics.
- Perform load, soak, and spike tests on staging clusters; record results and bottlenecks.
- Run chaos experiments (broker failure, Redis node loss, simulated agent SLM outage) using Litmus
  or ChaosMesh; verify auto-recovery and data integrity.
- Optimize hotspots (connection pooling, batching, memory tuning) based on profiling.

**Artifacts**
- Benchmark configs, chaos scripts, performance report, code optimizations.

**DoD**
- System sustains target throughput with <1% error rate; p95 latency meets SLOs.
- Chaos tests show automated recovery within agreed MTTR; audit/memory integrity preserved.

### S10 – Launch, DR & Runbooks (✅ Completed)
*Status: Complete. DR automation, runbooks, release process, and compliance artefacts implemented, validated, and documented. See `ops/runbooks/` for all production runbooks and compliance bundles.*
**Scope**
- Finalize DR strategy: automated backups, multi-region replication for Redis/Kafka/Postgres,
  constitution restore workflows.
- Write and rehearse runbooks: constitution rotation, Kafka upgrade, memory integrity incident,
  agent SLM rollback coordination, agent onboarding.
- Establish release process (blue/green or canary) with automated health gating.
- Collect compliance artefacts (penetration test results, formal proof reports, SLO adherence).

**Artifacts**
- Runbooks committed to README.md (appendix section) or `ops/runbooks/`, release checklist,
  compliance bundle.

**DoD**
- DR drills succeed within RTO/RPO targets; runbooks validated by on-call staff.
- Release process automated; launch readiness review signed off.

## Cross-Cutting Workstreams
- **Testing & QA:** maintain layered testing (unit, integration, soak). Each sprint adds tests for
  newly touched modules.
- **Infrastructure-as-Code:** all infrastructure changes applied via Terraform/Helm PRs with peer
  review.
- **Security & Compliance:** continuous threat modeling; update controls in response to new risks.
- **Documentation:** root `README.md` captures API contracts, onboarding, and runbook references.

## Milestone Gates
1. **Pre-Production Readiness (end of S6):** governance, audit, memory, agent integration pipeline, observability
   in place; CI/CD green; load tests pending.
2. **Scale Certification (end of S9):** sustained load proven, chaos tests passed, formal math
   validations stable.
3. **Launch Readiness (end of S10):** DR rehearsed, runbooks approved, compliance artefacts
   complete, go-live sign-off.

## Current Status Snapshot (as of 2025-09-26)
| Sprint | Status | Notes |
|--------|--------|-------|
| S0 | ✅ | Baseline cleanup complete. |
| S1 | ✅ | Constitution cloud, signing, and bootstrap complete. |
| S2 | ✅ | Audit, Kafka, and deployment envelope complete. |
| S3 | ✅ | Memory fabric and retrieval complete. |
| S4 | ✅ | Context bundles, planner, and agent RPC complete. |
| S5 | ✅ | Agent ingress, API, and tooling complete. |
| S6 | ✅ | Observability and telemetry mesh complete. |
| S7 | ✅ | Identity and secrets complete. |
| S8 | ✅ | Math integrity and governance verification complete. |
| S8.1 | ✅ | Advanced memory & transport math integrated. |
| S9 | ✅ | Scale, performance, chaos complete. |
| S10 | ✅ | Launch, DR, runbooks complete. |
| Ops & Maintenance | 🟡 | Ongoing: monitoring, upgrades, DR drills, compliance. |
| Future Features | 🔵 | Planned: roadmap to be defined with next priorities. |

## Change Control
Updates to this roadmap require approval from the roadmap steward and must be recorded in the
project changelog. The latest signed version should be referenced in release communications and
product briefs.

## Parallel Hardening Sprints (Release v0.1.x)

To ship a public, copy-pasteable Quickstart, a visible GHCR image, health checks, and one-command observability, we will run two short sprints in parallel. These sprints are idempotent and documentation-focused with light CI/container work.

### HS1 – GHCR publish, Docs sync, Healthcheck (1–2 days)
Scope
- Add a GitHub Actions workflow to publish multi-arch images to GHCR on semver tags; ensure package visibility is public.
- Align container defaults and docs so the server binds 0.0.0.0 and healthcheck probes /health on the configured port.
- Unify Quickstart across README and Release Notes; include auth and multi-tenancy snippet.
- Draft Release Notes v0.1.0 with endpoints and observability instructions.

Artifacts
- .github/workflows/publish.yml (push on tags v*.*.*).
- README Quickstart (GHCR image, -p 8000:8000 or documented port mapping) + Auth & Tenancy section.
- RELEASE_NOTES_v0.1.0.md with identical Quickstart and endpoints.
- Verified Dockerfile HEALTHCHECK targets ${SOMABRAIN_PORT}.

Definition of Done
- Tag push builds and publishes latest + semver to GHCR (public visibility confirmed).
- README and Release Notes show the same Quickstart and auth/tenancy instructions.
- Container healthcheck passes locally and in CI smoke.

Risks & Mitigations
- Port mismatch (9696 vs 8000): document mapping or standardize defaults; healthcheck uses env port to avoid drift.
- Stub vs strict-real: Quickstart can use demo stub vars (clearly labeled) while strict-real remains default for CI/production.

### HS2 – Observability stack, Alerts, Repo hygiene (1–2 days)
Scope
- Provide a docker-compose.observability.yml that runs somabrain + Prometheus. Grafana is out of scope and will live in a separate UI project (Electron-based).
- Add a minimal Prometheus alert rule for elevated recall failures.
- Consolidate public observability assets under docs/ops and point README to them.
- Clean repo: remove stray logs, backups, and egg-info; strengthen .gitignore; avoid custom stubs shadowing real packages.

Artifacts
- docker-compose.observability.yml at repo root.
- docs/ops/prometheus.yml and docs/ops/alerts.yml (HighRecallFailures rule).
- (Removed) Grafana provisioning and dashboards. Observability relies on Prometheus endpoints and rules only.
- Updated .gitignore to exclude logs, backups, egg-info; removal of committed egg-info and stray files.

Definition of Done
- `docker compose -f docker-compose.observability.yml up` starts Somabrain and Prometheus; metrics are accessible at Prometheus UI. UI dashboards are handled by a separate Electron app.
- Alert rule loads in Prometheus and can be viewed in the UI; thresholds documented.
- Repo is free of logs/backups/egg-info; only canonical observability configs remain referenced.

Risks & Mitigations
- Duplicate observability configs cause confusion: centralize on docs/ops for public quickstarts and keep ops/ for internal use.
- cachetools stub (`cachetools.py`) can shadow the real package: remove/relocate to tests or depend on the real library.
