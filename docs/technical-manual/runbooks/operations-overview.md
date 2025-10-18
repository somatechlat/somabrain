# Operations Overview

**Purpose**: Day-two operations checklist for SomaBrain when backend enforcement is enabled.

**Audience**: Platform engineers, SREs, and on-call responders.

**Prerequisites**: Familiarity with the deployment described in `../deployment.md` and access to production monitoring tooling.

---

## Service Topology

| Component | Purpose | Health Check |
| --- | --- | --- |
| API (`somabrain.app`) | Recall, remember, planner surface | `GET /health` (expects `{ "ok": true, "ready": true }`) |
| Memory service (`somamemory`) | Vector recall + write acknowledgement | `GET /health` on memory endpoint |
| Redis | Working-memory cache and rate limiting | `redis-cli PING` |
| Kafka (optional) | Audit/event streaming | `kafka-topics --describe --bootstrap-server …` |
| Postgres | Feedback + ledger persistence | `psql -c 'select 1;'` |
| OPA | Policy enforcement | `curl $OPA_URL/health?plugins` |

Backend-enforced deployments keep `/health` red until every dependency responds. Never bypass the failures—treat them as genuine outages.

---

## Startup Checklist

1. Export backend-enforcement variables (`SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1`, `SOMABRAIN_FORCE_FULL_STACK=1`, `SOMABRAIN_REQUIRE_MEMORY=1`).
2. Ensure Redis, Postgres, Kafka, and the memory HTTP service are reachable.
3. Launch the API container or `uvicorn` process.
4. Confirm `/health` reports `ready: true` and `stub_counts: {}`.
5. Verify Prometheus scrape (`/metrics`) and Grafana dashboards.

If any dependency is missing, backend enforcement keeps the API unhealthy—investigate the root cause rather than disabling enforcement.

---

## Monitoring & Alerts

| Signal | Source | Threshold |
| --- | --- | --- |
| `somabrain_recall_latency_seconds` | Prometheus | p95 > 250ms over 5m |
| `somabrain_density_trace_error_total` | Prometheus | Any increase (ρ normalization issue) |
| `somabrain_stub_usage_total` | Prometheus | Non-zero under backend enforcement (fatal) |
| `somabrain_planner_rate_limited_total` | Prometheus | Sudden spikes (>10/min) |
| `somabrain_memory_http_errors_total` | Prometheus | >1 per minute |

Dashboards ship in `grafana/` (import `grafana_dashboard.json`). Alertmanager templates live in `alerts.yml`.

---

## Incident Response

1. **Red `/health`** – Inspect `external_backends_required` and service statuses in the response, then remediate the dependency before restarting anything.
2. **Memory recall failures** – Confirm `SOMABRAIN_MEMORY_HTTP_ENDPOINT` resolves; backend enforcement forbids silent fallbacks.
3. **Density matrix drift** – Review logs for `DensityMatrix.project_psd()` warnings and reproduce locally with `pytest tests/test_density_matrix.py`.
4. **Kafka backlog** – Scale consumers in `services/smf` or temporarily pause audit streaming via `config.yaml` flags.

Document every incident in `artifacts/journal/` to preserve operational history.

---

## Maintenance Tasks

- **Backups**: Snapshot Postgres daily; archive Redis snapshots hourly when neuromodulator feedback is heavy.
- **Rolling Deployments**: Use blue/green or canary; keep one warm standby instance for smoke tests under backend enforcement.
- **Schema Migrations**: Run `alembic upgrade head` while draining traffic. Validate `/health` afterward.
- **Chaos Exercises**: Quarterly fault-injection using `benchmarks/scale/chaos_experiment.py` to validate recovery processes.

Keep this runbook in sync with production behaviour—update it in the same PR as any operational change.
