# Canonical Roadmap — Unified Sleep System

This roadmap defines the implementation plan for the **Unified Sleep System** as specified in the Software Requirements Specification (SRS). The Sleep System provides two public APIs:
* `POST /api/util/sleep` – a simple utility endpoint that sleeps for a configurable duration (used for testing and latency injection).
* `POST /api/brain/sleep_mode` – a cognitive‑sleep mode that runs NREM/REM cycles, updates memory consolidation, and emits metrics.

All new functionality is gated behind feature flags and follows the existing single‑image, values‑gated deployment model.

## 1) Architecture (high-level)

```
+-------------------+      +-------------------+      +-------------------+
|   Client/API      | ---> |   Orchestrator    | ---> |   Predictor Core   |
| (REST/gRPC)       |      | (Plan phase)      |      | (state/agent/action)|
+-------------------+      +-------------------+      +-------------------+
       |                         |                         |
       v                         v                         v
   +----------------+        +----------------+        +----------------+
   |  Sleep Service |        |  Memory Service|        |  Integrator Hub |
   | (util/sleep)   |        | (recall/remember) |    | (softmax, OPA) |
   +----------------+        +----------------+        +----------------+
       |                         ^                         |
       +-------------------+-----+-------------------------+
                          |
                          v
               +-------------------+
               |   Sleep Mode API  |
               | (/brain/sleep_mode) |
               +-------------------+
```

**Notes**
* Transport remains Kafka for internal events; the Sleep Service is a thin FastAPI wrapper.
* Feature flags control exposure of the new endpoints.
* All new Avro schemas are versioned under `proto/cog/`.

## 2) Contracts & Topics (Avro)

New schemas (added to `proto/cog/`):
* `sleep_request.avsc` – request payload for `/api/util/sleep` (fields: `duration_ms`).
* `sleep_mode_request.avsc` – request payload for `/api/brain/sleep_mode` (fields: `mode` enum {`nrem`, `rem`, `both`}, optional `ttl_ms`).
* `sleep_status.avsc` – status updates emitted on topic `cog.sleep.status`.
* `sleep_metrics.avsc` – metrics schema for Prometheus export.

## 3) Feature Flags (values‑gated)

* `ENABLE_UTIL_SLEEP` – toggles the `/api/util/sleep` endpoint.
* `ENABLE_BRAIN_SLEEP_MODE` – toggles the `/api/brain/sleep_mode` endpoint.
* `SLEEP_MODE_TTL_SECONDS` – default TTL for sleep cycles (configurable via Helm).

## 4) Observability & Metrics

Prometheus metrics exported by the Sleep Service:
* `somabrain_sleep_requests_total{mode="util"}` – count of util sleep calls.
* `somabrain_sleep_mode_runs_total{mode="nrem"}` – count of NREM runs.
* `somabrain_sleep_mode_duration_seconds` – histogram of sleep durations.
* `somabrain_sleep_last_run_timestamp` – gauge of last run time per tenant.

Health endpoint `/healthz` includes `sleep_enabled` flag.

## 5) Sprints & Acceptance Tests

### Sprint 0 – Foundations (Done)
* Verify existing API infrastructure, CI pipelines, and feature‑flag framework.

### Sprint 1 – Util Sleep Endpoint
* Add `sleep_request.avsc` and FastAPI handler `POST /api/util/sleep`.
* Validate `duration_ms` (0‑5000 ms) and return `{ok:true, slept_ms:<actual>}`.
* Export Prometheus metric `somabrain_sleep_requests_total`.
* Acceptance: 200 response, correct latency, metric increment.

### Sprint 2 – Sleep Mode API & Core Logic
* Implement `/api/brain/sleep_mode` with NREM/REM cycles using existing consolidation loops.
* Introduce background task that runs every `cfg.sleep_interval_seconds` (default 300 s).
* Emit `sleep_status.avsc` events and update metrics.
* Acceptance: endpoint returns `{run_id, started_at_ms, mode}`; background task updates memory consolidation.

### Sprint 3 – Metrics, OPA Policies & Flags
* Add Prometheus histograms for sleep durations and run counts.
* Create OPA policy `sleep.rego` enforcing tenant‑level quota (max 5 runs per hour).
* Feature‑flag gating and Helm values integration.
* Acceptance: policy blocks excess runs, metrics reflect correct counts.

### Sprint 4 – Integration & End‑to‑End Tests
* Write integration tests covering both endpoints, flag toggling, and metric exposure.
* Update CI to run sleep‑system test suite.
* Acceptance: all tests pass in CI, dashboards show sleep metrics.

### Sprint 5 – Canary Rollout & Production Deployment
* Deploy Sleep Service behind a canary flag to 5 % of traffic.
* Monitor latency, error rates, and resource usage.
* Rollout to 100 % upon successful canary.

## 6) Non‑Goals / Constraints

* No changes to the single‑image Docker policy.
* Sleep Service runs within the existing FastAPI process; no separate container.
* No persistent storage beyond existing memory backends – sleep state is transient.

## 7) Rollback Plan

* Disable `ENABLE_UTIL_SLEEP` / `ENABLE_BRAIN_SLEEP_MODE` flags via Helm.
* Rolling back the feature flag instantly disables the endpoints without redeploy.

---

This roadmap supersedes the previous Cognitive Thread roadmap and aligns the repository with the Unified Sleep System requirements.
