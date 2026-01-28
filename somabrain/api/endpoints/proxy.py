"""Proxy Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Proxy endpoints for external service integration.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest
from typing import Optional, Dict, Any
from ninja import Router
from pydantic import BaseModel

from somabrain.api.auth import api_key_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant

class ProxyRequest(BaseModel):
    service: str
    endpoint: str
    target_url: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

logger = logging.getLogger("somabrain.api.endpoints.proxy")

router = Router(tags=["proxy"])


@router.post("/forward", auth=api_key_auth)
def forward_request(request: HttpRequest, body: ProxyRequest):
    """Forward request to external service."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    # Basic proxy logic - forward to configured service
    target_url = getattr(body, "target_url", None)
    getattr(body, "payload", {})

    logger.debug(f"Proxy request for {ctx.tenant_id} to {target_url}")

    # This is a simplified proxy - full implementation would use httpx/requests
    return {
        "tenant_id": ctx.tenant_id,
        "service": body.service,
        "endpoint": body.endpoint,
        "status": 200,
        "response": {"proxy_response": "ok"},
    }
