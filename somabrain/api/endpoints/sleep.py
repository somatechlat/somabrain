"""Sleep Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Sleep state management endpoints with OPA, TTL, and Rate Limiting.
Combines functionality from:
- brain_sleep_router.py
- util_sleep_router.py
- policy_sleep_router.py
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from somabrain import metrics as M
from somabrain.api.auth import api_key_auth
from somabrain.auth import require_auth
from somabrain.infrastructure.cb_registry import get_cb
from somabrain.opa.client import opa_client
from somabrain.sleep import SleepState, SleepStateManager
from somabrain.sleep.cb_adapter import map_cb_to_sleep
from somabrain.sleep.models import TenantSleepState
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.sleep")

router = Router(tags=["sleep"])

# Helper to get sleep manager singleton
_sleep_manager: SleepStateManager = None


def _get_sleep_manager():
    """Execute get sleep manager."""

    global _sleep_manager
    if _sleep_manager is None:
        _sleep_manager = SleepStateManager()
    return _sleep_manager


# Real rate limiter using Django cache
# VIBE RULES: NO mocks, NO stubs - real implementations only
def _check_rate_limit(tenant_id: str, path: str):
    """Real rate limit check using Django cache."""
    from django.core.cache import cache

    # Rate limit: 100 requests per minute per tenant
    cache_key = f"ratelimit:{tenant_id}:{path}"
    current = cache.get(cache_key, 0)

    if current >= 100:
        M.RATE_LIMITED_TOTAL.labels(path=path).inc()
        raise HttpError(429, "rate limit exceeded")

    # Increment counter with 60 second expiry
    cache.set(cache_key, current + 1, timeout=60)


@router.get("/state", auth=api_key_auth)
def get_sleep_state(request: HttpRequest):
    """Get current sleep state for tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    try:
        state = TenantSleepState.objects.get(tenant_id=ctx.tenant_id)
        current_state = state.current_state
        timestamp = state.last_transition
    except TenantSleepState.DoesNotExist:
        current_state = "active"
        timestamp = None

    return {
        "tenant_id": ctx.tenant_id,
        "state": current_state,
        "timestamp": timestamp,
    }


def _process_sleep_transition(
    request: HttpRequest,
    mode: str,
    target_state_str: str,
    ttl_seconds: Optional[int] = None,
    trace_id: Optional[str] = None,
):
    """Execute process sleep transition.

    Args:
        request: The request.
        mode: The mode.
        target_state_str: The target_state_str.
        ttl_seconds: The ttl_seconds.
        trace_id: The trace_id.
    """

    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    tenant_id = ctx.tenant_id

    # Rate Limit
    _check_rate_limit(tenant_id, request.path)

    # OPA Check
    action_map = {
        "brain": "cognitive_sleep",
        "util": "sleep",
        "policy": "cognitive_sleep_policy",
    }
    opa_input = {
        "method": request.method,
        "path": request.path,
        "tenant_id": tenant_id,
        "action": action_map.get(mode, "sleep"),
        "target_state": target_state_str,
        "max_seconds": getattr(settings, "SLEEP_MAX_SECONDS", 3600),
    }
    if not opa_client.evaluate(opa_input):
        raise HttpError(403, "OPA policy denied sleep request")

    # Enum conversion
    try:
        target_state = SleepState[target_state_str.upper()]
    except KeyError:
        raise HttpError(400, f"Invalid sleep state: {target_state_str}")

    # Logic
    manager = _get_sleep_manager()
    cb = get_cb()

    # DB Transaction
    ss, created = TenantSleepState.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={
            "current_state": SleepState.ACTIVE.value,
            "target_state": SleepState.ACTIVE.value,
        },
    )

    current_state_enum = SleepState(ss.current_state.lower())
    # CB mapping
    current_state_enum = map_cb_to_sleep(cb, tenant_id, current_state_enum)

    if not manager.can_transition(current_state_enum, target_state):
        raise HttpError(
            400,
            f"Invalid transition from {current_state_enum.value} to {target_state.value}",
        )

    # Validation TTL
    max_sec = getattr(settings, "SLEEP_MAX_SECONDS", 3600)
    if ttl_seconds is not None and ttl_seconds > max_sec:
        raise HttpError(400, f"ttl_seconds exceeds maximum of {max_sec}")

    # Update
    ss.current_state = target_state.value
    ss.target_state = target_state.value

    if ttl_seconds is not None:
        ss.ttl = timezone.now() + datetime.timedelta(seconds=ttl_seconds)
        ss.scheduled_wake = ss.ttl
    else:
        ss.ttl = None
        ss.scheduled_wake = None

    ss.save()

    logger.info(
        f"Sleep transition ({mode}) for {tenant_id}: {current_state_enum.value} -> {target_state.value}"
    )

    return {"ok": True, "tenant": tenant_id, "new_state": target_state.value}


@router.post("/brain/mode", auth=api_key_auth)
def brain_sleep_mode(request: HttpRequest, payload: dict):
    """Cognitive-level sleep state transition (Brain)."""
    return _process_sleep_transition(
        request,
        mode="brain",
        target_state_str=payload.get("target_state", "active"),
        ttl_seconds=payload.get("ttl_seconds"),
        trace_id=payload.get("trace_id"),
    )


@router.post("/util/mode", auth=api_key_auth)
def util_sleep_mode(request: HttpRequest, payload: dict):
    """Utility sleep state transition (Util)."""
    return _process_sleep_transition(
        request,
        mode="util",
        target_state_str=payload.get("target_state", "active"),
        ttl_seconds=payload.get("ttl_seconds"),
        trace_id=payload.get("trace_id"),
    )


@router.post("/policy/mode", auth=api_key_auth)
def policy_sleep_mode(request: HttpRequest, payload: dict):
    """Policy-driven sleep state transition."""
    return _process_sleep_transition(
        request,
        mode="policy",
        target_state_str=payload.get("target_state", "active"),
        ttl_seconds=payload.get("ttl_seconds"),
        trace_id=payload.get("trace_id"),
    )


# Retaining generic /state and /transition for backward compat or unified access
@router.post("/state", auth=api_key_auth)
def set_sleep_state(request: HttpRequest, payload: dict):
    """Set sleep state (Generic)."""
    # Map to brain mode for generic setting?
    return _process_sleep_transition(
        request, mode="util", target_state_str=payload.get("state", "active")
    )


@router.post("/transition", auth=api_key_auth)
def transition_sleep_state(request: HttpRequest, payload: dict):
    """Transition based on trigger."""
    # This logic was: manager.transition(trigger)
    # We should probably implement it similarly or map trigger to state
    # For now, sticking to state-based for the upgraded parts.
    # Legacy 'transition' endpoint might need the trigger logic
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    manager = _get_sleep_manager()
    trigger = payload.get("trigger", "manual")
    new_state = manager.transition(ctx.tenant_id, trigger)

    # We need to persist this new state
    # Calling internal process? No, manager.transition might just return calculated state
    # We should persist it.

    # Persist
    ss, _ = TenantSleepState.objects.get_or_create(tenant_id=ctx.tenant_id)
    ss.current_state = new_state.name.lower()
    ss.target_state = new_state.name.lower()
    ss.save()

    return {
        "tenant_id": ctx.tenant_id,
        "state": new_state.name,
        "timestamp": timezone.now(),
    }
