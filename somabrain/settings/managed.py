"""Managed settings resolver — DB / Django only.

Operator law (binding):
- Settings and topology (URLs, hosts, ports) come from BrainSetting (DB) or
  Django settings. **Environment variables are not a settings channel.**
- Secrets come from Vault only (Covenant Art 26).
- No YAML/JSON file presets.

This module is the one lookup helper for call sites that need runtime knobs.
"""

from __future__ import annotations

from typing import Any

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


def managed_get(key: str, default: Any = None) -> Any:
    """Resolve a managed setting: BrainSetting (DB) then Django settings.

    Never reads ``os.environ``. Never opens config files.
    """
    # 1) BrainSetting (DB, administerable)
    try:
        from somabrain.brain_settings.models import BrainSetting

        value = BrainSetting.get(key, None)
        if value not in (None, ""):
            return value
    except Exception:
        pass

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
