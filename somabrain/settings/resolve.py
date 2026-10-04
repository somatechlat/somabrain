"""Single resolution helper for administrable values (SomaBrain).

This is the **only** way call sites may obtain a deployment URL, a service
host, or a tunable that an operator can override. Mirrors the somaAgent01
Capsule/AgentSetting resolver: every value is declared once on a settings
module (``settings/`` for infra topology, ``brain_settings`` for brain
knobs) and read through one resolver.

Resolution order for tunables
-----------------------------
1. ``BrainSetting`` (tenant-scoped DB row, hot-reload via cache) — brain knobs
   only, never infrastructure URLs.
2. Django settings — infra authority, declared in ``settings/*.py``.
3. Schema default **only** when the key is optional.

Deployment URLs
---------------
A URL is never named in logic. Call sites use ``require_url`` /
``optional_url``. A missing required URL raises
``ImproperlyConfigured`` (Rule 91, fail-closed). There is no localhost
fallback: a silent ``127.0.0.1`` is a URL an operator cannot change and a
reviewer cannot see.

Identity (tenant / namespace)
-----------------------------
``require_tenant`` / ``require_namespace`` **raise** on empty. There is no
``"default"`` partition on an auth, memory or namespace path.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

__all__ = [
    "UnconfiguredServiceError",
    "require_setting",
    "optional_setting",
    "require_url",
    "optional_url",
    "require_tenant",
    "require_namespace",
    "resolve_tunable",
]


class UnconfiguredServiceError(ImproperlyConfigured):
    """A required service URL or identity was not configured (Rule 91)."""


def _django_value(name: str) -> Any:
    from django.conf import settings

    if not hasattr(settings, name):
        return None
    value = getattr(settings, name)
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def require_setting(name: str) -> Any:
    """Return a required settings attribute or raise (fail-closed)."""
    value = _django_value(name)
    if value is None:
        raise UnconfiguredServiceError(
            f"Settings attribute {name!r} is required and not configured. "
            "Declare it on somabrain.settings and supply topology via env/Vault. "
            "There is no default at the call site (Rule 91)."
        )
    return value


def optional_setting(name: str, default: Any = None) -> Any:
    """Return a settings attribute when present, else *default*.

    Use only for keys whose schema default is declared on a settings module
    or documented as optional. Never pass a host or URL as *default*.
    """
    value = _django_value(name)
    return default if value is None else value


def require_url(name: str) -> str:
    """Return a configured deployment URL or raise.

    The value must already be a URL (scheme + host). Call sites never invent
    a base; operators change topology in env / Compose / Helm only.
    """
    value = require_setting(name)
    text = str(value).strip()
    if "://" not in text:
        raise UnconfiguredServiceError(
            f"Settings attribute {name!r} must be a URL with a scheme, got {text!r}. "
            "Protocol scheme constants live in somabrain.settings.constants; "
            "the effective base is this setting."
        )
    return text.rstrip("/")


def optional_url(name: str) -> str | None:
    """Return a configured URL when present, else ``None`` (no invented host)."""
    value = _django_value(name)
    if value is None:
        return None
    return require_url(name)


def require_tenant(tenant: str | None) -> str:
    """Return a non-empty tenant id or raise.

    Memory and auth are partitioned by tenant. There is no default partition.
    """
    if not isinstance(tenant, str) or not tenant.strip():
        raise UnconfiguredServiceError(
            "tenant must be a non-empty string; memory and auth are partitioned "
            "by tenant and there is no default partition (Rule 91)."
        )
    return tenant.strip()


def require_namespace(namespace: str | None) -> str:
    """Return a non-empty namespace or raise (no ``\"default\"`` on the path)."""
    if not isinstance(namespace, str) or not namespace.strip():
        raise UnconfiguredServiceError(
            "namespace must be a non-empty string; there is no default namespace "
            "on the resolution path (Rule 91)."
        )
    return namespace.strip()


def resolve_tunable(
    key: str,
    *,
    tenant: str | None = None,
    default: Any = None,
    require: bool = False,
) -> Any:
    """Resolve one brain tunable: BrainSetting (tenant) → Django settings.

    *key* is the canonical settings / ``BrainSetting`` key. When *tenant* is
    given, a tenant-scoped ``BrainSetting`` row wins over Django settings so
    Capsule-level brain knobs stay administrable. Infrastructure URLs are
    **not** resolved here — use ``require_url``.
    """
    if tenant:
        tenant = require_tenant(tenant)
        try:
            from somabrain.brain_settings.models import (
                BrainSetting,
                BrainSettingNotFound,
            )

            return BrainSetting.get(key, tenant=tenant)
        except BrainSettingNotFound:
            pass
        except ImproperlyConfigured:
            # DB unavailable: fall through to Django settings.
            pass

    value = _django_value(key)
    if value is not None:
        return value
    if require:
        return require_setting(key)
    return default
