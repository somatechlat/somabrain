# Runtime Configuration

This reference lists only the environment variables the runtime reads in strict mode. See the runbook for operational procedures.

| Variable | Default | Purpose | Where Used |
| --- | --- | --- | --- |
| `SOMABRAIN_STRICT_REAL` | unset (false) | Enforce no-stub execution paths | `somabrain.app` startup guard |
| `SOMABRAIN_FORCE_FULL_STACK` | 0 | Require external services before readiness | `somabrain/config.py` |
| `SOMABRAIN_REQUIRE_MEMORY` | 0 | Fail startup if memory HTTP endpoint is absent | `somabrain/config.py` |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | unset | URL of the long-term memory service | `somabrain/memory_client.py` |
| `SOMABRAIN_DISABLE_AUTH` | false | Allow unauthenticated requests (dev only) | `somabrain/app.py` |
| `SOMABRAIN_PREDICTOR_PROVIDER` | `mahal` | Selects predictor backend | `common/config/settings.py` |
| `SOMABRAIN_MODE` | unset | Labels the deployment (dev, staging, prod) | surfaced in `/health` |
| `SOMABRAIN_TENANT` | unset | Optional tenant override for CLI tools | `somabrain/app.py` |

### Loading Order
1. `.env.local` if present (written by `scripts/dev_up.sh`).
2. Real environment variables.
3. Defaults inside `common.config.settings.Settings`.

The `Settings` object is imported once at process start (`common/config/settings.py`) and reused everywhere. Avoid calling `os.getenv` directly in new code; rely on `shared_settings` instead.

### Local Convenience
Create a `.env.local` to mirror strict mode (also used by `scripts/generate_configmap.py`):
```env
SOMABRAIN_STRICT_REAL=1
SOMABRAIN_FORCE_FULL_STACK=1
SOMABRAIN_REQUIRE_MEMORY=1
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
SOMABRAIN_DISABLE_AUTH=1
SOMABRAIN_PREDICTOR_PROVIDER=mahal
```
Then run `docker compose up -d` or `uvicorn` with `PYTHONPATH=$(pwd)` to pick up the settings.

Update this table when you add or remove configuration knobs.
