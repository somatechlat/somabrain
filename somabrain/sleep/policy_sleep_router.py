"""Cognitive Sleep Policy API router.

Provides ``POST /api/brain/sleep_policy`` which mirrors the functionality of
``/api/brain/sleep_mode`` but is intended for higher‑level policy‑driven
control. The implementation re‑uses the same validation, OPA enforcement,
database persistence, and metric updates as ``brain_sleep_router``.

The request payload is defined by ``SleepRequest`` (same as the util and brain
endpoints). The endpoint updates the tenant's ``TenantSleepState`` record and
sets an optional TTL for auto‑wake. The gauge ``somabrain_sleep_state`` is
updated to reflect the new state.
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from somabrain.api.dependencies.auth import require_auth
from somabrain import metrics as M
from somabrain.app import cfg
from somabrain.tenant import get_tenant as get_tenant_async
from somabrain.opa.client import opa_client
from somabrain.sleep import SleepState, SleepStateManager
from somabrain.sleep.models import TenantSleepState
from somabrain.storage.db import get_session_factory
from somabrain.metrics import get_gauge
from somabrain.api.schemas.sleep import SleepRequest
from somabrain.infrastructure.cb_registry import get_cb
from somabrain.sleep.cb_adapter import map_cb_to_sleep

router = APIRouter()

_STATE_TO_INT: Dict[str, int] = {
    "active": 0,
    "light": 1,
    "deep": 2,
    "freeze": 3,
}

_sleep_state_gauge = get_gauge(
    "somabrain_sleep_state",
    "Current sleep state per tenant (0=active,1=light,2=deep,3=freeze)",
    labelnames=["tenant", "state"],
)

_RATE_LIMIT_PATH = "/api/brain/sleep_policy"
_rate_limiter: Any | None = None


def _get_rate_limiter() -> Any:
    global _rate_limiter
    if _rate_limiter is None:
        # Delay importing the app module until runtime to avoid circular imports
        from somabrain.app import rate_limiter as global_rate_limiter

        _rate_limiter = global_rate_limiter
    return _rate_limiter


@router.post("/api/brain/sleep_policy")
async def brain_sleep_policy(request: Request, body: SleepRequest) -> Dict[str, Any]:
    """Policy‑level sleep state transition.

    The semantics are identical to ``brain_sleep`` – the endpoint exists to
    provide a distinct URL for policy‑driven automation tools.
    """
    # Authentication
    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)
    tenant_id = ctx.tenant_id

    # Tenant-level rate limiting (shared bucket defined in somabrain.app).
    rate_limiter = _get_rate_limiter()
    if not rate_limiter.allow(tenant_id):
        try:
            M.RATE_LIMITED_TOTAL.labels(path=_RATE_LIMIT_PATH).inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    # OPA policy enforcement – reuse generic payload shape.
    opa_input = {
        "method": request.method,
        "path": request.url.path,
        "tenant_id": tenant_id,
        "action": "cognitive_sleep_policy",
        "target_state": body.target_state.value,
    }
    if not opa_client.evaluate(opa_input):
        raise HTTPException(status_code=403, detail="OPA policy denied cognitive sleep policy request")

    manager = SleepStateManager()
    cb = get_cb()
    target_state = SleepState[body.target_state.name]
    Session = get_session_factory()
    with Session() as session:
        ss: TenantSleepState | None = session.get(TenantSleepState, tenant_id)
        if ss is None:
            ss = TenantSleepState(
                tenant_id=tenant_id,
                current_state=SleepState.ACTIVE.value,
                target_state=SleepState.ACTIVE.value,
            )
            session.add(ss)
            session.commit()
        current_state = SleepState(ss.current_state.upper())
        # CB‑driven override
        current_state = map_cb_to_sleep(cb, tenant_id, current_state)
        if not manager.can_transition(current_state, target_state):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition from {current_state.value} to {target_state.value}",
            )
        # Persist state
        ss.current_state = target_state.value
        ss.target_state = target_state.value
        if body.ttl_seconds is not None:
            ttl_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=body.ttl_seconds)
            ss.ttl = ttl_dt
            ss.scheduled_wake = ttl_dt
        else:
            ss.ttl = None
            ss.scheduled_wake = None
        ss.updated_at = datetime.datetime.utcnow()
        session.add(ss)
        session.commit()

    # Update gauge
    state_int = _STATE_TO_INT.get(target_state.value, 0)
    _sleep_state_gauge.labels(tenant=tenant_id, state=str(state_int)).set(1)
    return {"ok": True, "tenant": tenant_id, "new_state": target_state.value}

# ---------------------------------------------------------------------------
# Background TTL auto‑wake task – reuse the same implementation as the brain
# router to ensure consistency across both endpoints.
# ---------------------------------------------------------------------------
_ttl_watcher_task: asyncio.Task | None = None


async def _ttl_watcher_loop(poll_seconds: float = 30.0) -> None:
    Session = get_session_factory()
    while True:
        try:
            now = datetime.datetime.utcnow()
            with Session() as session:
                expired = (
                    session.query(TenantSleepState)
                    .filter(TenantSleepState.ttl.is_not(None))
                    .filter(TenantSleepState.ttl <= now)
                    .all()
                )
                for row in expired:
                    row.current_state = SleepState.ACTIVE.value
                    row.target_state = SleepState.ACTIVE.value
                    row.ttl = None
                    row.scheduled_wake = None
                    row.updated_at = now
                    _sleep_state_gauge.labels(tenant=row.tenant_id, state="0").set(1)
                if expired:
                    session.commit()
        except Exception as exc:  # pragma: no cover – defensive logging
            import logging

            logging.getLogger(__name__).error("Error in TTL watcher (policy router): %s", exc)
        await asyncio.sleep(poll_seconds)


def start_ttl_watcher(poll_seconds: float = 30.0) -> None:
    """Start the background TTL watcher if not already running.

    The function is idempotent – calling it multiple times will not spawn
    duplicate tasks.
    """
    global _ttl_watcher_task
    if _ttl_watcher_task is None or _ttl_watcher_task.done():
        _ttl_watcher_task = asyncio.create_task(_ttl_watcher_loop(poll_seconds))
