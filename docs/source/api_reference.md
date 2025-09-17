---
mdformat: myst
---

# API Reference

This page includes the canonical API endpoints table maintained in the Markdown docs.

```{include} ../reference/api_endpoints.md
:relative-docs: ../
:relative-images: ../
```

## Per-endpoint compatibility details

### GET /health

- Purpose: Service health and component status
- Request: n/a
- Response: HealthResponse { ok: bool, components: dict }
- Compatibility
	- Method/Path: GET /health
	- Auth: Yes (if configured)
	- Minimal mode: Exposed
	- Tenant scope: Read-only; no mutation
	- Universe: Ignored
	- Side effects: None
	- Maps to: Health/Info

### POST /remember

- Purpose: Store a memory and warm WM
- Request: RememberRequest { coord?: "x,y,z", payload: MemoryPayload }
- Response: { ok: true, key?/coord? }
- Compatibility
	- Method/Path: POST /remember
	- Auth: Yes
	- Minimal mode: Exposed
	- Tenant scope: Writes to tenant WM/LTM
	- Universe: Optional; writes scoped links when set
	- Side effects: Indexing, WM warming, optional link updates
	- Maps to: Store/Upsert Memory

### POST /recall

- Purpose: Hybrid recall across WM/LTM (+HRR/diversity/graph as configured)
- Request: RecallRequest { query: string, top_k?: int, universe?: string }
- Response: { wm: [...], memory: [...], reality, drift?, hrr_cleanup? }
- Compatibility
	- Method/Path: POST /recall
	- Auth: Yes
	- Minimal mode: Exposed
	- Tenant scope: Reads per-tenant indices
	- Universe: Optional; narrows graph scope
	- Side effects: None
	- Maps to: Search/Recall

### POST /plan/suggest

- Purpose: Suggest a small plan from the semantic graph
- Request: { task_key: string, max_steps?: int, rel_types?: [string], universe?: string }
- Response: { plan: [string] }
- Compatibility
	- Method/Path: POST /plan/suggest
	- Auth: Yes
	- Minimal mode: Exposed
	- Tenant scope: Reads tenant graph
	- Universe: Recommended for plan scoping
	- Side effects: None
	- Maps to: Plan/Suggest

### POST /sleep/run

- Purpose: Run a single NREM/REM cycle now
- Request: { nrem?: bool, rem?: bool }
- Response: { nrem?, rem? }
- Compatibility
	- Method/Path: POST /sleep/run
	- Auth: Yes
	- Minimal mode: Exposed
	- Tenant scope: Consolidation for current tenant
	- Universe: Ignored
	- Side effects: Consolidation, summarization, cleanup
	- Maps to: Sleep/Consolidate (manual)

### POST /link

- Purpose: Create a typed link between two keys/coords
- Request: { from_key/to_key or from_coord/to_coord, type?: string, weight?: number, universe?: string }
- Response: { ok: true }
- Compatibility
	- Method/Path: POST /link
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Writes tenant graph edge
	- Universe: Recommended to segment edges
	- Side effects: Graph mutation (edge create/update)
	- Maps to: Link/Create Edge

### POST /graph/links

- Purpose: List outgoing links from a key/coord
- Request: { from_key or from_coord, type?: string, limit?: number, universe?: string }
- Response: { edges: [...], universe }
- Compatibility
	- Method/Path: POST /graph/links
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Reads tenant graph
	- Universe: Optional filter
	- Side effects: None
	- Maps to: Link/List Edges

### GET /metrics

- Purpose: Prometheus metrics
- Request: n/a
- Response: text/plain
- Compatibility
	- Method/Path: GET /metrics
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Global + per-tenant metrics
	- Universe: Ignored
	- Side effects: None
	- Maps to: Metrics/Prometheus

### GET /sleep/status

- Purpose: Last per-tenant NREM/REM timestamps
- Request: n/a
- Response: { enabled, interval_seconds, last }
- Compatibility
	- Method/Path: GET /sleep/status
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Current tenant only
	- Universe: Ignored
	- Side effects: None
	- Maps to: Sleep/Status (tenant)

### GET /sleep/status/all

- Purpose: Admin sleep times across tenants
- Request: n/a
- Response: { enabled, interval_seconds, tenants }
- Compatibility
	- Method/Path: GET /sleep/status/all
	- Auth: Yes (admin)
	- Minimal mode: Hidden
	- Tenant scope: All tenants (admin)
	- Universe: Ignored
	- Side effects: None
	- Maps to: Sleep/Status (admin)

### POST /act

- Purpose: Execute task loop (may store, plan, recall)
- Request: ActRequest { task, top_k?, universe? }
- Response: ActResponse { task, results[], plan?, plan_universe? }
- Compatibility
	- Method/Path: POST /act
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Reads/writes WM/LTM
	- Universe: Optional; affects plan/graph context
	- Side effects: May store memory, create links
	- Maps to: Act/Agent Loop

### POST /reflect

- Purpose: Cluster recent episodics; write semantic summaries
- Request: n/a
- Response: { created: int, summaries: [string] }
- Compatibility
	- Method/Path: POST /reflect
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Summarizes tenant episodics
	- Universe: Ignored
	- Side effects: Writes summary memories
	- Maps to: Reflect/Summarize

### POST /migrate/export

- Purpose: Export memories (+optional WM)
- Request: MigrateExportRequest { include_wm?, wm_limit? }
- Response: MigrateExportResponse { manifest, memories, wm }
- Compatibility
	- Method/Path: POST /migrate/export
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Exports current tenant data
	- Universe: Ignored
	- Side effects: None
	- Maps to: Data Export

### POST /migrate/import

- Purpose: Import memories (+warm WM)
- Request: MigrateImportRequest { manifest, memories, wm?, replace? }
- Response: { imported: int, wm_warmed: int }
- Compatibility
	- Method/Path: POST /migrate/import
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Writes tenant LTM/WM
	- Universe: Ignored
	- Side effects: Data writes; potential replace
	- Maps to: Data Import

### Persona (replacement for personality endpoints)

- Persona CRUD is available at `/persona/{id}` via PUT/GET/DELETE. Use the `Persona` schema (fields: `id`, `display_name`, `properties`) to persist tenant trait records used by the cognitive system.

### GET /brain/core/stats

- Purpose: Inspect core module stats
- Request: n/a
- Response: { thalamus, hippocampus, prefrontal, amygdala, neuromodulators }
- Compatibility
	- Method/Path: GET /brain/core/stats
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Read-only
	- Universe: Ignored
	- Side effects: None
	- Maps to: Core/Stats

### GET /metrics/snapshot

- Purpose: Compact JSON runtime stats
- Request: n/a
- Response: { api_version, tenant, namespace, ... }
- Compatibility
	- Method/Path: GET /metrics/snapshot
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Current tenant + system
	- Universe: Ignored
	- Side effects: None
	- Maps to: Metrics/Snapshot (JSON)

### GET /micro/diag

- Purpose: Microcircuits per-tenant diagnostics (if enabled)
- Request: n/a
- Response: { enabled, tenant, columns }
- Compatibility
	- Method/Path: GET /micro/diag
	- Auth: Yes
	- Minimal mode: Hidden
	- Tenant scope: Current tenant
	- Universe: Ignored
	- Side effects: None
	- Maps to: Diagnostics/Microcircuits

### Feature-gated endpoints

Flags: SOMABRAIN_EXPOSE_ALT_MEMORY_ENDPOINTS, SOMABRAIN_EXPOSE_BRAIN_DEMOS (always hidden in minimal mode)

- FNOM
	- POST /fnom/encode — Auth Yes, Minimal Hidden, Tenant writes; Maps: FNOM/Encode
	- POST /fnom/retrieve — Auth Yes, Minimal Hidden, Tenant reads; Maps: FNOM/Retrieve
	- POST /fnom/consolidate — Auth Yes, Minimal Hidden, Tenant writes; Maps: FNOM/Consolidate
	- POST /fnom/sleep — Auth Yes, Minimal Hidden, Tenant writes; Maps: FNOM/Sleep
	- GET /fnom/stats — Auth Yes, Minimal Hidden, Read-only; Maps: FNOM/Stats
	- GET /fnom/health — Auth Yes, Minimal Hidden, Read-only; Maps: FNOM/Health
	- POST /fnom/learn — Auth Yes, Minimal Hidden, Tenant writes; Maps: FNOM/Learn

- Fractal Memory
	- POST /fractal/encode — Auth Yes, Minimal Hidden, Tenant writes; Maps: Fractal/Encode
	- POST /fractal/retrieve — Auth Yes, Minimal Hidden, Tenant reads; Maps: Fractal/Retrieve
	- POST /fractal/consolidate — Auth Yes, Minimal Hidden, Tenant writes; Maps: Fractal/Consolidate
	- GET /fractal/stats — Auth Yes, Minimal Hidden, Read-only; Maps: Fractal/Stats
	- GET /fractal/health — Auth Yes, Minimal Hidden, Read-only; Maps: Fractal/Health
