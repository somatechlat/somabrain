"""Module calibration."""

from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError
from somabrain.services.calibration_service import calibration_service

router = Router(tags=["calibration"])


@router.get("/status")
def calibration_status(request: HttpRequest):
    """Execute calibration status.

    Args:
        request: The request.
    """

    if not calibration_service.enabled:
        return {"enabled": False}
    return calibration_service.get_all_calibration_status()


@router.get("/{domain}/{tenant}")
def calibration_get(request: HttpRequest, domain: str, tenant: str):
    """Execute calibration get.

    Args:
        request: The request.
        domain: The domain.
        tenant: The tenant.
    """

    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        return calibration_service.get_calibration_status(domain, tenant)
    except Exception as e:
        raise HttpError(500, str(e))


@router.get("/reliability/{domain}/{tenant}")
def calibration_reliability(request: HttpRequest, domain: str, tenant: str):
    """Execute calibration reliability.

    Args:
        request: The request.
        domain: The domain.
        tenant: The tenant.
    """

    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        return calibration_service.export_reliability_data(domain, tenant)
    except Exception as e:
        raise HttpError(500, str(e))
