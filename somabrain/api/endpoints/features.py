"""Module features."""

from ninja import Router
from typing import Dict, List
from somabrain.services.feature_flags import FeatureFlags
from django.http import HttpRequest

router = Router(tags=["features"])


@router.get("")
def features_status(request: HttpRequest) -> Dict:
    # Centralized flags only; overrides removed for enterprise mode.
    """Execute features status.

    Args:
        request: The request.
    """

    status = FeatureFlags.get_status()
    # Ninja handles serialization of dicts automatically
    return {"status": status}


@router.post("/disable")
def features_disable(request: HttpRequest, body: Dict[str, List[str]]):
    # Interface retained, but dynamic disabling removed in centralized mode.
    """Execute features disable.

    Args:
        request: The request.
        body: The body.
    """

    return {"ok": False, "error": "dynamic disabling removed"}


@router.post("/enable")
def features_enable(request: HttpRequest, body: Dict[str, List[str]]):
    """Execute features enable.

    Args:
        request: The request.
        body: The body.
    """

    return {"ok": False, "error": "dynamic enabling removed"}
