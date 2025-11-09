"""Tests for the ``LearnerService`` next‑event handling.

The test verifies that ``_observe_next_event`` correctly computes regret as
``1 - confidence`` and stores it in the ``soma_next_event_regret`` gauge.
"""

from __future__ import annotations

import builtins
import types

import pytest

from somabrain.services.learner_online import LearnerService


class DummyGauge:
    """Simple gauge replacement that records the last ``set`` value."""

    def __init__(self) -> None:
        self.value: float | None = None

    def set(self, v: float) -> None:  # pragma: no cover – exercised via test
        self.value = v

    def inc(self, *_, **__) -> None:  # noqa: D401 - not used in this test
        pass

    def dec(self, *_, **__) -> None:  # noqa: D401 - not used in this test
        pass


def test_observe_next_event_regret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Ensure regret = 1 - confidence is stored in the gauge.

    The ``LearnerService`` creates the gauge lazily via ``somabrain.metrics``.
    We replace the gauge with ``DummyGauge`` to capture the value.
    """
    svc = LearnerService()
    dummy = DummyGauge()
    # Patch the gauge attribute directly
    monkeypatch.setattr(svc, "_g_next_regret", dummy, raising=False)

    # Provide a synthetic next_event with confidence 0.8 → regret 0.2
    svc._observe_next_event({"confidence": 0.8, "tenant": "public"})

    captured = capsys.readouterr()
    assert "next_event" in captured.out
    # The dummy gauge should have recorded the regret value
    assert dummy.value == pytest.approx(0.2)
