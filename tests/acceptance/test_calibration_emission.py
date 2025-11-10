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

        def produce(self, topic: str, value: bytes):
            sent.append({"topic": topic, "value": value})

        def flush(self, timeout: float | None = None):
            return 0

    # Fake encode returns bytes with schema marker for inspection
    def fake_encode(record: Dict[str, Any], schema_name: str) -> bytes:  # type: ignore
        assert schema_name == "predictor_calibration"
        return f"{schema_name}:{record.get('domain','')}/{record.get('tenant','')}".encode()

    # Patch calibration tracker data so service emits one record
    from somabrain.calibration.calibration_metrics import calibration_tracker

    calibration_tracker.calibration_data.clear()
    key = ("search", "demo")
    calibration_tracker.calibration_data[key] = {
        "confidences": [0.6, 0.7, 0.8],
        "accuracies": [1, 0, 1],
        "samples": 3,
    }

    import somabrain.services.calibration_service as svc

    monkeypatch.setattr(svc, "encode", fake_encode, raising=True)
    monkeypatch.setattr(svc, "create_producer", lambda: DummyProducer(), raising=True)

    service = svc.CalibrationService()
    # Force-enabled for test regardless of features
    service.enabled = True

    # Act
    service._emit_calibration_snapshots()

    # Assert: at least one calibration event was produced with expected schema
    assert any(
        m["topic"].endswith("cog.predictor.calibration")
        and m["value"].startswith(b"predictor_calibration:")
        for m in sent
    )
