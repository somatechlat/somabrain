from __future__ import annotations
from typing import Optional
from fastapi import Depends, Request
from somabrain import metrics as M
from somabrain.constitution import ConstitutionEngine
from common.config.settings import settings  # type: ignore
from common.logging import logger
import math
from fastapi import HTTPException
from fastapi import HTTPException




# Centralized settings for mode-aware behavior


def compute_utility(
    p_confidence: float, cost: float, latency: float, const_params: dict
) -> float:
    # default params
    lam = const_params.get("lambda", const_params.get("lam", 1.0))
    mu = const_params.get("mu", 0.0)
    nu = const_params.get("nu", 0.0)

    return (
        lam * math.log(max(1e-12, p_confidence))
        - mu * float(cost)
        - nu * float(latency)
    )


def _get_constitution_engine(request: Request) -> Optional[ConstitutionEngine]:
    return getattr(request.app.state, "constitution_engine", None)


async def utility_guard(
    request: Request,
    engine: Optional[ConstitutionEngine] = Depends(_get_constitution_engine), ) -> None:
        pass
    """FastAPI dependency: compute U(r) and raise HTTPException if negative.

    This dependency expects the route handler to provide model confidence via
    request.state.model_confidence (float) or a header X-Model-Confidence.
    It is intentionally conservative and non-raising on missing constitution.
    """
    eng: Optional[ConstitutionEngine] = engine
    # Determine mode; in dev, relax strict constitution requirement (no mocks otherwise)
    dev_mode = False
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        if settings is not None:
            dev_mode = getattr(settings, "mode_normalized", "prod") == "dev"
        else:
            pass

            dev_mode = _settings.mode.strip().lower() in (
                "dev",
                "development", )
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        dev_mode = False

    # Enforce presence of a loaded constitution engine; fail-closed outside dev.
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        has_const = bool(eng and eng.get_constitution())
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        has_const = False
    if not has_const and not dev_mode:
        pass

        raise HTTPException(status_code=503, detail="constitution engine unavailable")

    # extract confidence/cost/latency from request (middleware or handler should set these)
    conf = getattr(request.state, "model_confidence", None)
    if conf is None:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            conf = float(request.headers.get("X-Model-Confidence", "0"))
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            conf = 0.0
    cost = float(getattr(request.state, "estimated_cost", 0.0))
    latency = float(getattr(request.state, "estimated_latency", 0.0))

    params = {}
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        params = eng.get_constitution().get("utility_params", {}) if eng else {}
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        params = {}

    u = compute_utility(conf, cost, latency, params)
    # attach for handler and metrics
    request.state.utility_value = u
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        M.UTILITY_VALUE.set(u)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    raise
    if u < 0 and not dev_mode:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            M.UTILITY_NEGATIVE.inc()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise

        raise HTTPException(status_code=403, detail="Rejected by utility guard")

    # In dev mode, normalize extremely negative values to 0 to avoid confusing downstreams
    if dev_mode and u < 0:
        request.state.utility_value = 0.0
