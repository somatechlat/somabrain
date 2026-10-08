"""Django Ninja authentication handlers.

The authentication boundary for SomaBrain is a pre-shared bearer token whose
value lives in Vault (VIBE Rule 164) and is read at bootstrap into
``SOMABRAIN_MEMORY_HTTP_TOKEN``. That single token is the trust boundary in
every deployment profile: the agent holds it, SomaBrain verifies it. There is
no second product-identity layer — SaaS auth (JWT/OAuth/API-key product
tables) was removed with the commerce overlay.

``require_auth`` / ``require_admin_auth`` are the defense-in-depth helpers
called inside handlers after Ninja has already authenticated the request.

``bind_credential_tenant`` is the tenant-binding seam: the authenticated
credential is the sole authority for which partition a request may touch.
A body/query/header tenant is an assertion only — a mismatch is 403.
"""

from __future__ import annotations

from django.http import HttpRequest

from somabrain.api.standalone_auth import StandaloneAPIKeyAuth
from somabrain.core.security import legacy_auth as _legacy_auth

# Defense-in-depth helpers used by endpoints.
require_auth = _legacy_auth.require_auth
require_admin_auth = _legacy_auth.require_admin_auth

# Canonical auth handler used by every route's ``auth=`` argument.
api_key_auth = StandaloneAPIKeyAuth()


def bind_credential_tenant(
    request: HttpRequest, asserted: str | None = None
) -> str:
    """Return the credential-tenant partition, refusing asserted mismatches.

    The authenticated credential (``request.auth["tenant_id"]``) is the sole
    authority for which partition a request may touch. A body/query/header
    tenant is an assertion only: when present and different, the request is
    refused with 403 — the same contract as ``api/endpoints/thread.py``.

    Parameters
    ----------
    request:
        The current HTTP request (must carry ``request.auth`` from the
        Ninja auth handler).
    asserted:
        Optional tenant id asserted by the caller (body field, query
        parameter, or ``X-Tenant-ID`` header). ``None`` means no assertion.
    """
    from django.conf import settings as django_settings
    from django.core.exceptions import PermissionDenied
    from ninja.errors import HttpError

    from somabrain.tenant import get_tenant_sync

    try:
        ctx = get_tenant_sync(
            request, getattr(django_settings, "SOMABRAIN_NAMESPACE")
        )
    except PermissionDenied as exc:
        # Header assertion contradicted the credential (get_tenant_sync).
        raise HttpError(403, str(exc)) from exc
    if asserted is not None and asserted != ctx.tenant_id:
        raise HttpError(
            403,
            "tenant mismatch: asserted tenant does not match authenticated tenant",
        )
    return ctx.tenant_id


__all__ = [
    "api_key_auth",
    "bind_credential_tenant",
    "require_auth",
    "require_admin_auth",
]
