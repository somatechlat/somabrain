---
mdformat: myst
---

# API Endpoints (machine-friendly summary)

This file contains a concise list of API endpoints and brief purpose descriptions used by `api_reference.md`.

- GET /health — Service health and component status
- POST /remember — Store text/facts/tasks with optional tags/metadata
- POST /recall — Retrieve by keyword/semantic cue; ranked results
- POST /link — Create typed relations between stored items
- POST /graph/links — List outgoing links from a key/coord
- POST /plan/suggest — Suggest a small plan from the semantic graph
- POST /sleep/run — Run consolidation (NREM/REM) on demand
- GET /sleep/status — Tenant-level last NREM/REM timestamps
- GET /sleep/status/all — Admin sleep status across tenants
- POST /act — Execute cognitive agent loop for a task
- POST /reflect — Build semantic summaries from recent episodics
- POST /migrate/export — Export memories (+optional WM)
- POST /migrate/import — Import memories and optionally warm WM
- GET /personality — Get per-tenant personality traits
- POST /personality — Set per-tenant traits
- GET /metrics — Prometheus metrics
- GET /metrics/snapshot — Compact JSON runtime stats
- GET /micro/diag — Microcircuits per-tenant diagnostics (if enabled)

For full per-endpoint compatibility details and request/response shapes, see `docs/source/api.md` and the running OpenAPI at `/openapi.json`.
