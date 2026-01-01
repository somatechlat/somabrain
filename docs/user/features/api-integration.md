# API Integration Guide

**Purpose** Show how to call SomaBrain’s public HTTP endpoints safely and reproducibly.

**Audience** Developers building clients, SDKs, or integrations against the FastAPI runtime in `somabrain/app.py`.

**Prerequisites** SomaBrain stack is running (see [Installation](../installation.md)), and you can authenticate with either a static API token or JWT.

---

## 1. Base Configuration

| Setting | Default | Where it comes from |
|---------|---------|---------------------|
| Base URL | `http://localhost:9696` | `SOMABRAIN_HOST` / `SOMABRAIN_PORT` in `.env` |
| Auth | Bearer token | `SOMABRAIN_API_TOKEN` or JWT fields in `somabrain.config.Config` |
| Tenant header | `X-Tenant-ID` | Parsed by `somabrain.tenant.get_tenant` |
| Content type | `application/json` | All public endpoints expect JSON bodies |

**Authentication**

- For static tokens set `SOMABRAIN_API_TOKEN=...` and supply `Authorization: Bearer <token>`.
– In dev mode, auth may be relaxed; otherwise include a valid Bearer token.
- JWT validation uses HS or RS algorithms depending on `cfg.jwt_secret` / `cfg.jwt_public_key_path`. Configure `SOMABRAIN_JWT_ISSUER` / `SOMABRAIN_JWT_AUDIENCE` if needed.

Example curl:

```bash
AUTH="Authorization: Bearer ${SOMABRAIN_API_TOKEN:-dev-token}"
TENANT="X-Tenant-ID: demo"
curl -sS http://localhost:9696/health -H "$AUTH" -H "$TENANT" | jq
```

---

## 2. Endpoint Catalogue

| Endpoint | Method | Description | Code Reference |
|----------|--------|-------------|----------------|
| `/health` | GET | Component liveness (Redis, Postgres, Kafka, memory backend, embedder) | `somabrain.app.health` |
| `/metrics` | GET | Prometheus metrics | `somabrain.app` (global registry) |
| `/remember` | POST | Store a single memory payload | `somabrain.app.remember` |
| `/recall` | POST | Semantic recall from working + long-term memory | `somabrain.app.recall` |
| `/context/evaluate` | POST | Build contextual prompt and retrieve weighted memories | `somabrain.api.context_route.evaluate_endpoint` |
| `/context/feedback` | POST | Submit utility/feedback scores that drive `AdaptationEngine` | `somabrain.api.context_route.feedback_endpoint` |
| `/act` | POST | Execute planner actions (enabled in full stack) | `somabrain.app.act` |
| `/plan/suggest` | POST | Request plan suggestions | `somabrain.app.plan_suggest` |
| `/sleep/run` | POST | Trigger NREM/REM consolidation | `somabrain.app.sleep_run` |
| `/neuromodulators` | POST/GET | Inspect or set neuromodulator state | `somabrain.app.neuromodulators` |

Endpoints gated by `if not _MINIMAL_API` require the full Docker stack (see `.env` flags such as `SOMABRAIN_FORCE_FULL_STACK`, `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`).

---

## 3. Request & Response Patterns

### 3.1 Remember / Recall

See [Memory Operations](memory-operations.md) for full payloads. Always include the tenant header when running multi-tenant tests:

```bash
curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}}'
```

### 3.2 Context Evaluate / Feedback

`somabrain/api/schemas/context.py` defines strongly typed bodies:

```bash
# evaluate
curl -sS http://localhost:9696/context/evaluate \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "query": "capital of France",
        "top_k": 3,
        "session_id": "demo-session"
      }' | jq '.prompt, .weights'

# feedback
curl -sS http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{
        "session_id": "demo-session",
        "query": "capital of France",
        "prompt": "Summarise the capital of France.",
        "response_text": "Paris is the capital of France.",
        "utility": 0.9,
        "reward": 0.9
      }'
```

Feedback drives the per-tenant adaptation state stored in Redis. Inspect the state with `GET /context/adaptation/state` (same headers; returns retrieval/utility weights, history length, learning rate).

### 3.3 Planning & Actions

Planning endpoints are optional and require the planner to be enabled (`SOMABRAIN_FORCE_FULL_STACK=1`):

```bash
curl -sS http://localhost:9696/plan/suggest \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"task": "draft release announcement", "top_k": 5}' | jq '.plans[:1]'
```

Consult `somabrain/schemas.py` for the exact response model (`PlanSuggestResponse`).

---

## 4. Error Handling & Observability

| Condition | HTTP code | Response field | Notes |
|-----------|-----------|----------------|-------|
| Missing/invalid token | 401 / 403 | `{"detail": "..."} ` | Implement retry/backoff only after reacquiring credentials. |
| Tenant quota exceeded | 429 | `{"detail": "daily write quota exceeded"}` | `somabrain.quotas.QuotaManager` enforces per-tenant caps. |
| Memory backend offline | 503 | `{"detail": {"message": "...", "breaker_open": true}}` | Writes are queued; check `somabrain.services.memory_service.MemoryService`. |
| Input validation | 400 | `{"detail": "Invalid payload: ..."}` | Raised by Pydantic models such as `MemoryPayload` and `FeedbackRequest`. |

**Tracing & Metrics**

- Supply `X-Request-ID` for end-to-end tracing. The same ID appears in responses and structured logs.
- Prometheus metrics at `/metrics` include request latency (`somabrain_request_latency_seconds`), memory operations, and adaptation counters.
- Kafka, Redis, and Postgres exporters in the Docker Compose stack expose infrastructure metrics on ports 20003–20007.

---

## 5. Python Example (httpx)

There is no official SDK. The snippet below uses `httpx` and the documented payloads.

```python
import asyncio
import httpx

AUTH = {"Authorization": "Bearer dev-token", "X-Tenant-ID": "demo"}
BASE = "http://localhost:9696"

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=AUTH, timeout=10) as client:
        # remember
        remember = await client.post(
            "/remember",
            json={"payload": {"task": "kb.paris", "content": "Paris is the capital of France."}},
        )
        remember.raise_for_status()

        # recall
        recall = await client.post("/recall", json={"query": "capital of France", "top_k": 3})
        recall.raise_for_status()
        for hit in recall.json().get("results", []):
            print(f"{hit.get('score', 0):.2f} → {hit.get('content')}")

asyncio.run(main())
```

Use the same approach for feedback and planning—serialise the Pydantic models documented in `somabrain/api/schemas`.

---

## 6. Reference Documents

- [Memory Operations](memory-operations.md) – Payload specifics and error cases.
- [Cognitive Reasoning](cognitive-reasoning.md) – Context builder, planner, adaptation flows.
- [Multi-tenant Usage](multi-tenant-usage.md) – Tenancy, universes, quotas.
- [API Reference](../../development/api-reference.md) – Complete endpoint inventory for operators.
