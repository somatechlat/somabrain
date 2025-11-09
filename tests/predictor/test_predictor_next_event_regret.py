import types

import pytest

from somabrain.services.learner_online import LearnerService


class _DummyGauge:
    def __init__(self):
        self.value = None
    def set(self, v):  # pragma: no cover
        self.value = v


@pytest.mark.parametrize("confidence,expected", [(0.0, 1.0), (0.25, 0.75), (0.8, 0.2), (1.0, 0.0)])
def test_learner_computes_regret_from_next_event(confidence, expected, monkeypatch):
    svc = LearnerService()
    g = _DummyGauge()
    monkeypatch.setattr(svc, "_g_next_regret", g, raising=False)
    ev = {"confidence": confidence, "tenant": "public"}
    svc._observe_next_event(ev)
    assert g.value == pytest.approx(expected)
