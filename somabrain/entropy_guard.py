"""Entropy guard utility.

The guard enforces the ``entropy_cap`` configuration defined in the global
``settings`` object (``common.config.settings``). When the observed entropy for a
candidate leader exceeds the cap, the guard signals that a leader change is
required.

VIBE compliance:
* No hard‑coded thresholds – the cap is read from ``settings``.
* Fail‑fast – if the configuration is missing the guard raises a clear error.
* Simple, pure‑Python implementation – easy to test and reason about.
"""

from __future__ import annotations

import logging
from typing import Optional

from common.config.settings import settings
shared_settings = settings

logger = logging.getLogger(__name__)


def get_entropy_cap() -> float:
    """Return the configured entropy cap.

    The ``entropy_cap`` setting must be defined in ``settings``; otherwise a
    ``RuntimeError`` is raised. This mirrors the VIBE rule of failing fast on
    missing configuration.
    """
    cap = getattr(shared_settings, "entropy_cap", None)
    if cap is None:
        raise RuntimeError(
            "Entropy cap is not configured. Set 'entropy_cap' in the settings."
        )
    try:
        return float(cap)
    except Exception as exc:
        raise RuntimeError(f"Invalid entropy_cap value: {cap}") from exc


def should_switch_leader(current_entropy: float, candidate: Optional[str] = None) -> bool:
    """Determine whether the leader should be switched.

    Parameters
    ----------
    current_entropy: float
        The entropy measured for the current leader.
    candidate: Optional[str]
        Identifier of a potential new leader (unused in the basic check but kept
        for future extensibility).

    Returns
    -------
    bool
        ``True`` if ``current_entropy`` exceeds the configured ``entropy_cap``.
    """
    cap = get_entropy_cap()
    if current_entropy > cap:
        logger.info(
            "Entropy %s exceeds cap %s – leader switch required.",
            current_entropy,
            cap,
        )
        return True
    logger.debug(
        "Entropy %s within cap %s – no leader change.", current_entropy, cap
    )
    return False
