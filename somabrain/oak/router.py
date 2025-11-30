from fastapi import APIRouter, Request
from somabrain.schemas import OakOptionCreateRequest, OakPlanSuggestResponse
from somabrain.auth import require_auth
from somabrain.oak.option_manager import option_manager
from somabrain.oak.planner import plan_for_tenant
from somabrain.milvus_client import MilvusClient
from common.config.settings import settings
from somabrain import metrics as M

"""FastAPI router that exposes Oak‑specific endpoints backed by Milvus.

The VIBE guidelines are respected:
    pass
* **Single source of truth** – all configuration is read from the global
  ``settings`` instance (defined in ``common.config.settings``).
* **Typed request/response models** – Pydantic models are defined in the
  existing ``somabrain.schemas`` package and are used here.
* **No magic numbers** – defaults such as ``top_k`` or similarity thresholds are
  taken from ``settings`` (or the Milvus client defaults).
* **Observability** – each handler increments a Prometheus gauge defined in
  ``somabrain.metrics`` (the gauge was added in a previous sprint).
"""


router = APIRouter()

# Re‑use a single Milvus client instance – creation is cheap (lazy connection).
_milvus = MilvusClient()


@router.post("/option/create", response_model=OakPlanSuggestResponse)
async def oak_option_create(body: OakOptionCreateRequest, request: Request):
    """Create a new Oak option and store it in Milvus.

    The function mirrors the previous Redis‑based implementation but now calls
    ``MilvusClient.upsert_option``.  The endpoint is protected by the same JWT
    guard used by the rest of the API.
    """
    require_auth(request, settings)
    opt = await option_manager.create_option(body)
    # Persist via Milvus – payload is the raw bytes stored in the option model.
    _milvus.upsert_option(
        tenant_id=opt.tenant_id,
        option_id=opt.option_id,
        payload=opt.payload, )
    # Increment per‑tenant option count gauge
    M.OPTION_COUNT.labels(opt.tenant_id).inc()
    return OakPlanSuggestResponse(plan=[opt.option_id])


@router.put("/option/{option_id}", response_model=OakPlanSuggestResponse)
async def oak_option_update(option_id: str, body: OakOptionCreateRequest, request: Request):
    """Replace the payload of an existing Oak option.

    The update is performed via ``MilvusClient.upsert_option`` which overwrites
    the existing row because ``option_id`` is the primary key.
    """
    require_auth(request, settings)
    opt = await option_manager.update_option(option_id, body)
    _milvus.upsert_option(
        tenant_id=opt.tenant_id,
        option_id=opt.option_id,
        payload=opt.payload, )
    M.OPTION_COUNT.labels(opt.tenant_id).inc()
    return OakPlanSuggestResponse(plan=[opt.option_id])


@router.get("/plan", response_model=OakPlanSuggestResponse)
async def oak_plan(request: Request, max_options: int | None = None):
    """Return a ranked list of Oak option identifiers for the tenant.

    The planner now queries Milvus via ``MilvusClient.search_similar`` to find
    the most similar existing options.
    """
    require_auth(request, settings)
    tenant_ctx = await request.app.state.get_tenant_async(request, settings.namespace)  # type: ignore[attr-defined]
    # Use the existing planner logic; it will internally call Milvus through the
    # option manager when needed.
    plan = await plan_for_tenant(tenant_ctx.tenant_id, max_options=max_options)
    return OakPlanSuggestResponse(plan=plan)
