"""Oak API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Oak options management backed by OptionManager (canonical) and SFM (memory
sink). T-1: Milvus writes only through SFM — Oak never talks to a vector
store directly.
"""

from __future__ import annotations

import base64
import logging
import uuid

from django.conf import settings
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain import metrics as M
from somabrain.api.auth import api_key_auth, require_auth
from somabrain.oak.option_manager import option_manager
from somabrain.oak.planner import plan_for_tenant
from somabrain.tenant import get_tenant_sync as get_tenant

logger = logging.getLogger("somabrain.api.endpoints.oak")

router = Router(tags=["oak"])


def _store_option_in_sfm(tenant_id: str, option_id: str, payload_bytes: bytes) -> None:
    """Persist an Oak option into SFM as a semantic memory.

    T-1 / D7: the only write path is the MemoryClient gateway
    (``memory_type=semantic``, ``payload.kind=option``). There is no direct
    Milvus write and no hash-fabricated vector. Fail-closed: a refused store
    raises so the caller never sees a success that missed SFM.
    """
    from somabrain.memory.client import MemoryClient

    namespace = str(getattr(settings, "SOMABRAIN_NAMESPACE", "") or "").strip()
    if not namespace:
        raise RuntimeError(
            "SOMABRAIN_NAMESPACE is required to store Oak options in SFM"
        )
    client = MemoryClient(cfg=settings, namespace=namespace, tenant=tenant_id)
    coord = client.coord_for_key(f"oak::{tenant_id}::{option_id}", universe=tenant_id)
    payload = {
        "coordinate": coord,
        "tenant": tenant_id,
        "namespace": namespace,
        "universe": tenant_id,
        "memory_type": "semantic",
        "kind": "option",
        "option_id": option_id,
        "id": option_id,
        "text": f"oak option {option_id}",
        "payload_b64": base64.b64encode(payload_bytes).decode("ascii"),
    }
    ok = client.store_from_payload(payload, request_id=str(uuid.uuid4()))
    if not ok:
        raise RuntimeError(f"SFM refused Oak option store for {option_id}")


# Local Schema Definitions
class OakOptionCreateRequest(Schema):
    """Data model for OakOptionCreateRequest."""

    payload: str  # base64 encoded
    option_id: str | None = None


class OakPlanSuggestResponse(Schema):
    """Data model for OakPlanSuggestResponse."""

    plan: list[str]


@router.post("/option/create", response=OakPlanSuggestResponse, auth=api_key_auth)
def oak_option_create(request: HttpRequest, body: OakOptionCreateRequest):
    """Create a new Oak option (Postgres canonical + SFM memory sink)."""
    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    try:
        payload_bytes = base64.b64decode(body.payload)
    except Exception:
        raise HttpError(400, "Invalid base64 payload")

    option_id = body.option_id or str(uuid.uuid4())

    try:
        opt = option_manager.create_option(ctx.tenant_id, option_id, payload_bytes)
        if not isinstance(opt, dict) or "error" in opt:
            detail = opt.get("error") if isinstance(opt, dict) else "invalid result"
            raise HttpError(
                400 if detail != "OAK model not migrated" else 503, str(detail)
            )
        # SFM is the only vector/memory sink for the option payload (T-1).
        _store_option_in_sfm(opt["tenant_id"], opt["option_id"], payload_bytes)
        M.OPTION_COUNT.labels(opt["tenant_id"]).inc()
        return {"plan": [opt["option_id"]]}
    except HttpError:
        raise
    except Exception as exc:
        raise HttpError(500, f"Option creation failed: {exc}")


@router.put("/option/{option_id}", response=OakPlanSuggestResponse, auth=api_key_auth)
def oak_option_update(
    request: HttpRequest, option_id: str, body: OakOptionCreateRequest
):
    """Replace the payload of an existing Oak option (Postgres + SFM)."""
    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    try:
        payload_bytes = base64.b64decode(body.payload)
    except Exception:
        raise HttpError(400, "Invalid base64 payload")

    try:
        opt = option_manager.update_option(ctx.tenant_id, option_id, payload_bytes)
        if not isinstance(opt, dict) or "error" in opt:
            detail = opt.get("error") if isinstance(opt, dict) else "invalid result"
            status = 404 if detail == "Option not found" else 503
            raise HttpError(status, str(detail))
        _store_option_in_sfm(opt["tenant_id"], opt["option_id"], payload_bytes)
        M.OPTION_COUNT.labels(opt["tenant_id"]).inc()
        return {"plan": [opt["option_id"]]}
    except HttpError:
        raise
    except Exception as exc:
        raise HttpError(500, f"Option update failed: {exc}")


@router.get("/plan", response=OakPlanSuggestResponse, auth=api_key_auth)
def oak_plan(request: HttpRequest, max_options: int | None = None):
    """Return a ranked list of Oak option identifiers for the tenant."""
    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    try:
        plan = plan_for_tenant(ctx.tenant_id, max_options=max_options)
        return {"plan": plan}
    except Exception as exc:
        raise HttpError(500, f"Planning failed: {exc}")
