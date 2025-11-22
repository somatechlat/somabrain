import math

from somabrain.services.integrator_hub_triplet import IntegratorHub


import pytest


pytestmark = [pytest.mark.unit, pytest.mark.skip_infra]


class DummyProducer:
    def __init__(self):
        self.records = []

    def produce(self, topic, payload):
        self.records.append((topic, payload))

    def flush(self):
        return


def test_precision_weighting_beats_confidence():
    # Start without IO/health servers
    hub = IntegratorHub(
        alpha=2.0,
        start_io=False,
        start_health=False,
        producer=DummyProducer(),
    )
    # Confidence alone would favor agent, but precision (lower error) should pick state
    hub._latest = {
        "state": {"confidence": 0.2, "delta_error": 0.1},
        "agent": {"confidence": 0.9, "delta_error": 0.9},
        "action": {"confidence": 0.1, "delta_error": 0.8},
    }
    leader = hub._select_leader()
    assert leader == "state"


def test_publish_global_uses_precision_weights():
    hub = IntegratorHub(
        alpha=1.5,
        start_io=False,
        start_health=False,
        producer=DummyProducer(),
    )
    hub._effective_cfg = lambda: {
        "alpha": hub.alpha,
        "temperature": 1.0,
        "enable": True,
        "opa_url": "",
    }
    hub._encode = lambda record, schema: b"payload"  # bypass avro for test
    hub._latest = {
        "state": {"confidence": 0.5, "delta_error": 0.2},
        "agent": {"confidence": 0.9, "delta_error": 0.6},
        "action": {"confidence": 0.1, "delta_error": 0.4},
    }
    hub._publish_global("state")
    # Ensure payload produced and weight ordering respects precision
    assert hub.producer.records, "No record produced"
    # precision weights: exp(-1.5*err)
    expected_state_weight = math.exp(-1.5 * 0.2)
    _, payload = hub.producer.records[0]
    assert payload == b"payload"
