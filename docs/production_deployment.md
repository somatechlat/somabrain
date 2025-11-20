# Production Deployment Guide for SomaBrain

This document provides step‑by‑step instructions for deploying the **SomaBrain** platform to a production environment. It builds on the completed ROAMDP implementation and covers the following areas:

1. **Prerequisites**
2. **Infrastructure setup** (Kubernetes, Docker, or VM based)
3. **Configuration** (environment variables, secrets, and tenant settings)
4. **Service startup**
5. **Observability** (Prometheus, Grafana, Alertmanager)
6. **Backup & Recovery**
7. **Post‑deployment verification**
8. **Performance tuning**

---

## 1. Prerequisites
- Python 3.11 (managed via `pyenv` – see `.python-version`)
- Docker ≥ 24.0, Docker‑Compose ≥ 2.20
- Access to a Kafka cluster (or local `docker-compose` setup)
- PostgreSQL ≥ 13 with the migrations applied (`alembic upgrade head`)
- Kubernetes cluster (optional) with `kubectl` configured
- Helm ≥ 3.12 (if using Helm charts)
- Sufficient CPU / memory for the number of tenants you plan to serve

## 2. Infrastructure Setup
### Docker‑Compose (quick local prod)
```bash
# From the repository root
cp env.example .env
# Edit .env to set production‑grade values (e.g., DB passwords, Kafka URLs)
docker compose -f docker-compose.yml up -d
```
### Kubernetes (recommended for scale)
1. Create a namespace per tenant or a single namespace with tenant‑labelled pods.
2. Apply the Helm chart located in `charts/somabrain`:
```bash
helm upgrade --install somabrain ./charts/somabrain \
  --namespace somabrain-prod \
  -f values-prod.yaml
```
3. Ensure the `CircuitBreaker` ConfigMap and `TenantQuotaManager` Secret are populated.

## 3. Configuration
All services read configuration from the **singleton** `common.config.settings.Settings` which pulls values from environment variables. Key sections:
- **Core** – `APP_HOST`, `APP_PORT`
- **Kafka** – `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`
- **Postgres** – `POSTGRES_DSN`
- **Feature Flags** – `FEATURE_FLAGS_PORT`
- **Tenant Settings** – `DEFAULT_TENANT`, `TENANT_LABELS`

Create a `.env.production` file and source it before starting services:
```bash
export $(cat .env.production | xargs)
```

## 4. Service Startup
```bash
# Activate the correct Python version
pyenv shell 3.11.6

# Migrate the DB (run once per deployment)
alembic upgrade head

# Start the API server
uvicorn somabrain.app:app --host $APP_HOST --port $APP_PORT

# Start background workers
python -m somabrain.workers.outbox_publisher &
python -m somabrain.workers.memory_writer &
```
If using Docker‑Compose, the `docker-compose.yml` already defines these services.

## 5. Observability
- **Metrics** are exposed at `/metrics` (Prometheus format). Scrape this endpoint in your Prometheus server.
- **Grafana dashboards** are provided in `grafana/dashboards/somabrain.json`.
- **Alertmanager** rules for circuit‑breaker state and outbox backlog are in `alertmanager.yml`.

## 6. Backup & Recovery
1. **PostgreSQL** – regular `pg_dump` backups. Store in an encrypted bucket.
2. **Kafka** – enable log compaction for the outbox topic to retain the last state per key.
3. **Local Journal** (if enabled) – rotate logs daily and ship to S3.

## 7. Post‑deployment Verification
| Check | Command / Expectation |
|------|------------------------|
| API health | `curl http://$APP_HOST:$APP_PORT/health` → `{"status":"ok"}` |
| Outbox metric | `curl http://$APP_HOST:$APP_PORT/metrics` → `outbox_pending{tenant="default"}` present |
| Circuit breaker | Trigger a failure and verify `circuit_breaker_state{tenant="default",state="open"}` appears |
| Kafka connectivity | `kafka-topics.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --list` includes the outbox topic |

## 8. Performance Tuning
- **CircuitBreaker thresholds** – adjust per‑tenant thresholds in `Settings` based on observed error rates.
- **TenantQuotaManager** – configure `MAX_BATCH_SIZE` and `MAX_BATCH_RATE` to match your SLA.
- **Postgres connection pool** – increase `SQLALCHEMY_POOL_SIZE` for high concurrency.
- **Kafka producer** – enable `linger.ms` and `batch.size` for throughput.
- **Profiler** – use `py‑spy` or `cProfile` on the API process to locate hot paths.

## 9. CI Verification Jobs

The repository now includes two additional GitHub Actions jobs that help ensure a reliable production rollout:

* **`performance_test`** – Executes a lightweight k6 load‑test against the API after the `deployment_verification` job.  The test script lives in `scripts/performance/load_test.k6.js` and records latency thresholds.  Results are uploaded as the `performance-test-report` artifact.
* **`profile_critical_paths`** – Runs a short `cProfile`‑based load against the service to capture hot spots in the request handling path.  The generated `profiling_report.txt` is uploaded as the `profiling-report` artifact.

Both jobs depend on `deployment_verification`, guaranteeing they only run when a full stack deployment has succeeded.  You can view the artifacts in the GitHub Actions UI under the respective job summary.

----

**Maintainers**: @somatechlat, @infra-team
**Last updated**: ${DATE}
