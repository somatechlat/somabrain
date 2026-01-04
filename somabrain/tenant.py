"""Tenant helper module.

Provides a thin async wrapper used throughout the codebase to resolve the
current tenant from an incoming request. Historically this functionality lived in
``somabrain.tenant`` and was imported as ``get_tenant``. During a refactor the
implementation was moved to ``somabrain.tenant_manager`` but the import sites
were not updated, resulting in a ``NameError`` when the Django Ninja endpoints tried
to call ``get_tenant_async``.

The new ``get_tenant`` function returns a simple context object with the
resolved ``tenant_id`` and the configured ``namespace``.  It uses the singleton
``TenantManager`` obtained via ``get_tenant_manager``.
"""

from __future__ import annotations

from dataclasses import dataclass
from django.http import HttpRequest

from .tenant_manager import get_tenant_manager


@dataclass
class TenantContext:
    """Minimal tenant context used by the API endpoints.

    Attributes
    ----------
    tenant_id: str
        The identifier of the resolved tenant.
    namespace: str
        The namespace configured for the application (typically the
        ``settings.SOMABRAIN_NAMESPACE`` value).
    """

    tenant_id: str
    namespace: str


async def get_tenant(request: HttpRequest, namespace: str) -> TenantContext:
    """Resolve the tenant for the given request.

    This function mirrors the original ``get_tenant`` API used throughout the
    project. It obtains a ``TenantManager`` instance, resolves the tenant ID from
    the request headers (or falls back to the default tenant), and returns a
    ``TenantContext`` containing both the tenant ID and the provided namespace.
    """
    manager = await get_tenant_manager()
    tenant_id = await manager.resolve_tenant_from_request(request)
    return TenantContext(tenant_id=tenant_id, namespace=namespace)