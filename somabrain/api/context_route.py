"""Evaluate/Feedback endpoints for SomaBrain."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from somabrain.api.dependencies.utility_guard import utility_guard
from somabrain.api.dependencies.auth import auth_guard, get_allowed_tenants, get_default_tenant
from somabrain.api.schemas.context import (
    EvaluateRequest,
    EvaluateResponse,
    FeedbackRequest,
    FeedbackResponse,
    MemoryItem,
)
from somabrain.context import ContextPlanner, PlanResult
from somabrain.context.factory import get_context_builder, get_context_planner
from somabrain import audit
from somabrain.learning import AdaptationEngine
from somabrain.storage.feedback import FeedbackStore
from somabrain.storage.token_ledger import TokenLedger

router = APIRouter()
_feedback_store = FeedbackStore()
_token_ledger = TokenLedger()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_endpoint(
    payload: EvaluateRequest,
    request: Request,
    _guard=Depends(utility_guard), auth=Depends(auth_guard),
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

    plan: PlanResult = planner.plan(bundle)
    checksum = _constitution_checksum()
    return EvaluateResponse(
        query=bundle.query,
        prompt=plan.prompt,
        tenant_id=tenant_id,
        memories=[MemoryItem(**m.__dict__) for m in bundle.memories],
        weights=bundle.weights,
        residual_vector=bundle.residual_vector,
        working_memory=bundle.working_memory_snapshot,
        constitution_checksum=checksum,
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(
    payload: FeedbackRequest,
    request: Request,
    _guard=Depends(utility_guard), auth=Depends(auth_guard),
):
    planner = get_context_planner()
    builder = get_context_builder()
    default_tenant = get_default_tenant()
    tenant_id = payload.tenant_id or default_tenant
    allowed = get_allowed_tenants()
    if allowed and tenant_id not in allowed:
        raise HTTPException(status_code=400, detail="unknown tenant")
    adapter = _get_adaptation(builder, planner)
    applied = adapter.apply_feedback(utility=payload.utility, reward=payload.reward)
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
            tokens = payload.metadata.get("tokens") or payload.metadata.get("tokens_used")
        if tokens is not None:
            _token_ledger.record(
                entry_id=f"{payload.session_id}:{uuid.uuid4().hex}",
                session_id=payload.session_id,
                tokens=float(tokens),
                tenant_id=tenant_id,
                model=payload.metadata.get("model") if isinstance(payload.metadata, dict) else None,
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
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"feedback persist failed: {exc}")
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
