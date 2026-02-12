"""
Tenant resolution facade.

Provides tenant context for the API layer. In AAAS mode, delegates to
somabrain.aaas.logic.tenant for full multi-tenant resolution. In Standalone
mode, returns a fixed "standalone" tenant without importing AAAS modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
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
    """Resolve the tenant for the given request.

    In Standalone mode, returns a fixed "standalone" tenant.
    In AAAS mode, delegates to the full tenant manager.
    """
    if not apps.is_installed("somabrain.aaas"):
        from django.conf import settings

        tenant_id = getattr(settings, "SOMABRAIN_DEFAULT_TENANT", "standalone")
        return TenantContext(tenant_id=tenant_id, namespace=namespace)

    from somabrain.aaas.logic.tenant import get_tenant as _aaas_get_tenant

    return await _aaas_get_tenant(request, namespace)


__all__ = ["TenantContext", "get_tenant"]
