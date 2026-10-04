"""Neuromod Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Neuromodulator management endpoints.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from pydantic import BaseModel

from somabrain.api.auth import api_key_auth, require_auth
from somabrain.tenant import get_tenant_sync as get_tenant


class NeuromodAdjustRequest(BaseModel):
    dopamine: float | None = None
    serotonin: float | None = None
    noradrenaline: float | None = None
    acetylcholine: float | None = None


logger = logging.getLogger("somabrain.api.endpoints.neuromod")

router = Router(tags=["neuromod"])

def _state_values(tenant_id: str) -> dict:
    from somabrain.bootstrap.singletons import get_neuromodulators
    from somabrain.runtime.neuromodulators import NeuromodState

    state = get_neuromodulators().get_state(tenant_id)
    if not isinstance(state, NeuromodState):
        state = NeuromodState()
    return {
        "dopamine": float(state.dopamine),
        "serotonin": float(state.serotonin),
        "noradrenaline": float(state.noradrenaline),
        "acetylcholine": float(state.acetylcholine),
    }


@router.get("/state", auth=api_key_auth)
def get_neuromod_state(request: HttpRequest):
    """Get neuromodulator state for tenant."""
    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    try:
        values = _state_values(ctx.tenant_id)
    except Exception as exc:
        logger.warning("Failed to get neuromod state: %s", exc)
        values = _state_values(ctx.tenant_id)

    return {
        "tenant_id": ctx.tenant_id,
        **values,
    }


@router.post("/adjust", auth=api_key_auth)
def adjust_neuromod(request: HttpRequest, body: NeuromodAdjustRequest):
    """Adjust neuromodulator values for tenant."""
    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    try:
        from somabrain.bootstrap.singletons import get_neuromodulators
        from somabrain.runtime.neuromodulators import NeuromodState

        store = get_neuromodulators()
        current = _state_values(ctx.tenant_id)
        for name in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
            val = getattr(body, name, None)
            if val is not None:
                current[name] = float(val)
        store.set_state(ctx.tenant_id, NeuromodState(**current))
        values = current
        logger.info("Neuromod adjusted for %s", ctx.tenant_id)
    except Exception as exc:
        logger.error("Failed to adjust neuromod: %s", exc)
        values = _state_values(ctx.tenant_id)

    return {
        "tenant_id": ctx.tenant_id,
        **values,
    }
