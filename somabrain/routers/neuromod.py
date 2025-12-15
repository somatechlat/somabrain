"""Neuromodulator Router
=======================

Endpoints for getting and setting neuromodulator state.
Neuromodulators (dopamine, serotonin, noradrenaline, acetylcholine) influence
cognitive processing and memory retrieval.

Endpoints:
- GET /neuromodulators - Get current neuromodulator state
- POST /neuromodulators - Set neuromodulator state (admin only)
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request

from common.config.settings import settings
from somabrain import audit, schemas as S
from somabrain.auth import require_auth, require_admin_auth
from somabrain.neuromodulators import NeuromodState, PerTenantNeuromodulators
from somabrain.tenant import get_tenant as get_tenant_async

logger = logging.getLogger(__name__)

router = APIRouter(tags=["neuromodulators"])

# Singleton instance
_per_tenant_neuromods = PerTenantNeuromodulators()


def _get_app_config():
    """Get app-level configuration."""
    try:
        from somabrain import runtime as rt

        return getattr(rt, "cfg", settings)
    except Exception:
        return settings


def _clamp(val: float, lo: float, hi: float) -> float:
    """Clamp a value to the given range."""
    return max(lo, min(hi, float(val)))


@router.get("/neuromodulators", response_model=S.NeuromodStateModel)
async def get_neuromodulators(request: Request):
    """Get current neuromodulator state for the tenant."""
    cfg = _get_app_config()
    require_auth(request, cfg)

    try:
        audit.log_admin_action(request, "neuromodulators_read")
    except Exception:
        pass

    tenant_ctx = await get_tenant_async(request, cfg.namespace)
    state = _per_tenant_neuromods.get_state(tenant_ctx.tenant_id)

    return S.NeuromodStateModel(
        dopamine=state.dopamine,
        serotonin=state.serotonin,
        noradrenaline=state.noradrenaline,
        acetylcholine=state.acetylcholine,
    )


@router.post("/neuromodulators", response_model=S.NeuromodStateModel)
async def set_neuromodulators(body: S.NeuromodStateModel, request: Request):
    """Set neuromodulator state (admin only).

    Values are clamped to physiologically plausible ranges:
    - dopamine: [0.0, 0.8]
    - serotonin: [0.0, 1.0]
    - noradrenaline: [0.0, 0.1]
    - acetylcholine: [0.0, 0.5]
    """
    cfg = _get_app_config()
    require_admin_auth(request, cfg)

    new_state = NeuromodState(
        dopamine=_clamp(body.dopamine, 0.0, 0.8),
        serotonin=_clamp(body.serotonin, 0.0, 1.0),
        noradrenaline=_clamp(body.noradrenaline, 0.0, 0.1),
        acetylcholine=_clamp(body.acetylcholine, 0.0, 0.5),
        timestamp=time.time(),
    )

    tenant_ctx = await get_tenant_async(request, cfg.namespace)
    _per_tenant_neuromods.set_state(tenant_ctx.tenant_id, new_state)

    try:
        audit.log_admin_action(
            request,
            "neuromodulators_set",
            {
                "tenant": tenant_ctx.tenant_id,
                "new_state": {
                    "dopamine": new_state.dopamine,
                    "serotonin": new_state.serotonin,
                    "noradrenaline": new_state.noradrenaline,
                    "acetylcholine": new_state.acetylcholine,
                },
            },
        )
    except Exception:
        pass

    return S.NeuromodStateModel(
        dopamine=new_state.dopamine,
        serotonin=new_state.serotonin,
        noradrenaline=new_state.noradrenaline,
        acetylcholine=new_state.acetylcholine,
    )
