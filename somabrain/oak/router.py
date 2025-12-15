"""FastAPI router that exposes Oak‑specific endpoints backed by Milvus.

The VIBE guidelines are respected:
* **Single source of truth** – all configuration is read from the global
  ``settings`` instance (defined in ``common.config.settings``).
* **Typed request/response models** – Pydantic models are defined in the
  existing ``somabrain.schemas`` package and are used here.
* **No magic numbers** – defaults such as ``top_k`` or similarity thresholds are
  taken from ``settings`` (or the Milvus client defaults).
* **Observability** – each handler increments a Prometheus gauge defined in
  ``somabrain.metrics`` (the gauge was added in a previous sprint).
"""

from fastapi import APIRouter, Request
import base64
import time
from somabrain.schemas import OakOptionCreateRequest, OakPlanSuggestResponse
from somabrain.auth import require_auth
from somabrain.oak.option_manager import option_manager
from somabrain.oak.planner import plan_for_tenant
from somabrain.milvus_client import MilvusClient
from common.config.settings import settings
from somabrain import metrics as M

router = APIRouter()

# Re‑use a single Milvus client instance – creation is cheap (lazy connection).
_milvus = MilvusClient()


@router.post("/option/create", response_model=OakPlanSuggestResponse)
async def oak_option_create(body: OakOptionCreateRequest, request: Request):
    """Create a new Oak option and store it in Milvus.

    The request payload is base64‑encoded. The endpoint resolves the tenant via
    the async ``get_tenant`` helper, decodes the payload, generates an
    ``option_id`` when omitted, and calls the synchronous ``OptionManager``.
    """
    require_auth(request, settings)
    from somabrain.tenant import get_tenant as get_tenant_async

    tenant_ctx = await get_tenant_async(request, settings.namespace)
    tenant_id = tenant_ctx.tenant_id

    payload_bytes = base64.b64decode(body.payload)
    option_id = body.option_id or str(int(time.time() * 1000))

    opt = option_manager.create_option(tenant_id, option_id, payload_bytes)
    _milvus.upsert_option(
        tenant_id=opt.tenant_id,
        option_id=opt.option_id,
        payload=opt.payload,
    )
    M.OPTION_COUNT.labels(opt.tenant_id).inc()
    return OakPlanSuggestResponse(plan=[opt.option_id])


@router.put("/option/{option_id}", response_model=OakPlanSuggestResponse)
async def oak_option_update(option_id: str, body: OakOptionCreateRequest, request: Request):
    """Replace the payload of an existing Oak option.

    The request body is base64‑encoded. The endpoint resolves the tenant, decodes
    the payload, and calls the synchronous ``OptionManager.update_option``.
    """
    require_auth(request, settings)
    from somabrain.tenant import get_tenant as get_tenant_async

    tenant_ctx = await get_tenant_async(request, settings.namespace)
    tenant_id = tenant_ctx.tenant_id
    payload_bytes = base64.b64decode(body.payload)
    opt = option_manager.update_option(tenant_id, option_id, payload_bytes)
    _milvus.upsert_option(
        tenant_id=opt.tenant_id,
        option_id=opt.option_id,
        payload=opt.payload,
    )
    M.OPTION_COUNT.labels(opt.tenant_id).inc()
    return OakPlanSuggestResponse(plan=[opt.option_id])


@router.get("/plan", response_model=OakPlanSuggestResponse)
async def oak_plan(request: Request, max_options: int | None = None):
    """Return a ranked list of Oak option identifiers for the tenant.

    The planner now queries Milvus via ``MilvusClient.search_similar`` to find
    the most similar existing options.
    """
    require_auth(request, settings)
    from somabrain.tenant import get_tenant as get_tenant_async

    tenant_ctx = await get_tenant_async(request, settings.namespace)
    plan = plan_for_tenant(tenant_ctx.tenant_id, max_options=max_options)
    return OakPlanSuggestResponse(plan=plan)
