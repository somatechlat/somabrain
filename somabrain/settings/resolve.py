"""Single resolution helper for administrable values (SomaBrain).

This is the **only** way call sites may obtain a deployment URL, a service
host, or a tunable that an operator can override.

ZERO OPTIONAL PATHS (operator law, 2026-10-09). Missing values are a refusal
naming the setting. Every path is required and official.

Resolution order for tunables
-----------------------------
1. ``BrainSetting`` (tenant-scoped DB row) — brain knobs only.
2. Django settings — infra authority, declared in ``settings/*.py``.

Deployment URLs
---------------
``require_url`` only. A missing URL raises ``UnconfiguredServiceError``.
There is no localhost fallback and no "not configured" soft path.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

__all__ = [
    "UnconfiguredServiceError",
    "require_setting",
    "require_url",
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


def resolve_tunable(key: str, *, tenant: str | None = None) -> Any:
    """Resolve one brain tunable: BrainSetting (tenant) → Django settings.

    Required. Missing → ``require_setting`` refusal naming the key.
    Infrastructure URLs are **not** resolved here — use ``require_url``.
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

    return require_setting(key)
