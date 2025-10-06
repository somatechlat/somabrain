import pytest

from somabrain.learning.adaptation import AdaptationEngine, RetrievalWeights

def test_dynamic_learning_rate_scaling(monkeypatch):
    # Create engine with dynamic LR enabled
    retrieval = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.1, tau=0.7)
    engine = AdaptationEngine(retrieval, tenant_id="tenantXYZ", enable_dynamic_lr=True)
    # Mock dopamine level to a known value (e.g., 0.3)
    monkeypatch.setattr(engine, "_get_dopamine_level", lambda: 0.3)
    base_lr = engine._base_lr
    # Apply feedback; should adjust learning rate based on dopamine
    engine.apply_feedback(utility=1.0)
    expected_lr = base_lr * min(max(0.5 + 0.3, 0.5), 1.2)  # 0.8 * base_lr
    assert pytest.approx(engine._lr, rel=1e-5) == expected_lr
