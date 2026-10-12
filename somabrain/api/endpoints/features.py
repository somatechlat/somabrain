"""Module features."""

from django.http import HttpRequest
from ninja import Router

from somabrain.api.auth import api_key_auth
from somabrain.services.feature_flags import FeatureFlags

router = Router(tags=["features"])


@router.get("", auth=api_key_auth)
def features_status(request: HttpRequest) -> dict:
    # Centralized flags only; overrides removed for enterprise mode.
    """Execute features status.

    Args:
        request: The request.
    """

    status = FeatureFlags.get_status()
    # Ninja handles serialization of dicts automatically
    return {"status": status}


@router.post("/disable", auth=api_key_auth)
def features_disable(request: HttpRequest, body: dict[str, list[str]]):
    # Interface retained, but dynamic disabling removed in centralized mode.
    """Execute features disable.

    Args:
        request: The request.
        body: The body.
    """

    return {"ok": False, "error": "dynamic disabling removed"}


@router.post("/enable", auth=api_key_auth)
def features_enable(request: HttpRequest, body: dict[str, list[str]]):
    """Execute features enable.

    Args:
        request: The request.
        body: The body.
    """

    return {"ok": False, "error": "dynamic enabling removed"}
