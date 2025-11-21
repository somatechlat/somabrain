# Integrator Hub v2 (softmax/OPA/Redis)

## Overview
- Consumes `predictor_update` events (state/agent/action) from Kafka.
- Computes confidence `exp(-alpha * error)` and selects leader via softmax with configurable temperature.
- Optional OPA veto: POSTs `{input: {leader, weights}}` to `SOMABRAIN_OPA_URL`; rejects publish if result is false.
- Optional Redis cache: stores latest global frame at `globalframe:{leader}` with 5m TTL.
- Publishing and leader election gated by `ENABLE_COG_THREADS` (default off).

## Settings (single source: `common.config.settings` / env)
- `ENABLE_COG_THREADS` (default `0`)
- `SOMABRAIN_PREDICTOR_ALPHA` (confidence mapping)
- `SOMABRAIN_INTEGRATOR_TEMPERATURE` (softmax temperature; <=0 uses argmax)
- `SOMABRAIN_INTEGRATOR_HEALTH_PORT` (default 9015)
- `SOMABRAIN_TOPIC_STATE_UPDATES`, `SOMABRAIN_TOPIC_AGENT_UPDATES`, `SOMABRAIN_TOPIC_ACTION_UPDATES`, `SOMABRAIN_TOPIC_GLOBAL_FRAME`
- `SOMABRAIN_KAFKA_URL` (bootstrap), `SOMABRAIN_REDIS_URL` (via `get_redis_url`), `SOMABRAIN_OPA_URL` (optional)

## Metrics
- `somabrain_integrator_leader_total{leader}`
- `somabrain_integrator_error{domain}`
- `somabrain_integrator_opa_reject_total{leader}`
- `somabrain_integrator_redis_cache_total{leader}`

## Operational Notes
- Keep `ENABLE_COG_THREADS=0` until Kafka/Redis smoke is validated in CI.
- If OPA is unavailable, integrations continue (publish skipped only on explicit veto or request failure).
- Redis cache is best-effort; failures do not block publishing.
