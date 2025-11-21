import math
from somabrain.services.integrator_hub_triplet import IntegratorHub

class DummyProducer:
    def __init__(self):
        self.sent = []
    def produce(self, topic, value):
        self.sent.append((topic, value))
    def flush(self):
        pass

class DummyRedis:
    def __init__(self):
        self.cache = {}
    def setex(self, key, ttl, val):
        self.cache[key] = val


def test_softmax_leader_selection():
    hub = IntegratorHub(
        producer=DummyProducer(),
        redis_client=None,
        opa_request=lambda url, ctx: True,
        start_io=False,
        start_health=False,
    )
    # inject latest confidences
    hub._latest = {
        "state": {"confidence": math.exp(-0.1)},
        "agent": {"confidence": math.exp(-0.5)},
        "action": {"confidence": math.exp(-1.0)},
    }
    cfg = hub._effective_cfg()
    assert cfg["alpha"] > 0
    leader = hub._select_leader()
    assert leader == "state"


def test_opa_veto_blocks_publish():
    prod = DummyProducer()
    hub = IntegratorHub(
        producer=prod,
        redis_client=DummyRedis(),
        opa_request=lambda url, ctx: False,
        start_io=False,
        start_health=False,
    )
    hub._latest = {
        "state": {"confidence": 1.0},
        "agent": {"confidence": 0.5},
        "action": {"confidence": 0.2},
    }
    hub._publish_global("state")
    assert prod.sent == []
