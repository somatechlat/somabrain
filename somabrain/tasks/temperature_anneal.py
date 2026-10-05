"""Temperature annealing background task.

The task periodically decays the ``tau`` (softmax temperature) used by the
integrator hub.  The schedule constants (``TAU_DECAY_FACTOR``, ``TAU_FLOOR``,
``TAU_INTERVAL``) come from ``somabrain.math.contracts`` — the single
math-contract source (DEF-05/DEF-06 fixed: one set, no settings twins).

The implementation is a simple ``asyncio`` coroutine that sleeps for the
configured interval (seconds) and then multiplies the current ``tau`` by
the decay factor while respecting the floor.

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

from somabrain.math.contracts import TAU_DECAY_FACTOR, TAU_FLOOR, TAU_INTERVAL

logger = logging.getLogger(__name__)


def _load_config() -> dict[str, Any]:
    """Load annealing configuration from ``somabrain.math.contracts``.

    Returns keys:
    * ``factor`` – multiplicative decay factor (e.g., 0.95).
    * ``floor`` – lower bound for ``tau``.
    * ``interval`` – interval in seconds between decays.
    """
    factor = TAU_DECAY_FACTOR
    floor = TAU_FLOOR
    interval = TAU_INTERVAL
    if factor <= 0 or factor >= 1:
        raise RuntimeError("TAU_DECAY_FACTOR must be in (0, 1)")
    if floor <= 0:
        raise RuntimeError("TAU_FLOOR must be positive")
    if interval <= 0:
        raise RuntimeError("TAU_INTERVAL must be positive")
    return {"factor": factor, "floor": floor, "interval": interval}


async def run_anneal_task(
    get_current_tau: callable[[], float], set_tau: callable[[float], None]
) -> None:
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
