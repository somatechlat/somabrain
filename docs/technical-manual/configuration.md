# Runtime Configuration

**Purpose**: Central reference for SomaBrain environment variables and configuration loading order when enforcing external backends.

**Audience**: Operators and system administrators configuring SomaBrain in any environment.

**Prerequisites**: Familiarity with `.env` management, Kubernetes/Helm secret distribution, and the deployment process described in `deployment.md`.

---

## Environment Variable Reference

| Variable | Default | Purpose | Where Used |
| --- | --- | --- | --- |
| `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | unset (false) | Enforce no-stub execution paths | `somabrain.app` startup guard |
| `SOMABRAIN_FORCE_FULL_STACK` | 0 | Require external services before readiness | `common/config/settings.py` |
| `SOMABRAIN_REQUIRE_MEMORY` | 0 | Fail startup if memory HTTP endpoint is absent | `common/config/settings.py` |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | unset (Docker stack sets `http://host.docker.internal:9595`) | URL of the long-term memory service | `somabrain/memory_client.py` |
| `SOMABRAIN_DISABLE_AUTH` | 0 | Allow unauthenticated requests (dev only) | `somabrain/app.py` |
| `SOMABRAIN_PREDICTOR_PROVIDER` | `mahal` | Select predictor backend | `common/config/settings.py` |
| `SOMABRAIN_MODE` | unset | Labels the deployment (dev, staging, prod) | Surfaced in `/health` |
| `SOMABRAIN_TENANT` | unset | Optional tenant override for CLI tools | `somabrain/app.py` |
| `SOMABRAIN_REDIS_URL` | `redis://localhost:6379/0` | Working-memory and cache endpoint | `somabrain/memstore.py` |
| `SOMABRAIN_KAFKA_BOOTSTRAP` | unset | Kafka bootstrap servers | `somabrain/audit.py` |
| `SOMABRAIN_POSTGRES_DSN` | unset | Postgres connection string | `somabrain/db/__init__.py` |

Update the table whenever new knobs are introduced or deprecated so operators have a single source of truth.

---

## Loading Order

1. `.env` in the project root (written by `scripts/dev_up.sh` or `scripts/assign_ports.sh`).
2. Real environment variables provided by the shell, container, or orchestrator.
3. Defaults inside `common.config.settings.Settings`.

The `Settings` singleton is instantiated once at process start. Avoid direct `os.getenv` lookups in new code—import `shared_settings` from `common.config.settings` instead so changes propagate consistently. For local work, start from `.env.example` and copy it to `.env`.

---

## Local Backend-Enforcement Template

Use the following `.env` snippet to mirror production behaviour on a workstation:

```env
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
SOMABRAIN_FORCE_FULL_STACK=1
SOMABRAIN_REQUIRE_MEMORY=1
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
SOMABRAIN_DISABLE_AUTH=1
SOMABRAIN_PREDICTOR_PROVIDER=mahal
SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma_pass@127.0.0.1:5432/somabrain
```

> The bundled Docker Compose stack expects a real memory service reachable at
> `http://host.docker.internal:9595`; update the value if your deployment runs
> the service elsewhere.

Reload the process or run `scripts/dev_up.sh --rebuild` after editing the file so the stack picks up the new values.

---

## Operational Notes

- Backend-enforced deployments remain unhealthy until all dependent services respond. Verify readiness with `curl -fsS http://localhost:9696/health | jq`.
- Configuration toggles should be surfaced through Git-managed manifests (`docker-compose.yml`, Helm values, or ConfigMaps) rather than ad-hoc changes on running hosts.
- When introducing new environment variables, add tests in `tests/test_config.py` to prevent drift and update this page alongside the code change.
