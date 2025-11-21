from somabrain.sleep import SleepState
from somabrain.sleep.cb_adapter import map_cb_to_sleep
from somabrain.infrastructure.circuit_breaker import CircuitBreaker


def test_cb_open_maps_freeze():
    cb = CircuitBreaker()
    tenant = "t1"
    cb.record_failure(tenant)
    cb.record_failure(tenant)
    cb.record_failure(tenant)  # opens
    assert cb.is_open(tenant)
    assert map_cb_to_sleep(cb, tenant, SleepState.ACTIVE) == SleepState.FREEZE


def test_cb_reset_attempt_maps_light():
    cb = CircuitBreaker(global_failure_threshold=1, global_reset_interval=0.0)
    tenant = "t1"
    cb.record_failure(tenant)
    assert cb.is_open(tenant)
    # Force last failure time far in the past so reset is allowed immediately
    cb._last_failure_time[tenant] = 0.0
    # should attempt reset immediately
    assert map_cb_to_sleep(cb, tenant, SleepState.ACTIVE) == SleepState.LIGHT
