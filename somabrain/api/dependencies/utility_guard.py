from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request

from somabrain import metrics as M
from somabrain.constitution import ConstitutionEngine

# Centralized settings for mode-aware behavior
from common.config.settings import settings  # type: ignore


def compute_utility(
    p_confidence: float, cost: float, latency: float, const_params: dict
) -> float:
    # default params
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
    # Determine mode; in dev, relax strict constitution requirement (no mocks otherwise)
    dev_mode = False
    try:
        if settings is not None:
            dev_mode = getattr(settings, "mode_normalized", "prod") == "dev"
        else:

            dev_mode = _settings.mode.strip().lower() in (
                "dev",
                "development",
            )
    except Exception:
        dev_mode = False

    # Enforce presence of a loaded constitution engine; fail-closed outside dev.
    try:
        has_const = bool(eng and eng.get_constitution())
    except Exception:
        has_const = False
    if not has_const and not dev_mode:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="constitution engine unavailable")

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
    # In dev mode, be permissive: allow negative utility or missing confidence.
    if u < 0 and not dev_mode:
        try:
            M.UTILITY_NEGATIVE.inc()
        except Exception:
            pass
        # do not perform side effects; the route can choose to inspect this and return 403
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Rejected by utility guard")

    # In dev mode, normalize extremely negative values to 0 to avoid confusing downstreams
    if dev_mode and u < 0:
        request.state.utility_value = 0.0
