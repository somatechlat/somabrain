from __future__ import annotations

import importlib
import time
from dataclasses import replace


def test_drift_rollback_pipeline(monkeypatch):
    """End-to-end simulation of drift -> rollback side effects.

    Verifies:
    - DriftDetector marks instability and triggers rollback.
    - Rollback emits conservative config_update (simulated via patched producer).
    - Feature overrides are attempted when auto_rollback enabled.
    """
    # Patch feature flags/mode to enable drift & auto rollback
    import somabrain.modes as modes
    base = modes.get_mode_config()
    monkeypatch.setattr(
        modes,
        "get_mode_config",
        lambda: replace(base, enable_drift=True, enable_auto_rollback=True, fusion_normalization=True),
    )

    # Patch producer to capture emitted topic payloads without Kafka
    sent = []
    class _MockProducer:
        def send(self, topic, value):  # type: ignore
            sent.append((topic, value))
            class _F:  # minimal future mimic
                def get(self, timeout=5):
                    return None
            return _F()

    import somabrain.common.kafka as ck
    monkeypatch.setattr(ck, 'make_producer', lambda: _MockProducer())

    # Reload drift_detector to apply patched producer & mode flags
    drift_mod = importlib.reload(importlib.import_module('somabrain.monitoring.drift_detector'))
    det = drift_mod.DriftDetector(
        drift_mod.DriftConfig(
            entropy_threshold=0.05,
            regret_threshold=0.05,
            window_size=10,
            min_samples=3,
            cooldown_period=0,
            adaptive=False,
        )
    )

    # Simulate high entropy + high regret via low confidence repeatedly
    tenant = 'acpt'
    domain = 'state'
    for _ in range(3):  # min_samples satisfied
        det.add_observation(domain, tenant, confidence=0.1, entropy=0.99)
        time.sleep(0.005)

    # One more to trigger drift detection
    drifted = det.add_observation(domain, tenant, confidence=0.1, entropy=0.99)
    assert drifted is True
    st = det.get_drift_status(domain, tenant)
    assert st['stable'] is False
    # Verify at least one rollback related topic emission occurred
    topics = [t for (t, _) in sent]
    assert any('cog.fusion.rollback.events' in t for t in topics), topics
    assert any('cog.config.updates' in t for t in topics), topics
