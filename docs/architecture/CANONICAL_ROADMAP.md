# SomaBrain Canonical Roadmap (Sprint-Based)

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
- **NO_MOCKS policy:** tests rely on real services (or deterministic in-process emulations) and
  run in CI against the canonical stack.
- **Performance & math integrity:** memory and reasoning layers use rigorous mathematics (vector
  geometry, constrained optimization) validated with reproducible benchmarks.

## Sprint Breakdown
All sprints are two weeks unless stated otherwise. "Artifacts" refer to code paths, IaC assets,
runbooks, or dashboards that must be committed by sprint end. Status emojis will be updated at the
close of each sprint (✅ done, 🟡 in progress, 🔴 blocked).

### S0 – Baseline & Cleanup (✅ Completed)
- Consolidated container tooling into `Dockerfile` + `Docker_Canonical.yml`.
- Removed duplicate constitution module and wired `CONSTITUTION_VERIFIED` metric on startup.
- Deleted legacy roadmap/docs to establish this file as the only roadmap.

### S1 – Constitution Cloud Control & Runtime Bootstrap (Week 1–2)
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

### S2 – Audit, Kafka Backbone & Deployment Envelope (Week 3–4)
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

### S3 – Memory Fabric & Multi-View Retrieval (Week 5–6)

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
- Grafana panels for cache hit rate, write amplification, consistency alerts.

### S4 – Context Bundles, Planner Loop & Agent RPC (Week 7–8)
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

### S5 – Agent Ingress, API Contract & Developer Tooling (Week 9–10)
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

### S6 – Observability & Telemetry Mesh (Week 11–12)
**Scope**
- Instrument code paths with OpenTelemetry (trace + metrics) and configure collectors in the
  canonical stack.
- Create dashboards for governance, memory, agent-facing SLM telemetry, audit; export Grafana JSON
  to `ops/grafana/`.
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

### S7 – Identity & Secrets (Week 13–14)
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

### S8 – Mathematical Integrity & Governance Verification (Week 15–16)
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

### S8.1 – Integrate Advanced Memory & Transport Math (NEW, Week 17–18)
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

### S9 – Scale, Performance & Chaos (Week 17–18)
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

### S10 – Launch, DR & Runbooks (Week 19–20)
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
| S1 | 🟡 | Queued – awaiting constitution cloud implementation kickoff. |
| S2–S10 | 🔵 | Planned – dependent on S1 completion and infra provisioning. |

## Change Control
Updates to this roadmap require approval from the roadmap steward and must be recorded in the
project changelog. The latest signed version should be referenced in release communications and
product briefs.
