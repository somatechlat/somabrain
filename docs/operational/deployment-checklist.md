# SomaBrain Deployment Checklist (Strict Mode)

- Kafka
  - Bootstrap (`SOMABRAIN_KAFKA_URL`) reachable from services
  - Topics created: `cog.state.updates`, `cog.agent.updates`, `cog.action.updates`, `cog.global.frame`, `cog.config.updates`, `cog.fusion.drift.events`, `cog.fusion.rollback.events`
  - Schema registry populated with required Avro schemas
  - Network/DNS, TLS, and ACLs configured for producers/consumers

- Redis / Postgres / OPA
  - Redis URL (`SOMABRAIN_REDIS_URL`) reachable; minimal latency and maxmemory policy set
  - Postgres reachable with migrations applied (`alembic upgrade head`)
  - OPA URL/policy configured when enabled; enforce fail-closed posture

- Environment
  - Strict mode flags set: `ENABLE_DRIFT_DETECTION`, `ENABLE_AUTO_ROLLBACK` (as desired), `SOMABRAIN_FF_COG_INTEGRATOR`
  - Disable legacy flags and fallbacks; Avro-only IO confirmed
  - Learning tenants file mounted (`config/learning.tenants.yaml`) with per-tenant `entropy_cap`
  - Drift state dir writeable (`SOMABRAIN_DRIFT_STORE`, default `./data/drift/state.json`)

- Observability
  - OpenTelemetry collector endpoint configured; API/SDK versions aligned
  - Prometheus scrape of `/metrics` endpoints enabled for services
  - Alerts: drift rate, rollback events, integrator errors, OPA veto ratio

- Health/Readiness
  - Health server enabled where supported (`HEALTH_PORT`)
  - Liveness and readiness probes configured in orchestrator (K8s)
  - Backoff/restart policy for critical services

- Security
  - Secrets injected via env or secret manager; no secrets in images
  - Network policies restrict east-west traffic; Kafka/Redis/DB only from services
  - TLS where applicable; verify certs in CI before deploy

- Testing in Env
  - Run smoke tests: produce minimal `belief_update` events and verify `global_frame` publication
  - Validate drift/rollback telemetry topics receive events under forced conditions
  - Confirm calibration service metrics and acceptance logic under sample data

- Run Commands (examples)

```sh
# Apply DB migrations
alembic upgrade head

# Start core services (compose)
docker compose -f docker-compose.yml up -d integrator calibration drift

# Verify metrics endpoints (replace host/ports accordingly)
curl -sf http://localhost:9090/metrics | head -n 20 || true

# Force a drift snapshot (if admin endpoint available)
# curl -X POST http://integrator:8080/drift/snapshot
```
