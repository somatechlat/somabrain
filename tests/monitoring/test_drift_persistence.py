import os
import tempfile
import json
from pathlib import Path

from somabrain.monitoring import drift_detector as dd
from somabrain.monitoring.drift_detector import DriftDetector, DriftConfig


def test_drift_state_persistence_round_trip(monkeypatch):
    # Enable drift + rollback for detector
    monkeypatch.setenv("ENABLE_DRIFT_DETECTION", "1")
    monkeypatch.setenv("ENABLE_AUTO_ROLLBACK", "0")  # rollback not required for persistence
    # Use small window/min_samples for quick drift trigger
    cfg = DriftConfig(entropy_threshold=0.2, regret_threshold=0.2, window_size=8, min_samples=3, cooldown_period=0, adaptive=False, ema_alpha=0.5)
    with tempfile.TemporaryDirectory() as tmp:
        store_path = str(Path(tmp) / "drift_state.json")
        monkeypatch.setenv("SOMABRAIN_DRIFT_STORE", store_path)
        # Stub producer to avoid Kafka dependency
        class _StubProd:
            def send(self, *args, **kwargs):
                return None
        monkeypatch.setattr(dd, "make_producer", lambda: _StubProd())
        det = DriftDetector(config=cfg)
        # Feed observations that exceed thresholds (high entropy/regret)
        domain = "state"
        tenant = "public"
        # Simulate high regret by low confidence values; entropy is not used directly here
        for _ in range(3):
            det.add_observation(domain, tenant, confidence=0.05, entropy=0.95)
        # One extra to ensure persistence after drift
        det.add_observation(domain, tenant, confidence=0.05, entropy=0.95)
        # Drift should be detected and persisted
        assert Path(store_path).exists(), "Persistence file not created"
        data = json.loads(Path(store_path).read_text())
        key = f"{domain}:{tenant}"
        assert key in data.get("entries", {}), "Entry not persisted"
        entry = data["entries"][key]
        assert entry["last_drift_time"] > 0, "last_drift_time not recorded"
        # Create a fresh detector and ensure state is loaded
        det2 = DriftDetector(config=cfg)
        st2 = det2.states[key]
        assert st2.last_drift_time == entry["last_drift_time"], "Loaded last_drift_time mismatch"

