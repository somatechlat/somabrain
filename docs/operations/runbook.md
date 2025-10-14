# SomaBrain Operations Runbook

> SomaBrain runs in strict mode by default. These procedures assume real backing services with no stubs.

---

## 1. Service Topology

| Component | Purpose | Health Check |
| --- | --- | --- |
| API (`somabrain.app`) | Recall/remember/planner surface | `GET /health` (expects `{"ok": true, "ready": true}`) |
| Memory service (`somamemory`) | Vector recall + write ack | `GET /health` on memory endpoint |
| Redis | Working-memory cache, rate limiting | `redis-cli PING` |
| Kafka (optional) | Audit/event streaming | `kafka-topics --describe --bootstrap-server ...` |
| Postgres | Feedback + ledger | `psql -c 'select 1;'` |
| OPA | Policy enforcement | `curl $OPA_URL/health?plugins` |

Strict mode (`SOMABRAIN_STRICT_REAL=1`) keeps the API red until all dependencies respond.

---

## 2. Startup Checklist

1. Export strict-mode variables (`SOMABRAIN_STRICT_REAL=1`, `SOMABRAIN_FORCE_FULL_STACK=1`, `SOMABRAIN_REQUIRE_MEMORY=1`).
2. Ensure Redis, Postgres, Kafka, and the memory HTTP service are reachable.
3. Launch the API via `uvicorn` or container runtime.
4. Confirm `/health` reports `ready: true` and `stub_counts: {}`.
5. Verify Prometheus scrape (`/metrics`) and check dashboards.

If any dependency is missing, strict mode keeps the API in a failed state—investigate before admitting traffic.

---

## 3. Monitoring & Alerts

| Signal | Source | Threshold |
| --- | --- | --- |
| `somabrain_recall_latency_seconds` | Prometheus | p95 > 250ms over 5m |
| `somabrain_density_trace_error_total` | Prometheus | Any increase (rho normalization issue) |
| `somabrain_stub_usage_total` | Prometheus | Non-zero under strict mode (fatal) |
| `somabrain_planner_rate_limited_total` | Prometheus | Sudden spikes (>10/min) |
| `somabrain_memory_http_errors_total` | Prometheus | >1 per minute |

Dashboards live under `grafana/` (import `grafana_dashboard.json`). Alertmanager rules reside in `alerts.yml`.

---

## 4. Incident Response

1. **Red `/health`** – Inspect `strict_real` flag in the response, then check the dependency failing. Restart only after dependency is healthy.
2. **Memory recall failures** – Confirm `SOMABRAIN_MEMORY_HTTP_ENDPOINT` resolves. Fall back to in-process memory only if strict mode is disabled.
3. **Density matrix drift** – Review logs for `DensityMatrix.project_psd()` warnings; run `pytest tests/test_density_matrix.py` to reproduce locally.
4. **Kafka backlog** – Scale consumers in `services/smf` or pause audit streaming by toggling the relevant config in `config.yaml`.

Document any incident in the operations journal under `artifacts/journal/`.

---

## 5. Maintenance Tasks

- **Backups**: Snapshot Postgres daily; archive Redis snapshots hourly when neuromodulator feedback is heavy.
- **Rolling Deployments**: Use blue/green or canary; keep one instance in warm standby with strict mode enabled for smoke tests.
- **Schema Migrations**: Run `alembic upgrade head` while API is in maintenance. Confirm `/health` after migrations complete.
- **Chaos Exercises**: Quarterly fault-injection using `benchmarks/scale/chaos_experiment.py` to prove recovery paths.

Keep this runbook synchronized with actual production behavior—submit a PR whenever procedures change.
