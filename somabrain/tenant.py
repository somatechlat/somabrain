"""
Tenant resolution facade.

``tenant_id`` is a **data-partition key** — it isolates one caller's memories
from another's. The partition is bound to the **authenticated credential**
(``request.auth["tenant_id"]``). ``X-Tenant-ID`` is an optional assertion: it
may select nothing and it may never widen access. A mismatch is rejected
(403). There is no header-based partition authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.http import HttpRequest


@dataclass
class TenantContext:
    """Minimal tenant context used by the API endpoints.

    Attributes
    ----------
    tenant_id: str
        The identifier of the resolved tenant (credential-bound).
    namespace: str
        The namespace configured for the application.
    """

    tenant_id: str
    namespace: str


async def get_tenant(request: HttpRequest, namespace: str | None) -> TenantContext:
    """Resolve the tenant partition for the given request."""
    return _resolve(request, namespace)


def get_tenant_sync(request: HttpRequest, namespace: str | None) -> TenantContext:
    """Resolve the tenant partition synchronously."""
    return _resolve(request, namespace)


def _credential_tenant(request: HttpRequest) -> str | None:
    """Tenant bound to the authenticated credential, if any."""
    auth = getattr(request, "auth", None)
    if isinstance(auth, dict):
        tid = auth.get("tenant_id") or auth.get("tenant")
        if tid:
            return str(tid)
    return None


def _resolve(request: HttpRequest, namespace: str | None) -> TenantContext:
    """Single resolution path shared by the async and sync facades.

    Authority order:
    1. Credential tenant (``request.auth``) — sole authority.
    2. Header ``X-Tenant-ID`` — assertion only; must match the credential.
    3. ``SOMABRAIN_DEFAULT_TENANT`` — only when the credential carries no
       tenant (standalone single-tenant bootstrap), and only if the header
       does not contradict it.
    """
    from django.conf import settings

    from somabrain.settings.resolve import require_namespace, require_tenant

    cred_tenant = _credential_tenant(request)
    header_tenant = request.headers.get("X-Tenant-ID")

    from django.core.exceptions import PermissionDenied

    if cred_tenant:
        tenant_id = require_tenant(cred_tenant)
        if header_tenant is not None and header_tenant != tenant_id:
            raise PermissionDenied(
                "tenant mismatch: X-Tenant-ID does not match the authenticated credential"
            )
    else:
        # No credential tenant (e.g. unauthenticated internal call): header
        # may name the partition only when it equals the configured default,
        # never an arbitrary partition.
        default_tenant = getattr(settings, "SOMABRAIN_DEFAULT_TENANT", None)
        if header_tenant is not None:
            if default_tenant and header_tenant != default_tenant:
                raise PermissionDenied(
                    "tenant mismatch: X-Tenant-ID is not bound to any credential"
                )
            tenant_id = require_tenant(header_tenant)
        else:
            tenant_id = require_tenant(default_tenant)

    ns = require_namespace(
        request.headers.get("X-Namespace")
        or namespace
        or getattr(settings, "SOMABRAIN_NAMESPACE")
    )
    return TenantContext(tenant_id=tenant_id, namespace=ns)


__all__ = ["TenantContext", "get_tenant", "get_tenant_sync"]
