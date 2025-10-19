from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from somabrain.context.builder import RetrievalWeights
from somabrain.learning.adaptation import AdaptationEngine, UtilityWeights


def test_feedback_updates_and_rollback_restores() -> None:
    retrieval = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.4, tau=0.7)
    utility = UtilityWeights(lambda_=1.2, mu=0.3, nu=0.3)
    engine = AdaptationEngine(
        retrieval=retrieval, utility=utility, learning_rate=0.05, max_history=10
    )

    baseline = (
        retrieval.alpha,
        retrieval.gamma,
        utility.lambda_,
        utility.mu,
        utility.nu,
    )

    applied = engine.apply_feedback(utility=0.9, reward=None)
    assert applied is True

    assert retrieval.alpha > baseline[0]
    assert retrieval.gamma <= baseline[1]
    assert utility.lambda_ > baseline[2]
    assert utility.mu <= baseline[3]
    assert utility.nu <= baseline[4]

    saved = engine._state
    assert saved["retrieval"]["alpha"] == retrieval.alpha
    assert saved["utility"]["lambda_"] == utility.lambda_

    rolled_back = engine.rollback()
    assert rolled_back is True

    restored = (
        retrieval.alpha,
        retrieval.gamma,
        utility.lambda_,
        utility.mu,
        utility.nu,
    )
    assert restored == baseline


def test_dynamic_learning_rate_uses_dopamine_signal() -> None:
    retrieval = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.3, tau=0.8)
    engine = AdaptationEngine(
        retrieval=retrieval,
        utility=UtilityWeights(lambda_=1.0, mu=0.4, nu=0.4),
        learning_rate=0.05,
        enable_dynamic_lr=True,
    )

    engine._get_dopamine_level = lambda: 0.35  # type: ignore[assignment]

    baseline_lr = engine._base_lr
    engine.apply_feedback(utility=1.0)

    expected_lr = baseline_lr * min(max(0.5 + 0.35, 0.5), 1.2)
    assert abs(engine._lr - expected_lr) < 1e-6
