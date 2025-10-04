# SomaBrain Configuration Reference

All runtime configuration is controlled via environment variables. This document now reflects the actual code paths and defaults.

## 0. OIDC/JWT Authentication (Keycloak, Cognito, Auth0)

* `SOMABRAIN_DISABLE_AUTH` – Set to `1` to skip JWT validation (dev only). Default is `0`.
* `SOMABRAIN_JWT_SECRET` – HS256 secret for dev/testing.
* `SOMABRAIN_JWT_PUBLIC_KEY_PATH`, `SOMABRAIN_JWT_ISSUER`, `SOMABRAIN_JWT_AUDIENCE` – RSA‑based validation for production.
* To re‑enable auth, clear `SOMABRAIN_DISABLE_AUTH` and provide the appropriate JWT settings.

---
## 1. Environment Variables (core)

| Variable | Default | Description | Referenced In |
|----------|---------|-------------|---------------|
| `SOMABRAIN_HOST` | `0.0.0.0` | Bind address for FastAPI. | `somabrain/app.py` |
| `SOMABRAIN_PORT` | `9696` | Port for the API server. | `somabrain/app.py` |
| `SOMABRAIN_WORKERS` | `1` | Uvicorn worker count. | `docker-entrypoint.sh` |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | **required** – e.g. `http://host.docker.internal:9595` | URL of the external memory service. In Kubernetes this is `http://somamemory.<ns>.svc.cluster.local:9595`. | `somabrain/memory_client.py` |
| `SOMABRAIN_REDIS_URL` | `redis://redis:6379/0` | Redis connection string. | Various cache and rate‑limit components |
| `SOMABRAIN_POSTGRES_DSN` | **required** | Postgres DSN for ledger, constitution, etc. | `somabrain/storage/db.py` |
| `SOMABRAIN_KAFKA_URL` | `kafka://kafka:9092` | Kafka bootstrap address. | Audit pipeline |
| `SOMABRAIN_OPA_URL` | `http://sb_opa:8181` | OPA policy engine endpoint. | `somabrain/api/middleware/opa.py` |
| `SOMABRAIN_DISABLE_AUTH` | `0` | Skip JWT validation when set to `1`. | `somabrain/auth.py` |
| `SOMABRAIN_STRICT_REAL` | `0` | Enforce "no‑stubs" mode (predictor, embedder, recall). | Various runtime checks |
| `SOMABRAIN_PREDICTOR_PROVIDER` | `stub` (dev) | Predictor implementation (`mahal`, `llm`, `stub`). In strict mode `stub` is rejected. | `somabrain/app.py` |
| `SOMABRAIN_FORCE_FULL_STACK` | `0` | Require external memory, real embedder, and non‑stub predictor for readiness. | `somabrain/app.py` |
| `SOMABRAIN_CONSOLIDATION_TIMEOUT_S` | `1.0` | Max seconds per NREM/REM phase during `/sleep/run` to avoid long requests. | `somabrain/consolidation.py` |
| `SOMABRAIN_ENABLE_BEST` | `0` | Shortcut that enables full stack + weighting defaults. | `somabrain/app.py` |
| `SOMABRAIN_REQUIRE_MEMORY` | `1` | When `1` the memory service must be reachable; otherwise the process fails on startup. | `somabrain/memory_client.py` |
| `SOMABRAIN_MEMORY_ENABLE_WEIGHTING` | `0` | Enable phase‑based weighting for recall results. | `somabrain/memory_client.py` |
| `SOMABRAIN_MEMORY_PHASE_PRIORS` | — | Comma‑separated `phase:multiplier` list (e.g. `bootstrap:1.05,general:1.0`). | `somabrain/memory_client.py` |
| `SOMABRAIN_MEMORY_QUALITY_EXP` | `1.0` | Exponent applied to `quality_score` before weighting. | `somabrain/memory_client.py` |
| `SOMABRAIN_HTTP_MAX_CONNS` | `64` | Max concurrent httpx connections to the memory service. | `somabrain/memory_client.py` |
| `SOMABRAIN_HTTP_KEEPALIVE` | `32` | Max keep‑alive connections. | `somabrain/memory_client.py` |
| `SOMABRAIN_HTTP_RETRIES` | `1` | Transport‑level retry count. | `somabrain/memory_client.py` |
| `SOMABRAIN_OTLP_ENDPOINT` | — | OTLP collector for traces/metrics. | `observability/provider.py` |
| `SOMABRAIN_TENANT_CONFIG_PATH` | — | Optional path/URL to tenant config YAML/JSON. | `somabrain/tenant.py` |
| `SOMABRAIN_DEFAULT_TENANT` | `sandbox` | Default tenant when none supplied. | Context evaluation |
| `SOMABRAIN_JWT_*` | — | JWT secret/public‑key, issuer, audience. | `somabrain/auth.py` |
| `SOMABRAIN_SANDBOX_TENANTS` / `*_FILE` | — | Allow‑list of sandbox tenant IDs. | Context evaluation |

### Predictor Provider Precedence
1. `SOMABRAIN_PREDICTOR_PROVIDER` (env)
2. `predictor_provider` in `config.yaml`
3. Fallback `stub` (rejected in strict mode)

If strict mode is enabled and the resolved provider is `stub`, the process aborts with a clear error.

### Strict Mode (`SOMABRAIN_STRICT_REAL=1`)
* Disallows any stub usage.
* Requires a real predictor (`mahal` or `llm`).
* Memory recall must succeed via HTTP or deterministic in‑process path.
* Embedder must be a real implementation (`tiny` is the default).

## 2. Port Allocation (dev_up.sh)

`scripts/dev_up.sh` performs the following steps:
1. Detects free host ports for Somabrain, Redis, Kafka, Prometheus, Postgres, and Memory.
2. Writes a clean `.env.local` with those ports (fixed defaults are used when ports are free).
3. Starts the Docker Compose stack with `docker compose -f Docker_Canonical.yml up -d --build`.
4. Waits for the Somabrain `/health` endpoint to become healthy.
5. Generates `ports.json` for test harnesses.

In production, port mapping is handled by Kubernetes Services; the script is only for local development.

---
## 3. Compose Stack (`Docker_Canonical.yml`)

Key services:
* `redis` – persisted via named volume `redis_data`.
* `kafka` – single‑node broker (Redpanda) on port `9092`.
* `opa` – policy engine on `8181`.
* `prometheus` – metrics on `9090`.
* `postgres` – database on host port `15432` (container `5432`).
* `somabrain` – API on host port `9696` (container `9696`).
* `somamemory` – external memory service on host port `9595` (container `9595`).

All services share the `somabrain_somabrain_net` network.

---
## 4. Feature Flags (future)

* `SOMABRAIN_ENABLE_REWARD_GATE` – toggles reward‑gate middleware.
* `SOMABRAIN_ENABLE_TRACING` – forces tracing even without OTLP endpoint.
* `SOMABRAIN_DISABLE_CONSTITUTION_ENFORCEMENT` – dev‑only, bypasses constitution checks (never enable in prod).

---
## 5. Testing Configuration

Integration tests read `ports.json` to discover service endpoints. The test harness expects:
* API at `http://localhost:${SOMABRAIN_HOST_PORT}` (default `9696`).
* Memory at `http://localhost:${SOMAMEMORY_HOST_PORT}` (default `9595`).
* Redis, Kafka, Postgres, OPA reachable on their default ports.

When running against a remote cluster, port‑forward the services and set `SOMA_API_URL` accordingly.

---
## 6. Health & Readiness Contract

`/health` now returns:
```json
{
  "ok": true,
  "components": {"memory": {"http": true}, "wm_items": "tenant-scoped", "api_version": "v1"},
  "namespace": "somabrain_ns:public",
  "predictor_provider": "mahal",
  "strict_real": true,
  "embedder": {"provider": "tiny", "dim": 256},
  "ready": true,
  "memory_items": 0,
  "stub_counts": {}
}
```
Readiness requires a non‑stub predictor, a working embedder, and a reachable memory service (or deterministic in‑process recall when memory is unavailable).

Dev‑mode notes:
- Docker profile uses a single worker (SOMABRAIN_WORKERS=1) to preserve in‑process WM read‑your‑writes across requests.
- If you run multiple workers locally, immediate `/recall` after `/remember` may rely on the external memory backend. Keep memory healthy or add a brief client retry.

---
## 7. Deployment Guidance

* **Kubernetes** – use the provided Helm chart (not included in this repo) which creates ConfigMaps for the env vars above and Secrets for credentials. Services are exposed via ClusterIP; ingress is handled by an optional Envoy mTLS layer (`ops/envoy`).
* **Envoy mTLS** – optional; see `ops/envoy/README.md` for setup steps. If not used, access the API directly on port `9696`.

---
## 8. Advanced Math Modules (2025)

* **Density Matrix Cleanup** – `DENSITY_MATRIX_ENABLED=1` (controls `memory/density.py`).
* **FRGO Transport Learning** – `FRGO_ENABLED=1` (controls `transport/flow_opt.py`).
* **Bridge Planning** – `BRIDGE_PLANNING_ENABLED=1` (controls `transport/bridge.py`).

These modules are gated behind environment flags and are monitored for stability.

---
## 9. Outbox (offline writes)

Failed writes to the memory service are stored in `./data/somabrain/outbox.jsonl` (configurable via `outbox_path` in `config.yaml`). A background worker retries these entries and updates the `OUTBOX_PENDING` metric.

---
*This document is the single source of truth for configuration. All other docs that duplicate environment variable tables should be removed or redirected here.*
