# Predictor Service API

The predictor services (`predictor-agent`, `predictor-state`, `predictor-action`) share the same lightweight HTTP interface, exposed only when the `HEALTH_PORT` environment variable is set. These services primarily run background Kafka loops; the HTTP surface is designed for operational visibility.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Returns `{ "ok": true, "service": "predictor_<domain>" }` when the loop is running. |

The health endpoint is provided for Kubernetes liveness/readiness probes. No payload is required, and a `200 OK` indicates the predictor loop started successfully.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HEALTH_PORT` | Optional port; when set, the predictor starts the FastAPI health server on this port. |
| `SOMABRAIN_FF_PREDICTOR_*` | Feature flags that enable predictor loops (`STATE`, `AGENT`, `ACTION`). |
| `ENABLE_COG_THREADS` | Composite flag; enables predictors when individual feature flags are unset. |

See `docs/cog-threads/configuration.md` for the complete list of cognitive-thread configuration options.

---

## Kafka Emissions

Predictors do not expose mutation endpoints. Instead, they continuously publish Avro-encoded belief updates to the following topics:

- `cog.state.updates`
- `cog.agent.updates`
- `cog.action.updates`

Each record adheres to `proto/cog/belief_update.avsc`. When `SOMA_COMPAT=1`, predictors also emit SOMA-compatible belief updates to the `soma.belief.*` topics. Downstream services (segmentation, integrator) consume these topics.

---

## Metrics & Tracing

- OpenTelemetry spans are emitted via `observability.provider`.
- Prometheus metrics are exported through the shared `somabrain.metrics` module when present.

Enable Prometheus scraping by configuring the platform's service monitor or PodMonitor to target the predictor pods on the metrics port defined by the base runtime.
