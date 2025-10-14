# REST API Snapshot

FastAPI lives in `somabrain/app.py`. This page lists the stable endpoints exposed in strict mode.

| Method | Path | Purpose | Request Model | Response Model |
| --- | --- | --- | --- | --- |
| GET | `/health` | Readiness + dependency status | – | `schemas.HealthResponse` |
| GET | `/healthz` | Alias of `/health` for probes | – | same as `/health` |
| POST | `/recall` | Retrieve memories ranked by scorer | `schemas.RecallRequest` | `schemas.RecallResponse` |
| POST | `/remember` | Persist memory payloads | `schemas.RememberRequest` | `schemas.RememberResponse` |
| POST | `/delete` | Delete long-term memory items | `schemas.DeleteRequest` | `schemas.DeleteResponse` |
| POST | `/recall/delete` | Delete working-memory rows | `schemas.DeleteRequest` | `schemas.DeleteResponse` |
| POST | `/plan/suggest` | Transport-aware planning query | `schemas.PlanSuggestRequest` | `schemas.PlanSuggestResponse` |
| POST | `/sleep/run` | Trigger offline consolidation | `schemas.SleepRunRequest` | `schemas.SleepRunResponse` |
| GET | `/sleep/status` | Status for current tenant | – | `schemas.SleepStatusResponse` |
| GET | `/sleep/status/all` | Status for all tenants | – | `schemas.SleepStatusAllResponse` |
| POST | `/personality` | Update personality parameters | `schemas.PersonalityState` | `schemas.PersonalityState` |
| POST | `/act` | Execute an action via policy | `schemas.ActRequest` | `schemas.ActResponse` |
| GET | `/neuromodulators` | Fetch neuromodulator state | – | `schemas.NeuromodStateModel` |
| POST | `/neuromodulators` | Adjust neuromodulator state | `schemas.NeuromodStateModel` | `schemas.NeuromodStateModel` |
| POST | `/graph/links` | Query graph edges for transport | `schemas.GraphLinksRequest` | `schemas.GraphLinksResponse` |
| POST | `/reflect` | Trigger reflective update cycle | `schemas.ReflectRequest` | `schemas.ReflectResponse` |
| POST | `/migrate/export` | Export memory payloads | `schemas.MigrateExportRequest` | `schemas.MigrateExportResponse` |

### Usage Notes
- All write endpoints honour strict mode: if external services are unreachable, requests fail with 5xx.
- Tenancy is selected via the `X-Soma-Tenant` header; defaults to settings tenant when absent.
- Authentication is disabled only when `SOMABRAIN_DISABLE_AUTH=1`.
- OpenAPI: run `./scripts/export_openapi.py` to regenerate `artifacts/openapi.json`.

Extend this table whenever a new public endpoint ships.
