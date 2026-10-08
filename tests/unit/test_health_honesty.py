"""W-H2 health honesty: top-level ``ok`` must roll up from real components.

``/health`` used to hardcode ``resp["ok"] = True`` and call an undefined
``_ping()`` (NameError swallowed → ``memory.ok`` always False). These tests
drive the real ``health()`` handler with mocked component probes and assert
that the top-level flag flips with component health. Fail-closed is fine;
fake True is not.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest import mock

import pytest

pytestmark = pytest.mark.no_django

# ---------------------------------------------------------------------------
# Minimal Django bootstrap (no Vault, no live backends). The production
# settings chain refuses empty credentials; this suite only needs the
# settings object and the health router importable so it can mock probes.
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
        # Sleep-parameter defaults required to import somabrain.sleep.
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
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    django.setup()

from somabrain.api.endpoints import health as health_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Ctx:
    namespace = "test-ns"
    tenant_id = "tenant-test"


class _NSMem:
    def count(self) -> int:
        return 0


class _MtMemory:
    def for_namespace(self, namespace: str) -> _NSMem:
        return _NSMem()


class _CB:
    state = "CLOSED"


class _Request:
    headers: dict[str, str] = {}


def _patch_probes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ping_ms: float | None = 12.5,
    postgres_ok: bool = True,
    kafka_ok: bool = True,
    memory_present: bool = True,
) -> None:
    """Replace every external probe used by ``health()`` with a controllable stub.

    Lazy imports inside ``health()`` are satisfied by injecting lightweight
    stand-ins into ``sys.modules`` so the handler never pulls the real
    Django model graph (constitution, OPA bootstrap, sleep params).
    """
    import sys
    import types

    monkeypatch.setattr(
        health_mod, "get_app_config", lambda: SimpleNamespace(namespace="test-ns")
    )
    monkeypatch.setattr(
        health_mod, "get_mt_memory", lambda: _MtMemory() if memory_present else None
    )
    monkeypatch.setattr(health_mod, "get_embedder", lambda: object())
    monkeypatch.setattr(health_mod, "get_tenant", lambda request, ns: _Ctx())
    monkeypatch.setattr(health_mod, "check_postgres", lambda *a, **k: postgres_ok)
    monkeypatch.setattr(health_mod, "check_kafka", lambda *a, **k: kafka_ok)
    monkeypatch.setattr(health_mod, "_ping", lambda: ping_ms)

    def _fake_module(name: str, **attrs: object) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod

    _fake_module(
        "somabrain.infrastructure.cb_registry",
        get_cb=lambda: _CB(),
    )
    _fake_module(
        "somabrain.sleep",
        SleepState=SimpleNamespace(ACTIVE=SimpleNamespace(name="ACTIVE")),
    )
    _fake_module(
        "somabrain.sleep.cb_adapter",
        map_cb_to_sleep=lambda state: SimpleNamespace(name="ACTIVE"),
    )
    _fake_module(
        "somabrain.services.constitution",
        get_constitution_engine=lambda: SimpleNamespace(
            get_constitution=lambda: None, get_checksum=lambda: None
        ),
    )
    _fake_module(
        "somabrain.bootstrap.opa",
        create_opa_engine=lambda: None,
    )


# ---------------------------------------------------------------------------
# _ping: real probe, fail-closed
# ---------------------------------------------------------------------------


def test_ping_returns_latency_when_memory_endpoint_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_ping measures a real probe and returns milliseconds on success."""
    monkeypatch.setattr(health_mod, "ping", lambda url: True)
    ms = health_mod._ping()
    assert ms is not None
    assert ms >= 0.0


def test_ping_fail_closed_when_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ping returns None (not fake True) when the memory endpoint is down."""
    monkeypatch.setattr(health_mod, "ping", lambda url: False)
    assert health_mod._ping() is None


def test_ping_fail_closed_when_no_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ping returns None when SOMABRAIN_MEMORY_HTTP_ENDPOINT is unset."""
    monkeypatch.setattr(
        django_settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "", raising=False
    )
    monkeypatch.setattr(
        health_mod, "ping", lambda url: (_ for _ in ()).throw(AssertionError("must not probe"))
    )
    assert health_mod._ping() is None


# ---------------------------------------------------------------------------
# /health top-level ok rollup
# ---------------------------------------------------------------------------


def test_health_ok_true_when_all_components_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All component probes green → top-level ok is True."""
    _patch_probes(monkeypatch, ping_ms=3.0, postgres_ok=True, kafka_ok=True)
    resp = health_mod.health(_Request())
    assert resp["ok"] is True
    assert resp["components"]["memory"]["ok"] is True
    assert resp["components"]["postgres"]["ok"] is True
    assert resp["components"]["kafka"]["ok"] is True


def test_health_ok_flips_false_when_postgres_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single down component (postgres) must flip top-level ok to False."""
    _patch_probes(monkeypatch, ping_ms=3.0, postgres_ok=False, kafka_ok=True)
    resp = health_mod.health(_Request())
    assert resp["components"]["postgres"]["ok"] is False
    assert resp["ok"] is False


def test_health_ok_flips_false_when_memory_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memory probe failure (ping_ms None) must flip top-level ok to False."""
    _patch_probes(monkeypatch, ping_ms=None, postgres_ok=True, kafka_ok=True)
    resp = health_mod.health(_Request())
    assert resp["components"]["memory"]["ok"] is False
    assert resp["ok"] is False


def test_health_ok_flips_false_when_kafka_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kafka probe failure must flip top-level ok to False."""
    _patch_probes(monkeypatch, ping_ms=3.0, postgres_ok=True, kafka_ok=False)
    resp = health_mod.health(_Request())
    assert resp["components"]["kafka"]["ok"] is False
    assert resp["ok"] is False


def test_health_ok_false_when_ping_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_ping raising must be treated as down (fail-closed), not up."""

    def _boom() -> float | None:
        raise RuntimeError("probe exploded")

    _patch_probes(monkeypatch, ping_ms=3.0, postgres_ok=True, kafka_ok=True)
    monkeypatch.setattr(health_mod, "_ping", _boom)
    resp = health_mod.health(_Request())
    assert resp["components"]["memory"]["ok"] is False
    assert resp["ok"] is False


# ---------------------------------------------------------------------------
# /healthz is liveness-only
# ---------------------------------------------------------------------------


def test_healthz_is_liveness_only_not_full_health() -> None:
    """/healthz must not claim full component health."""
    resp = health_mod.healthz(_Request())
    body = resp
    # Liveness probe: process is up. It must not claim component aggregate health.
    assert body.get("probe") == "liveness" or body.get("scope") == "liveness"
    # Must not advertise a full-health "ok" claim.
    assert body.get("ok") is not True
    assert body.get("status") not in ("healthy", "ok", "degraded", "critical")


# ---------------------------------------------------------------------------
# system_health /simple is liveness-only
# ---------------------------------------------------------------------------


def test_system_health_simple_is_liveness_only() -> None:
    """/simple must document itself as liveness, not full health."""
    from somabrain.api.endpoints import system_health as sh

    body = sh.get_simple_health(_Request())
    assert body.get("probe") == "liveness" or body.get("scope") == "liveness"
    assert body.get("ok") is not True
    assert body.get("status") not in ("healthy", "ok", "degraded", "critical")


# ---------------------------------------------------------------------------
# check_cognitive_load must not hardcode True
# ---------------------------------------------------------------------------


def test_check_cognitive_load_false_when_imports_fail() -> None:
    """check_cognitive_load reports False when the OAK modules cannot import."""
    import sys

    from somabrain.health import helpers as health_helpers

    real_planner = sys.modules.pop("somabrain.oak.planner", None)
    real_om = sys.modules.pop("somabrain.oak.option_manager", None)

    class _Blocker:
        def find_module(self, name, path=None):  # pragma: no cover - import hook
            if name in ("somabrain.oak.planner", "somabrain.oak.option_manager"):
                return self
            return None

        def load_module(self, name):  # pragma: no cover - import hook
            raise ImportError(f"blocked for test: {name}")

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        result = health_helpers.check_cognitive_load()
        assert result["planner_loaded"] is False
        assert result["option_manager_loaded"] is False
    finally:
        sys.meta_path.remove(blocker)
        if real_planner is not None:
            sys.modules["somabrain.oak.planner"] = real_planner
        if real_om is not None:
            sys.modules["somabrain.oak.option_manager"] = real_om


def test_check_cognitive_load_matches_real_api() -> None:
    """check_cognitive_load flags agree with the real callable check."""
    from somabrain.health import helpers as health_helpers

    result = health_helpers.check_cognitive_load()
    assert isinstance(result["planner_loaded"], bool)
    assert isinstance(result["option_manager_loaded"], bool)
    if result["planner_loaded"]:
        from somabrain.oak.planner import plan_for_tenant

        assert callable(plan_for_tenant)
    if result["option_manager_loaded"]:
        from somabrain.oak.option_manager import option_manager

        assert callable(getattr(option_manager, "list_options", None))
