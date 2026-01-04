"""Cognitive Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Cognitive processing endpoints: plan suggestion, action execution, personality.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
from somabrain.schemas import (
    PlanSuggestResponse,
    PlanSuggestRequest,
    ActResponse,
    ActRequest,
    PersonalityState,
)
from somabrain.auth import require_auth
from somabrain.api.auth import bearer_auth
from somabrain.focus_state import FocusState
from somabrain.services.cognitive_loop_service import eval_step as _eval_step
from somabrain.services.memory_service import MemoryService
from somabrain.services.plan_engine import PlanEngine, PlanRequestContext
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.cognitive")

_LOG_PREFIX = "[COGNITIVE]"
_LOG_TENANT_FMT = "tenant=%s"
_LOG_OP_FMT = "op=%s"

router = Router(tags=["cognitive"])

# Session-scoped FocusState cache
_focus_state_cache: Dict[str, FocusState] = {}


# Helper functions
def _get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "runtime.py"
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


def _get_mt_memory():
    """Get multi-tenant memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


def _get_embedder():
    """Get embedder singleton."""
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
    session_id: str, tenant_id: str, cfg
) -> Optional[FocusState]:
    """Get or create FocusState for session."""
    if not getattr(cfg, "USE_FOCUS_STATE", True):
        return None

    cache_key = f"{tenant_id}:{session_id}"
    if cache_key in _focus_state_cache:
        return _focus_state_cache[cache_key]

    try:
        from somabrain.context_hrr import HRRContext

        dim = int(getattr(cfg, "HRR_DIM", 512) or 512)
        hrr = HRRContext(dim=dim)
        focus = FocusState(
            hrr_context=hrr, cfg=cfg, session_id=session_id, tenant_id=tenant_id
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


# Endpoints
@router.post("/plan/suggest", response=PlanSuggestResponse, auth=bearer_auth)
def plan_suggest(request: HttpRequest, body: PlanSuggestRequest):
    """Suggest a small plan derived from semantic graph around task key."""
    mt_memory = _get_mt_memory()
    embedder = _get_embedder()

    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE", "default"))
    require_auth(request, settings)

    task_key = str(getattr(body, "task_key", None) or "").strip()
    if not task_key:
        raise HttpError(400, "missing task_key")

    max_steps = int(
        getattr(body, "max_steps", None)
        or getattr(settings, "SOMABRAIN_PLAN_MAX_STEPS", 5)
        or 5
    )

    rel_types = getattr(body, "rel_types", None)
    if rel_types is not None and not isinstance(rel_types, list):
        raise HttpError(400, "rel_types must be a list of strings")

    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = getattr(body, "universe", None) or header_u

    if not getattr(settings, "SOMABRAIN_USE_PLANNER", False):
        return {"plan": []}

    try:
        memsvc = MemoryService(mt_memory, ctx.namespace)
        mem_client = memsvc.client()
        graph_client = _get_graph_client(mem_client)
        engine = PlanEngine(settings, mem_client=mem_client, graph_client=graph_client)

        task_vec = embedder.embed(task_key) if embedder else np.zeros(512)
        plan_ctx = PlanRequestContext(
            tenant_id=ctx.tenant_id,
            task_key=task_key,
            task_vec=task_vec,
            start_coord=(0.0, 0.0),
            time_budget_ms=int(getattr(settings, "PLAN_TIME_BUDGET_MS", 50) or 50),
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
        ctx.tenant_id,
        task_key,
        len(plan_result),
    )

    return {"plan": plan_result}


@router.post("/act", response=ActResponse, auth=bearer_auth)
def act_endpoint(request: HttpRequest, body: ActRequest):
    """Execute an action/task and return step results."""
    mt_memory = _get_mt_memory()
    embedder = _get_embedder()
    singletons = _get_app_singletons()

    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    predictor_factory = singletons.get("predictor_factory")
    per_tenant_neuromodulators = singletons.get("per_tenant_neuromodulators")
    personality_store = singletons.get("personality_store")
    amygdala = singletons.get("amygdala")

    predictor = predictor_factory() if predictor_factory else None
    wm_vec = embedder.embed(body.task) if embedder else None
    session_id = request.headers.get("X-Session-ID") or f"{ctx.tenant_id}:default"
    focus_state = _get_or_create_focus_state(session_id, ctx.tenant_id, settings)

    previous_focus_vec: Optional[np.ndarray] = None
    if focus_state is not None:
        previous_focus_vec = focus_state.previous_focus_vec

    if focus_state is not None and wm_vec is not None:
        recall_hits: List[tuple] = []
        focus_state.update(wm_vec, recall_hits)

    initial_novelty = float(
        getattr(body, "novelty", None)
        or getattr(settings, "SOMABRAIN_DEFAULT_NOVELTY", 0.0)
        or 0.0
    )

    step_result = _eval_step(
        novelty=initial_novelty,
        wm_vec=wm_vec,
        cfg=settings,
        predictor=predictor,
        neuromods=per_tenant_neuromodulators,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=ctx.tenant_id,
        previous_focus_vec=previous_focus_vec,
    )

    act_step = {
        "step": body.task,
        "novelty": step_result.get("pred_error", initial_novelty),
        "pred_error": step_result.get("pred_error", initial_novelty),
        "salience": step_result.get(
            "salience", getattr(settings, "SOMABRAIN_DEFAULT_SALIENCE", 0.0) or 0.0
        ),
        "stored": step_result.get("gate_store", False),
        "wm_hits": step_result.get("wm_hits", 0),
        "memory_hits": step_result.get("memory_hits", 0),
        "policy": step_result.get("policy"),
        "no_prev_focus": step_result.get("no_prev_focus", False),
    }

    if focus_state is not None:
        mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
        if mem_client:
            focus_state.persist_snapshot(
                mem_client,
                store_gate=step_result.get("gate_store", False),
                universe=getattr(body, "universe", None),
            )

    plan_result: List[str] = []
    if getattr(settings, "USE_PLANNER", False):
        try:
            mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
            if mem_client:
                graph_client = _get_graph_client(mem_client)
                engine = PlanEngine(
                    settings, mem_client=mem_client, graph_client=graph_client
                )
                task_vec = wm_vec if wm_vec is not None else np.zeros(512)
                plan_ctx = PlanRequestContext(
                    tenant_id=ctx.tenant_id,
                    task_key=body.task,
                    task_vec=task_vec,
                    start_coord=(0.0, 0.0),
                    focus_vec=focus_state.current_focus_vec if focus_state else None,
                    time_budget_ms=int(
                        getattr(settings, "SOMABRAIN_PLAN_TIME_BUDGET_MS", 50) or 50
                    ),
                    max_steps=int(
                        getattr(settings, "SOMABRAIN_PLAN_MAX_STEPS", 5) or 5
                    ),
                    rel_types=[],
                    universe=getattr(body, "universe", None),
                )
                composite_plan = engine.plan(plan_ctx)
                plan_result = composite_plan.to_legacy_steps()
        except Exception as exc:
            logger.warning(f"PlanEngine failed in /act: {exc}")

    log_truncate_len = int(
        getattr(settings, "SOMABRAIN_LOG_TASK_TRUNCATE_LEN", 50) or 50
    )
    task_preview = body.task[:log_truncate_len] if body.task else ""

    logger.debug(
        "%s Action executed | %s | task=%s | salience=%.3f",
        _LOG_PREFIX,
        ctx.tenant_id,
        task_preview,
        act_step.get("salience", 0.0),
    )

    return ActResponse(
        task=body.task,
        results=[act_step],
        plan=plan_result,
        plan_universe=body.universe,
    )


@router.post("/personality", response=PersonalityState, auth=bearer_auth)
def set_personality(request: HttpRequest, state: PersonalityState) -> PersonalityState:
    """Set personality traits (reserved for future implementation)."""
    raise HttpError(404, "Not Found")


@router.get("/micro/diag", auth=bearer_auth)
def micro_diag(request: HttpRequest):
    """Get microcircuit diagnostics for the current tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")

    if not getattr(settings, "SOMABRAIN_USE_MICROCIRCUITS", False):
        return {
            "enabled": False,
            "namespace": ctx.namespace,
            "trace_id": trace_id,
            "deadline_ms": deadline_ms,
            "idempotency_key": idempotency_key,
        }

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
