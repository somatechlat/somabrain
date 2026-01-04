"""Context API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Evaluate/Feedback endpoints for context-aware processing.
"""



from __future__ import annotations

import logging
import time
import uuid
from typing import Optional
from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.context")

router = Router(tags=["context"])


@router.get("/feature-flags")
def feature_flags_endpoint(request: HttpRequest):
    """Get current feature flag status."""
    try:
        from somabrain.services.feature_flags import FeatureFlags
        return FeatureFlags.get_status()
    except Exception as exc:
        logger.warning(f"Failed to get feature flags: {exc}")
        return {}


@router.post("/evaluate", auth=bearer_auth)
def evaluate_endpoint(request: HttpRequest, payload: dict):
    """Evaluate context and return prompt with memories."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    try:
        from somabrain.context.factory import get_context_builder, get_context_planner
        
        builder = get_context_builder()
        planner = get_context_planner()
        
        tenant_id = payload.get("tenant_id") or ctx.tenant_id
        query = payload.get("query", "")
        top_k = int(payload.get("top_k", 10))
        session_id = payload.get("session_id")
        
        # Build context bundle
        bundle = builder.build(query=query, top_k=top_k, session_id=session_id)
        plan = planner.plan(bundle)
        
        memories = [{"content": str(m)} for m in (bundle.memories or [])]
        
        return {
            "query": query,
            "prompt": plan.prompt,
            "tenant_id": tenant_id,
            "memories": memories,
            "weights": bundle.weights,
        }
    except Exception as exc:
        raise HttpError(500, f"Context build failed: {exc}")


@router.post("/feedback", auth=bearer_auth)
def feedback_endpoint(request: HttpRequest, payload: dict):
    """Record feedback for learning adaptation."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    start_time = time.perf_counter()
    tenant_id = payload.get("tenant_id") or ctx.tenant_id
    
    try:
        from somabrain.context.factory import get_context_builder, get_context_planner
        from somabrain.api.context_state import get_context_route_state
        
        builder = get_context_builder()
        planner = get_context_planner()
        
        # Get adaptation engine
        def _get_adaptation(builder, planner, tenant_id):
            """Execute get adaptation.

                Args:
                    builder: The builder.
                    planner: The planner.
                    tenant_id: The tenant_id.
                """

            return get_context_route_state().get_adaptation_engine(builder, planner, tenant_id)
        
        adapter = _get_adaptation(builder, planner, tenant_id=tenant_id)
        
        # Apply feedback
        utility = payload.get("utility")
        reward = payload.get("reward")
        applied = adapter.apply_feedback(utility=utility, reward=reward)
        
        # Record feedback
        if applied:
            try:
                from somabrain.api.context_state import get_context_route_state
                route_state = get_context_route_state()
                route_state.increment_feedback_counter()
                
                from somabrain import metrics
                metrics.record_learning_feedback_applied(tenant_id)
            except Exception:
                pass
        
        # Record latency
        elapsed = time.perf_counter() - start_time
        
        return {
            "accepted": True,
            "adaptation_applied": applied,
            "elapsed_ms": round(elapsed * 1000, 2),
        }
    except Exception as exc:
        raise HttpError(500, f"Feedback processing failed: {exc}")


@router.get("/adaptation/state", auth=bearer_auth)
def adaptation_state_endpoint(request: HttpRequest, tenant_id: Optional[str] = None):
    """Get current adaptation weights and learning state."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    target_tenant = tenant_id or ctx.tenant_id
    
    try:
        from somabrain.context.factory import get_context_builder, get_context_planner
        from somabrain.api.context_state import get_context_route_state
        
        builder = get_context_builder()
        planner = get_context_planner()
        
        def _get_adaptation(builder, planner, tenant_id):
            """Execute get adaptation.

                Args:
                    builder: The builder.
                    planner: The planner.
                    tenant_id: The tenant_id.
                """

            return get_context_route_state().get_adaptation_engine(builder, planner, tenant_id)
        
        adapter = _get_adaptation(builder, planner, tenant_id=target_tenant)
        route_state = get_context_route_state()
        
        return {
            "tenant_id": target_tenant,
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
            "history_len": route_state.feedback_counter,
            "learning_rate": getattr(adapter, "_lr", 0.0),
        }
    except Exception as exc:
        raise HttpError(500, f"Failed to get adaptation state: {exc}")


@router.post("/adaptation/reset", auth=bearer_auth)
def adaptation_reset_endpoint(request: HttpRequest, payload: dict):
    """Reset adaptation engine to defaults (dev mode only)."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    # Gate to dev mode only
    if getattr(settings, "MODE_NORMALIZED", "prod") != "dev":
        raise HttpError(403, "Adaptation reset not allowed outside dev mode")
    
    tenant_id = payload.get("tenant_id") or ctx.tenant_id
    
    try:
        from somabrain.context.factory import get_context_builder, get_context_planner
        from somabrain.api.context_state import get_context_route_state
        
        builder = get_context_builder()
        planner = get_context_planner()
       
        def _get_adaptation(builder, planner, tenant_id):
            """Execute get adaptation.

                Args:
                    builder: The builder.
                    planner: The planner.
                    tenant_id: The tenant_id.
                """

            return get_context_route_state().get_adaptation_engine(builder, planner, tenant_id)
        
        adapter = _get_adaptation(builder, planner, tenant_id=tenant_id)
        adapter.reset(clear_history=payload.get("reset_history", True))
        
        # Reset counter
        get_context_route_state().feedback_counter = 0
        
        logger.info(f"Adaptation reset for tenant {tenant_id}")
        
        return {"ok": True, "tenant_id": tenant_id}
    except Exception as exc:
        raise HttpError(500, f"Adaptation reset failed: {exc}")