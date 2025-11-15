# SomaBrain ROAMDP (Canonical)

This file is the canonical Somabrain ROAMDP (Roadmap & Action Plan).
It summarizes gaps discovered in the codebase and a prioritized, phased implementation plan for development sprints.

## Summary
- Many roadmap building blocks already exist: DB-backed outbox, outbox publisher worker, metrics, and a memory service facade.
- Key gaps: per-tenant circuit-breaker isolation, tenant-aware outbox processing and metrics wiring, idempotency guarantees (DB constraints + Kafka keying), and some doc/code divergence around journaling.

## Prioritized Implementation Plan (Phases)

### Phase 0 — Safety & Observability (1–2 sprints)
- 0.1 Per-tenant circuit-breaker: convert class-level circuit state to per-tenant state in `somabrain/services/memory_service.py`. Ensure `CIRCUIT_STATE` metric is labeled by tenant.
- 0.2 Outbox pending metric wiring: implement `_update_outbox_metric()` and ensure `OUTBOX_PENDING` is updated per tenant by worker/service.
- 0.3 Tenant-aware pending queries: extend `somabrain/db/outbox.py:get_pending_events(limit, tenant_id=None)` and add appropriate DB indices.

### Phase 1 — Idempotency, DB Constraints & Worker Hardening (1–3 sprints)
- 1.1 DB constraints & indices: add migration for unique index on `(tenant_id, dedupe_key)` and index on `(status, tenant_id, created_at)`.
- 1.2 Producer keying & headers: publish Kafka messages with stable key (dedupe_key/tenant) and relevant headers.
- 1.3 Per-tenant batch quotas & backpressure: allow worker to process per-tenant batches and enforce quotas.

### Phase 2 — Replay/Recovery & Operational Tooling (1–2 sprints)
- 2.1 Admin replay endpoints: add admin API to inspect and replay pending/failed events per tenant.
- 2.2 Optional local journaling: if required, add opt-in local journal and migration script to DB-outbox.

### Phase 3 — Monitoring & Canary Rollout (1 sprint)
- 3.1 Automated alerts for per-tenant outbox/circuit metrics (Prometheus / alertmanager).
- 3.2 Feature flags & canary rollout for enabling tenant-aware behavior (admin endpoints, CLI tooling).

### Phase 4 — Tests, Docs & CI (ongoing)
- 4.1 Unit/integration tests covering tenant isolation and idempotency.
- 4.2 Update `scripts/roadmap_invariant_scanner.py` and CI invariants to assert the new behaviors.

## Concrete files to change (examples)
- `somabrain/services/memory_service.py` — per-tenant circuit state and metric wiring.
- `somabrain/db/outbox.py` & `somabrain/db/models/outbox.py` — tenant-aware queries and DB indices.
- `somabrain/workers/outbox_publisher.py` — message keying, tenant batching, and headers.
- `somabrain/metrics.py` — ensure per-tenant metrics are registered once and used consistently.
- `migrations/` — add Alembic migration to create unique index on `(tenant_id, dedupe_key)` and pending-event index.

## Acceptance Criteria (high level)
- Circuit breaker isolation per tenant; metrics labeled accordingly.
- Outbox idempotency via DB constraint + Kafka keying; no duplicate downstream events under retries.
- Per-tenant visibility and admin replay tooling.
- Dashboards & alerts reflect tenant-level health and outbox backlog.

## Notes & Next Steps
- I scanned core modules and prepared this plan. I can now:
  - (A) Prepare precise code patches for Phase 0 (per-tenant circuit-breaker + metrics wiring), or
  - (B) Draft the DB migration SQL and test plan for Phase 1, or
  - (C) Create issue/PR templates and a sprint breakdown to implement the phases in CI/CD.
- Please confirm which of the above you want me to implement next. Also confirm whether I should proceed to hard-delete demo/shim/legacy code found earlier (I will list candidates first).

---
Generated: automated synthesis of repository scan and roadmap (Nov 13, 2025).
