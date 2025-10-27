# Frequently Asked Questions

**Purpose** Provide quick answers to operational and integration issues new users encounter most often.

**Audience** Developers and operators running SomaBrain locally or in a lab.

**Prerequisites** Read the [Installation Guide](installation.md) and [Quick Start Tutorial](quick-start-tutorial.md).

---

## Installation & Environment

### Q1. `/health` returns `"memory_ok": false`. What does that mean?

`somabrain.app.health` pings the external memory HTTP service using `SOMABRAIN_MEMORY_HTTP_ENDPOINT`. If the service is offline or misconfigured, the check fails and `/remember` will either queue writes (when `SOMABRAIN_REQUIRE_MEMORY=0`) or return HTTP 503.

Common local pitfall (Docker on macOS/Windows): using `http://127.0.0.1:9595` inside a container. Inside containers, `127.0.0.1` is the container itself, not your host. Use `http://host.docker.internal:9595` instead and verify via `GET /diagnostics` (check `memory_endpoint`).

### Q2. Can I run the API without Docker?

Yes, but you must provide the dependencies yourself (Redis, Kafka, OPA, Postgres, memory HTTP service). The `uvicorn somabrain.app:app` command in the [Installation Guide](installation.md) assumes these services already exist. For most users the Docker Compose bundle is the quickest path.

### Q3. How do I disable auth for local testing?
### Q4. How do I quickly verify my wiring?

Call `GET /diagnostics`. It returns a sanitized snapshot including:
- `in_container`: whether the API is running in a container
- `mode`: current deployment mode (`enterprise` maps to production policy)
- `memory_endpoint`: the effective endpoint the API will call
- `external_backends_required` and `require_memory`: enforcement flags

If `memory_endpoint` shows `localhost` while `in_container` is `true`, switch to `http://host.docker.internal:9595` and restart the API container.

Set `SOMABRAIN_DISABLE_AUTH=1` before starting the API. Authentication (`require_auth`) will be bypassed for all endpoints. Remember to unset the flag outside dev environments.

---

## Memory Operations

### Q5. `/remember` responded with `503 memory backend unavailable; write queued`. Did I lose data?

No. `MemoryService` journaled the payload to `journal_dir` and flagged the breaker. Once the memory service becomes reachable, queued entries are replayed. If you need the write to succeed synchronously, ensure the backend is online or set `SOMABRAIN_REQUIRE_MEMORY=0` while testing.

### Q6. `/recall` returns an empty list. How can I debug it?

1. Confirm `/remember` succeeded (`"ok": true`, `"breaker_open": null`).
2. Check the memory backend logs to verify it stored the payload.
3. Ensure the query text shares vocabulary with the stored content; the BHDC layer uses semantic similarity but still benefits from overlapping terms.
4. Increase `top_k` or lower scoring thresholds in your client; the API does not expose a server-side threshold parameter.

### Q7. Is there an update endpoint?

There is no dedicated PATCH/PUT endpoint. To “update” a memory, submit a new payload via `/remember` with the corrected content. If you need to remove old entries, call `/delete` with the relevant coordinate or task.

---

## Context & Feedback

### Q8. What happens when I call `/context/feedback`?

The payload is validated by `somabrain/api/schemas/context.py::FeedbackRequest`, then `AdaptationEngine.apply_feedback` adjusts retrieval (`alpha`, `gamma`) and utility (`lambda_`, `mu`, `nu`) weights for your tenant. The state is stored in Redis and mirrored by `/context/adaptation/state`. You can override the learning gains or bounds with the environment variables described in [Cognitive Reasoning](features/cognitive-reasoning.md).

### Q9. I see `"adaptation_applied": false` in the feedback response. Why?

`apply_feedback` returns `False` when the signal is `None`, when the adapter rejects the update due to constraint violations, or when the payload fails validation. Check the response HTTP status (should be 400 if validation failed) and inspect `somabrain/app.py::feedback_endpoint` log messages for details.

---

## Tenancy & Quotas

### Q10. How are tenants separated?

Every request uses `X-Tenant-ID` or, if absent, the first 16 characters of the bearer token. Redis keys, adaptation state, and metrics are namespaced by tenant (`somabrain_ns:<tenant>`). See [Multi-Tenant Usage](features/multi-tenant-usage.md) for a deeper explanation.

### Q11. What happens when the daily write quota is exceeded?

`QuotaManager.allow_write` returns `False`, causing `/remember` to raise HTTP 429 (`"daily write quota exceeded"`). Counters reset at midnight UTC. Adjust `SOMABRAIN_QUOTA_DAILY_WRITES` or modify `QuotaConfig` if you need a higher limit.

---

## Observability

### Q12. Where do I find metrics?

All runtime metrics are exposed at `GET /metrics` in Prometheus format. Look for:

- `somabrain_request_latency_seconds` – per-endpoint latency.
- `somabrain_feedback_total` – feedback submissions per tenant.
- `somabrain_tau_gauge` – current τ values after duplicate adjustments.

Exporters for Redis, Kafka, Postgres, and Prometheus itself are exposed on ports 20001–20007 when you run Docker Compose.

### Q13. How can I correlate logs with API responses?

Pass `X-Request-ID` with your call. The same ID appears in:

- API responses (`trace_id`).
- Structured logs (logged in `somabrain/app.py` handlers).
- Prometheus metrics labels when applicable.

---

Still stuck? Reach out via your team channel with the `trace_id`, tenant ID, and the command you ran. That information maps directly to the runtime state described above.
