# Cognitive-Thread Configuration

This guide captures every feature flag, environment variable, and Helm value that controls the cognitive-thread services. It reflects the canonical roadmap and the production deployment model. All configuration is ASCII-safe and backed by real code in this repository.

---

## Flag Surface Area

| Flag | Default | Description | Services |
|------|---------|-------------|----------|
| `ENABLE_COG_THREADS` | `0` | Composite switch that enables all cognitive-thread workers when set. Required for any predictor/segmentation/integrator workload. | Predictors, Segmentation, Integrator |
| `SOMABRAIN_FF_PREDICTOR_STATE` | `0` | Enables the state predictor loop and its FastAPI health endpoint. | `services/predictor-state/main.py` |
| `SOMABRAIN_FF_PREDICTOR_AGENT` | `0` | Enables the agent predictor loop. | `services/predictor-agent/main.py` |
| `SOMABRAIN_FF_PREDICTOR_ACTION` | `0` | Enables the action predictor loop. | `services/predictor-action/main.py` |
| `SOMABRAIN_FF_COG_SEGMENTATION` | `0` | Turns on the segmentation service (leader-change or CPD mode). | `somabrain/services/segmentation_service.py` |
| `SOMABRAIN_FF_COG_INTEGRATOR` | `0` | Starts the integrator hub processing and OPA/Redis integration. | `somabrain/services/integrator_hub.py` |
| `SOMA_COMPAT` | `0` | Emits legacy SOMA-compatible belief updates and integrator context records when true. | Predictors, Integrator |
| `SOMABRAIN_FORCE_FULL_STACK` | `0` | Forces all dependent services (Kafka, Redis, etc.) to be available or the API raises. | Core API |
| `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | `0` | Rejects requests when the external memory backend is unavailable. | Core API |

> **Tip:** The feature flags above are also accessible through `common.config.settings.Settings` (e.g. `Settings().force_full_stack`). Prefer using `Settings` in new code; direct `os.getenv` lookups remain for backward compatibility only.

---

## Predictor Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOMABRAIN_KAFKA_URL` | `kafka://localhost:30001` | Bootstrap servers for all producers. Shared across every service. |
| `SOMABRAIN_DEFAULT_TENANT` | `public` | Tenant identifier embedded in Avro records. |
| `AGENT_UPDATE_PERIOD` / `STATE_UPDATE_PERIOD` / `ACTION_UPDATE_PERIOD` | `0.7` / `0.5` / `0.9` | Sleep intervals (seconds) between emissions. |
| `AGENT_MODEL_VER` / `STATE_MODEL_VER` / `ACTION_MODEL_VER` | `v1` | Model version string written to `posterior` metadata. |
| `SOMA_COMPAT` | see table above | Adds SOMA legacy topics (`soma.belief.*`) to each producer. |
| `HEALTH_PORT` | unset | When provided, the predictor starts a FastAPI health server on the specified port. |

Predictor services live under `services/predictor-*`. Each entrypoint reads the configuration shown and uses `libs.kafka_cog.AvrosSerde` for schema enforcement.

---

## Segmentation Service Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOMABRAIN_SEGMENT_MODE` | `leader` | Determines the processing mode: `leader` (GlobalFrame based) or `cpd` (Change Point Detection). |
| `SOMABRAIN_SEGMENT_MAX_DWELL_MS` | `0` | Optional dwell cap; emits a boundary when exceeded even if the leader is unchanged. |
| `SOMABRAIN_CPD_MIN_SAMPLES` | `20` | Warm-up samples required before CPD decisions. |
| `SOMABRAIN_CPD_Z` | `4.0` | Z-score threshold for CPD mode. |
| `SOMABRAIN_CPD_MIN_GAP_MS` | `1000` | Minimum milliseconds between CPD boundaries per domain. |
| `SOMABRAIN_CPD_MIN_STD` | `0.02` | Floor on running standard deviation to avoid divide-by-zero. |
| `SOMABRAIN_CONSUMER_GROUP` | `segmentation-service` | Kafka consumer group id. |
| `HEALTH_PORT` | unset | Optional FastAPI health probe server. |

The service initialises metrics (`somabrain_segments_emitted_total`, `somabrain_segments_dwell_ms`) and uses Avro schemas from `proto/cog/` when available.

---

## Integrator Hub Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOMABRAIN_REDIS_URL` | unset | Redis cache for the latest GlobalFrame per tenant. |
| `SHADOW_RATIO` | `0.0` | Fraction of frames routed to the shadow topic for evaluation. |
| `SOMABRAIN_OPA_URL` | unset | Base URL for OPA policy queries. |
| `SOMABRAIN_OPA_POLICY` | unset | Policy path (e.g. `soma.policy.integrator`). |
| `SOMA_OPA_FAIL_CLOSED` | `false` | When true, deny frames if OPA is unreachable. |
| `SOMA_COMPAT` | `0` | Publishes SOMA-integrator compatibility records to `soma.integrator.context`. |
| `SOMABRAIN_CONSUMER_GROUP` | `integrator-hub-v1` | Kafka consumer group id. |
| `SOMABRAIN_FF_COG_INTEGRATOR` | see flag table | Primary feature toggle for the service. |
| `HEALTH_PORT` | unset | Optional FastAPI health probe server. |

The hub exposes Prometheus counters (`somabrain_integrator_updates_total`, `somabrain_integrator_frames_total`, etc.) and relies on the Avro schemas `belief_update.avsc`, `global_frame.avsc`, and `integrator_context.avsc` under `proto/cog/`.

---

## OPA policies

Policies live under `ops/opa/policies/` (e.g., `ops/opa/policies/integrator.rego`, package `soma.policy.integrator`).

Local docker-compose mounts this directory into the OPA container so you can iterate without a bundle server. In Kubernetes, the `soma-infra` chart depends on an OPA chart; policy delivery can be handled via your platform’s bundle mechanism or a ConfigMap/volume as appropriate for the environment.

---

## Configuration Sources & Priority

1. **Helm values** (`infra/helm/charts/soma-apps/values.yaml`) – declare defaults for every environment. The `envCommon` block maps directly to the tables above. A top-level `featureFlags.enableCogThreads` is provided; the Helm templates translate it into `ENABLE_COG_THREADS` in each deployment so you can flip the entire pipeline with one value.
2. **Environment variables** – `docker-compose.yml`, CI runners, and Kubernetes can override Helm values at runtime.
3. **`.env` files** – local development uses `.env.local` or `.env` generated by `scripts/generate_global_env.sh`.
4. **Code defaults** – each service provides safe fallbacks so unit tests do not require the full stack.

`common.config.settings.Settings` merges these layers and provides typed access. Prefer injecting `Settings()` where possible to keep configuration consistent across services.

---

## Validation & Tests

- `tests/kafka/test_avro_contracts.py` ensures all Avro schemas exist and can round-trip via `fastavro` when available.
- CI enforces `pytest --cov` with a minimum coverage of 85%, linting (ruff, black, mypy), Dockerfile scans, and Helm linting (see `.github/workflows/ci.yml`).
- Integration tests (`tests/integration/`) boot the full stack via Docker Compose and KIND to verify end-to-end behaviour.

---

## Operational Notes

- Toggle the entire cognitive-thread pipeline by setting `featureFlags.enableCogThreads` in Helm values (templates inject `ENABLE_COG_THREADS` automatically) or by exporting `ENABLE_COG_THREADS=1` across the involved deployments.
- Rollback is instant: set the flag back to `0` and redeploy. Services will stay running but idle so existing pods do not thrash.
- When canarying, pair feature-flag flips with metric dashboards for predictors (`somabrain_predictor_*`), segmentation (`somabrain_segments_*`), and integrator (`somabrain_integrator_*`).

---

For implementation details, see:
- `services/predictor-*/main.py`
- `somabrain/services/segmentation_service.py`
- `somabrain/services/integrator_hub.py`
- `services/opa_sidecar/policies`
- Helm chart templates under `infra/helm/charts/soma-apps/templates`
