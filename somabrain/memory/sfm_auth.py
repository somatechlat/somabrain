"""Brain→SFM credential resolution.

SFM authenticates with ``SOMA_API_TOKEN`` (its own credential, seeded from
Vault). The agent↔brain ``SOMABRAIN_MEMORY_HTTP_TOKEN`` is a different trust
boundary and must never be presented to SFM.

This module is the **only** place that decides which bearer the brain sends
to the memory HTTP endpoint.
"""

from __future__ import annotations

__all__ = ["resolve_sfm_api_token"]


def resolve_sfm_api_token(cfg: object | None = None) -> str | None:
    """Return the SFM bearer token or None when not provisioned.

    Order:
    1. Explicit ``cfg.soma_api_token`` / ``cfg.SOMA_API_TOKEN`` (when a config
       object carries a pinned credential).
    2. ``somabrain.settings.django_core.get_api_token()`` — Vault-backed.
    3. Django settings ``SOMA_API_TOKEN``.
    """
    if cfg is not None:
        for name in ("soma_api_token", "SOMA_API_TOKEN"):
            value = getattr(cfg, name, None)
            if value:
                return str(value)

    try:
        from somabrain.settings.django_core import get_api_token

        token = get_api_token()
        if token:
            return str(token)
    except Exception:
        pass

    try:
        from django.conf import settings

        token = getattr(settings, "SOMA_API_TOKEN", None)
        if token:
            return str(token)
    except Exception:
        pass

    return None
