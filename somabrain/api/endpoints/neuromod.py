"""Neuromod Router - Django Ninja Version

Neuromodulator management endpoints.

Boundary rule (DEBT-003): every value written through this API is validated
against ``somabrain.math.contracts.NEURO_BOUNDS`` by
``somabrain.runtime.neuromodulators.checked_value``. Non-finite input and
out-of-box values are **rejected** (HTTP 422) — never silently stored.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError
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

_NEUROMOD_FIELDS = ("dopamine", "serotonin", "noradrenaline", "acetylcholine")


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

    values = _state_values(ctx.tenant_id)

    return {
        "tenant_id": ctx.tenant_id,
        **values,
    }


@router.post("/adjust", auth=api_key_auth)
def adjust_neuromod(request: HttpRequest, body: NeuromodAdjustRequest):
    """Adjust neuromodulator values for tenant.

    Each provided field must be finite and inside the documented bounds
    (DA [0.2, 0.8], 5-HT [0, 1], NE [0, 0.1], ACh [0, 0.1]); otherwise the
    request is rejected with 422 and nothing is written.
    """
    from somabrain.runtime.neuromodulators import (
        NeuromodValueError,
        checked_value,
    )

    ctx = get_tenant(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    current = _state_values(ctx.tenant_id)
    for name in _NEUROMOD_FIELDS:
        val = getattr(body, name, None)
        if val is None:
            continue
        try:
            current[name] = checked_value(name, float(val))
        except NeuromodValueError as exc:
            raise HttpError(422, f"invalid neuromodulator value: {exc}") from exc

    from somabrain.bootstrap.singletons import get_neuromodulators
    from somabrain.runtime.neuromodulators import NeuromodState

    store = get_neuromodulators()
    store.set_state(ctx.tenant_id, NeuromodState(**current))
    logger.info("Neuromod adjusted for %s", ctx.tenant_id)

    return {
        "tenant_id": ctx.tenant_id,
        **current,
    }
