# Runtime Configuration

**Purpose**: Central reference for SomaBrain environment variables and configuration loading order when enforcing external backends.

**Audience**: Operators and system administrators configuring SomaBrain in any environment.

**Prerequisites**: Familiarity with `.env` management, Kubernetes/Helm secret distribution, and the deployment process described in `deployment.md`.

---

## Environment Variable Reference

Authoritative settings come from `common/config/settings.py`. New code should import `from common.config.settings import settings`.

| Variable | Default | Purpose | Source |
| --- | --- | --- | --- |
| `SOMABRAIN_MODE` | `enterprise` (treated as prod) | Deployment mode: dev, staging, prod; `enterprise` maps to prod | shared settings |
| `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | unset (false) | Enforce real backends (no stubs) | shared settings |
| `SOMABRAIN_STRICT_REAL` | 1 (default in env.example, Helm, Compose) | Hard-fail on stub/placeholder paths | deployment defaults |
| `SOMABRAIN_FORCE_FULL_STACK` | 0 | Also require all external services before ready | shared settings |
| `SOMABRAIN_REQUIRE_MEMORY` | 1 (in Docker envs) | Fail startup if memory HTTP is absent/unhealthy | shared settings |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | Docker default: `http://host.docker.internal:9595` | URL of the external memory service | shared settings → memory client |
| `SOMABRAIN_MEMORY_HTTP_TOKEN` | unset | Bearer token for memory service | shared settings → memory client |
| `SOMABRAIN_HTTP_MAX_CONNS` | 64 | Max HTTP connections to backends | shared settings |
| `SOMABRAIN_HTTP_KEEPALIVE` | 32 | Keepalive connections | shared settings |
| `SOMABRAIN_HTTP_RETRIES` | 1 | Backend HTTP retry attempts | shared settings |
| `SOMABRAIN_DISABLE_AUTH` | 0 | Bypass API auth (dev only) | app |
| `SOMABRAIN_MINIMAL_PUBLIC_API` | 0 | Expose a reduced surface (experiments) | app |
| `SOMABRAIN_PREDICTOR_PROVIDER` | `stub` (Docker sets `mahal`) | Predictor backend selection | shared settings |
| `SOMA_HEAT_METHOD` | `lanczos` (default in env.example, Helm, Compose) | Heat kernel approximation: `chebyshev` or `lanczos` | diffusion |
| `SOMABRAIN_ENABLE_TEACH_FEEDBACK` | 1 (default in env.example, Helm, Compose) | Enable teach→r_user reward processor loop | cognition |
| `SOMABRAIN_REDIS_URL` | unset | Redis URL (e.g. `redis://somabrain_redis:6379/0`) | shared settings |
| `SOMABRAIN_KAFKA_URL` | unset | Kafka bootstrap (e.g. `kafka://somabrain_kafka:9092`) | shared settings |
| `SOMABRAIN_OPA_URL` | unset | OPA base URL | shared settings |
| `SOMA_OPA_TIMEOUT` | 2.0 | OPA request timeout (seconds) | shared settings |
| `SOMA_OPA_FAIL_CLOSED` | 0 (dev), 1 (non‑dev) | Treat OPA failures as deny | shared settings (mode-derived) |
| `SOMABRAIN_POSTGRES_DSN` | unset | Postgres DSN | shared settings |
| `SOMABRAIN_JWT_SECRET` | unset | API JWT HMAC secret | shared settings |
| `SOMABRAIN_JWT_PUBLIC_KEY_PATH` | unset | API JWT public key path | shared settings |
| `SOMABRAIN_MEMORY_ENABLE_WEIGHTING` | 0 | Enable memory weighting heuristics | shared settings |
| `SOMABRAIN_MEMORY_PHASE_PRIORS` | unset | Phase weights for memory | shared settings |
| `SOMABRAIN_MEMORY_QUALITY_EXP` | 1.0 | Memory quality exponent | shared settings |
| `SOMABRAIN_DOCKER_MEMORY_FALLBACK` | unset | In-container fallback endpoint if main env is unset | shared settings |

Update this table whenever you introduce or deprecate environment knobs. Keep names consistent with the code.

---

## Loading Order

1. `.env` in the project root (written by `scripts/dev_up.sh` or `scripts/dev_up_9999.sh`).
2. Real environment variables provided by the shell, container, or orchestrator.
3. Defaults inside `common.config.settings.Settings`.

The `Settings` singleton is instantiated once at process start. Avoid direct `os.getenv` lookups in new code—import `shared_settings` from `common.config.settings` instead so changes propagate consistently. For local work, start from `.env.example` and copy it to `.env`.

---

## Modes and derived behaviour

SomaBrain normalizes `SOMABRAIN_MODE` into `{dev, staging, prod}`. The legacy `enterprise` value maps to `prod`.

| Input mode | Normalized | API auth enabled | Require external backends | OPA fail closed | Log level |
| --- | --- | --- | --- | --- | --- |
| `dev`, `development` | dev | No | Yes | No | DEBUG |
| `staging` | staging | Yes | Yes | Yes | INFO |
| `prod`, `enterprise`, empty/unknown | prod | Yes | Yes | Yes | WARNING |

Notes:
- “Require external backends” is enforced across all modes by policy. Avoid stubs in production paths.
- Memory service calls require tokens in all modes.

## Local Backend-Enforcement Template

Use the following `.env` snippet to mirror production behaviour on a workstation:

```env
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
SOMABRAIN_FORCE_FULL_STACK=1
SOMABRAIN_REQUIRE_MEMORY=1
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595   # For direct host runs (uvicorn)
SOMABRAIN_DISABLE_AUTH=1
SOMABRAIN_PREDICTOR_PROVIDER=mahal
SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma_pass@127.0.0.1:5432/somabrain
```

When running inside Docker on macOS/Windows, `127.0.0.1` refers to the container, not the host.
Use:

```env
# In Docker containers (Compose)
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595
```

The dev stack and Dockerfile default to this endpoint for safety.

Reload the process or run `scripts/dev_up.sh --rebuild` after editing the file so the stack picks up the new values.

---

## Operational Notes

- Backend-enforced deployments remain unhealthy until all dependent services respond. Verify readiness with `curl -fsS http://localhost:9696/healthz | jq`.
- Configuration toggles should be surfaced through Git-managed manifests (`docker-compose.yml`, Helm values, or ConfigMaps) rather than ad-hoc changes on running hosts.
- When introducing new environment variables, add tests in `tests/test_config.py` to prevent drift and update this page alongside the code change.

### Best-mode defaults (enabled out of the box)

To simplify safe-by-default deployments, we enable a set of production-grade defaults in Docker Compose and Helm values:

- Strict real execution: `SOMABRAIN_STRICT_REAL=1`
- Diffusion method: `SOMA_HEAT_METHOD=lanczos`
- Teach feedback processor: `SOMABRAIN_ENABLE_TEACH_FEEDBACK=1`

These can be overridden at runtime if you need to roll back quickly:

- Switch heat method: `SOMA_HEAT_METHOD=chebyshev`
- Disable teach feedback loop: `SOMABRAIN_ENABLE_TEACH_FEEDBACK=0`

See also: Technical Manual → Predictors (diffusion) for parameter tuning, and Development Manual → Testing for the teach→reward E2E smoke.

## Diagnostics

- Startup logs print the effective memory endpoint, whether a token is present, mode, and whether the process runs in a container. A warning is emitted if the endpoint is `localhost`/`127.0.0.1` inside Docker.
- `GET /diagnostics` returns a sanitized snapshot:

```json
{
	"in_container": true,
	"mode": "enterprise",
	"external_backends_required": true,
	"require_memory": true,
	"memory_endpoint": "http://host.docker.internal:9595",
	"env_memory_endpoint": "http://host.docker.internal:9595",
	"shared_settings_present": true,
	"shared_settings_memory_endpoint": "http://host.docker.internal:9595",
	"memory_token_present": true,
	"api_version": 1
}
```

Use this to confirm wiring and policy flags during incidents.
