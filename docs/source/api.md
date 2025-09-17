---
mdformat: myst
---

# API Reference (canonical)

This single canonical API reference consolidates quickstart examples, per-endpoint compatibility notes, and operational details. It is the authoritative source for integration and will be kept in sync with the running FastAPI app and OpenAPI schema.

----

## Quickstart — remember & recall

Remember (store a memory)

- Endpoint: POST /remember
- Body: `RememberRequest` { coord?: "x,y,z", payload: MemoryPayload }

Minimal MemoryPayload fields:
- `task` (optional short identifier)
- `importance` (int, default 1)
- `memory_type` (string, default "episodic")
- `timestamp` (optional unix epoch seconds) — server will set if omitted
- `who/did/what/where/when/why` optional context strings

Example curl (canonical):

```sh
curl -X POST http://localhost:9696/remember \
	-H "Content-Type: application/json" \
	-d '{"coord": null, "payload": {"task":"write docs","importance":1,"memory_type":"episodic","timestamp": 1693750000.123,"who":"agent_zero","did":"tested","what":"remember endpoint","where":"terminal","when":"2025-09-03T20:35:00Z","why":"API test"}}'
```

Recall (search memories)

- Endpoint: POST /recall
- Body: `RecallRequest` { query: string, top_k?: int, universe?: string }

Example curl:

```sh
curl -X POST http://localhost:9696/recall \
	-H "Content-Type: application/json" \
	-d '{"query":"remember endpoint","top_k":5}'
```

Response shapes: refer to the OpenAPI schema at `/openapi.json` for exact fields and types. Key response fields:
- `/recall` returns `RecallResponse` containing `wm` (working memory hits) and `memory` (long-term memory items).
- `/remember` returns `RememberResponse` with `ok`, `success`, `namespace`, and `trace_id`.

----

## Per-endpoint compatibility & notes

The following sections document purpose, request and response shapes, and operational constraints. For exact types, check `/openapi.json` and `somabrain/schemas.py`.

### GET /health

- Purpose: Service health and component status
- Response: `HealthResponse` { ok: bool, components: dict }

### POST /remember

- Purpose: Store a memory and warm WM
- Request: `RememberRequest`
- Response: `RememberResponse`

Notes: Auth required when configured. Writes are tenant-scoped; use `X-Tenant-ID` to set tenant.

### POST /recall

- Purpose: Hybrid recall across WM/LTM, HRR/diversity and graph as configured
- Request: `RecallRequest`
- Response: `RecallResponse`

Notes: Non-destructive read; supports `universe` filtering.

### POST /plan/suggest

- Purpose: Suggest a small plan from the semantic graph
- Request: `PlanSuggestRequest`
- Response: `PlanSuggestResponse`

Example curl:

```sh
curl -X POST http://localhost:9696/plan/suggest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: public" \
  -d '{
    "task_key": "write docs",
    "max_steps": 5,
    "rel_types": ["depends_on","part_of","related"]
  }'
```

### POST /sleep/run

- Purpose: Run a manual consolidation (NREM/REM)
- Request: `SleepRunRequest` { nrem?: bool, rem?: bool }
- Response: `SleepRunResponse` { ok: bool, run_id?: str, started_at_ms?: int, mode?: str, details?: dict }

Notes: This endpoint triggers consolidation work and may be slow depending on configured batch sizes.

### GET /sleep/status

- Purpose: Tenant-level last NREM/REM timestamps
- Response: `SleepStatusResponse` { enabled, interval_seconds, last }

### GET /sleep/status/all

- Purpose: Admin view of sleep status for all tenants
- Response: `SleepStatusAllResponse` { enabled, interval_seconds, tenants }

### POST /link

- Purpose: Create/update a typed graph link between memory keys or coordinates
- Request: `LinkRequest`
- Response: `LinkResponse` { ok: bool }

Examples:

1) Link by coordinates (comma strings)

```sh
curl -X POST http://localhost:9696/link \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: public" \
  -d '{
    "from_coord": "0.1,0.2,0.3",
    "to_coord":   "-0.4,0.5,-0.6",
    "type": "depends_on",
    "weight": 1.0
  }'
```

2) Link by keys (server derives stable coordinates per key and universe)

```sh
curl -X POST http://localhost:9696/link \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: public" \
  -d '{
    "from_key": "write docs",
    "to_key":   "gather examples",
    "type": "part_of",
    "weight": 0.8,
    "universe": "real"
  }'
```

### POST /graph/links

- Purpose: List outgoing links from a key/coord
- Request: `GraphLinksRequest`
- Response: `GraphLinksResponse` { edges: [...], universe }

Example curl:

```sh
curl -X POST http://localhost:9696/graph/links \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: public" \
  -d '{
    "from_key": "write docs",
    "type": "depends_on",
    "limit": 50
  }'
```

Response contains an `edges` array with `{ from, to, type, weight }` and an `universe` echo.

### POST /act

- Purpose: Run the cognitive agent loop for a task
- Request: `ActRequest`
- Response: `ActResponse`

### POST /reflect

- Purpose: Build semantic summaries from recent episodic memories
- Response: `ReflectResponse` { created: int, summaries: [string] }

### POST /migrate/export

- Purpose: Export memories (+WM)
- Request: `MigrateExportRequest`
- Response: `MigrateExportResponse`

### POST /migrate/import

- Purpose: Import memories and optionally warm WM
- Request: `MigrateImportRequest`
- Response: `MigrateImportResponse` { imported: int, wm_warmed: int }

### Persona endpoints

- Persona CRUD has moved to `/persona` (PUT/GET/DELETE). Use `Persona` schema with `id`, `display_name`, and `properties` to persist tenant traits.

### GET /metrics and GET /metrics/snapshot

- Purpose: Prometheus metrics and JSON snapshot of runtime stats

### Feature-gated endpoints

Some endpoints are hidden in minimal mode or behind feature flags (FNOM, Fractal memory endpoints, demo endpoints). See `docs/source` feature docs for flags.

----

## Keeping docs in sync with code

- The OpenAPI JSON `/openapi.json` is generated from Pydantic models in `somabrain/schemas.py` and the FastAPI route decorators (`response_model=`). Use that file for machine-readable integration.
- We maintain one canonical `docs/source/api.md`. Do not add duplicate `api.rst` or other copies — this file is authoritative.

To refresh the local snapshot in `docs/generated/openapi.json` from a running server:

```sh
curl -s http://localhost:9696/openapi.json > docs/generated/openapi.json
```

----

## Examples & integration tips

- Always set `Content-Type: application/json` when POSTing.
- Use `X-Tenant-ID` header to scope writes/reads by tenant (default: `public`).
- For programmatic clients prefer `timestamp` numeric epoch and `when` as ISO string.

For more details, check the OpenAPI at `http://127.0.0.1:9696/openapi.json` while the app is running.
