import pytest
from unittest import mock

from somabrain.context.builder import ContextBuilder, MemoryRecord

# Patch the metrics update function to avoid side effects and capture calls
@pytest.fixture(autouse=True)
def patch_metrics(monkeypatch):
    mock_update = mock.Mock()
    monkeypatch.setattr('somabrain.metrics.update_learning_retrieval_weights', mock_update)
    return mock_update

def make_dummy_builder():
    # Simple embed function that returns a constant vector
    def embed_fn(text: str):
        return [0.1] * 10
    return ContextBuilder(embed_fn)

def test_tau_decreases_on_low_duplicate_ratio(patch_metrics):
    builder = make_dummy_builder()
    # Set initial tau
    builder._weights.tau = 0.7
    # Create memories with low duplicate ratio (only one duplicate)
    memories = [
        MemoryRecord(id="a", score=1.0, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="a", score=0.9, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="b", score=0.8, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="c", score=0.7, metadata={}, embedding=[0.0]*10),
    ]
    # Call compute_weights (query vector can be zeros)
    builder._compute_weights([0.0]*10, memories)
    # Expect tau decreased by 0.05, clamped to lower bound 0.4
    assert pytest.approx(builder._weights.tau, 0.001) == 0.65
    # Verify metric update called with correct tenant (default)
    patch_metrics.assert_called()
    args, kwargs = patch_metrics.call_args
    assert kwargs["tau"] == builder._weights.tau

def test_tau_increases_on_high_duplicate_ratio(patch_metrics):
    builder = make_dummy_builder()
    builder._weights.tau = 0.7
    # All IDs identical -> high duplicate ratio > 0.5
    memories = [
        MemoryRecord(id="x", score=1.0, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="x", score=0.9, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="x", score=0.8, metadata={}, embedding=[0.0]*10),
        MemoryRecord(id="x", score=0.7, metadata={}, embedding=[0.0]*10),
    ]
    builder._compute_weights([0.0]*10, memories)
    # Expect tau increased by 0.1, not exceeding 1.2
    assert pytest.approx(builder._weights.tau, 0.001) == 0.8
    patch_metrics.assert_called()
    args, kwargs = patch_metrics.call_args
    assert kwargs["tau"] == builder._weights.tau
