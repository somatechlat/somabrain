"""Circuit-breaker to sleep-state mapping utilities."""

from __future__ import annotations

from somabrain.sleep import SleepState


def map_cb_to_sleep(cb, tenant_id: str, current: SleepState) -> SleepState:
    """Map circuit-breaker status to sleep state.

    - Open -> FREEZE
    - Reset attempt (should_attempt_reset) -> LIGHT
    - Otherwise keep current
    """
    try:
        if cb.is_open(tenant_id):
            if cb.should_attempt_reset(tenant_id):
                return SleepState.LIGHT
            return SleepState.FREEZE
        if cb.should_attempt_reset(tenant_id):
            return SleepState.LIGHT
    except Exception as exc: raise
    return current
