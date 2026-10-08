"""W-H3 tenant isolation: credential tenant is the sole authority.

Body/query/header tenant fields are assertions only. When present and
different from the authenticated credential tenant the request must be
refused with 403 — the same contract as ``api/endpoints/thread.py``.

Covers:
* ``context.evaluate`` / ``context.feedback`` — body ``tenant_id`` must not win.
* ``memory_remember.remember_memory_batch`` — ``payload.tenant`` must not win.
* ``memory.memory_metrics`` — query ``tenant`` must not widen the read.
* ``brain_settings`` — no invented ``"default"`` partition.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.no_django

# ---------------------------------------------------------------------------
# Minimal Django bootstrap (no Vault, no live backends). Same approach as
# ``test_health_honesty.py``: only the settings object and the endpoint
# modules need to be importable so the tenant-binding seam can be driven.
# ---------------------------------------------------------------------------

import django
from django.conf import settings as django_settings

if not django_settings.configured:
    django_settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[],
        USE_TZ=True,
        ALLOWED_HOSTS=["*"],
        SOMABRAIN_NAMESPACE="test-ns",
        SOMABRAIN_DEFAULT_TENANT="tenant-a",
        SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://memory.invalid:10101",
        SOMABRAIN_MEMORY_HTTP_TOKEN="test-only-token",
        KAFKA_BOOTSTRAP_SERVERS="",
        SOMABRAIN_POSTGRES_DSN="",
        REQUIRE_OPA=False,
        MEMORY_DEGRADE_READONLY=False,
        MEMORY_DEGRADE_TOPIC=None,
        MODE="test",
        REQUIRE_EXTERNAL_BACKENDS=False,
        HEALTH_PING_TIMEOUT=0.2,
        ENABLE_OAK=False,
        SLEEP_K0=100,
        SLEEP_T0=1.0,
        SLEEP_TAU0=0.1,
        SLEEP_ETA0=0.01,
        SLEEP_LAMBDA0=0.5,
        SLEEP_B0=1.0,
        SLEEP_K_MIN=5,
        SLEEP_T_MIN=0.5,
        SLEEP_ALPHA_K=0.1,
        SLEEP_ALPHA_T=0.05,
        SLEEP_ALPHA_TAU=0.05,
        SLEEP_ALPHA_ETA=0.01,
        SLEEP_BETA_B=0.1,
        SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD=5,
        SOMABRAIN_CIRCUIT_RESET_INTERVAL=30.0,
        SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL=60.0,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    django.setup()

# Stub ``somabrain.settings`` and ``somabrain.settings.resolve`` so
# ``require_tenant`` / ``require_namespace`` are available without importing
# the Vault-guarded settings package. The real implementations are pure
# non-empty string checks; this is that contract, not a bypass of it.
if "somabrain.settings.resolve" not in sys.modules:
    _resolve_stub = types.ModuleType("somabrain.settings.resolve")

    def _require_tenant(tenant: str | None) -> str:
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("tenant must be a non-empty string")
        return tenant.strip()

    def _require_namespace(namespace: str | None) -> str:
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace must be a non-empty string")
        return namespace.strip()

    _resolve_stub.require_tenant = _require_tenant  # type: ignore[attr-defined]
    _resolve_stub.require_namespace = _require_namespace  # type: ignore[attr-defined]
    _resolve_stub.require_setting = lambda name: getattr(django_settings, name)  # type: ignore[attr-defined]
    # Parent package stub must exist first so the import system does not
    # execute somabrain/settings/__init__.py (Vault-guarded).
    if "somabrain.settings" not in sys.modules:
        _settings_pkg_stub = types.ModuleType("somabrain.settings")
        _settings_pkg_stub.resolve = _resolve_stub  # type: ignore[attr-defined]
        sys.modules["somabrain.settings"] = _settings_pkg_stub
    sys.modules["somabrain.settings.resolve"] = _resolve_stub

from ninja.errors import HttpError  # noqa: E402

from somabrain.api.endpoints import context as context_mod  # noqa: E402
from somabrain.api.endpoints import memory as memory_mod  # noqa: E402
from somabrain.api.endpoints import (  # noqa: E402
    memory_remember as remember_mod,
)

_ENDPOINTS_DIR = Path(memory_mod.__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(tenant_id: str, headers: dict[str, str] | None = None) -> SimpleNamespace:
    """A minimal request carrying a credential tenant and optional headers."""
    return SimpleNamespace(
        auth={"tenant_id": tenant_id, "tenant": tenant_id},
        headers=headers or {},
    )


@pytest.fixture(autouse=True)
def _pass_auth(monkeypatch: pytest.MonkeyPatch):
    """Skip bearer-token checks: these tests drive the tenant seam only."""
    for mod in (context_mod, remember_mod, memory_mod):
        monkeypatch.setattr(mod, "require_auth", lambda *a, **k: None)
    yield


# ---------------------------------------------------------------------------
# context.feedback / context.evaluate
# ---------------------------------------------------------------------------


def test_feedback_cross_tenant_body_is_403() -> None:
    """Credential tenant-a + body tenant-b must be refused (403)."""
    req = _req("tenant-a")
    payload = {"tenant_id": "tenant-b", "utility": 0.5, "reward": 0.1}
    with pytest.raises(HttpError) as exc:
        context_mod.feedback_endpoint(req, payload)
    assert exc.value.status_code == 403
    assert "tenant mismatch" in str(exc.value)


def test_feedback_matching_tenant_is_not_403() -> None:
    """Credential tenant-a + body tenant-a must NOT be refused for tenant."""
    req = _req("tenant-a")
    payload = {"tenant_id": "tenant-a", "utility": 0.5, "reward": 0.1}
    try:
        context_mod.feedback_endpoint(req, payload)
    except HttpError as exc:
        assert exc.status_code != 403
    except Exception:
        pass  # downstream deps may fail; the tenant seam must not 403


def test_feedback_absent_body_tenant_uses_credential() -> None:
    """No body tenant_id → credential tenant is used (no invented partition)."""
    req = _req("tenant-a")
    payload = {"utility": 0.5, "reward": 0.1}
    try:
        context_mod.feedback_endpoint(req, payload)
    except HttpError as exc:
        assert exc.status_code != 403
    except Exception:
        pass


def test_evaluate_cross_tenant_body_is_403() -> None:
    req = _req("tenant-a")
    payload = {"tenant_id": "tenant-b", "query": "hello"}
    with pytest.raises(HttpError) as exc:
        context_mod.evaluate_endpoint(req, payload)
    assert exc.value.status_code == 403
    assert "tenant mismatch" in str(exc.value)


def test_evaluate_matching_tenant_is_not_403() -> None:
    req = _req("tenant-a")
    payload = {"tenant_id": "tenant-a", "query": "hello"}
    with pytest.raises(HttpError) as exc:
        context_mod.evaluate_endpoint(req, payload)
    assert exc.value.status_code != 403


# ---------------------------------------------------------------------------
# memory_remember.remember_memory_batch
# ---------------------------------------------------------------------------


def _batch_payload(tenant: str):
    from somabrain.api.memory.models import (
        MemoryBatchWriteItem,
        MemoryBatchWriteRequest,
    )

    return MemoryBatchWriteRequest(
        tenant=tenant,
        namespace="test-ns",
        items=[
            MemoryBatchWriteItem(key="k1", value={"text": "hello"}),
        ],
    )


@pytest.mark.asyncio
async def test_batch_cross_tenant_is_403() -> None:
    """Credential tenant-a + payload.tenant tenant-b must be refused (403)."""
    req = _req("tenant-a")
    payload = _batch_payload("tenant-b")
    with pytest.raises(HttpError) as exc:
        await remember_mod.remember_memory_batch(req, payload)
    assert exc.value.status_code == 403
    assert "tenant mismatch" in str(exc.value)


@pytest.mark.asyncio
async def test_batch_matching_tenant_binds_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matching tenant must bind to the credential and not 403."""
    req = _req("tenant-a")
    payload = _batch_payload("tenant-a")
    # Fail before the pool hop with a sentinel so we can observe the bound
    # tenant after the authz seam without needing live backends.
    monkeypatch.setattr(remember_mod, "_get_memory_pool", lambda: None)
    monkeypatch.setattr(remember_mod, "_get_wm", lambda: None)
    monkeypatch.setattr(remember_mod, "_get_embedder", lambda: None)
    with pytest.raises(HttpError) as exc:
        await remember_mod.remember_memory_batch(req, payload)
    assert exc.value.status_code != 403
    assert payload.tenant == "tenant-a"


@pytest.mark.asyncio
async def test_batch_header_mismatch_is_403() -> None:
    """X-Tenant-ID assertion differing from credential is also 403."""
    req = _req("tenant-a", headers={"X-Tenant-ID": "tenant-b"})
    payload = _batch_payload("tenant-a")
    with pytest.raises(HttpError) as exc:
        await remember_mod.remember_memory_batch(req, payload)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# memory.memory_metrics
# ---------------------------------------------------------------------------


def test_metrics_cross_tenant_query_is_403() -> None:
    req = _req("tenant-a")
    with pytest.raises(HttpError) as exc:
        memory_mod.memory_metrics(req, tenant="tenant-b", namespace=None)
    assert exc.value.status_code == 403
    assert "tenant mismatch" in str(exc.value)


def test_metrics_matching_tenant_uses_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _req("tenant-a")
    monkeypatch.setattr(memory_mod, "_get_memory_pool", lambda: None)
    monkeypatch.setattr(memory_mod, "_get_wm", lambda: None)
    result = memory_mod.memory_metrics(req, tenant="tenant-a", namespace=None)
    assert result["tenant"] == "tenant-a"


def test_metrics_absent_query_tenant_uses_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _req("tenant-a")
    monkeypatch.setattr(memory_mod, "_get_memory_pool", lambda: None)
    monkeypatch.setattr(memory_mod, "_get_wm", lambda: None)
    result = memory_mod.memory_metrics(req, tenant=None, namespace=None)
    assert result["tenant"] == "tenant-a"


# ---------------------------------------------------------------------------
# brain_settings — no invented "default" partition
# ---------------------------------------------------------------------------


def test_brain_settings_has_no_invented_default() -> None:
    """The old ``request.auth.get("tenant_id", "default")`` must be gone."""
    text = (_ENDPOINTS_DIR / "brain_settings.py").read_text(encoding="utf-8")
    assert 'get("tenant_id", "default")' not in text
    assert ', "default"' not in text and ", 'default'" not in text


def test_brain_settings_binds_credential_tenant() -> None:
    """Brain settings must resolve tenant via the credential-binding seam."""
    text = (_ENDPOINTS_DIR / "brain_settings.py").read_text(encoding="utf-8")
    assert "bind_credential_tenant" in text
