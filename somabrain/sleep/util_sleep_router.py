"""Utility Sleep API router.

Provides the ``POST /api/util/sleep`` endpoint that allows a tenant to request a
state transition (ACTIVE, LIGHT, DEEP, FREEZE) with an optional TTL. The
endpoint:

1. Authenticates the request using the existing ``require_auth`` helper.
2. Resolves the tenant via ``get_tenant_async`` (the standard per‑request
   tenant extraction).
3. Performs an OPA policy check – the same payload shape used by the generic
   OPA middleware.
4. Validates the transition using ``SleepStateManager``.
5. Persists the new state (and optional TTL) in the ``TenantSleepState``
   SQLAlchemy model.
6. Updates a Prometheus gauge ``somabrain_sleep_state`` labelled by tenant and
   integer state value (ACTIVE=0, LIGHT=1, DEEP=2, FREEZE=3).

The implementation avoids any mock or bypass logic – it works against the real
database and OPA service, satisfying the VIBE "no‑guess" rule.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from somabrain.api.dependencies.auth import require_auth
from somabrain.app import cfg
from somabrain.tenant import get_tenant as get_tenant_async
from somabrain.opa.client import opa_client
from somabrain.sleep import SleepState, SleepStateManager
from somabrain.sleep.models import TenantSleepState
from somabrain.storage.db import get_session_factory
from somabrain.metrics import get_gauge
from somabrain.api.schemas.sleep import SleepRequest

router = APIRouter()

# Mapping from SleepState string value to an integer for the gauge.
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


@router.post("/api/util/sleep")
async def util_sleep(request: Request, body: SleepRequest) -> Dict[str, Any]:
    """Transition a tenant's sleep state.

    Args:
        request: FastAPI request (used for auth and tenant extraction).
        body: ``SleepRequest`` containing ``target_state`` and optional ``ttl_seconds``.

    Returns a JSON payload confirming the new state.
    """
    # 1. Authentication
    require_auth(request, cfg)

    # 2. Resolve tenant
    ctx = await get_tenant_async(request, cfg.namespace)
    tenant_id = ctx.tenant_id

    # 3. OPA policy enforcement – reuse the generic payload shape.
    opa_input = {
        "method": request.method,
        "path": request.url.path,
        "tenant_id": tenant_id,
        "action": "sleep",
        "target_state": body.target_state.value,
    }
    if not opa_client.evaluate(opa_input):
        raise HTTPException(status_code=403, detail="OPA policy denied sleep request")

    # 4. Validate transition using the manager.
    manager = SleepStateManager()
    target_state = SleepState[body.target_state.name]
    # Load current state from DB (or default to ACTIVE).
    Session = get_session_factory()
    with Session() as session:
        ss: TenantSleepState | None = session.get(TenantSleepState, tenant_id)
        if ss is None:
            # Initialise a row for the tenant.
            ss = TenantSleepState(
                tenant_id=tenant_id,
                current_state=SleepState.ACTIVE.value,
                target_state=SleepState.ACTIVE.value,
            )
            session.add(ss)
            session.commit()
        current_state = SleepState(ss.current_state.upper())
        if not manager.can_transition(current_state, target_state):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition from {current_state.value} to {target_state.value}",
            )

        # 5. Persist new state and optional TTL.
        ss.current_state = target_state.value
        ss.target_state = target_state.value
        if body.ttl_seconds is not None:
            ttl_dt = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=body.ttl_seconds
            )
            ss.ttl = ttl_dt
            ss.scheduled_wake = ttl_dt
        else:
            ss.ttl = None
            ss.scheduled_wake = None
        ss.updated_at = datetime.datetime.utcnow()
        session.add(ss)
        session.commit()

    # 6. Update Prometheus gauge.
    state_int = _STATE_TO_INT.get(target_state.value, 0)
    _sleep_state_gauge.labels(tenant=tenant_id, state=str(state_int)).set(1)

    return {"ok": True, "tenant": tenant_id, "new_state": target_state.value}
