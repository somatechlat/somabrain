"""D10: /health must read the real degrade settings — no ghost keys.

The real keys live on the settings chain as ``SOMABRAIN_MEMORY_DEGRADE_*``
(``somabrain/settings/cognitive.py:126-133``). The health endpoint used to
read the non-existent ``MEMORY_DEGRADE_*`` names and hardcode
``memory_degrade_queue: True``. Ghost settings + a fabricated flag are both
operator-law violations.

This suite drives the real ``health()`` handler with the real settings module
attributes (no invented key names) and asserts:

* the handler references only ``SOMABRAIN_MEMORY_DEGRADE_*``
* ``memory_degrade_queue`` is derived, never hardcoded True
* the reported values match the live settings
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
HEALTH_SRC = (BRAIN_ROOT / "somabrain" / "api" / "endpoints" / "health.py").read_text(
    encoding="utf-8"
)
COGNITIVE_SRC = (
    BRAIN_ROOT / "somabrain" / "settings" / "cognitive.py"
).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Source-level: ghost keys are gone; real keys are present
# ---------------------------------------------------------------------------


def test_health_source_has_no_ghost_memory_degrade_keys() -> None:
    for line_no, line in enumerate(HEALTH_SRC.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for ghost in (
            '"MEMORY_DEGRADE_READONLY"',
            '"MEMORY_DEGRADE_TOPIC"',
            "'MEMORY_DEGRADE_READONLY'",
            "'MEMORY_DEGRADE_TOPIC'",
        ):
            if ghost in stripped:
                raise AssertionError(
                    f"ghost settings key at health.py:{line_no}: {stripped!r}"
                )


def test_health_source_reads_real_somabrain_memory_degrade_keys() -> None:
    assert "SOMABRAIN_MEMORY_DEGRADE_READONLY" in HEALTH_SRC
    assert "SOMABRAIN_MEMORY_DEGRADE_TOPIC" in HEALTH_SRC
    assert "SOMABRAIN_MEMORY_DEGRADE_QUEUE" in HEALTH_SRC


def test_health_does_not_hardcode_memory_degrade_queue_true() -> None:
    for line_no, line in enumerate(HEALTH_SRC.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "memory_degrade_queue" in stripped and "True" in stripped:
            # Assignment of a literal True is the fabricated flag.
            if "=" in stripped and "is True" not in stripped:
                raise AssertionError(
                    f"hardcoded memory_degrade_queue at health.py:{line_no}: {stripped!r}"
                )


def test_cognitive_settings_define_the_real_keys() -> None:
    """The keys health reads must actually exist on the settings chain."""
    assert "SOMABRAIN_MEMORY_DEGRADE_QUEUE" in COGNITIVE_SRC
    assert "SOMABRAIN_MEMORY_DEGRADE_READONLY" in COGNITIVE_SRC
    assert "SOMABRAIN_MEMORY_DEGRADE_TOPIC" in COGNITIVE_SRC


# ---------------------------------------------------------------------------
# Handler-level: values are derived from live settings
# ---------------------------------------------------------------------------


def _bootstrap_django():
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
            SOMABRAIN_MEMORY_DEGRADE_QUEUE=True,
            SOMABRAIN_MEMORY_DEGRADE_READONLY=False,
            SOMABRAIN_MEMORY_DEGRADE_TOPIC="memory.degraded",
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
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
        )
        django.setup()
    return django_settings


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


def _patch_probes(monkeypatch: pytest.MonkeyPatch, health_mod) -> None:
    import sys
    import types

    monkeypatch.setattr(
        health_mod, "get_app_config", lambda: SimpleNamespace(namespace="test-ns")
    )
    monkeypatch.setattr(health_mod, "get_mt_memory", lambda: _MtMemory())
    monkeypatch.setattr(health_mod, "get_embedder", lambda: object())
    monkeypatch.setattr(health_mod, "get_tenant", lambda request, ns: _Ctx())
    monkeypatch.setattr(health_mod, "check_postgres", lambda *a, **k: True)
    monkeypatch.setattr(health_mod, "check_kafka", lambda *a, **k: True)
    monkeypatch.setattr(health_mod, "_ping", lambda: 3.0)

    def _fake_module(name: str, **attrs: object) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod

    _fake_module("somabrain.infrastructure.cb_registry", get_cb=lambda: _CB())
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
    _fake_module("somabrain.bootstrap.opa", create_opa_engine=lambda: None)


def test_health_reports_live_somabrain_memory_degrade_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    django_settings = _bootstrap_django()
    from somabrain.api.endpoints import health as health_mod

    _patch_probes(monkeypatch, health_mod)
    resp = health_mod.health(_Request())
    assert resp["memory_degrade_readonly"] is False
    assert resp["memory_degrade_topic"] == "memory.degraded"
    # Derived, not fabricated: queue enabled and not readonly → True.
    assert resp["memory_degrade_queue"] is True


def test_memory_degrade_queue_derived_false_when_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """readonly=True must suppress the queue flag (derived, not hardcoded)."""
    django_settings = _bootstrap_django()
    monkeypatch.setattr(
        django_settings, "SOMABRAIN_MEMORY_DEGRADE_READONLY", True, raising=False
    )
    from somabrain.api.endpoints import health as health_mod

    _patch_probes(monkeypatch, health_mod)
    resp = health_mod.health(_Request())
    assert resp["memory_degrade_readonly"] is True
    assert resp["memory_degrade_queue"] is False


def test_memory_degrade_queue_derived_false_when_queue_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    django_settings = _bootstrap_django()
    monkeypatch.setattr(
        django_settings, "SOMABRAIN_MEMORY_DEGRADE_QUEUE", False, raising=False
    )
    from somabrain.api.endpoints import health as health_mod

    _patch_probes(monkeypatch, health_mod)
    resp = health_mod.health(_Request())
    assert resp["memory_degrade_queue"] is False
