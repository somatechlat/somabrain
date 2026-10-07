"""Module calibration."""

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somabrain.api.auth import api_key_auth, require_auth
from somabrain.services.calibration_service import calibration_service
from somabrain.tenant import get_tenant_sync

router = Router(tags=["calibration"])


def _resolve_tenant(request: HttpRequest, asserted: str | None = None) -> str:
    """Resolve the tenant from the authenticated context.

    A path tenant is treated as an assertion: if provided and it does not
    match the authenticated tenant, the request is rejected. The
    authenticated context is always the sole authority.
    """
    require_auth(request, settings)
    ctx = get_tenant_sync(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    if asserted is not None and asserted != ctx.tenant_id:
        raise HttpError(403, "tenant mismatch: asserted tenant does not match authenticated tenant")
    return ctx.tenant_id


@router.get("/status", auth=api_key_auth)
def calibration_status(request: HttpRequest):
    """Execute calibration status for the authenticated tenant.

    Args:
        request: The request.
    """
    tenant_id = _resolve_tenant(request)

    if not calibration_service.enabled:
        return {"enabled": False}
    # Return only the authenticated tenant's calibration data — never all tenants.
    return {
        key: value
        for key, value in calibration_service.get_all_calibration_status().items()
        if key.endswith(f":{tenant_id}")
    }


@router.get("/{domain}/{tenant}", auth=api_key_auth)
def calibration_get(request: HttpRequest, domain: str, tenant: str):
    """Execute calibration get for the authenticated tenant.

    Args:
        request: The request.
        domain: The domain.
        tenant: Asserted tenant — must match the authenticated tenant.
    """
    tenant_id = _resolve_tenant(request, tenant)

    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        return calibration_service.get_calibration_status(domain, tenant_id)
    except Exception as e:
        raise HttpError(500, str(e))


@router.get("/reliability/{domain}/{tenant}", auth=api_key_auth)
def calibration_reliability(request: HttpRequest, domain: str, tenant: str):
    """Execute calibration reliability for the authenticated tenant.

    Args:
        request: The request.
        domain: The domain.
        tenant: Asserted tenant — must match the authenticated tenant.
    """
    tenant_id = _resolve_tenant(request, tenant)

    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        return calibration_service.export_reliability_data(domain, tenant_id)
    except Exception as e:
        raise HttpError(500, str(e))
