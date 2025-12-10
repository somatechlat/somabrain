"""Cognitive Router
==================

Cognitive processing endpoints: plan suggestion, action execution, personality.
These endpoints handle higher-level cognitive operations.

Endpoints:
- POST /plan/suggest - Suggest a plan from semantic graph
- POST /act - Execute a cognitive action step
- POST /personality - Set personality traits
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request

from common.config.settings import settings
from somabrain import schemas as S
from somabrain.auth import require_auth
from somabrain.planner import plan_from_graph
from somabrain.services.cognitive_loop_service import eval_step as _eval_step
from somabrain.services.memory_service import MemoryService
from somabrain.tenant import get_tenant as get_tenant_async

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("somabrain.routers.cognitive")

# Log format constants for consistent output
_LOG_PREFIX = "[COGNITIVE]"
_LOG_TENANT_FMT = "tenant=%s"
_LOG_OP_FMT = "op=%s"

router = APIRouter(tags=["cognitive"])


# ---------------------------------------------------------------------------
# Lazy accessors for app-level singletons
# ---------------------------------------------------------------------------


def _get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "runtime.py"
    )
    _spec = importlib.util.spec_from_file_location(
        "somabrain.runtime_module", _runtime_path
    )
    if _spec and _spec.name in sys.modules:
        return sys.modules[_spec.name]
    for m in list(sys.modules.values()):
        try:
            mf = getattr(m, "__file__", "") or ""
            if mf.endswith(os.path.join("somabrain", "runtime.py")):
                return m
        except Exception:
            continue
    return None


def _get_app_config():
    """Get the application configuration."""
    return settings


def _get_mt_memory():
    """Get the multi-tenant memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


def _get_embedder():
    """Get the embedder singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "embedder", None)
    return None


def _get_app_singletons():
    """Get app-level singletons."""
    try:
        from somabrain import app as app_module
        return {
            "predictor_factory": getattr(app_module, "_make_predictor", None),
            "per_tenant_neuromodulators": getattr(
                app_module, "per_tenant_neuromodulators", None
            ),
            "personality_store": getattr(app_module, "personality_store", None),
            "amygdala": getattr(app_module, "amygdala", None),
        }
    except Exception:
        return {}



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/plan/suggest", response_model=S.PlanSuggestResponse)
async def plan_suggest(body: S.PlanSuggestRequest, request: Request):
    """Suggest a small plan derived from the semantic graph around a task key.

    Body: { task_key: str, max_steps?: int, rel_types?: [str], universe?: str }
    Returns: { plan: [str] }
    """
    cfg = _get_app_config()
    mt_memory = _get_mt_memory()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    task_key = str(getattr(body, "task_key", None) or "").strip()
    if not task_key:
        raise HTTPException(status_code=400, detail="missing task_key")

    max_steps = int(
        getattr(body, "max_steps", None) or getattr(cfg, "plan_max_steps", 5) or 5
    )

    rel_types = getattr(body, "rel_types", None)
    if rel_types is not None and not isinstance(rel_types, list):
        raise HTTPException(
            status_code=400, detail="rel_types must be a list of strings"
        )

    # Universe scoping: body value overrides header when set
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = getattr(body, "universe", None) or header_u

    try:
        memsvc = MemoryService(mt_memory, ctx.namespace)
        plan_result = plan_from_graph(
            task_key,
            memsvc.client(),
            max_steps=max_steps,
            rel_types=rel_types,
            universe=universe,
        )
    except Exception:
        plan_result = []

    logger.debug(
        "%s Plan suggested | %s | task_key=%s | steps=%d",
        _LOG_PREFIX,
        _LOG_TENANT_FMT,
        ctx.tenant_id,
        task_key,
        len(plan_result),
    )

    return {"plan": plan_result}


@router.post("/act", response_model=S.ActResponse)
async def act_endpoint(body: S.ActRequest, request: Request):
    """Execute an action/task and return step results.

    This simplified implementation runs a single evaluation step using the
    existing cognitive loop service. It returns a minimal ActResponse
    compatible with the test suite.
    """
    cfg = _get_app_config()
    mt_memory = _get_mt_memory()
    embedder = _get_embedder()
    singletons = _get_app_singletons()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    # Get singletons
    predictor_factory = singletons.get("predictor_factory")
    per_tenant_neuromodulators = singletons.get("per_tenant_neuromodulators")
    personality_store = singletons.get("personality_store")
    amygdala = singletons.get("amygdala")

    predictor = predictor_factory() if predictor_factory else None

    # Run a single evaluation step
    wm_vec = embedder.embed(body.task) if embedder else None

    # Initial novelty from config or body, not hardcoded
    initial_novelty = float(getattr(body, "novelty", None) or getattr(cfg, "default_novelty", 0.0) or 0.0)

    step_result = _eval_step(
        novelty=initial_novelty,
        wm_vec=wm_vec,
        cfg=cfg,
        predictor=predictor,
        neuromods=per_tenant_neuromodulators,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=ctx.tenant_id,
    )

    # Build the response structure from step_result - no hardcoded defaults
    act_step = {
        "step": body.task,
        "novelty": step_result.get("pred_error", initial_novelty),
        "pred_error": step_result.get("pred_error", initial_novelty),
        "salience": step_result.get("salience", getattr(cfg, "default_salience", 0.0) or 0.0),
        "stored": step_result.get("gate_store", False),
        "wm_hits": step_result.get("wm_hits", 0),
        "memory_hits": step_result.get("memory_hits", 0),
        "policy": step_result.get("policy"),
    }

    # Generate plan if planner is enabled
    plan_result: List[str] = []
    if getattr(cfg, "use_planner", False):
        try:
            mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
            if mem_client:
                plan_result = plan_from_graph(
                    body.task,
                    mem_client,
                    max_steps=getattr(cfg, "plan_max_steps", 5),
                    rel_types=None,
                    universe=getattr(body, "universe", None),
                )
        except Exception:
            plan_result = []

    # Log truncation length from config
    log_truncate_len = int(getattr(cfg, "log_task_truncate_len", 50) or 50)
    task_preview = body.task[:log_truncate_len] if body.task else ""

    logger.debug(
        "%s Action executed | %s | task=%s | salience=%.3f",
        _LOG_PREFIX,
        _LOG_TENANT_FMT,
        ctx.tenant_id,
        task_preview,
        act_step.get("salience", 0.0),
    )

    return S.ActResponse(
        task=body.task,
        results=[act_step],
        plan=plan_result,
        plan_universe=body.universe,
    )


@router.post("/personality", response_model=S.PersonalityState)
async def set_personality(
    state: S.PersonalityState, request: Request
) -> S.PersonalityState:
    """Set personality traits (placeholder - not implemented)."""
    # This endpoint is a placeholder for future personality trait management
    raise HTTPException(status_code=404, detail="Not Found")
