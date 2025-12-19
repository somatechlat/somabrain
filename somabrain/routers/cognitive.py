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
from typing import Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Request

from common.config.settings import settings
from somabrain import schemas as S
from somabrain.auth import require_auth
from somabrain.focus_state import FocusState
from somabrain.services.cognitive_loop_service import eval_step as _eval_step
from somabrain.services.memory_service import MemoryService
from somabrain.services.plan_engine import PlanEngine, PlanRequestContext
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
# Session-scoped FocusState cache (Requirement 10.1)
# ---------------------------------------------------------------------------
_focus_state_cache: Dict[str, FocusState] = {}


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


def _get_or_create_focus_state(
    session_id: str,
    tenant_id: str,
    cfg,
) -> Optional[FocusState]:
    """Get or create FocusState for session (Requirement 10.1).

    Returns None if use_focus_state is disabled.
    """
    if not getattr(cfg, "use_focus_state", True):
        return None

    cache_key = f"{tenant_id}:{session_id}"
    if cache_key in _focus_state_cache:
        return _focus_state_cache[cache_key]

    # Create new FocusState with HRRContext
    try:
        from somabrain.context_hrr import HRRContext

        dim = int(getattr(cfg, "hrr_dim", 512) or 512)
        hrr = HRRContext(dim=dim)
        focus = FocusState(
            hrr_context=hrr,
            cfg=cfg,
            session_id=session_id,
            tenant_id=tenant_id,
        )
        _focus_state_cache[cache_key] = focus
        return focus
    except Exception as exc:
        logger.warning(f"Failed to create FocusState: {exc}")
        return None


def _get_graph_client(mem_client):
    """Extract GraphClient from memory client."""
    if mem_client is None:
        return None
    if hasattr(mem_client, "graph_client"):
        return mem_client.graph_client
    if hasattr(mem_client, "_graph"):
        return mem_client._graph
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/plan/suggest", response_model=S.PlanSuggestResponse)
async def plan_suggest(body: S.PlanSuggestRequest, request: Request):
    """Suggest a small plan derived from the semantic graph around a task key.

    Body: { task_key: str, max_steps?: int, rel_types?: [str], universe?: str }
    Returns: { plan: [str] }

    Uses PlanEngine when use_planner is True (Requirement 10.3).
    """
    cfg = _get_app_config()
    mt_memory = _get_mt_memory()
    embedder = _get_embedder()

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

    # When use_planner is False, return empty plan (Requirement 10.4)
    if not getattr(cfg, "use_planner", False):
        return {"plan": []}

    try:
        memsvc = MemoryService(mt_memory, ctx.namespace)
        mem_client = memsvc.client()
        graph_client = _get_graph_client(mem_client)

        # Use PlanEngine for unified planning (Requirement 10.3)
        engine = PlanEngine(cfg, mem_client=mem_client, graph_client=graph_client)

        # Create task vector if embedder available
        task_vec = embedder.embed(task_key) if embedder else np.zeros(512)

        plan_ctx = PlanRequestContext(
            tenant_id=ctx.tenant_id,
            task_key=task_key,
            task_vec=task_vec,
            start_coord=(0.0, 0.0),  # Will be resolved by planner
            time_budget_ms=int(getattr(cfg, "plan_time_budget_ms", 50) or 50),
            max_steps=max_steps,
            rel_types=rel_types or [],
            universe=universe,
        )

        composite_plan = engine.plan(plan_ctx)
        plan_result = composite_plan.to_legacy_steps()

    except Exception as exc:
        logger.warning(f"PlanEngine failed: {exc}")
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

    Uses FocusState for session-scoped focus tracking and passes
    previous_focus_vec to eval_step for proper prediction comparison.

    Requirements: 10.1, 10.2
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

    # Get task embedding
    wm_vec = embedder.embed(body.task) if embedder else None

    # Get session ID from header or generate from tenant
    session_id = request.headers.get("X-Session-ID") or f"{ctx.tenant_id}:default"

    # Get or create FocusState for session (Requirement 10.1)
    focus_state = _get_or_create_focus_state(session_id, ctx.tenant_id, cfg)

    # Get previous focus vector for prediction comparison (Requirement 10.2)
    previous_focus_vec: Optional[np.ndarray] = None
    if focus_state is not None:
        previous_focus_vec = focus_state.previous_focus_vec

    # Update FocusState with current task (Requirement 10.1)
    if focus_state is not None and wm_vec is not None:
        # Get recall hits if available (empty list if none)
        recall_hits: List[tuple] = []
        focus_state.update(wm_vec, recall_hits)

    # Initial novelty from config or body
    initial_novelty = float(
        getattr(body, "novelty", None) or getattr(cfg, "default_novelty", 0.0) or 0.0
    )

    # Pass previous_focus_vec to eval_step (Requirement 10.2)
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
        previous_focus_vec=previous_focus_vec,
    )

    # Build the response structure from step_result
    act_step = {
        "step": body.task,
        "novelty": step_result.get("pred_error", initial_novelty),
        "pred_error": step_result.get("pred_error", initial_novelty),
        "salience": step_result.get(
            "salience", getattr(cfg, "default_salience", 0.0) or 0.0
        ),
        "stored": step_result.get("gate_store", False),
        "wm_hits": step_result.get("wm_hits", 0),
        "memory_hits": step_result.get("memory_hits", 0),
        "policy": step_result.get("policy"),
        "no_prev_focus": step_result.get("no_prev_focus", False),
    }

    # Persist focus snapshot if enabled (Requirement 8.1-8.5)
    if focus_state is not None:
        mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
        if mem_client:
            focus_state.persist_snapshot(
                mem_client,
                store_gate=step_result.get("gate_store", False),
                universe=getattr(body, "universe", None),
            )

    # Generate plan if planner is enabled (Requirement 10.3)
    plan_result: List[str] = []
    if getattr(cfg, "use_planner", False):
        try:
            mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
            if mem_client:
                graph_client = _get_graph_client(mem_client)
                engine = PlanEngine(cfg, mem_client=mem_client, graph_client=graph_client)

                task_vec = wm_vec if wm_vec is not None else np.zeros(512)
                plan_ctx = PlanRequestContext(
                    tenant_id=ctx.tenant_id,
                    task_key=body.task,
                    task_vec=task_vec,
                    start_coord=(0.0, 0.0),
                    focus_vec=focus_state.current_focus_vec if focus_state else None,
                    time_budget_ms=int(getattr(cfg, "plan_time_budget_ms", 50) or 50),
                    max_steps=int(getattr(cfg, "plan_max_steps", 5) or 5),
                    rel_types=[],
                    universe=getattr(body, "universe", None),
                )
                composite_plan = engine.plan(plan_ctx)
                plan_result = composite_plan.to_legacy_steps()
        except Exception as exc:
            logger.warning(f"PlanEngine failed in /act: {exc}")
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
    """Set personality traits (reserved for future implementation)."""
    # This endpoint is reserved for future personality trait management
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/micro/diag")
async def micro_diag(request: Request):
    """Get microcircuit diagnostics for the current tenant.

    Returns information about the multi-column working memory state
    including per-column statistics and tenant context.
    """
    cfg = _get_app_config()
    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")

    if not cfg.use_microcircuits:
        return {
            "enabled": False,
            "namespace": ctx.namespace,
            "trace_id": trace_id,
            "deadline_ms": deadline_ms,
            "idempotency_key": idempotency_key,
        }

    # Get mc_wm from app module
    try:
        from somabrain import app as app_module

        mc_wm = getattr(app_module, "mc_wm", None)
        stats = mc_wm.stats(ctx.tenant_id) if mc_wm else {}
    except Exception:
        stats = {}

    return {
        "enabled": True,
        "tenant": ctx.tenant_id,
        "columns": stats,
        "namespace": ctx.namespace,
        "trace_id": trace_id,
        "deadline_ms": deadline_ms,
        "idempotency_key": idempotency_key,
    }
