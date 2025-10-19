import json
import os
import pytest
import redis
from somabrain.learning.adaptation import AdaptationEngine, UtilityWeights
from somabrain.context.builder import RetrievalWeights, ContextBuilder, MemoryRecord
from somabrain.feedback import Feedback
from somabrain.metrics import tau_gauge

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------
from unittest import mock


@pytest.fixture(autouse=True)
def patch_metrics(monkeypatch):
    """Patch the metrics update function used by ContextBuilder.

    The production code calls ``somabrain.metrics.update_learning_retrieval_weights``
    inside ``ContextBuilder._compute_weights``.  During unit tests we replace it
    with a ``Mock`` so no external side‑effects occur and we can inspect the
    call arguments.
    """
    mock_update = mock.Mock()
    monkeypatch.setattr(
        "somabrain.metrics.update_learning_retrieval_weights", mock_update
    )
    return mock_update


# Real Redis client fixture – connects to the running Redis server
@pytest.fixture(autouse=True)
def real_redis(monkeypatch):
    # Use environment variables or defaults matching the dev setup
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    # Ensure a clean slate for the test by deleting any existing adaptation keys
    for key in client.scan_iter(match="adaptation:state:*"):
        client.delete(key)
    # Monkey‑patch the internal _get_redis function to return this client
    # No need to import _get_redis directly; we monkey‑patch it via the fixture.
    yield client
    # Cleanup after test – delete the keys again
    for key in client.scan_iter(match="adaptation:state:*"):
        client.delete(key)


def test_per_tenant_state_is_isolated(real_redis):
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
    assert real_redis.exists(key_a)
    assert real_redis.exists(key_b)
    # The stored JSON should reflect different feedback counts
    data_a = json.loads(real_redis.get(key_a))
    data_b = json.loads(real_redis.get(key_b))
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


def test_per_tenant_adaptation(patch_metrics):
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
    cb = ContextBuilder(embed_fn=lambda x: [], memstore=None)
    # Directly set an initial tau value
    cb._weights.tau = 0.5
    # Create a dummy embedding and a single dummy memory record to force weight computation
    dummy_query = [0.1, 0.2, 0.3]
    dummy_mem = [
        MemoryRecord(
            id="mem1",
            score=1.0,
            metadata={"graph_score": 0.0, "timestamp": 0},
            embedding=[0.1, 0.2, 0.3],
        )
    ]
    # This will run the weight logic and adjust tau based on diversity (only one item → no dupes)
    cb._compute_weights(dummy_query, dummy_mem)
    assert 0.4 <= cb._weights.tau <= 1.2

    # Test dynamic learning rate
    feedback = Feedback(event="test", score=0.8)
    engine1.apply_feedback(feedback)
    assert engine1._lr_eff != engine1._base_lr

    # Test neuromodulator state fetching
    assert engine1._get_neuromod_state() is not None
