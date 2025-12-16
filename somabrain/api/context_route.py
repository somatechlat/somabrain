"""Evaluate/Feedback endpoints for SomaBrain.

Uses DI container for state management. ContextRouteState encapsulates
feedback store, token ledger, adaptation engines, and rate limiting.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from somabrain.api.dependencies.utility_guard import utility_guard
from somabrain.api.dependencies.auth import (
    auth_guard,
    get_allowed_tenants_async,
    get_default_tenant_async,
)
from somabrain.api.schemas.context import (
    EvaluateRequest,
    EvaluateResponse,
    FeedbackRequest,
    FeedbackResponse,
    MemoryItem,
    AdaptationStateResponse,
    AdaptationGainsState,
    AdaptationConstraintsState,
    RetrievalWeightsState,
    UtilityWeightsState,
)
from somabrain.api.context_state import get_context_route_state
from somabrain.api.context_validation import (
    validate_evaluate_response,
    validate_evaluate_response_size,
    validate_feedback_fields,
    validate_feedback_metadata,
    validate_feedback_reward_utility,
)
from somabrain.context import ContextPlanner
from somabrain.context.factory import get_context_builder, get_context_planner
from somabrain import audit
from somabrain.learning import AdaptationEngine
from somabrain.metrics import (
    update_learning_retrieval_weights,
    update_learning_utility_weights,
    record_learning_feedback_applied,
    record_learning_feedback_rejected,
    record_learning_feedback_latency,
    update_learning_effective_lr,
)

# Import central feature flag view and metrics utilities
from config.feature_flags import FeatureFlags
from somabrain import metrics as _metrics


# Register Prometheus gauges for each feature flag so they are exposed via
# ``/metrics``. ``_metrics.get_gauge`` returns an existing gauge if one was
# already created, making this safe to call multiple times (e.g., on module
# reloads).
def _register_flag_gauges() -> None:
    status = FeatureFlags.get_status()
    for name, enabled in status.items():
        gauge = _metrics.get_gauge(
            "somabrain_feature_flag",
            "Feature flag status (1=enabled, 0=disabled)",
            labelnames=["flag"],
        )
        gauge.labels(flag=name).set(1 if enabled else 0)


_register_flag_gauges()

router = APIRouter()


def _enforce_feedback_rate_limit(tenant_id: str) -> None:
    """Enforce per-tenant rate limiting for feedback requests."""
    get_context_route_state().enforce_rate_limit(tenant_id)


@router.get("/feature-flags")
def feature_flags_endpoint() -> dict:
    """Expose the current feature-flag status."""
    _register_flag_gauges()
    return FeatureFlags.get_status()


def _get_feedback_store() -> FeedbackStore:
    """Get the FeedbackStore instance from DI container."""
    return get_context_route_state().get_feedback_store()


def _get_token_ledger() -> TokenLedger:
    """Get the TokenLedger instance from DI container."""
    return get_context_route_state().get_token_ledger()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_endpoint(
    payload: EvaluateRequest,
    request: Request,
    _guard=Depends(utility_guard),
    auth=Depends(auth_guard),
):
    builder = get_context_builder()
    planner = get_context_planner()
    default_tenant = await get_default_tenant_async()
    tenant_id = payload.tenant_id or default_tenant
    # Ensure the builder knows the tenant for metric attribution
    if hasattr(builder, "set_tenant"):
        builder.set_tenant(tenant_id)
    allowed = await get_allowed_tenants_async()
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
    memories = [MemoryItem(**m.__dict__) for m in bundle.memories]

    # Enforce payload size/length limits
    validate_evaluate_response(
        bundle, memories, plan.prompt, bundle.residual_vector, bundle.working_memory_snapshot
    )

    resp_obj = EvaluateResponse(
        query=bundle.query,
        prompt=plan.prompt,
        tenant_id=tenant_id,
        memories=memories,
        weights=bundle.weights,
        residual_vector=bundle.residual_vector,
        working_memory=bundle.working_memory_snapshot,
        constitution_checksum=_constitution_checksum(),
    )
    validate_evaluate_response_size(resp_obj.dict())
    return resp_obj


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(
    payload: FeedbackRequest,
    request: Request,
    _guard=Depends(utility_guard),
    auth=Depends(auth_guard),
):
    start_time = time.perf_counter()
    planner = get_context_planner()
    builder = get_context_builder()
    default_tenant = await get_default_tenant_async()
    tenant_id = payload.tenant_id or default_tenant
    _enforce_feedback_rate_limit(tenant_id)
    # Ensure the builder knows the tenant for metric attribution
    if hasattr(builder, "set_tenant"):
        builder.set_tenant(tenant_id)
    allowed = await get_allowed_tenants_async()
    if allowed and tenant_id not in allowed:
        raise HTTPException(status_code=400, detail="unknown tenant")

    # Enforce payload size/length limits
    validate_feedback_fields(
        payload.session_id, payload.query, payload.prompt, payload.response_text
    )
    validate_feedback_metadata(payload.metadata)

    # Validate reward and utility
    reward_val, util_val = validate_feedback_reward_utility(payload.reward, payload.utility)

    adapter = _get_adaptation(builder, planner, tenant_id=tenant_id)
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
    # Increment feedback counter if adaptation was applied
    route_state = get_context_route_state()
    if applied:
        adapter_count = getattr(adapter, "_feedback_count", 0)
        # Track the highest observed count from either the adapter or state counter.
        route_state.feedback_counter = max(route_state.increment_feedback_counter(), adapter_count)

        # Record metrics on successful feedback application
        record_learning_feedback_applied(tenant_id)

        # Update weight metrics
        update_learning_retrieval_weights(
            tenant_id,
            alpha=adapter.retrieval_weights.alpha,
            beta=adapter.retrieval_weights.beta,
            gamma=adapter.retrieval_weights.gamma,
            tau=adapter.retrieval_weights.tau,
        )
        update_learning_utility_weights(
            tenant_id,
            lambda_=adapter.utility_weights.lambda_,
            mu=adapter.utility_weights.mu,
            nu=adapter.utility_weights.nu,
        )

        # Update effective learning rate metric
        lr_eff = getattr(adapter, "_lr", 0.0)
        update_learning_effective_lr(tenant_id, lr_eff)
    else:
        # Feedback rejected - determine reason
        reason = "bounds" if payload.utility is None or payload.reward is None else "outlier"
        record_learning_feedback_rejected(tenant_id, reason)
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
            k: after["retrieval"][k] - before["retrieval"][k] for k in before["retrieval"]
        },
        "utility": {k: after["utility"][k] - before["utility"][k] for k in before["utility"]},
    }
    event_id = _make_event_id(payload.session_id)
    try:
        store = _get_feedback_store()
        store.record(
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
            ledger = _get_token_ledger()
            ledger.record(
                entry_id=f"{payload.session_id}:{uuid.uuid4().hex}",
                session_id=payload.session_id,
                tokens=float(tokens),
                tenant_id=tenant_id,
                model=(
                    payload.metadata.get("model") if isinstance(payload.metadata, dict) else None
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
        store = _get_feedback_store()
        store_total = store.total_count()
        adapter_total = getattr(adapter, "_feedback_count", 0)
        route_state.feedback_counter = max(route_state.feedback_counter, adapter_total, store_total)

    # Record feedback latency
    elapsed = time.perf_counter() - start_time
    record_learning_feedback_latency(tenant_id, elapsed)

    return FeedbackResponse(accepted=True, adaptation_applied=applied)


def _constitution_checksum() -> Optional[str]:
    from somabrain.constitution import ConstitutionEngine

    engine = ConstitutionEngine()
    engine.load()
    return engine.get_checksum()


# Backward compatibility: module-level reference (deprecated)
_adaptation_engines: dict[str, AdaptationEngine] = {}


def _get_adaptation(
    builder, planner: ContextPlanner, tenant_id: str = "default"
) -> AdaptationEngine:
    """Get or create a per-tenant AdaptationEngine instance.

    Each tenant maintains independent learning state. Uses DI container
    for state management.
    """
    return get_context_route_state().get_adaptation_engine(builder, planner, tenant_id)


def _make_event_id(session_id: str) -> str:
    suffix = uuid.uuid4().hex
    max_prefix = 64 - len(suffix) - 1  # account for colon separator
    prefix = (session_id or "")[: max(0, max_prefix)]
    if prefix:
        return f"{prefix}:{suffix}"
    # Fall back to suffix-only when no session id provided or prefix length is zero
    return suffix[:64]


@router.get("/adaptation/state", response_model=AdaptationStateResponse)
async def adaptation_state_endpoint(
    request: Request, tenant_id: Optional[str] = None, auth=Depends(auth_guard)
):
    """Return current adaptation weights (retrieval + utility) and history length.

    Useful for external monitoring/tests to verify learning progress without
    mutating state. Supports per-tenant queries via ?tenant_id=X parameter.
    """
    builder = get_context_builder()
    planner = get_context_planner()
    default_tenant = await get_default_tenant_async()
    tid = tenant_id or default_tenant
    adapter = _get_adaptation(builder, planner, tenant_id=tid)
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
    gains_state = AdaptationGainsState(**asdict(adapter._gains))
    constraints_state = AdaptationConstraintsState(**asdict(adapter._constraint_bounds))
    # Access protected members for observability (history length, lr)
    # Use the DI container state for a clean monotonic metric.
    # The counter is incremented on each successful feedback application.
    route_state = get_context_route_state()
    adapter_count = getattr(adapter, "_feedback_count", 0)
    store = _get_feedback_store()
    store_total = int(store.total_count())
    history_len = max(int(route_state.feedback_counter), int(adapter_count), int(store_total))
    learning_rate = float(getattr(adapter, "_lr", 0.0))
    return AdaptationStateResponse(
        retrieval=retrieval_state,
        utility=utility_state,
        history_len=history_len,
        learning_rate=learning_rate,
        gains=gains_state,
        constraints=constraints_state,
    )


class ResetAdaptationRequest(BaseModel):
    tenant_id: Optional[str] = None
    base_lr: Optional[float] = None
    reset_history: bool = True
    retrieval_defaults: Optional[RetrievalWeightsState] = None
    utility_defaults: Optional[UtilityWeightsState] = None
    gains: Optional[AdaptationGainsState] = None
    constraints: Optional[AdaptationConstraintsState] = None


@router.post("/adaptation/reset")
async def adaptation_reset_endpoint(
    payload: ResetAdaptationRequest,
    request: Request,
    auth=Depends(auth_guard),
):
    """Reset the per-tenant adaptation engine to defaults for clean benchmarks.

    This endpoint is intended for operator/benchmark use. It does not return
    a model and will simply respond with a JSON status on success.
    """
    # Gate reset to dev mode only to avoid misuse in staging/prod.
    try:
        from common.config.settings import settings as _shared

        if getattr(_shared, "mode_normalized", "prod") != "dev":
            raise HTTPException(
                status_code=403, detail="adaptation reset not allowed outside dev mode"
            )
    except HTTPException:
        raise
    except Exception:
        # If settings cannot be imported, remain conservative and allow only when legacy auth is disabled
        try:
            from somabrain.auth import _auth_disabled as _legacy_auth_disabled

            if not _legacy_auth_disabled():
                raise HTTPException(
                    status_code=403, detail="adaptation reset blocked (no mode info)"
                )
        except Exception:
            raise HTTPException(status_code=403, detail="adaptation reset blocked (no mode info)")
    builder = get_context_builder()
    planner = get_context_planner()
    default_tenant = await get_default_tenant_async()
    tenant_id = payload.tenant_id or default_tenant
    adapter = _get_adaptation(builder, planner, tenant_id=tenant_id)

    # Optionally replace constraints/gains/base_lr
    if payload.constraints is not None:
        from somabrain.learning.adaptation import AdaptationConstraints

        c = payload.constraints
        adapter.set_constraints(
            AdaptationConstraints(
                alpha_min=c.alpha_min,
                alpha_max=c.alpha_max,
                gamma_min=c.gamma_min,
                gamma_max=c.gamma_max,
                lambda_min=c.lambda_min,
                lambda_max=c.lambda_max,
                mu_min=c.mu_min,
                mu_max=c.mu_max,
                nu_min=c.nu_min,
                nu_max=c.nu_max,
            )
        )
    if payload.gains is not None:
        from somabrain.learning.adaptation import AdaptationGains

        g = payload.gains
        adapter.set_gains(
            AdaptationGains(alpha=g.alpha, gamma=g.gamma, lambda_=g.lambda_, mu=g.mu, nu=g.nu)
        )
    if payload.base_lr is not None:
        adapter.set_base_learning_rate(float(payload.base_lr))

    # Build optional defaults structures
    retrieval_defaults = None
    if payload.retrieval_defaults is not None:
        from somabrain.context.builder import RetrievalWeights

        rd = payload.retrieval_defaults
        retrieval_defaults = RetrievalWeights(
            alpha=rd.alpha, beta=rd.beta, gamma=rd.gamma, tau=rd.tau
        )
    utility_defaults = None
    if payload.utility_defaults is not None:
        from somabrain.learning.adaptation import UtilityWeights

        ud = payload.utility_defaults
        utility_defaults = UtilityWeights(lambda_=ud.lambda_, mu=ud.mu, nu=ud.nu)

    adapter.reset(
        retrieval_defaults=retrieval_defaults,
        utility_defaults=utility_defaults,
        base_lr=payload.base_lr,
        clear_history=bool(payload.reset_history),
    )

    # Reset counter view as well so state.history_len starts at 0
    get_context_route_state().feedback_counter = 0

    audit.publish_event(
        {
            "action": "context.adaptation_reset",
            "tenant_id": tenant_id,
            "base_lr": payload.base_lr,
            "reset_history": payload.reset_history,
        }
    )
    return {"ok": True, "tenant_id": tenant_id}
