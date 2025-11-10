from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_predictor_calibration_event_emitted(monkeypatch):
    # Arrange: patch encoder and tracker to observe emission
    sent: list[Dict[str, Any]] = []

    class DummyProducer:
        def __init__(self):
            self.closed = False

        def send(self, topic: str, value: bytes):  # match calibration_service usage
            sent.append({"topic": topic, "value": value})

        def flush(self, timeout: float | None = None):  # pragma: no cover
            return 0

    # Fake encode returns bytes with schema marker for inspection
    def fake_encode(record: Dict[str, Any], schema_name: str) -> bytes:  # type: ignore
        assert schema_name == "predictor_calibration"
        return f"{schema_name}:{record.get('domain','')}/{record.get('tenant','')}".encode()

    # Patch calibration tracker data via public add_observation to ensure proper key format
    from somabrain.calibration.calibration_metrics import calibration_tracker

    calibration_tracker.calibration_data.clear()
    for c, a in [(0.6, 1), (0.7, 0), (0.8, 1)]:
        calibration_tracker.add_observation("search", "demo", c, a)

    # Ensure feature gate allows calibration during service init
    import somabrain.modes as modes

    orig_enabled = modes.feature_enabled
    monkeypatch.setattr(
        modes,
        "feature_enabled",
        lambda key: True if key == "calibration" else orig_enabled(key),
        raising=True,
    )

    import somabrain.services.calibration_service as svc

    monkeypatch.setattr(svc, "encode", fake_encode, raising=True)
    monkeypatch.setattr(svc, "make_producer", lambda: DummyProducer(), raising=True)

    service = svc.CalibrationService()

    # Act
    service._emit_calibration_snapshots()

    # Assert: at least one calibration event was produced with expected schema
    assert any(
        m["topic"].endswith("cog.predictor.calibration")
        and m["value"].startswith(b"predictor_calibration:")
        for m in sent
    )
