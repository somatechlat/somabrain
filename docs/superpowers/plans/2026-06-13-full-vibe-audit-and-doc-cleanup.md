# Full VIBE Audit & Documentation Cleanup Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden SomaBrain into a production-grade, VIBE-compliant Django+Ninja codebase: remove security risks, fake data paths, broad exception swallowing, global mutable state, AI-generated filler, and outdated docs; then verify with the existing test matrix.

**Architecture:** Treat the codebase as a real-time Django API that depends on SomaFractalMemory (HTTP), Postgres, Redis, Kafka, and optional Milvus/Vault/OPA. All fixes must be observable (logs/metrics/health), fail-closed for security, and documented. Work is split by risk/security first, then correctness, then quality/docs.

**Tech Stack:** Python 3.12, Django 5.2, Django Ninja, SFM HTTP client, Postgres, Redis, Kafka, Docker Compose standalone, Kubernetes/Tilt/Helm.

---

## Scope & File Map

The audit covered five domains. The plan below merges them into one ordered backlog. Because the cleanup is large, tasks are grouped into **phases**. Each phase is independently testable.

| Domain | Key Files |
|---|---|
| Memory | `somabrain/memory/**`, `somabrain/controls/memory_client.py`, `somabrain/services/memory_service.py`, `somabrain/api/endpoints/memory.py`, `somabrain/api/endpoints/memory_remember.py`, `somabrain/memory/client/transport.py`, `somabrain/memory/transport.py`, `somabrain/memory/client/write.py`, `somabrain/memory/client/read.py`, `somabrain/memory/client/core.py`, `somabrain/memory/client/search.py`, `somabrain/memory/wm/wm_salience.py` |
| API / Auth / Tenant | `somabrain/api/**`, `somabrain/tenant.py`, `somabrain/core/security/**`, `somabrain/api/auth.py`, `somabrain/api/standalone_auth.py`, `somabrain/aaas/auth/oauth.py`, `somabrain/aaas/auth/core.py`, `somabrain/aaas/auth/permissions.py`, `somabrain/api/endpoints/auth.py`, `somabrain/api/endpoints/admin.py`, `somabrain/api/endpoints/system_health.py`, `somabrain/api/endpoints/health.py`, `somabrain/api/dependencies/utility_guard.py`, `somabrain/api/context_validation.py`, `somabrain/api/memory/helpers.py` |
| Cognitive / Runtime | `somabrain/api/endpoints/cognitive.py`, `somabrain/services/retrieval_pipeline.py`, `somabrain/services/cognitive_loop_service.py`, `somabrain/services/plan_engine.py`, `somabrain/admin/brain/focus_state.py`, `somabrain/controls/cognitive_middleware.py`, `somabrain/runtime/manager.py`, `somabrain/runtime/neuromodulators.py`, `somabrain/runtime/healthchecks.py`, `somabrain/runtime/supervisor.py`, `somabrain/runtime/modes.py`, `somabrain/predictors/**`, `somabrain/settings/cognitive.py` |
| Settings / Infra | `somabrain/settings/**`, `config/**`, `infra/**`, `.env.example`, `config/env.example`, `infra/tls/**`, `infra/standalone/docker-compose.yml`, `infra/standalone/Dockerfile`, `infra/standalone/docker-entrypoint.sh`, `infra/k8s/**`, `infra/tilt/**`, `infra/helm/**` |
| Tests / Docs | `tests/**`, `docs/**`, `AGENTS.md`, `README.md`, `VIBE_RULES.md` |

---

## Phase 1 — Security & Secrets (Critical)

### Task 1.1: Remove committed TLS private key from git

**Files:**
- Delete from git: `infra/tls/somabrain.internal.crt`, `infra/tls/somabrain.internal.key`
- Add/update: `infra/tls/.gitignore`, `infra/tls/README.md`

- [ ] **Step 1: Remove tracked TLS secrets**

```bash
git rm --cached infra/tls/somabrain.internal.crt infra/tls/somabrain.internal.key
```

- [ ] **Step 2: Ensure `.gitignore` blocks them**

```gitignore
*.crt
*.key
*.pem
```

- [ ] **Step 3: Add a local cert generation script**

Create `infra/tls/generate-local-certs.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
CN="${1:-somabrain.internal}"
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "infra/tls/${CN}.key" \
  -out "infra/tls/${CN}.crt" \
  -days 365 -subj "/CN=${CN}"
```

- [ ] **Step 4: Verify no secrets are tracked**

```bash
git ls-files infra/tls/
```

Expected: only `README.md`, `.gitignore`, and `generate-local-certs.sh`.

- [ ] **Step 5: Commit**

```bash
git add infra/tls/
git commit -m "security: remove committed TLS key/cert and add local generation script"
```

---

### Task 1.2: Eliminate JWT signature bypass in DEBUG mode

**Files:**
- Modify: `somabrain/aaas/auth/oauth.py:22-90`
- Test: existing auth tests + add a forgery test

- [ ] **Step 1: Write failing test**

Create/append `tests/unit/test_oauth_debug_bypass.py`:

```python
import pytest
from somabrain.aaas.auth.oauth import JWTAuth


class TestJWTAuthNoDebugBypass:
    def test_debug_mode_does_not_accept_unsigned_token(self, settings):
        settings.DEBUG = True
        auth = JWTAuth()
        # Token with alg=none / forged signature
        forged = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjMifQ."
        assert auth.authenticate(None, forged) is None
```

- [ ] **Step 2: Run and confirm failure**

```bash
pytest tests/unit/test_oauth_debug_bypass.py -v
```

- [ ] **Step 3: Remove bypass code**

In `somabrain/aaas/auth/oauth.py`, delete the `if getattr(settings, "DEBUG", False):` block and rely on normal JWKS decoding.

```python
def _decode_with_jwks(self, token: str) -> dict | None:
    try:
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=getattr(settings, "KEYCLOAK_CLIENT_ID", None),
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        return None
```

- [ ] **Step 4: Delete unused JWKS cache attributes**

Remove `_jwks_cache`, `_jwks_fetched_at`, `JWKS_CACHE_TTL` or implement real caching.

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_oauth_debug_bypass.py tests/unit/test_aaas_mode.py -v
```

- [ ] **Step 6: Commit**

```bash
git add somabrain/aaas/auth/oauth.py tests/unit/test_oauth_debug_bypass.py
git commit -m "security: remove DEBUG JWT signature bypass and stale JWKS cache attrs"
```

---

### Task 1.3: Harden login JWT signing

**Files:**
- Modify: `somabrain/api/endpoints/auth.py:90-170`
- Modify: `somabrain/settings/django_core.py:133-137`
- Modify: `.env.example`, `config/env.example`

- [ ] **Step 1: Require `SOMABRAIN_JWT_SECRET` explicitly**

In `auth.py`, replace:

```python
secret = getattr(settings, "SOMABRAIN_JWT_SECRET", settings.SECRET_KEY)
```

with:

```python
secret = getattr(settings, "SOMABRAIN_JWT_SECRET", None)
if not secret:
    raise ImproperlyConfigured("SOMABRAIN_JWT_SECRET must be set")
```

- [ ] **Step 2: Make token TTL configurable**

```python
from datetime import timedelta

ttl_hours = getattr(settings, "SOMABRAIN_JWT_ACCESS_TOKEN_TTL_HOURS", 24)
exp = datetime.utcnow() + timedelta(hours=int(ttl_hours))
```

- [ ] **Step 3: Separate Django `SECRET_KEY` from JWT secret**

In `django_core.py`, ensure `SECRET_KEY` is read independently:

```python
SECRET_KEY = env.str("SECRET_KEY", default=None)
SOMABRAIN_JWT_SECRET = env.str("SOMABRAIN_JWT_SECRET", default=None)
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be set")
```

- [ ] **Step 4: Update env templates**

Add to `.env.example` and `config/env.example`:

```bash
SECRET_KEY=replace-me-in-production
SOMABRAIN_JWT_SECRET=replace-me-in-production
SOMABRAIN_JWT_ACCESS_TOKEN_TTL_HOURS=24
```

- [ ] **Step 5: Commit**

```bash
git add somabrain/api/endpoints/auth.py somabrain/settings/django_core.py .env.example config/env.example
git commit -m "security: require explicit JWT secret and configurable token TTL"
```

---

### Task 1.4: Fix rate-limit key when client IP is missing

**Files:**
- Modify: `somabrain/api/endpoints/auth.py:148-163`

- [ ] **Step 1: Ensure non-empty rate-limit key**

```python
client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
client_ip = client_ip.split(",")[0].strip() or "unknown"
rate_limit_key = f"auth_rate_limit:{client_ip}"
```

- [ ] **Step 2: Add test**

```python
def test_login_rate_limit_key_never_empty(rf):
    request = rf.post("/api/auth/login")
    request.META = {}
    # exercise the helper logic
    assert _rate_limit_key(request) == "auth_rate_limit:unknown"
```

- [ ] **Step 3: Commit**

```bash
git add somabrain/api/endpoints/auth.py tests/unit/test_auth_rate_limit.py
git commit -m "security: avoid empty rate-limit key for anonymous login attempts"
```

---

### Task 1.5: Fix supervisor credentials embedded in URL

**Files:**
- Modify: `somabrain/api/endpoints/admin.py:41-47`

- [ ] **Step 1: Use separate credentials, not URL credentials**

```python
from xmlrpc.client import ServerProxy, Transport

url = getattr(settings, "SUPERVISOR_URL", "http://somabrain_cog:9001/RPC2")
user = getattr(settings, "SUPERVISOR_HTTP_USER", None)
pwd = getattr(settings, "SUPERVISOR_HTTP_PASS", None)

if user and pwd:
    transport = Transport()
    server = ServerProxy(url, transport=transport)
    server._ServerProxy__transport.user = user
    server._ServerProxy__transport.password = pwd
else:
    server = ServerProxy(url)
```

(Or use `httpx` basic-auth wrapper if XML-RPC transport is too low-level.)

- [ ] **Step 2: Remove defaults from `infra.py`**

```python
SUPERVISOR_HTTP_USER = env.str("SUPERVISOR_HTTP_USER")  # no default
SUPERVISOR_HTTP_PASS = env.str("SUPERVISOR_HTTP_PASS")  # no default
```

- [ ] **Step 3: Commit**

```bash
git add somabrain/api/endpoints/admin.py somabrain/settings/infra.py
git commit -m "security: stop embedding supervisor credentials in URL"
```

---

### Task 1.6: Harden standalone auth empty-token handling

**Files:**
- Modify: `somabrain/api/standalone_auth.py:34-45`

- [ ] **Step 1: Fail closed when token is not configured**

```python
expected = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", None)
if not expected:
    logger.error("SOMABRAIN_MEMORY_HTTP_TOKEN is not configured")
    return None
if token != expected:
    return None
```

- [ ] **Step 2: Commit**

```bash
git add somabrain/api/standalone_auth.py
git commit -m "security: reject all requests when standalone API token is unset"
```

---

### Task 1.7: Remove hardcoded test database passwords

**Files:**
- Modify: `tests/conftest.py:28`
- Modify: `tests/standalone/conftest.py:16-19`
- Modify: `docs/USER_GUIDE.md:862`, `docs/SRS_FULL.md:716`

- [ ] **Step 1: Remove password defaults**

In `tests/conftest.py`:

```python
"SOMA_DB_PASSWORD": os.environ["SOMA_DB_PASSWORD"],
```

In `tests/standalone/conftest.py`:

```python
_pg_password = os.environ.get("TEST_PG_PASSWORD") or os.environ["POSTGRES_PASSWORD"]
```

- [ ] **Step 2: Update docs to use placeholder**

Replace hardcoded passwords with `<YOUR_DB_PASSWORD>` and instructions to export env vars.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/standalone/conftest.py docs/USER_GUIDE.md docs/SRS_FULL.md
git commit -m "security: remove hardcoded test and doc database passwords"
```

---

## Phase 2 — Correctness: Stop Fake Data & Silent Failures (Critical)

### Task 2.1: Remove fake retrieval candidates

**Files:**
- Modify: `somabrain/services/retrieval_pipeline.py:114-192`

- [ ] **Step 1: Delete fabricated exact-match fallback**

Remove:

```python
if not payload:
    payload = {"task": key}
    score = 1.0
```

If exact memory lookup returns no payload, do not invent one.

- [ ] **Step 2: Delete fake cosine candidate**

Remove:

```python
candidates.append(_candidate_from_payload({"task": req.query}, retriever="cosine", score=0.3))
```

Return an empty list or a structured error when the backend is unavailable.

- [ ] **Step 3: Tighten exception handling**

Catch `httpx.HTTPStatusError`, `httpx.TimeoutException`, `httpx.ConnectError` separately; log unexpected exceptions.

- [ ] **Step 4: Commit**

```bash
git add somabrain/services/retrieval_pipeline.py
git commit -m "fix: remove fabricated retrieval candidates and tighten error handling"
```

---

### Task 2.2: Remove fake predictor fallbacks

**Files:**
- Modify: `somabrain/predictors/base.py:280-297`
- Modify: `somabrain/services/cognitive_loop_service.py:179-196`

- [ ] **Step 1: Fail fast on missing graph file**

In `base.py`:

```python
if not graph_path or not Path(graph_path).exists():
    raise ImproperlyConfigured(
        f"Predictor graph file not configured or missing: {graph_path!r}"
    )
```

Delete `make_line_graph_laplacian` fallback.

- [ ] **Step 2: Remove zero-error fabricated predictor result**

In `cognitive_loop_service.py`, replace the `type("PR", ...)` stub with a real degraded response or raise a clear error.

- [ ] **Step 3: Commit**

```bash
git add somabrain/predictors/base.py somabrain/services/cognitive_loop_service.py
git commit -m "fix: remove fake predictor graph and zero-error result stubs"
```

---

### Task 2.3: Fix memory endpoint silent failures

**Files:**
- Modify: `somabrain/api/endpoints/memory.py:126-145`
- Modify: `somabrain/api/endpoints/memory_remember.py:108, 238`
- Modify: `somabrain/services/memory_service.py:138-282`

- [ ] **Step 1: Map typed exceptions to HTTP status**

Create a helper:

```python
def _map_memory_error(exc: Exception) -> HttpError:
    if isinstance(exc, httpx.TimeoutException):
        return HttpError(504, "memory backend timeout")
    if isinstance(exc, httpx.ConnectError):
        return HttpError(503, "memory backend unreachable")
    if isinstance(exc, MemoryServiceError):
        return HttpError(502, str(exc))
    return HttpError(500, f"unexpected memory error: {exc}")
```

- [ ] **Step 2: Replace broad `except Exception` in `memory_service.py`**

Catch `httpx.HTTPError`, `RuntimeError` (from client), and a custom `MemoryServiceError`; re-raise unexpected exceptions.

- [ ] **Step 3: Surface LTM failures when `layer == "both"`**

Add a `degraded` flag to the response instead of silently dropping LTM results.

- [ ] **Step 4: Commit**

```bash
git add somabrain/api/endpoints/memory.py somabrain/api/endpoints/memory_remember.py somabrain/services/memory_service.py
git commit -m "fix: stop swallowing memory backend errors and surface degraded state"
```

---

### Task 2.4: Fix `utility_guard` dev-mode detection

**Files:**
- Modify: `somabrain/api/dependencies/utility_guard.py:58-63`

- [ ] **Step 1: Use a real setting**

```python
mode = getattr(settings, "SOMABRAIN_MODE", "production").lower()
dev_mode = mode in ("dev", "development", "local")
```

- [ ] **Step 2: Commit**

```bash
git add somabrain/api/dependencies/utility_guard.py
git commit -m "fix: use SOMABRAIN_MODE for utility guard dev-mode detection"
```

---

### Task 2.5: Fix `system_health` hardcoded values

**Files:**
- Modify: `somabrain/api/endpoints/system_health.py:438-448, 532`

- [ ] **Step 1: Use real checks / real version**

```python
import django
"version": django.get_version(),
```

For cognitive check, query actual runtime singletons or return `None`.

- [ ] **Step 2: Commit**

```bash
git add somabrain/api/endpoints/system_health.py
git commit -m "fix: remove hardcoded django version and fake cognitive health check"
```

---

## Phase 3 — Lifecycle & Global State (High)

### Task 3.1: Remove module-level side effects from settings

**Files:**
- Modify: `somabrain/settings/django_core.py:79-131`
- Modify: `somabrain/settings/infra.py:24, 39-96`

- [ ] **Step 1: Move Vault bootstrap to an explicit function**

In `django_core.py`:

```python
def configure_vault_secrets():
    """Apply Vault secrets to os.environ. Call once during startup."""
    ...
```

Call it from `somabrain/config/wsgi.py` or `AppConfig.ready()`.

- [ ] **Step 2: Move TF_METAL env mutation**

In `infra.py`, wrap in a function:

```python
def configure_tf_metal():
    os.environ.setdefault("TF_METAL_DEVICE_HANDLING", "1")
```

- [ ] **Step 3: Commit**

```bash
git add somabrain/settings/django_core.py somabrain/settings/infra.py
git commit -m "refactor: move settings module-level side effects into explicit startup hooks"
```

---

### Task 3.2: Replace global mutable singletons

**Files:**
- Modify: `somabrain/api/endpoints/cognitive.py:42`
- Modify: `somabrain/runtime/manager.py:23-26`
- Modify: `somabrain/runtime/neuromodulators.py:424`
- Modify: `somabrain/aaas/auth/core.py:163`
- Modify: `somabrain/aaas/auth/oauth.py:22-24`

- [ ] **Step 1: Bound focus-state cache**

```python
from cachetools import TTLCache
_focus_state_cache: Dict[str, FocusState] = TTLCache(maxsize=10_000, ttl=3600)
```

- [ ] **Step 2: Encapsulate runtime globals in a class**

In `runtime/manager.py`:

```python
class RuntimeManager:
    def __init__(self):
        self._embedder = None
        self._mt_wm = None
        self._mt_memory = None
        self._cfg = None
        self._lock = threading.Lock()
```

- [ ] **Step 3: Commit per subsystem**

```bash
git add somabrain/api/endpoints/cognitive.py
git commit -m "refactor: bound focus-state cache with TTL"
git add somabrain/runtime/manager.py somabrain/runtime/neuromodulators.py
git commit -m "refactor: encapsulate runtime globals"
git add somabrain/aaas/auth/core.py somabrain/aaas/auth/oauth.py
git commit -m "refactor: remove class-level mutable caches in auth"
```

---

### Task 3.3: Remove `controls/memory_client.py` global instance

**Files:**
- Modify: `somabrain/controls/memory_client.py:129`
- Modify all callers of `memory_client`

- [ ] **Step 1: Delete global instance**

```python
# Remove: memory_client = MemoryClient()
```

- [ ] **Step 2: Update callers to instantiate or receive via DI**

For tests, create a fixture:

```python
@pytest.fixture
def memory_client():
    return MemoryClient()
```

- [ ] **Step 3: Commit**

```bash
git add somabrain/controls/memory_client.py tests/e2e/test_unified_integration.py
git commit -m "refactor: remove global MemoryClient singleton"
```

---

## Phase 4 — Infra & Deployment Hardening (High)

### Task 4.1: Replace uvicorn with gunicorn in K8s/Tilt

**Files:**
- Modify: `infra/k8s/brain-resilient.yaml:242`
- Modify: `infra/tilt/Tiltfile:54`
- Modify: `infra/standalone/Dockerfile` (remove smoke test copy if not needed)

- [ ] **Step 1: Use gunicorn command**

```yaml
command: ["gunicorn", "somabrain.config.wsgi:application", "-b", "0.0.0.0:20020", "--workers", "4"]
```

- [ ] **Step 2: Remove `--reload`**

- [ ] **Step 3: Commit**

```bash
git add infra/k8s/brain-resilient.yaml infra/tilt/Tiltfile
git commit -m "infra: use gunicorn instead of uvicorn in k8s and tilt"
```

---

### Task 4.2: Fix fake outbox-publisher healthcheck

**Files:**
- Modify: `infra/standalone/docker-compose.yml:718-722`

- [ ] **Step 1: Add a real probe or remove it**

If no health endpoint exists:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:30101/healthz')"]
  interval: 30s
  timeout: 5s
  retries: 3
```

(Or remove the healthcheck block entirely.)

- [ ] **Step 2: Commit**

```bash
git add infra/standalone/docker-compose.yml
git commit -m "infra: replace no-op outbox-publisher healthcheck"
```

---

### Task 4.3: Harden K8s manifests

**Files:**
- Modify: `infra/k8s/somabrain-deployment.yaml`
- Modify: `infra/k8s/somabrain-simple.yaml`
- Modify: `infra/helm/charts/soma-infra/values.yaml`
- Modify: `infra/helm/charts/soma-infra/templates/secret.yaml`

- [ ] **Step 1: Switch data services to ClusterIP**

- [ ] **Step 2: Use non-debug OPA image**

- [ ] **Step 3: Non-root + read-only rootfs**

```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
```

- [ ] **Step 4: Enable auth in Helm prod values / fail closed on missing secrets**

- [ ] **Step 5: Commit**

```bash
git add infra/k8s/ infra/helm/
git commit -m "infra: harden k8s networking, security contexts, and helm defaults"
```

---

### Task 4.4: Remove stale supervisor config

**Files:**
- Delete: `infra/ops/supervisor/supervisord.conf`

- [ ] **Step 1: Delete**

```bash
git rm infra/ops/supervisor/supervisord.conf
```

- [ ] **Step 2: Commit**

```bash
git commit -m "infra: remove stale supervisor config referencing non-existent services"
```

---

## Phase 5 — Code Quality: Exceptions, Docstrings, AI Slop (Medium)

### Task 5.1: Replace broad `except Exception` in production code

**Files:**
- Modify: `somabrain/core/security/legacy_auth.py`, `vault_client.py`
- Modify: `somabrain/api/endpoints/memory.py`, `memory_remember.py`, `cognitive.py`, `admin.py`, `health.py`, `system_health.py`
- Modify: `somabrain/api/dependencies/utility_guard.py`, `context_validation.py`, `memory/helpers.py`
- Modify: `somabrain/services/cognitive_loop_service.py`, `plan_engine.py`
- Modify: `somabrain/memory/client/write.py`, `read.py`, `core.py`, `transport.py`

- [ ] **Step 1: Establish exception mapping helper**

Create `somabrain/common/errors.py` if not exists:

```python
class SomaBrainError(Exception):
    pass

class ConfigurationError(SomaBrainError):
    pass

class BackendUnavailableError(SomaBrainError):
    pass
```

- [ ] **Step 2: Replace catches file-by-file**

Catch specific exceptions (`ValueError`, `TypeError`, `KeyError`, `OSError`, `httpx.HTTPError`, `jwt.PyJWTError`, etc.). Log unexpected exceptions with `logger.exception`.

- [ ] **Step 3: Commit in batches**

```bash
git add somabrain/core/security/ somabrain/api/
git commit -m "refactor: tighten exception handling in API and security modules"
```

---

### Task 5.2: Remove AI filler docstrings and hype language

**Files:**
- Modify: all files in `somabrain/api/**`, `somabrain/aaas/**`, `somabrain/memory/**`, `somabrain/runtime/**`, `somabrain/services/**`, `somabrain/predictors/**`

- [ ] **Step 1: Automated search/replace for `"Execute ..."` docstrings**

Use a script to delete or replace docstrings that match `"""Execute ..."""` with a one-line description.

- [ ] **Step 2: Remove hype words**

Search and review:

```bash
grep -Rin "Zero-Latency\|sub-millisecond\|honest 501\|brain-like\|crucial\|sophisticated\|perfect\|flawless\|magic\|VIBE COMPLIANT\|10 PERSONAS" somabrain/ docs/ README.md
```

- [ ] **Step 3: Commit**

```bash
git add somabrain/ README.md docs/
git commit -m "docs: remove AI filler docstrings and hype language from production code"
```

---

### Task 5.3: Fix dead code and unreachable branches

**Files:**
- Modify: `somabrain/api/endpoints/memory_remember.py:44-49, 223-229`
- Modify: `somabrain/memory/client/transport.py:99-105`
- Modify: `somabrain/api/endpoints/system_health.py:506-507`
- Modify: `somabrain/core/security/legacy_auth.py:79-83`

- [ ] **Step 1: Delete dead code**

- [ ] **Step 2: Commit**

```bash
git add somabrain/
git commit -m "refactor: remove dead code and unreachable branches"
```

---

## Phase 6 — Documentation Alignment (High)

### Task 6.1: Create/update root `AGENTS.md`

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Write canonical agent guidance**

```markdown
# Agent Guide for SomaBrain

## Build & Test
- Run tests: `SOMABRAIN_PORT=30101 TEST_MEMORY_HTTP_ENDPOINT=http://localhost:10101 pytest tests/unit tests/standalone tests/e2e tests/integration tests/property tests/proofs/category_b`
- Restart app after code changes: `docker compose -f infra/standalone/docker-compose.yml restart somabrain_standalone_app`
- Standalone cluster: `docker compose -f infra/standalone/docker-compose.yml up -d`

## Conventions
- No `uvicorn` in production paths; use gunicorn + Django WSGI.
- No broad `except Exception` without logging and specific fallback rationale.
- No hardcoded secrets or default passwords in code/docs/tests.
- No AI filler docstrings or hype language.
- All auth must fail closed.

## Key Files
- Settings: `somabrain/settings/standalone.py`
- API routers: `somabrain/api/v1.py`, `somabrain/api/endpoints/`
- Memory client: `somabrain/memory/client/core.py`
- Memory service: `somabrain/services/memory_service.py`
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add root AGENTS.md with current build/test conventions"
```

---

### Task 6.2: Consolidate `.env.example` files

**Files:**
- Modify: `.env.example`
- Delete or merge: `config/env.example`

- [ ] **Step 1: Make root `.env.example` authoritative**

Include all required variables with placeholder values:

```bash
SECRET_KEY=replace-me
SOMABRAIN_JWT_SECRET=replace-me
SOMABRAIN_POSTGRES_DSN=postgresql://somabrain:<password>@127.0.0.1:30106/somabrain
POSTGRES_PASSWORD=replace-me
SOMABRAIN_REDIS_URL=redis://localhost:30104/0
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:10101
SOMABRAIN_MEMORY_HTTP_TOKEN=replace-me
SOMABRAIN_PORT=30101
SOMABRAIN_MODE=standalone
```

- [ ] **Step 2: Remove duplicates**

- [ ] **Step 3: Commit**

```bash
git add .env.example config/env.example
git commit -m "docs: consolidate env templates into single authoritative .env.example"
```

---

### Task 6.3: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Remove unsupported claims**

Delete or qualify: "Quantum-inspired", "Enterprise-Ready", "GDPR/HIPAA/SOC2-ready", specific latency/throughput numbers without benchmarks.

- [ ] **Step 2: Update ports and paths**

- Default port: `30101`
- API base: `/api/`
- Memory endpoints: `/api/memory/remember`, `/api/memory/recall`, `/api/memory/metrics`

- [ ] **Step 3: Update module table**

Map real modules:

| Module | Path |
|---|---|
| Working Memory | `somabrain.memory.wm.core` |
| LTM Client | `somabrain.memory.client` |
| Memory Service | `somabrain.services.memory_service` |
| Runtime | `somabrain.runtime.manager` |
| API | `somabrain.api.endpoints` |

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README to match current code, ports, and modules"
```

---

### Task 6.4: Fix `docs/USER_GUIDE.md`, `docs/OPS_MANUAL.md`, `docs/ONBOARDING.md`

**Files:**
- Modify: `docs/USER_GUIDE.md`, `docs/OPS_MANUAL.md`, `docs/ONBOARDING.md`

- [ ] **Step 1: Fix broken paths**

Replace `somabrain/schemas.py` → `somabrain/schemas/api.py`, `somabrain/neuromodulators.py` → `somabrain/runtime/neuromodulators.py`, etc.

- [ ] **Step 2: Remove hardcoded credentials**

- [ ] **Step 3: Update port references**

- [ ] **Step 4: Commit**

```bash
git add docs/USER_GUIDE.md docs/OPS_MANUAL.md docs/ONBOARDING.md
git commit -m "docs: align user/ops/onboarding guides with current code and remove credentials"
```

---

### Task 6.5: Fix `docs/SRS_FULL.md` compliance claims

**Files:**
- Modify: `docs/SRS_FULL.md`

- [ ] **Step 1: Remove "VIBE Compliance: 99.8%" claim**

- [ ] **Step 2: Remove SQLAlchemy reference if Django-only**

- [ ] **Step 3: Update TODO count / track in issues**

- [ ] **Step 4: Commit**

```bash
git add docs/SRS_FULL.md
git commit -m "docs: remove unverifiable compliance claims and stale ORM references"
```

---

## Phase 7 — Tests & Verification (High)

### Task 7.1: Tighten broad `except Exception` in tests

**Files:**
- Modify: `tests/conftest.py`, `tests/standalone/conftest.py`, `tests/proofs/conftest.py`, `tests/proofs/**`, `tests/integration/**`, `tests/smoke/**`

- [ ] **Step 1: Replace with specific exceptions**

Catch `urllib.error.URLError`, `httpx.RequestError`, `socket.error`, `KafkaError`, etc.

- [ ] **Step 2: Add assertions instead of discarding checks**

In `tests/proofs/category_e/test_resilience.py`, turn discarded assignments (`_ = health.get(...)`) into real assertions.

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: tighten broad exception handling and add missing assertions"
```

---

### Task 7.2: Rename/remove mocks in proof tests

**Files:**
- Modify: `tests/proofs/category_e/test_memory_e2e.py`, `tests/proofs/category_b/test_wm_persistence.py`, `tests/proofs/category_e/test_resilience.py`

- [ ] **Step 1: Rename `MockConfig` → `TestConfig`, `TestMemoryClient` → `InMemoryMemoryClient`, `TestCircuitBreaker` → `InMemoryCircuitBreaker`**

- [ ] **Step 2: Document exceptions in CONTRIBUTING if unit-only**

- [ ] **Step 3: Commit**

```bash
git add tests/proofs/
git commit -m "test: rename proof-test stubs to avoid mock wording"
```

---

### Task 7.3: Add tests for new behavior

**Files:**
- Create: `tests/unit/test_oauth_debug_bypass.py`, `tests/unit/test_auth_rate_limit.py`, `tests/integration/test_memory_tenant_isolation.py`

- [ ] **Step 1: Write tests**

```python
# tests/integration/test_memory_tenant_isolation.py
import httpx


def test_tenant_a_cannot_recall_tenant_b_memory():
    base = "http://localhost:30101"
    token = "..."
    headers = {"Authorization": f"Bearer {token}"}
    httpx.post(f"{base}/api/memory/remember", headers=headers | {"X-Tenant-ID": "t_a"}, json={...})
    resp = httpx.post(f"{base}/api/memory/recall", headers=headers | {"X-Tenant-ID": "t_b"}, json={"query": "..."})
    assert not any(hit.get("payload", {}).get("tenant") == "t_a" for hit in resp.json()["results"])
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/integration/test_memory_tenant_isolation.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_memory_tenant_isolation.py
git commit -m "test: add tenant isolation integration test"
```

---

### Task 7.4: Final verification suite

- [ ] **Step 1: Run the full matrix**

```bash
SOMABRAIN_PORT=30101 TEST_MEMORY_HTTP_ENDPOINT=http://localhost:10101 pytest tests/unit tests/standalone tests/e2e tests/integration tests/property tests/proofs/category_b -q
```

- [ ] **Step 2: Check for remaining AI slop**

```bash
grep -Rin '"""Execute ' somabrain/ tests/ | wc -l
```

Target: 0 in production code; acceptable only in trivial private test helpers.

- [ ] **Step 3: Check for remaining broad exceptions**

```bash
grep -Rin 'except Exception' somabrain/ tests/ | wc -l
```

Target: only where truly defensive and logged.

- [ ] **Step 4: Check for hardcoded secrets**

```bash
git ls-files | grep -E '\.(key|crt|pem)$'
grep -Rin 'password.*=.*[^<>]*\b' somabrain/ tests/ docs/ | grep -v '<YOUR_'
```

- [ ] **Step 5: Commit results / tag**

```bash
git tag vibe-audit-2026-06-13
```

---

## Self-Review Checklist

| Requirement | Task(s) |
|---|---|
| Remove committed secrets | 1.1 |
| No JWT bypass / explicit secrets | 1.2, 1.3, 1.6 |
| No fake data / silent failures | 2.1, 2.2, 2.3, 2.4, 2.5 |
| No module-level side effects | 3.1, 3.2, 3.3 |
| Infra uses gunicorn, harden K8s | 4.1, 4.2, 4.3, 4.4 |
| Tight exception handling | 5.1, 7.1 |
| Remove AI slop / hype | 5.2 |
| Remove dead code | 5.3 |
| Docs reflect current code | 6.1, 6.2, 6.3, 6.4, 6.5 |
| Full test verification | 7.4 |

## Execution Choice

Plan saved to `docs/superpowers/plans/2026-06-13-full-vibe-audit-and-doc-cleanup.md`.

Recommended execution: **Subagent-Driven** — dispatch one subagent per phase, review after each phase, run the verification matrix after Phase 7.
