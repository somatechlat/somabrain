"""Tests for per‑tenant configuration overrides in ``LearnerService``.

The learner reads a YAML file (path configurable via ``SOMABRAIN_LEARNING_TENANTS_FILE``)
containing ``tau_decay_rate`` and ``entropy_cap`` values. The test creates a temporary
YAML file, points the env var to it, constructs a ``LearnerService`` instance and
verifies that the emitted config update respects the decay rate.
"""

from __future__ import annotations

import os
import tempfile
import yaml

import pytest

from somabrain.services.learner_online import LearnerService


def test_emit_cfg_respects_tau_decay(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create a temporary tenant overrides file with a decay of 0.1 (10% reduction)
    overrides = {"public": {"tau_decay_rate": 0.1, "entropy_cap": 0.9}}
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        yaml.safe_dump(overrides, tf)
        temp_path = tf.name
    # Point the env var to the temporary file
    monkeypatch.setenv("SOMABRAIN_LEARNING_TENANTS_FILE", temp_path)
    # Instantiate the service – it will load the overrides on init
    svc = LearnerService()
    # Capture the emitted payload by monkey‑patching the producer's produce method
    captured = {}

    class DummyProducer:
        def produce(self, topic, payload, callback=None):  # pragma: no cover
            captured["topic"] = topic
            captured["payload"] = payload
            if callback:
                # Simulate a successful delivery
                class Msg:
                    def partition(self):
                        return 0

                    def offset(self):
                        return 0

                callback(None, Msg())

        def flush(self, timeout=None):
            pass

    svc._producer = DummyProducer()
    # Emit a config with an initial tau of 0.8 – after 10% decay it should be 0.72
    svc._emit_cfg("public", 0.8, lr=0.05)
    # Decode the payload (JSON fallback should be used in the test environment)
    import json

    payload_dict = json.loads(captured["payload"].decode("utf-8"))
    assert payload_dict["exploration_temp"] == pytest.approx(0.72)
