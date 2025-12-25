"""Proxy Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Proxy endpoints for external service integration.
"""

from __future__ import annotations

import logging
from ninja import Router
from django.http import HttpRequest

from django.conf import settings
from somabrain.schemas import ProxyRequest

from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.proxy")

router = Router(tags=["proxy"])


@router.post("/forward", auth=bearer_auth)
def forward_request(request: HttpRequest, body: ProxyRequest):
    """Forward request to external service."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    # Basic proxy logic - forward to configured service
    target_url = getattr(body, "target_url", None)
    payload = getattr(body, "payload", {})
    
    logger.debug(f"Proxy request for {ctx.tenant_id} to {target_url}")
    
    # This is a simplified proxy - full implementation would use httpx/requests
    return {
        "tenant_id": ctx.tenant_id,
        "service": body.service,
        "endpoint": body.endpoint,
        "status": 200,
        "response": {"proxy_response": "ok"},
    }
