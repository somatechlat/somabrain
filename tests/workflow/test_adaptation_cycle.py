from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from somabrain.context.builder import RetrievalWeights
from somabrain.learning.adaptation import (
    AdaptationEngine,
    UtilityWeights,
    AdaptationGains,
    AdaptationConstraints,
)


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


def test_injected_gains_override() -> None:
    retrieval = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.4, tau=0.7)
    gains = AdaptationGains(alpha=2.0, gamma=-1.0, lambda_=1.0, mu=-0.25, nu=-0.25)
    engine = AdaptationEngine(
        retrieval=retrieval,
        utility=UtilityWeights(lambda_=1.0, mu=0.3, nu=0.3),
        learning_rate=0.05,
        gains=gains,
    )
    engine.apply_feedback(utility=1.0)
    # With alpha gain 2.0: delta = 0.05 * 2.0 * 1.0 = 0.1 (alpha increases)
    assert retrieval.alpha == pytest.approx(1.1, rel=1e-6)
    # With gamma gain -1.0: delta = 0.05 * -1.0 * 1.0 = -0.05 (gamma decreases)
    assert retrieval.gamma == pytest.approx(0.35, rel=1e-6)


def test_injected_constraints_respected() -> None:
    retrieval = RetrievalWeights(alpha=0.7, beta=0.2, gamma=0.3, tau=0.7)
    utility = UtilityWeights(lambda_=0.9, mu=0.3, nu=0.3)
    constraints = AdaptationConstraints(
        alpha_min=0.6,
        alpha_max=5.0,
        gamma_min=0.2,
        gamma_max=1.0,
        lambda_min=0.8,
        lambda_max=5.0,
        mu_min=0.01,
        mu_max=5.0,
        nu_min=0.01,
        nu_max=5.0,
    )
    engine = AdaptationEngine(
        retrieval=retrieval,
        utility=utility,
        learning_rate=0.05,
        constraints=constraints,
    )
    engine.apply_feedback(utility=-1.0)
    assert retrieval.alpha >= 0.6
    assert retrieval.gamma >= 0.2
    assert utility.lambda_ >= 0.8
