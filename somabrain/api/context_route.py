"""Evaluate/Feedback endpoints for SomaBrain."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from somabrain.api.dependencies.utility_guard import utility_guard
from somabrain.api.dependencies.auth import (
    auth_guard,
    get_allowed_tenants,
    get_default_tenant,
)
from somabrain.api.schemas.context import (
    EvaluateRequest,
    EvaluateResponse,
    FeedbackRequest,
    FeedbackResponse,
    MemoryItem,
    AdaptationStateResponse,
    RetrievalWeightsState,
    UtilityWeightsState,
)
from somabrain.context import ContextPlanner
from somabrain.context.factory import get_context_builder, get_context_planner
from somabrain import audit
from somabrain.learning import AdaptationEngine
from somabrain.storage.feedback import FeedbackStore
from somabrain.storage.token_ledger import TokenLedger

router = APIRouter()
_feedback_store = FeedbackStore()
_token_ledger = TokenLedger()

# Global counter for feedback applications across requests
_feedback_counter = 0


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_endpoint(
    payload: EvaluateRequest,
    request: Request,
    _guard=Depends(utility_guard),
    auth=Depends(auth_guard),
):
    builder = get_context_builder()
    planner = get_context_planner()
    default_tenant = get_default_tenant()
    tenant_id = payload.tenant_id or default_tenant
    allowed = get_allowed_tenants()
    if allowed and tenant_id not in allowed:
        raise HTTPException(status_code=400, detail="unknown tenant")
    try:
        bundle = builder.build(
            query=payload.query,
            top_k=payload.top_k,
            session_id=payload.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"context build failed: {exc}")

    plan = planner.plan(bundle)
    # Enforce payload size/length limits
    if len(bundle.memories) > 20:
        raise HTTPException(status_code=400, detail="memories exceeds 20 items")
    if len(bundle.prompt) > 4096:
        raise HTTPException(
            status_code=400, detail="prompt length exceeds 4096 characters"
        )
    if len(bundle.residual_vector) > 2048:
        raise HTTPException(
            status_code=400, detail="residual vector exceeds 2048 floats"
        )
    if len(bundle.working_memory_snapshot) > 10:
        raise HTTPException(status_code=400, detail="working memory exceeds 10 items")
    import json

    resp_obj = EvaluateResponse(
        query=bundle.query,
        prompt=plan.prompt,
        tenant_id=tenant_id,
        memories=[MemoryItem(**m.__dict__) for m in bundle.memories],
        weights=bundle.weights,
        residual_vector=bundle.residual_vector,
        working_memory=bundle.working_memory_snapshot,
        constitution_checksum=_constitution_checksum(),
    )
    if len(json.dumps(resp_obj.dict())) > 128 * 1024:
        raise HTTPException(status_code=400, detail="response size exceeds 128 KB")
    return resp_obj


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(
    payload: FeedbackRequest,
    request: Request,
    _guard=Depends(utility_guard),
    auth=Depends(auth_guard),
):
    planner = get_context_planner()
    builder = get_context_builder()
    default_tenant = get_default_tenant()
    tenant_id = payload.tenant_id or default_tenant
    allowed = get_allowed_tenants()
    if allowed and tenant_id not in allowed:
        raise HTTPException(status_code=400, detail="unknown tenant")
    # Enforce payload size/length limits
    for field in [
        payload.session_id,
        payload.query,
        payload.prompt,
        payload.response_text,
    ]:
        if field and len(field) > 1024:
            raise HTTPException(
                status_code=400, detail="input field exceeds 1024 characters"
            )
    import json

    if payload.metadata is not None:
        try:
            if len(json.dumps(payload.metadata)) > 8 * 1024:
                raise HTTPException(status_code=400, detail="metadata exceeds 8 KB")
        except Exception:
            raise HTTPException(status_code=400, detail="invalid metadata encoding")

    adapter = _get_adaptation(builder, planner)
    # Capture weights before adaptation
    before = {
        "retrieval": {
            "alpha": adapter.retrieval_weights.alpha,
            "beta": adapter.retrieval_weights.beta,
            "gamma": adapter.retrieval_weights.gamma,
            "tau": adapter.retrieval_weights.tau,
        },
        "utility": {
            "lambda_": adapter.utility_weights.lambda_,
            "mu": adapter.utility_weights.mu,
            "nu": adapter.utility_weights.nu,
        },
    }
    applied = adapter.apply_feedback(utility=payload.utility, reward=payload.reward)
    # Increment global feedback counter if adaptation was applied
    global _feedback_counter
    if applied:
        adapter_count = getattr(adapter, "_feedback_count", 0)
        # Track the highest observed count from either the adapter or module-level counter.
        _feedback_counter = max(_feedback_counter + 1, adapter_count)
    # Capture weights after adaptation
    after = {
        "retrieval": {
            "alpha": adapter.retrieval_weights.alpha,
            "beta": adapter.retrieval_weights.beta,
            "gamma": adapter.retrieval_weights.gamma,
            "tau": adapter.retrieval_weights.tau,
        },
        "utility": {
            "lambda_": adapter.utility_weights.lambda_,
            "mu": adapter.utility_weights.mu,
            "nu": adapter.utility_weights.nu,
        },
    }
    # Compute deltas
    delta = {
        "retrieval": {
            k: after["retrieval"][k] - before["retrieval"][k]
            for k in before["retrieval"]
        },
        "utility": {
            k: after["utility"][k] - before["utility"][k] for k in before["utility"]
        },
    }
    event_id = _make_event_id(payload.session_id)
    try:
        _feedback_store.record(
            event_id=event_id,
            session_id=payload.session_id,
            query=payload.query,
            prompt=payload.prompt,
            response_text=payload.response_text,
            utility=payload.utility,
            reward=payload.reward,
            metadata=payload.metadata,
        )
        tokens = None
        if isinstance(payload.metadata, dict):
            tokens = payload.metadata.get("tokens") or payload.metadata.get(
                "tokens_used"
            )
        if tokens is not None:
            _token_ledger.record(
                entry_id=f"{payload.session_id}:{uuid.uuid4().hex}",
                session_id=payload.session_id,
                tokens=float(tokens),
                tenant_id=tenant_id,
                model=(
                    payload.metadata.get("model")
                    if isinstance(payload.metadata, dict)
                    else None
                ),
            )
        audit.publish_event(
            {
                "action": "context.feedback",
                "decision": "recorded",
                "session_id": payload.session_id,
                "tenant_id": tenant_id,
                "utility": payload.utility,
                "reward": payload.reward,
                "event_id": event_id,
                "adaptation": {
                    "applied": applied,
                    "before": before,
                    "after": after,
                    "delta": delta,
                },
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"feedback persist failed: {exc}")
    if applied:
        try:
            store_total = _feedback_store.total_count()
            adapter_total = getattr(adapter, "_feedback_count", 0)
            _feedback_counter = max(_feedback_counter, adapter_total, store_total)
        except Exception:
            pass
    return FeedbackResponse(accepted=True, adaptation_applied=applied)


def _constitution_checksum() -> Optional[str]:
    try:
        from somabrain.constitution import ConstitutionEngine

        engine = ConstitutionEngine()
        engine.load()
        return engine.get_checksum()
    except Exception:
        return None


_adaptation_engine: Optional[AdaptationEngine] = None


def _get_adaptation(builder, planner: ContextPlanner) -> AdaptationEngine:
    global _adaptation_engine
    if _adaptation_engine is None:
        adaptation = AdaptationEngine(
            retrieval=builder.weights,
            utility=planner.utility_weights,
        )
        _adaptation_engine = adaptation
    return _adaptation_engine


def _make_event_id(session_id: str) -> str:
    return f"{session_id}:{uuid.uuid4().hex}"


@router.get("/adaptation/state", response_model=AdaptationStateResponse)
async def adaptation_state_endpoint(request: Request, auth=Depends(auth_guard)):
    """Return current adaptation weights (retrieval + utility) and history length.

    Useful for external monitoring/tests to verify learning progress without
    mutating state.
    """
    builder = get_context_builder()
    planner = get_context_planner()
    adapter = _get_adaptation(builder, planner)
    retrieval_state = RetrievalWeightsState(
        alpha=adapter.retrieval_weights.alpha,
        beta=adapter.retrieval_weights.beta,
        gamma=adapter.retrieval_weights.gamma,
        tau=adapter.retrieval_weights.tau,
    )
    utility_state = UtilityWeightsState(
        lambda_=adapter.utility_weights.lambda_,
        mu=adapter.utility_weights.mu,
        nu=adapter.utility_weights.nu,
    )
    # Access protected members for observability (history length, lr)
    # Use the module‑level feedback counter for a clean monotonic metric.
    # The counter is incremented on each successful feedback application.
    adapter_count = getattr(adapter, "_feedback_count", 0)
    store_total = 0
    try:
        store_total = int(_feedback_store.total_count())
    except Exception:
        store_total = 0
    history_len = max(int(_feedback_counter), int(adapter_count), int(store_total))
    learning_rate = float(getattr(adapter, "_lr", 0.0))
    return AdaptationStateResponse(
        retrieval=retrieval_state,
        utility=utility_state,
        history_len=history_len,
        learning_rate=learning_rate,
    )
