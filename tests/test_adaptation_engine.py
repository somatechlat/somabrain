import pytest
from somabrain.context.builder import RetrievalWeights
from somabrain.learning.adaptation import AdaptationEngine, UtilityWeights

def test_adaptation_apply_and_rollback():
    rw = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.5, tau=0.7)
    uw = UtilityWeights(lambda_=1.0, mu=0.5, nu=0.2)
    engine = AdaptationEngine(retrieval=rw, utility=uw, learning_rate=0.1)
    # Save initial values
    initial = (rw.alpha, rw.gamma, uw.lambda_, uw.mu, uw.nu)
    # Apply feedback
    applied = engine.apply_feedback(utility=2.0, reward=None)
    assert applied
    # Values should have changed
    changed = (rw.alpha, rw.gamma, uw.lambda_, uw.mu, uw.nu)
    assert changed != initial
    # Rollback
    rolled = engine.rollback()
    assert rolled
    # Values should be restored
    restored = (rw.alpha, rw.gamma, uw.lambda_, uw.mu, uw.nu)
    assert restored == initial

def test_adaptation_constraints():
    rw = RetrievalWeights(alpha=4.9, beta=0.2, gamma=0.95, tau=0.7)
    uw = UtilityWeights(lambda_=4.9, mu=0.02, nu=0.02)
    engine = AdaptationEngine(retrieval=rw, utility=uw, learning_rate=10.0)
    # Apply large positive feedback, should clamp to upper bounds
    engine.apply_feedback(utility=10.0)
    assert rw.alpha <= 5.0
    assert uw.lambda_ <= 5.0
    # Apply large negative feedback, should clamp to lower bounds
    engine.apply_feedback(utility=-100.0)
    assert rw.alpha >= 0.1
    assert uw.lambda_ >= 0.1
    assert uw.mu >= 0.01
    assert uw.nu >= 0.01
