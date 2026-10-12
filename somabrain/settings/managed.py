"""Managed settings resolver — DB / Django only.

Operator law (binding):
- Settings and topology (URLs, hosts, ports) come from BrainSetting (DB) or
  Django settings. **Environment variables are not a settings channel.**
- Secrets come from Vault only (Covenant Art 26).
- No YAML/JSON file presets.

This module is the one lookup helper for call sites that need runtime knobs.

Async note (T-5 honesty):
Django ORM is sync-only. ASGI request handlers that call ``managed_get``
directly would raise ``SynchronousOnlyOperation``; earlier versions swallowed
that in ``except Exception`` and returned empty settings, so
``POST /memory/remember`` failed with "Memory HTTP endpoint required but not
configured" even when the BrainSetting row was correct. ORM reads now hop to a
worker thread from a running event loop so the value is either real or the
failure is explicit — never a silent empty.
"""

from __future__ import annotations

from typing import Any, Callable

_BRAIN_KEYS = (
    "memory_http_endpoint",
    "kafka_bootstrap_servers",
    "opa_url",
    "redis_host",
    "redis_port",
    "api_url",
    "milvus_host",
    "milvus_port",
    "schema_registry_url",
    "auth_url",
)


def _db_call(fn: Callable[[], Any]) -> Any:
    """Run a sync ORM callable from sync *or* ASGI without silent failure.

    From a normal thread the callable runs inline. From a running event loop
    the callable runs on a worker thread (Django ORM is sync-only) and the
    result is returned to the caller. Missing rows stay missing; infrastructure
    errors raise instead of looking like an unconfigured key.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn()

    from concurrent.futures import ThreadPoolExecutor

    from somabrain.settings.resolve import require_setting

    timeout = float(require_setting("MANAGED_GET_DB_TIMEOUT_S"))
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="managed_get") as pool:
        return pool.submit(fn).result(timeout=timeout)


def managed_get(key: str, default: Any = None) -> Any:
    """Resolve a managed setting: BrainSetting (DB) then Django settings.

    Never reads ``os.environ``. Never opens config files.
    """
    # 1) BrainSetting (DB, administerable) — tenant from settings identity
    try:
        from somabrain.brain_settings.models import BrainSetting
        from somabrain.settings.resolve import require_setting

        tenant = require_setting("SOMABRAIN_DEFAULT_TENANT")
        value = _db_call(lambda: BrainSetting.get(key, str(tenant)))
        if value not in (None, ""):
            return value
    except Exception as exc:
        # "Missing key" is a real unconfigured state (BrainSettingNotFound).
        # Anything else (DB down, async ORM misuse, bug) must not look like
        # an unconfigured setting — fail-closed naming the error.
        from somabrain.brain_settings.models import BrainSettingNotFound

        if not isinstance(exc, (BrainSettingNotFound, LookupError, KeyError)):
            raise

    # 2) Django settings (same name or SOMABRAIN_* / upper)
    try:
        from django.conf import settings

        for name in (key, key.upper(), f"SOMABRAIN_{key.upper()}"):
            if hasattr(settings, name):
                value = getattr(settings, name)
                if value not in (None, ""):
                    return value
    except Exception:
        pass

    return default


def topology() -> dict[str, Any]:
    """Return the managed topology map (URLs from DB/Django, not ENV)."""
    return {k: managed_get(k, "") for k in _BRAIN_KEYS}
