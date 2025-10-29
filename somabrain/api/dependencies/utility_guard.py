from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request

from somabrain import metrics as M
from somabrain.constitution import ConstitutionEngine


def compute_utility(
    p_confidence: float, cost: float, latency: float, const_params: dict
) -> float:
    # default params fallback
    lam = const_params.get("lambda", const_params.get("lam", 1.0))
    mu = const_params.get("mu", 0.0)
    nu = const_params.get("nu", 0.0)
    import math

    return (
        lam * math.log(max(1e-12, p_confidence))
        - mu * float(cost)
        - nu * float(latency)
    )


def _get_constitution_engine(request: Request) -> Optional[ConstitutionEngine]:
    return getattr(request.app.state, "constitution_engine", None)


async def utility_guard(
    request: Request,
    engine: Optional[ConstitutionEngine] = Depends(_get_constitution_engine),
) -> None:
    """FastAPI dependency: compute U(r) and raise HTTPException if negative.

    This dependency expects the route handler to provide model confidence via
    request.state.model_confidence (float) or a header X-Model-Confidence.
    It is intentionally conservative and non-raising on missing constitution.
    """
    eng: Optional[ConstitutionEngine] = engine
    # If no constitution engine is available or not loaded, act as a no-op guard.
    # This matches the docstring promise: non-raising on missing constitution.
    try:
        has_const = bool(eng and eng.get_constitution())
    except Exception:
        has_const = False
    if not has_const:
        # Attach a neutral utility value for observability and allow the request.
        try:
            request.state.utility_value = 0.0
            M.UTILITY_VALUE.set(0.0)
        except Exception:
            pass
        return

    # extract confidence/cost/latency from request (middleware or handler should set these)
    conf = getattr(request.state, "model_confidence", None)
    if conf is None:
        try:
            conf = float(request.headers.get("X-Model-Confidence", "0"))
        except Exception:
            conf = 0.0
    cost = float(getattr(request.state, "estimated_cost", 0.0))
    latency = float(getattr(request.state, "estimated_latency", 0.0))

    params = {}
    try:
        params = eng.get_constitution().get("utility_params", {}) if eng else {}
    except Exception:
        params = {}

    u = compute_utility(conf, cost, latency, params)
    # attach for handler and metrics
    request.state.utility_value = u
    try:
        M.UTILITY_VALUE.set(u)
    except Exception:
        pass
    if u < 0:
        try:
            M.UTILITY_NEGATIVE.inc()
        except Exception:
            pass
        # do not perform side effects; the route can choose to inspect this and return 403
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Rejected by utility guard")
