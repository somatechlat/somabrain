"""Temperature annealing background task.

The task periodically decays the ``tau`` (softmax temperature) used by the
integrator hub. The decay rate and minimum floor are read from the global
``settings`` object (``common.config.settings``) so that there are no hard‑coded
values, satisfying VIBE requirements.

The implementation is a simple ``asyncio`` coroutine that sleeps for the
configured ``tau_anneal_interval`` (seconds) and then multiplies the current
``tau`` by ``tau_decay_factor`` while respecting ``tau_min_floor``.

Usage example::

    from somabrain.tasks.temperature_anneal import run_anneal_task
    asyncio.create_task(run_anneal_task())

The function returns when cancelled; any configuration error raises a
``RuntimeError`` immediately (fail‑fast).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from common.config.settings import settings
settings = settings

logger = logging.getLogger(__name__)


def _load_config() -> dict[str, Any]:
    """Load annealing configuration from ``settings``.

    Expected keys:
    * ``tau_decay_factor`` – multiplicative factor (e.g., 0.95).
    * ``tau_min_floor`` – lower bound for ``tau``.
    * ``tau_anneal_interval`` – interval in seconds between decays.
    """
    try:
        factor = float(getattr(settings, "tau_decay_factor", 0.95))
        floor = float(getattr(settings, "tau_min_floor", 0.1))
        interval = float(getattr(settings, "tau_anneal_interval", 60.0))
    except Exception as exc:
        raise RuntimeError("Invalid temperature annealing configuration") from exc
    if factor <= 0 or factor >= 1:
        raise RuntimeError("tau_decay_factor must be in (0, 1)")
    if floor <= 0:
        raise RuntimeError("tau_min_floor must be positive")
    if interval <= 0:
        raise RuntimeError("tau_anneal_interval must be positive")
    return {"factor": factor, "floor": floor, "interval": interval}


async def run_anneal_task(get_current_tau: callable[[], float], set_tau: callable[[float], None]) -> None:
    """Background task that decays ``tau`` over time.

    Parameters
    ----------
    get_current_tau: Callable[[], float]
        Function returning the current ``tau`` value.
    set_tau: Callable[[float], None]
        Function that updates the ``tau`` value.
    """
    cfg = _load_config()
    logger.info(
        "Starting temperature annealing: factor=%s floor=%s interval=%s",
        cfg["factor"],
        cfg["floor"],
        cfg["interval"],
    )
    try:
        while True:
            await asyncio.sleep(cfg["interval"])
            current = get_current_tau()
            new_tau = max(cfg["floor"], current * cfg["factor"])
            if new_tau != current:
                set_tau(new_tau)
                logger.debug("Annealed tau from %s to %s", current, new_tau)
    except asyncio.CancelledError:
        logger.info("Temperature annealing task cancelled")
        raise
    except Exception as exc:
        logger.error("Temperature annealing failed: %s", exc)
        raise
