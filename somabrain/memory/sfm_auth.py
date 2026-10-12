"""Brain→SFM credential resolution.

Live standalone: SFM authenticates the **shared** Vault credential
``secret/agent/credentials[somabrain_memory_http_token]`` (same value the
agent presents to the brain). There is no second SFM-only token in that
document — two independently seeded credentials is the 401 this module
previously caused.

This module is the **only** place that decides which bearer the brain sends
to the memory HTTP endpoint.
"""

from __future__ import annotations

__all__ = ["resolve_sfm_api_token", "build_sfm_request_headers"]


def build_sfm_request_headers(
    cfg: object | None = None,
    *,
    namespace: str | None = None,
    tenant: str | None = None,
) -> dict[str, str]:
    """Single Brain→SFM header builder (auth + tenancy).

    One transport, one auth-header builder (R5). Never a second credential
    path. Tenant/namespace are required (T-5 fail-closed).

    ``namespace`` / ``tenant`` may be passed explicitly (MemoryClient keeps
    them on ``self``, not on ``cfg``). Explicit args win over cfg attributes.
    """
    token_value = resolve_sfm_api_token(cfg)
    if not token_value:
        raise RuntimeError(
            "memory transport: SOMA_API_TOKEN is not provisioned "
            "(Brain→SFM credential missing — fail closed, never anonymous)"
        )
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token_value}",
    }
    ns = str(namespace or getattr(cfg, "namespace", "") or "").strip()
    tn = ""
    # Namespace may be ``base:tenant:namespace`` (api/memory/helpers).
    if ":" in ns:
        parts = ns.split(":")
        if len(parts) >= 2:
            tn = parts[1]
    if not tn:
        tn = str(tenant or getattr(cfg, "tenant", "") or "").strip()
    if not ns:
        raise RuntimeError(
            "memory transport: namespace is not configured (T-5 fail-closed)"
        )
    if not tn:
        raise RuntimeError(
            "memory transport: tenant is not configured (T-5 fail-closed)"
        )
    headers["X-Soma-Namespace"] = ns
    headers["X-Soma-Tenant"] = tn
    return headers


def resolve_sfm_api_token(cfg: object | None = None) -> str | None:
    """Return the SFM bearer token or None when not provisioned.

    Order (Vault is authoritative — R5):
    1. Vault shared credential ``somabrain_memory_http_token`` (the one SFM
       accepts). Always preferred: a pinned cfg token that disagrees is the
       classic dual-credential 401.
    2. Explicit ``cfg.soma_api_token`` / ``cfg.SOMA_API_TOKEN`` (bootstrap pin)
       only when Vault is unreachable.
    3. ``somabrain.settings.django_core.get_api_token()`` / Django
       ``SOMA_API_TOKEN`` after bootstrap merged the same Vault value.
    """
    try:
        from somabrain.core.security.vault_client import get_runtime_secret

        token = get_runtime_secret("memory_http_token")
        if token:
            return str(token).strip()
    except Exception:
        pass

    if cfg is not None:
        for name in ("soma_api_token", "SOMA_API_TOKEN"):
            value = getattr(cfg, name, None)
            if value:
                text = str(value).strip()
                # Bootstrap must never treat a log line as a credential.
                if text and " " not in text:
                    return text

    try:
        from somabrain.settings.django_core import get_api_token

        token = get_api_token()
        if token and " " not in str(token):
            return str(token).strip()
    except Exception:
        pass

    try:
        from django.conf import settings

        token = getattr(settings, "SOMA_API_TOKEN", None)
        if token and " " not in str(token):
            return str(token).strip()
    except Exception:
        pass

    return None
