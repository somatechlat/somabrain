"""Circuit-breaker to sleep-state mapping utilities."""

from __future__ import annotations

from somabrain.sleep import SleepState
from typing import Dict

# Simple hysteresis cache to avoid flapping between states
_LAST_STATE: Dict[str, SleepState] = {}


def map_cb_to_sleep(cb, tenant_id: str, current: SleepState) -> SleepState:
    """Map circuit-breaker status to sleep state with light hysteresis.

    - Open -> FREEZE
    - Reset attempt (should_attempt_reset) -> LIGHT
    - Closed -> ACTIVE
    Retains previous state if checks fail to avoid jitter.
    """
    try:
        if cb.is_open(tenant_id):
            nxt = (
                SleepState.LIGHT
                if cb.should_attempt_reset(tenant_id)
                else SleepState.FREEZE
            )
        else:
            nxt = (
                SleepState.LIGHT
                if cb.should_attempt_reset(tenant_id)
                else SleepState.ACTIVE
            )
    except Exception:
        nxt = _LAST_STATE.get(tenant_id, current)
    _LAST_STATE[tenant_id] = nxt
    return nxt