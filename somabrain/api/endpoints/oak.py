"""Oak API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Oak options management backed by Milvus and OptionManager.
"""

from __future__ import annotations

import base64
import time
import logging
from typing import List, Optional
from ninja import Router, Schema
from django.http import HttpRequest
from ninja.errors import HttpError
from django.conf import settings

from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant
from somabrain.oak.option_manager import option_manager
from somabrain.oak.planner import plan_for_tenant
from somabrain.milvus_client import MilvusClient
from somabrain import metrics as M

logger = logging.getLogger("somabrain.api.endpoints.oak")

router = Router(tags=["oak"])

# Re-use Milvus client (lazy)
_milvus = MilvusClient()

# Local Schema Definitions
class OakOptionCreateRequest(Schema):
    """Data model for OakOptionCreateRequest."""

    payload: str  # base64 encoded
    option_id: Optional[str] = None

class OakPlanSuggestResponse(Schema):
    """Data model for OakPlanSuggestResponse."""

    plan: List[str]

@router.post("/option/create", response=OakPlanSuggestResponse, auth=bearer_auth)
def oak_option_create(request: HttpRequest, body: OakOptionCreateRequest):
    """Create a new Oak option and store it in Milvus."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    try:
        payload_bytes = base64.b64decode(body.payload)
    except Exception:
        raise HttpError(400, "Invalid base64 payload")

    option_id = body.option_id or str(int(time.time() * 1000))

    try:
        opt = option_manager.create_option(ctx.tenant_id, option_id, payload_bytes)
        _milvus.upsert_option(
            tenant_id=opt.tenant_id,
            option_id=opt.option_id,
            payload=opt.payload,
        )
        M.OPTION_COUNT.labels(opt.tenant_id).inc()
        return {"plan": [opt.option_id]}
    except Exception as exc:
        raise HttpError(500, f"Option creation failed: {exc}")

@router.put("/option/{option_id}", response=OakPlanSuggestResponse, auth=bearer_auth)
def oak_option_update(request: HttpRequest, option_id: str, body: OakOptionCreateRequest):
    """Replace the payload of an existing Oak option."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    try:
        payload_bytes = base64.b64decode(body.payload)
    except Exception:
        raise HttpError(400, "Invalid base64 payload")

    try:
        opt = option_manager.update_option(ctx.tenant_id, option_id, payload_bytes)
        _milvus.upsert_option(
            tenant_id=opt.tenant_id,
            option_id=opt.option_id,
            payload=opt.payload,
        )
        M.OPTION_COUNT.labels(opt.tenant_id).inc()
        return {"plan": [opt.option_id]}
    except Exception as exc:
         raise HttpError(500, f"Option update failed: {exc}")

@router.get("/plan", response=OakPlanSuggestResponse, auth=bearer_auth)
def oak_plan(request: HttpRequest, max_options: Optional[int] = None):
    """Return a ranked list of Oak option identifiers for the tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    try:
        plan = plan_for_tenant(ctx.tenant_id, max_options=max_options)
        return {"plan": plan}
    except Exception as exc:
        raise HttpError(500, f"Planning failed: {exc}")