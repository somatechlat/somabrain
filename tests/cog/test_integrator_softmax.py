from __future__ import annotations

import time

from somabrain.services.integrator_hub import SoftmaxIntegrator, DomainObs


def test_softmax_integrator_picks_highest_confidence() -> None:
    sm = SoftmaxIntegrator(tau=1.0, stale_seconds=5.0)
    now = time.time()
    # Three domains with different confidences
    sm.update("tenantA", "state", DomainObs(ts=now, confidence=0.6, delta_error=0.4))
    sm.update("tenantA", "agent", DomainObs(ts=now, confidence=0.2, delta_error=0.8))
    sm.update("tenantA", "action", DomainObs(ts=now, confidence=0.1, delta_error=0.9))

    leader, weights, raw = sm.snapshot("tenantA")
    assert leader == "state"
    assert set(weights.keys()) == {"state", "agent", "action"}
    # Softmax yields strictly highest for the largest input
    assert weights["state"] > weights["agent"] > weights["action"]


def test_softmax_integrator_stale_evictions() -> None:
    sm = SoftmaxIntegrator(tau=1.0, stale_seconds=0.01)
    sm.update("t", "state", DomainObs(ts=time.time() - 1.0, confidence=0.9, delta_error=0.1))
    leader, weights, raw = sm.snapshot("t")
    # No recent observations -> default leader
    assert leader == "state"
    assert weights["state"] == 1.0
