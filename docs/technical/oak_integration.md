---
title: Oak (ROAMDP) Integration Guide
author: SomaBrain Team
date: 2025-11-27
---

# Overview

This document describes the **Oak hierarchical‑RL option layer** that has been
added to the SomaBrain microservice.  Oak introduces *options* (temporally
extended actions) and a deterministic planner that selects high‑utility option
sequences for a given tenant.  All new functionality follows the **VIBE coding
rules** – no hard‑coded literals, no placeholder `pass` statements, full type
annotations, and comprehensive test coverage.

The integration touches the following subsystems:

* **Configuration** – new settings in `common/config/settings.py`.
* **API** – three FastAPI endpoints (`/oak/option/create`, `/oak/option/{id}`
  `PUT`, `/oak/plan`).
* **Persistence** – Milvus vector store for option payloads and JSON
  serialization of the full `OptionModel`.
* **Events** – Avro‑encoded `OptionCreated` and `OptionUpdated` events published
  to Kafka.
* **Policy** – OPA policy (`opa/option.rego`) that restricts creation and
  update to the `brain_admin` role.
* **Observability** – Prometheus gauges `somabrain_option_utility_avg` and
  `somabrain_option_count`.
* **Testing & CI** – unit and integration test suites, benchmark script, and
  updated GitHub Actions workflow.

---

## Architecture Diagram

```
+-------------------+      +-------------------+      +-------------------+
|   FastAPI (app)  | ---> |   OPA Engine      | ---> |   Kafka (outbox)  |
|   (Oak routes)   |      |   (option.rego)   |      |   option_created  |
|                   |      |                   |      |   option_updated  |
|   Milvus Client   | <--- |   MemoryClient    | <--- |   Memory Service  |
|   (vector store)  |      |   (core)          |      |   (Redis/PG)      |
|   Prometheus      |      |   Metrics         |      +-------------------+
|   (gauges)        |      +-------------------+
+-------------------+
```

The diagram shows the flow of a request through FastAPI, OPA policy
evaluation, Milvus persistence, and event publishing.  All components share the
central `settings` instance for configuration.

---

## Configuration (`common/config/settings.py`)

The following **Oak‑specific** settings are added.  All values are read from the
environment (e.g., `OAK_BASE_UTILITY`) with sensible defaults; they can also be
overridden in a `config.yaml` file when the service is deployed via Helm.

| Setting | Type | Default | Description |
|--------|------|---------|-------------|
| `ENABLE_OAK` | `bool` | `False` | Feature flag – disables all Oak endpoints when `False`. |
| `OAK_BASE_UTILITY` | `float` | `1.0` | Base utility used in `Option` utility calculation. |
| `OAK_UTILITY_FACTOR` | `float` | `0.1` | Multiplier applied to payload length when computing utility. |
| `OAK_TAU_MIN` | `float` | `30.0` | Minimum time‑to‑live (seconds) for an option. |
| `OAK_TAU_MAX` | `float` | `300.0` | Maximum time‑to‑live (seconds) for an option. |
| `OAK_PLAN_MAX_OPTIONS` | `int` | `10` | Upper bound on the number of option IDs returned by the planner. |
| `OAK_SIMILARITY_THRESHOLD` | `float` | `0.9` | Cosine similarity threshold used by the planner to stop early. |
| `OAK_REWARD_THRESHOLD` | `float` | `0.5` | Minimum environment reward required to trigger option creation. |
| `OAK_NOVELTY_THRESHOLD` | `float` | `0.2` | Minimum novelty metric required to trigger option creation. |
| `OAK_GAMMA` | `float` | `0.99` | Discount factor for environment reward accumulation. |
| `OAK_ALPHA` | `float` | `0.1` | EMA update factor for transition and reward models. |
| `OAK_KAPPA` | `float` | `1.0` | Weight applied to feature reward in the utility formula. |
| `opa_bundle_path` | `str` | `./opa` | Directory containing OPA policy bundles (including `option.rego`). |

These settings are accessed throughout the code via `settings.<NAME>`; no hard‑coded
values remain.

---

## API Endpoints (FastAPI)

All Oak endpoints are guarded by `require_auth` and the OPA middleware.  The
feature flag `ENABLE_OAK` must be `True` for the routes to be reachable.

### 1. Create Option

* **Method**: `POST`
* **Path**: `/oak/option/create`
* **Request model**: `OakOptionCreateRequest`
  ```json
  {
    "option_id": "optional‑string",
    "payload": "base64‑encoded‑bytes"
  }
  ```
* **Response model**: `OakPlanSuggestResponse`
  ```json
  {"plan": ["opt_12345"]}
  ```
* **OPA rule**: `allow_option_creation`

### 2. Update Option

* **Method**: `PUT`
* **Path**: `/oak/option/{option_id}`
* **Request model**: same as create (`OakOptionCreateRequest`).
* **Response model**: `OakPlanSuggestResponse` containing the updated option ID.
* **OPA rule**: `allow_option_update`

### 3. Planner

* **Method**: `POST`
* **Path**: `/oak/plan`
* **Request model**: `OakPlanRequest` (fields: `start_state`, `target_feature`, optional `similarity_thresh`, optional `max_options`).
* **Response model**: `OakPlanSuggestResponse` – ordered list of option IDs.
* **Latency guarantee**: ≤ 200 ms for ≤ 500 stored options (validated by the benchmark script).

---

## Avro Schemas

The Oak layer publishes two Avro events.  Schemas live under
`proto/cog/avro/` and are loaded by `libs.kafka_cog.avro_schemas`.

* **`option_created.avsc`** – fields: `option_id` (string), `tenant_id` (string),
  `timestamp` (long, ms epoch), `payload` (bytes).
* **`option_updated.avsc`** – identical fields, separate topic (`oak.option.updated`).

Both events are emitted by `OptionManager._publish_creation` and
`OptionManager._publish_update` using the `AvroSerde` helper.

---

## OPA Policy (`opa/option.rego`)

```rego
package somabrain.option

allow_option_creation {
    input.method == "POST"
    input.path = ["oak", "option", "create"]
    input.user.role == "brain_admin"
}

allow_option_update {
    input.method == "PUT"
    input.path = ["oak", "option", "update", _]
    input.user.role == "brain_admin"
}

default allow = false
allow { allow_option_creation }
allow { allow_option_update }
```

The policy is loaded at startup by `SimpleOPAEngine` (bundle path defined in
`settings.opa_bundle_path`).  Any request that does not satisfy the rules is
denied with a `403` response.

---

## Observability (Prometheus)

Two new gauges are exported via `somabrain.metrics`:

* `somabrain_option_utility_avg` – average utility of all created options, labelled
  by `tenant_id`.
* `somabrain_option_count` – total number of stored options per tenant.

Metrics are updated in `OptionManager.create_option` and `OptionManager.update_option`
using the `OPTION_COUNT` and `OPTION_UTILITY_AVG` gauges.

---

## Persistence of the Full Option Model

`OptionManager._persist_model(tenant_id)` serialises the complete list of options
for a tenant to JSON and stores it via `MemoryClient.remember` under the topic
`oak.option.model`.  The JSON structure follows Appendix B of the SRS:

```json
{
  "options": [
    {
      "id": "opt_1",
      "tenant_id": "tenant_a",
      "payload": [0,1,2,...],
      "utility": 12.3,
      "tau": 45.0,
      "created_ts": 1730186400.123
    }
    // … more options …
  ]
}
```

The method is called after every successful creation or update, ensuring the
model stays in sync with Milvus.

---

## Testing Strategy

### Unit Tests (`tests/unit/`)
* **Option utility** – verify `Option.__post_init__` computes utility and τ using
  the configured settings.
* **OptionManager.create_option** – asserts Milvus up‑sert is called, Avro event is
  published, metrics are incremented, and JSON model persistence succeeds.
* **OptionManager.update_option** – same assertions for the update path.
* **Planner** – confirm `plan_for_tenant` returns a list ordered by utility and
  respects `settings.OAK_PLAN_MAX_OPTIONS`.

### Integration Tests (`tests/integration/`)
* Spin up a temporary Milvus container (via Docker‑Compose) and verify that
  vectors are searchable after creation.
* Load the OPA bundle and test that a request with a non‑admin role receives a
  `403`.
* End‑to‑end flow: create option → update option → call `/oak/plan` and ensure the
  returned plan includes the created option ID.

### Performance Benchmark (`scripts/benchmark_oak.py`)
* Generates 500 options, runs the planner, and asserts the median latency is
  ≤ 180 ms (allows a small margin for CI hardware).  The script is executed as
  part of the CI `benchmark` job.

---

## CI/CD Changes (`.github/workflows/ci.yml`)

* Install `pymilvus` and start a Milvus service in the `services` section.
* Install `opa` CLI and copy the `opa/` directory into the container.
* Run the new unit and integration test suites (`pytest -m oak`).
* Execute `scripts/benchmark_oak.py` and fail the job if the latency target is
  exceeded.
* Build the Docker image with the additional `option.rego` file and the Avro
  schemas bundled under `/app/proto/cog/avro`.

---

## Deployment (Helm)

Add the following values to `helm/somabrain/values.yaml`:

```yaml
oak:
  enabled: true            # toggles the Oak feature flag
  opaBundlePath: "/app/opa"
  milvus:
    host: "milvus.svc.cluster.local"
    port: 19530
    collection: "oak_options"
```

The Helm chart sets the environment variables accordingly (e.g., `ENABLE_OAK`
and `OPA_BUNDLE_PATH`).  A canary rollout can be performed by deploying a
second release with `oak.enabled: true` and routing a small percentage of
traffic via an ingress weight.

---

## Security Considerations

* **OPA enforcement** guarantees that only users with the `brain_admin` role can
  create or modify options.
* **TLS** should be enabled for the Milvus endpoint in production (set
  `MILVUS_TLS=true` and provide certificates via Helm secrets).
* **Audit logging** – `OptionManager` logs creation and update events at `INFO`
  level, and the middleware records the OPA decision for every request.

---

## FAQ

**Q: How do I enable Oak in a local dev environment?**
> Set `ENABLE_OAK=1` in your `.env` file or export it before running the
> service.  The default is `False` to avoid accidental exposure.

**Q: Where are the Avro schemas stored?**
> Under `proto/cog/avro/`.  They are packaged into the Docker image and loaded
> at runtime by `libs.kafka_cog.avro_schemas`.

**Q: What happens if Milvus is unavailable?**
> Oak writes now fail fast. `OptionManager` surfaces the `RuntimeError` raised
> by `MilvusClient` so the API request returns an error instead of silently
> succeeding.  Each retry attempt increments
> `somabrain_milvus_upsert_retry_total`, and exhausting all retries increments
> `somabrain_milvus_upsert_failure_total` so alerts can fire immediately.

---

*Document version 1.0 – November 27 2025*
