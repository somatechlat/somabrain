"""
Tenant resolution facade.

``tenant_id`` is a **data-partition key** — it isolates one caller's memories
from another's. It is not a product tenancy. The resolved identity comes from
the request (`X-Tenant-ID`) or from the configured default, and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest


@dataclass
class TenantContext:
    """Minimal tenant context used by the API endpoints.

    Attributes
    ----------
    tenant_id: str
        The identifier of the resolved tenant.
    namespace: str
        The namespace configured for the application.
    """

    tenant_id: str
    namespace: str


async def get_tenant(request: HttpRequest, namespace: str) -> TenantContext:
    """Resolve the tenant partition for the given request.

    ``X-Tenant-ID`` and ``X-Namespace`` override the configured defaults so a
    caller can address its own partition explicitly. There is no ambient tenant
    context and no product tenancy to resolve.
    """
    return _resolve(request, namespace)


def get_tenant_sync(request: HttpRequest, namespace: str) -> TenantContext:
    """Resolve the tenant partition synchronously.

    Same resolution as :func:`get_tenant`; the async wrapper only exists so
    async endpoints can await it without offloading.
    """
    return _resolve(request, namespace)


def _resolve(request: HttpRequest, namespace: str) -> TenantContext:
    """Single resolution path shared by the async and sync facades."""
    from django.conf import settings

    tenant_id = request.headers.get("X-Tenant-ID") or getattr(
        settings, "SOMABRAIN_DEFAULT_TENANT", None
    )
    if not tenant_id:
        raise ImproperlyConfigured(
            "SOMABRAIN_DEFAULT_TENANT must be set; tenant resolution is fail-closed"
        )
    ns = request.headers.get("X-Namespace") or namespace or "default"
    return TenantContext(tenant_id=tenant_id, namespace=ns)


__all__ = ["TenantContext", "get_tenant", "get_tenant_sync"]
