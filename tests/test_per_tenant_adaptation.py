import os
import json
import pytest
from unittest import mock
from somabrain.learning.adaptation import AdaptationEngine, UtilityWeights
from somabrain.context.builder import RetrievalWeights
from somabrain.metrics import tau_gauge
from somabrain.feedback import Feedback
from somabrain.context_builder import ContextBuilder

# Simple in‑memory mock for Redis
class DummyRedis:
    def __init__(self):
        self.store = {}
    def setex(self, key, ttl, value):
        self.store[key] = (value, ttl)
    def get(self, key):
        return self.store.get(key, (None,))[0]

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    dummy = DummyRedis()
    monkeypatch.setattr('somabrain.learning.adaptation._get_redis', lambda: dummy)
    yield dummy

@pytest.fixture(autouse=True)
def patch_metrics(monkeypatch):
    mock_update = mock.Mock()
    monkeypatch.setattr('somabrain.metrics.update_learning_retrieval_weights', mock_update)
    return mock_update

def test_per_tenant_state_is_isolated(patch_redis):
    # Create two engines with different tenant ids
    rw1 = RetrievalWeights()
    uw1 = UtilityWeights()
    engine_a = AdaptationEngine(rw1, uw1, tenant_id="tenant_a")
    rw2 = RetrievalWeights()
    uw2 = UtilityWeights()
    engine_b = AdaptationEngine(rw2, uw2, tenant_id="tenant_b")

    # Apply feedback to each engine
    engine_a.apply_feedback(utility=1.0)
    engine_b.apply_feedback(utility=2.0)

    # Verify that each tenant has its own persisted state key
    key_a = "adaptation:state:tenant_a"
    key_b = "adaptation:state:tenant_b"
    assert key_a in patch_redis.store
    assert key_b in patch_redis.store
    # The stored JSON should reflect different feedback counts
    data_a = json.loads(patch_redis.store[key_a][0])
    data_b = json.loads(patch_redis.store[key_b][0])
    assert data_a["feedback_count"] == 1
    assert data_b["feedback_count"] == 1
    # Ensure that the learning rates differ according to the applied signal
    assert data_a["learning_rate"] != data_b["learning_rate"]

def test_per_tenant_feedback_updates_weights_and_metrics(patch_metrics):
    # Create engine for a specific tenant
    retrieval = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.1, tau=0.7)
    engine = AdaptationEngine(retrieval, tenant_id="tenant123", enable_dynamic_lr=False)
    # Apply feedback with positive utility
    engine.apply_feedback(utility=0.5)
    # Verify that retrieval weights changed (alpha increased)
    assert engine.retrieval_weights.alpha > 1.0
    # Verify metrics update called with correct tenant id and new weights
    assert patch_metrics.called
    args, kwargs = patch_metrics.call_args
    assert kwargs["tenant_id"] == "tenant123"
    assert kwargs["alpha"] == engine.retrieval_weights.alpha
    assert kwargs["beta"] == engine.retrieval_weights.beta
    assert kwargs["gamma"] == engine.retrieval_weights.gamma
    assert kwargs["tau"] == engine.retrieval_weights.tau

def test_per_tenant_adaptation():
    engine1 = AdaptationEngine(tenant_id="tenantA")
    engine2 = AdaptationEngine(tenant_id="tenantB")
    
    # Verify separate state isolation
    assert engine1._state != engine2._state
    
    # Test Redis state persistence
    engine1.save_state()
    loaded_state = engine1.load_state()
    assert loaded_state == engine1._state

    # Verify metrics isolation
    assert tau_gauge.labels("tenantA")._value != tau_gauge.labels("tenantB")._value

    # Test diversity adaptation
    cb = ContextBuilder()
    cb._current_tau = 0.5
    cb._track_diversity()
    assert 0.4 <= cb._current_tau <= 1.2

    # Test dynamic learning rate
    feedback = Feedback(event="test", score=0.8)
    engine1.apply_feedback(feedback)
    assert engine1._lr_eff != engine1._base_lr

    # Test neuromodulator state fetching
    assert engine1._get_neuromod_state() is not None
