"""Module utility_guard."""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest
from ninja.errors import HttpError
from django.conf import settings

from somabrain import metrics as M
from somabrain.constitution import ConstitutionEngine


def compute_utility(
    p_confidence: float, cost: float, latency: float, const_params: dict
) -> float:
    # default params
    """Execute compute utility.

    Args:
        p_confidence: The p_confidence.
        cost: The cost.
        latency: The latency.
        const_params: The const_params.
    """

    lam = const_params.get("lambda", const_params.get("lam", 1.0))
    mu = const_params.get("mu", 0.0)
    nu = const_params.get("nu", 0.0)
    import math

    return (
        lam * math.log(max(1e-12, p_confidence))
        - mu * float(cost)
        - nu * float(latency)
    )


def _get_constitution_engine() -> Optional[ConstitutionEngine]:
    """Get the ConstitutionEngine singleton."""
    try:
        from somabrain.app import app

        return getattr(app.state, "constitution_engine", None)
    except Exception:
        return None


async def utility_guard(request: HttpRequest) -> None:
    """Compute U(r) and raise HttpError if negative.

    This guard expects the route handler or middleware to provide model confidence.
    """
    engine = _get_constitution_engine()

    # Determine mode; in dev, relax strict constitution requirement
    dev_mode = False
    try:
        if settings is not None:
            dev_mode = getattr(settings, "mode_normalized", "prod") == "dev"
    except Exception:
        dev_mode = False

    # Enforce presence of a loaded constitution engine; fail-closed outside dev.
    try:
        has_const = bool(engine and engine.get_constitution())
    except Exception:
        has_const = False
    if not has_const and not dev_mode:
        raise HttpError(503, "constitution engine unavailable")

    # extract confidence/cost/latency from request
    # Check request.state (if present) or headers
    state = getattr(request, "state", None)

    conf = getattr(state, "model_confidence", None) if state else None
    if conf is None:
        try:
            conf = float(request.headers.get("X-Model-Confidence", "0"))
        except Exception:
            conf = 0.0

    cost = float(getattr(state, "estimated_cost", 0.0)) if state else 0.0
    latency = float(getattr(state, "estimated_latency", 0.0)) if state else 0.0

    params = {}
    try:
        if engine and engine.get_constitution():
            params = engine.get_constitution().get("utility_params", {})
    except Exception:
        params = {}

    u = compute_utility(conf, cost, latency, params)

    # attach for handler
    if state:
        state.utility_value = u
    else:
        # Fallback if no state container
        setattr(request, "utility_value", u)

    try:
        M.UTILITY_VALUE.set(u)
    except Exception:
        pass

    # In dev mode, be permissive
    if u < 0 and not dev_mode:
        try:
            M.UTILITY_NEGATIVE.inc()
        except Exception:
            pass
        raise HttpError(403, "Rejected by utility guard")

    # In dev mode, normalize
    if dev_mode and u < 0:
        if state:
            state.utility_value = 0.0
        else:
            setattr(request, "utility_value", 0.0)
