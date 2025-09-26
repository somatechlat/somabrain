# SomaBrain Configuration Reference

All runtime state is controlled via environment variables or configuration files sourced from
managed secret stores. This document details every configuration surface, expected defaults, and the
relevant code paths.


## 0. OIDC/JWT Authentication (Keycloak, Cognito, Auth0)

SomaBrain supports OIDC-compliant JWT authentication for all API endpoints. To enable:

- Set `auth_required: true` in config or `SOMABRAIN_AUTH_REQUIRED=1` in env.
- For HS256 (dev/test): set `jwt_secret` or `SOMABRAIN_JWT_SECRET`.
- For RS256 (production): set `jwt_public_key_path` or `SOMABRAIN_JWT_PUBLIC_KEY_PATH` to a PEM file (downloaded from your OIDC provider's JWKS endpoint).
- Set `jwt_issuer` and `jwt_audience` to match your OIDC provider (Keycloak, Cognito, etc).

**Keycloak Example:**
```
auth_required: true
jwt_public_key_path: /secrets/keycloak_public.pem
jwt_issuer: https://keycloak.example.com/realms/somabrain
jwt_audience: somabrain-agents
```

**Cognito Example:**
```
auth_required: true
jwt_public_key_path: /secrets/cognito_public.pem
jwt_issuer: https://cognito-idp.<region>.amazonaws.com/<user-pool-id>
jwt_audience: <app-client-id>
```

Tokens must be sent as `Authorization: Bearer <JWT>` in all API requests. The backend will validate signature, issuer, and audience.

---
## 1. Environment Variables

| Variable | Default | Description | Referenced In |
|----------|---------|-------------|---------------|
| `SOMABRAIN_HOST` | `0.0.0.0` | Bind address for FastAPI service. | `somabrain/app.py` |
| `SOMABRAIN_PORT` | `9696` | Internal port for API server. Exposed host port is auto-chosen by `scripts/dev_up.sh`. | `somabrain/app.py` |
| `SOMABRAIN_WORKERS` | `4` | Gunicorn/Uvicorn workers in container deployments. | Dockerfile entrypoint |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | _required_ | Base URL of external memory service. Leave blank to enable offline mode (writes buffered). | `somabrain/memory_client.py` |
| `SOMABRAIN_REDIS_URL` | `redis://sb_redis:6379/0` | Connection string for Redis cluster. | Constitution cache, rate limiting, hot memory cache. |
| `SOMABRAIN_POSTGRES_DSN` | _required_ | Postgres DSN for ledger, constitution history, graph tables. | `somabrain/storage/db.py` and stores under `somabrain/storage/`. |
| `SOMABRAIN_KAFKA_URL` | `kafka://sb_kafka:9092` | Kafka bootstrap address. | `somabrain/audit.py`, pipeline workers. |
| `SOMABRAIN_KAFKA_SASL_*` | — | SASL username/password for secured clusters. | Kafka client configuration. |
| `SOMABRAIN_KAFKA_TLS_*` | — | Paths or inline certs for TLS auth. | Kafka client configuration. |
| `SOMABRAIN_CONSTITUTION_KEY` | `soma:constitution` | Redis key storing active constitution JSON. | `somabrain/constitution/cloud.py` |
| `SOMABRAIN_CONSTITUTION_SIG_KEY` | `soma:constitution:sig` | Redis key for constitution signature blob. | Same |
| `SOMABRAIN_CONSTITUTION_PUBKEY_PATH` | — | PEM path for verifying constitution signatures (provided by secret store). | `somabrain/constitution/cloud.py` |
| `SOMABRAIN_CONSTITUTION_THRESHOLD` | `2` | Minimum signatures required for constitution update. | `somabrain/constitution/cloud.py` |
| `SOMABRAIN_OPA_URL` | `http://sb_opa:8181` | OPA service endpoint. | `somabrain/api/middleware/opa.py` |
| `SOMABRAIN_OTLP_ENDPOINT` | — | OTLP collector endpoint for exporting traces/metrics. | `observability/provider.py` |
| `SOMABRAIN_TENANT_CONFIG_PATH` | — | Optional path/URL to tenant configuration (JSON/YAML). | `somabrain/tenant.py` |
| `SOMABRAIN_RATE_LIMIT_*` | — | Rate limiting quotas (per-minute, per-second). | `somabrain/ratelimit.py` |
| `SOMABRAIN_TOKEN_LEDGER_DSN` | matches Postgres DSN | DB connection for token accounting (`token_usage`). | `somabrain/storage/token_ledger.py` |
| `SOMABRAIN_FEEDBACK_DSN` | matches Postgres DSN | Optional override for feedback storage (`feedback_events`). | `somabrain/storage/feedback.py` |
| `SOMABRAIN_DEFAULT_TENANT` | `sandbox` | Default tenant identifier when requests omit `tenant_id`. | `/context/evaluate` |
| `SOMABRAIN_JWT_SECRET` | — | HS256 JWT secret for auth (dev/testing). | `somabrain/auth.py` |
| `SOMABRAIN_JWT_PUBLIC_KEY_PATH` | — | Path to PEM public key for JWT validation. | `somabrain/auth.py` |
| `SOMABRAIN_JWT_ISSUER` | — | Expected JWT issuer claim. | `somabrain/auth.py` |
| `SOMABRAIN_JWT_AUDIENCE` | — | Expected JWT audience claim. | `somabrain/auth.py` |
| `SOMABRAIN_SANDBOX_TENANTS` | — | Comma-separated allowlist of tenant ids. | `/context/evaluate` |
| `SOMABRAIN_SANDBOX_TENANTS_FILE` | — | YAML file listing sandbox tenants. | `/context/evaluate` |

All secrets (Kafka passwords, Postgres credentials, private keys) must be delivered via Vault or
cloud secret manager and injected as environment variables or mounted files.

## 2. Port Allocation

`scripts/dev_up.sh` orchestrates local deployment by:
1. Computing free host ports for Somabrain, Redis, Kafka, Postgres, Prometheus using `lsof` / `ss`.
2. Writing `.env.local` with the assignments.
3. Invoking `docker compose -f Docker_Canonical.yml up -d` with the env file.
4. Generating `ports.json` summarizing the active bindings. Test harnesses read this file to target
   the correct ports.

In production, port mappings are managed by Kubernetes Services/Ingress. Ensure that readiness and
liveness probes match the configured ports.

## 3. Configuration Files

| File | Purpose |
|------|---------|
| `docker-entrypoint.sh` | Bootstraps application start, runs migrations (future), launches Uvicorn. |
| `ports.json` | Generated by `dev_up.sh`; not committed. Lists host ports for active services. |
| `configs/tenant/*.yaml` (future) | Tenant-specific overrides (rate limits, token budgets). |
| `ops/prometheus/prometheus.yml` (future) | Prometheus scrape targets for canonical stack. |

## 4. Compose Stack (`Docker_Canonical.yml`)

Services started:
- `redis` – persisted via named volume `redis_data`.
- `kafka` (Redpanda) – single-node dev broker; production uses external KRaft cluster.
- `opa` – policy engine pulling bundles from `ops/opa/policies` (to be populated).
- `prometheus` – monitoring stack.
- `somabrain` – built via `Dockerfile`, binds container port 9696 to host port from `.env.local`.
- `postgres` – development database; production uses managed service.
- *(Agent-side SLM inference is not part of the canonical stack; agents run their own models and
   connect over the public API.)*

## 5. Feature Flags & Behavior

Upcoming feature flags (implemented as environment toggles):
- `SOMABRAIN_ENABLE_REWARD_GATE` – toggles reward gating middleware (default off until S4).
- `SOMABRAIN_ENABLE_TRACING` – forces tracing initialization even if OTLP endpoint missing (for
  debugging).
- `SOMABRAIN_DISABLE_CONSTITUTION_ENFORCEMENT` – development-only flag to bypass constitution checks.
  **Never enable in production.**

## 6. Testing Configuration

- Integration tests rely on the canonical stack; tests lookup `ports.json` to determine endpoints.
- Benchmarks read configuration from `benchmarks/config/*.yaml` (coming in S9) to drive load.
- Test secrets (Kafka, Redis) are stored in `.env.test` for local runs; CI injects secrets via
  GitHub Actions environment variables.

## 7. Deployment Configuration

Kubernetes manifests (to be added in `infra/`):
- ConfigMaps for base environment variables.
- Secrets for credentials (mounted via CSI).
- Horizontal Pod Autoscaler definitions for API and background workers (agents scale their own
  SLM infrastructure separately).
- PodDisruptionBudgets for stateful services.

Update this document whenever new configuration knobs are introduced or existing ones change.

## 8. mTLS Ingress with Envoy

All inbound API traffic is routed through Envoy, which enforces mutual TLS (mTLS).

- Envoy listens on port 8443 and proxies to the internal API service.
- Only clients with valid certificates signed by the trusted CA can connect.
- The `somabrain` service is no longer exposed directly; ingress is via Envoy on port 8443.

### Setup Steps

1. **Generate Certificates**
   Run the provided script to generate a CA, server, and client certificates:
   ```sh
   cd ops/envoy
   ./generate_certs.sh
   ```
   This creates `ca.crt`, `server.crt`, `server.key`, `client.crt`, `client.key` in `ops/envoy/certs/`.

2. **Build and Start the Stack**
   ```sh
   docker compose -f Docker_Canonical.yml build envoy
   # Or build all services:
   docker compose -f Docker_Canonical.yml build
   docker compose -f Docker_Canonical.yml up
   ```
   Envoy listens on `8443` (mTLS). All API requests must use this port and present a valid client certificate.

3. **Test mTLS Ingress**
   Example curl command (from project root):
   ```sh
   curl --cert ops/envoy/certs/client.crt --key ops/envoy/certs/client.key --cacert ops/envoy/certs/ca.crt \
     https://localhost:8443/health
   ```
   You should see the health response from the API. Requests without a valid client cert will be rejected.

4. **Configuration Details**
   - Envoy config: `ops/envoy/envoy.yaml`
   - Certs: `ops/envoy/certs/`
   - Dockerfile: `ops/envoy/Dockerfile`
   - Compose: `Docker_Canonical.yml` (service: `envoy`)

5. **Security Notes**
   - Never share private keys (`server.key`, `client.key`).
   - For production, use a real CA and rotate certs regularly.
   - Adjust `match_subject_alt_names` in `envoy.yaml` as needed for your client CN/SAN.

For more details, see the [Envoy mTLS docs](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/ssl).

## 9. Advanced Math Modules (2025)

### Density Matrix Cleanup
- Enable with `DENSITY_MATRIX_ENABLED=1` (default: off).
- Controls: `DENSITY_MATRIX_LAMBDA`, `DENSITY_MATRIX_ALPHA` (mixing weights).
- See `memory/density.py` for details.

### FRGO Transport Learning
- Enable with `FRGO_ENABLED=1` (default: off).
- Controls: `FRGO_ETA`, `FRGO_ALPHA`, `FRGO_LAMBDA`, `FRGO_CMIN`, `FRGO_CMAX`.
- See `transport/flow_opt.py` for details.

### Bridge Planning (Heat Kernel/Sinkhorn)
- Enable with `BRIDGE_PLANNING_ENABLED=1` (default: off).
- Controls: `BRIDGE_BETA`, `BRIDGE_NITER`, `BRIDGE_TOL`.
- See `transport/bridge.py` for details.

All modules are float64, batched, and monitored for stability. See `docs/architecture/DETAILED_ARCHITECTURE.md` for math details.
