PRODUCTION READINESS & ROADMAP for SomaBrain
============================================

Status: Draft — single-source plan for turning the local `cleanup/prepare-release` branch into a production-ready release. This file is the canonical, detailed plan that captures design decisions, priorities, tests, observability, security, release steps, migration utilities and timelines.

Goals
-----
- Ensure memory durability, observability, and correct numerics for HRR/quantum components.
- Provide reliable CI, reproducible builds, and clear release/checklist for pushing to remote registries.
- Harden operations (monitoring, alerting, metrics) so incidents are detected early and triaged quickly.
- Protect data (PII/sensitive content), provide provenance, and make migration between memory backends safe.

Acceptance criteria (what “ready for remote push” means)
--------------------------------------------------------
1. Unit and integration tests: all tests pass locally and in CI; coverage targets met for core modules (numerics, memory_client, journal, recall path).
2. Docker image builds reproducibly; smoke test verifies `/health` and `/metrics` on container startup.
3. Journaling: persistent journal append/replay validated; migration tool exists to import journal into chosen persistent backend.
4. Monitoring: Prometheus scrapes `/metrics`; Grafana dashboard imports and shows tiles & sparklines; basic alert rules trigger in test scenarios.
5. Quotas: production quota backed by durable store (Redis) or otherwise explicitly documented tradeoffs.
6. Security: admin endpoints require tokens; secrets not hard-coded; documentation includes secret management guidance.
7. Release checklist documented and followed; no remote push without manual approval by project lead.

High-level plan (phases)
------------------------
Phase A — Verify & Harden (0–3 days)
- A1 Run full test suite, fix critical failures. (P0)
- A2 Validate journaling: write memory -> confirm JSONL append -> restart server -> replay shows memory. (P0)
- A3 Add/verify CI pipeline for tests & linters. (P0)

Phase B — Observability & Alerts (1–7 days)
- B1 Build Prometheus + Grafana compose file and example `prometheus.yml`. (P1)
- B2 Create Grafana dashboard JSON (panels for the KPIs below). (P1)
- B3 Add Alertmanager rules and test alert firing. (P1)

Phase C — Durability & Scale (3–14 days)
- C1 Decide on production memory backend: persistent somafractalmemory vs external store (qdrant/faiss) + implement migration tooling. (P0/P1)
- C2 Implement Redis-backed quota manager (pluggable) or document and accept tradeoffs. (P0/P1)

Phase D — Security, Release & Ops (3–10 days)
- D1 Add token-based auth for admin endpoints; audit require_auth flow. (P0)
- D2 Add release process, automated build, and image publish (manual gate). (P1)
- D3 Add data redaction options for journaling; document retention & encryption. (P1)

Core tasks & checklist (concrete items)
---------------------------------------
Each item has: Task, Owner (TBD), Priority (P0..P2), Est Effort (hours), Acceptance.

A. Verify & Harden
- Run tests (pytest). P0, 1–3h. Acceptance: tests pass; failures triaged.
- Fix any unit test regressions introduced by numerics hardening. P0, 1–2d.
- Add integration test for remember->journal append->restart->replay->recall. P0, 4–8h. Acceptance: test passes. This guards durability.
- Add a tiny smoke script: POST /remember (sample payload) -> GET /recall -> assert memory present. P0, 2–4h.

B. Observability & Alerts
- Provide `docker-compose.monitoring.yml` including somabrain, Prometheus, Grafana, Alertmanager (optional). P1, 1–3d.
- Create `prometheus.yml` scrape config for `127.0.0.1:9696/metrics` and compose metadata. P1, 1–2h.
- Create Grafana dashboard JSON; include panels for: requests_total, avg_latency_ms, WM_utilization, WM_admits/min, journal_appends/min, quota_denies. P1, 1–2d.
- Define simple Alertmanager rules and test via synthetic load. P1, 4–8h.

C. Durability & Backend
- Choose backend (meeting production durability): either
  - Option 1: somafractalmemory with persistent storage (on-disk or object store)
  - Option 2: external vector DB (qdrant/FAISS) + metadata store (Postgres/Redis)
  Decision criteria: durability, latency, cost, operational familiarity. P0, research 1–2d.
- Implement `scripts/migrate_journal_to_backend.py` to import journal.jsonl into backend. P1, 1–3d.
- Add tests that the migration tool is idempotent and can be re-run safely. P1, 1–2d.

D. Quotas & Rate Limiting
- Implement Redis-backed `QuotaManager` with the same API. Provide config toggle. P0, 1–3d.
- Add per-tenant quota metrics and dashboards. P1, 4–8h.

E. CI / Release
- GitHub Actions or equivalent: run ruff/black, mypy (optional), pytest, build docs. P1, 1–2d.
- Add a `release` job that builds Docker image; push guarded by manual approval. P1, 1–2d.

F. Security & Governance
- Require token for sensitive endpoints; document usage & rotate keys. P0, 1–2d.
- Add optional payload redaction for journaling (configurable). P1, 1–2d.

G. Documentation & Training
- Add `docs/PRODUCTION_ROADMAP.md` (this file) to docs index; build docs in CI. P1, 2–4h.
- Add operational runbook: how to inspect metrics, how to restore journal, how to run migration. P1, 4–8h.

KPIs, metrics & alert definitions (detailed)
--------------------------------------------
This section contains the KPI formulas and example alert rules you can drop straight into Prometheus/Grafana.

Core KPIs (what to collect & why)
- requests_total (counter): baseline traffic and spike detection.
- avg_latency_ms = (somabrain_http_latency_seconds_sum / somabrain_http_latency_seconds_count) * 1000.
- errors_per_min & error_rate = delta(http_5xx_total)/min and errors/requests.
- WM_utilization = somabrain_wm_utilization (gauge 0..1).
- WM_admits_per_min = delta(somabrain_wm_admit_total) * 60000/poll_ms.
- journal_appends_per_min = delta(JOURNAL_APPEND) * 60000/poll_ms. (metric name may be `JOURNAL_APPEND` or `somabrain_journal_append_total` depending on instrumentation)
- quota_denies_per_min = delta(somabrain_quota_denied_total) * 60000/poll_ms.

Suggested thresholds (initial)
- avg_latency_ms alert: avg_latency_ms > 500ms for 3m.
- WM utilization alert: WM_utilization > 0.85 for 5m.
- Journal vs admits alert: if journal_appends_per_min == 0 AND wm_admits_per_min > 10 for 2m -> SEV1 (durability risk).
- Quota denies: quota_denies_per_min > 0 for 1m (dev) or >5/min in prod -> investigate.
- Error rate: error_rate > 0.01 AND errors_per_min > 5 -> investigate.

Example PromQL expressions
- avg latency (ms): (rate(somabrain_http_latency_seconds_sum[1m]) / rate(somabrain_http_latency_seconds_count[1m])) * 1000
- requests per min: rate(somabrain_http_requests_total[1m]) * 60
- wm admits per min: rate(somabrain_wm_admit_total[1m]) * 60
- journal appends per min: rate(somabrain_journal_append_total[1m]) * 60 OR rate(JOURNAL_APPEND[1m]) * 60

Alert example (yaml pseudo)
```
- alert: HighAvgRequestLatency
  expr: (rate(somabrain_http_latency_seconds_sum[5m]) / rate(somabrain_http_latency_seconds_count[5m])) * 1000 > 500
  for: 3m
  labels:
    severity: page
  annotations:
    summary: "High average request latency"
    description: "Average request latency > 500 ms for 3m"
```

Data migration & backup strategy
--------------------------------
- Journal (JSONL) is authoritative for single-node durability if enabled. Ensure it's written to a durable mounted volume and rotated/compacted regularly.
- For multi-node or scale-out, migrate journal to chosen backend using `scripts/migrate_journal_to_backend.py`. Migration steps:
  1. Pause writers (or coordinate a quiesce window). 2. Export journal snapshot. 3. Run migration script into backend (idempotent mode). 4. Validate count & sample records. 5. Switch reads to backend. 6. Resume writers.
- Add periodic backup job that copies journal segments to object storage with retention policy.

Security & privacy
------------------
- Require tokens for admin endpoints (X-Admin-Token) and document how to rotate.
- Journal redaction: add config `journal_redact_fields = ["content", "who"]` and optionally hash values before persist.
- Encrypt journal at rest via OS-level encrypted volumes or encryption-in-transit to object storage.

CI & release blueprint (GitHub Actions summary)
-----------------------------------------------
- jobs:
  - test: runs ruff/black (if configured), pytest, mypy; artifacts: test-report
  - docs: build docs, upload artifacts/site
  - build: build docker image and run a container smoke test (check /health /metrics), do not push automatically
  - release: manual workflow_dispatch that tags and pushes image to registry (requires manual approval)

Developer ergonomics
--------------------
- Add `.pre-commit-config.yaml` with ruff/black/isort hooks.
- Provide `scripts/dev_start.sh` that launches somabrain in dev mode with example env (non-root, reduced quotas) and `scripts/dev_stop.sh`.
- Provide `scripts/smoke_mem_test.py` to exercise remember->recall->restart->replay flows.

Rollout & rollback plan
-----------------------
- Canary rollout: publish image to internal registry, run small canary instance behind a proxy, run integration tests with canary, monitor KPIs for 15–60 minutes, then promote.
- Rollback: retain previous image tag and roll back if KPIs exceed thresholds; run `scripts/migrate_backend_rollback` if migration was performed.

Owner & communication
---------------------
- Assign owners per area (proposed):
  - Core numerics & tests: Engineering lead (math)
  - Memory backend & migration: Storage/infra lead
  - Observability & dashboards: SRE/Observability
  - Release & CI: DevOps
  - Security & governance: Security lead

How this file should be used
---------------------------
- This file is the single on-disk canonical plan for production readiness. Keep it in `docs/` and update as tasks progress. Each major task must link to a PR and reference this file's section.
- Before pushing to remote: all P0 items must be completed and checked off in a PR with green CI.

Next immediate steps (recommended)
----------------------------------
1. Approve this roadmap file and commit to local branch. (done)
2. Run full test suite and produce a test report (I can run it now, confirm?).
3. Validate journaling end-to-end (I can run an automated script that remembers a sample item, checks JSONL, restarts server and rechecks). Confirm before I proceed.

Notes & rationale (concise)
---------------------------
- Keep the monitoring math simple (averages & rates) for fast triage, then add percentiles and drift metrics as second-order improvements.
- Durability is the single most important property for this project: we are building a memory system that agents rely on. Journal + persistent backend + migration tools is the minimal safe path.
- Observability and alerting prevents data loss and operational surprises during agent experiments.

Appendices (templates & snippets)
---------------------------------
- Example small smoke script to test journaling:
```python
# scripts/smoke_mem_test.py
import requests, time
r = requests.post('http://127.0.0.1:9696/remember', json={'coord': None, 'payload':{'task':'smoke test','importance':1}})
print('remember status', r.status_code, r.text)
# check journal file and restart server externally, then recall
```

- Example Prometheus `prometheus.yml` snippet:
```yaml
scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['host.docker.internal:9696']
```

- Example Graph panel list (for Grafana):
  - Requests per minute
  - Avg latency (ms)
  - Requests by endpoint (stacked)
  - WM utilization %
  - WM admits/min
  - Journal appends/min
  - Quota denies

Document history
----------------
- 2025-09-12: Draft created from repository inspection during development session. Update the file with PR links and progress as tasks are completed.
