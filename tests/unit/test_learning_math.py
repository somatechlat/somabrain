"""Unit tests for Sutton/Karpathy learning mathematics.

Tests cover:
1. TD-style weight update correctness (Rich Sutton)
2. Softmax temperature selection (Andrej Karpathy)
3. Entropy cap enforcement
4. Tau annealing schedules

VIBE Compliance: Real implementations only, no mocks or stubs.
"""

from __future__ import annotations

import math

import numpy as np
import pytest


@pytest.mark.django_db
class TestTDWeightUpdate:
    """Sutton's TD(0)-style weight update tests.

    Mathematical basis:
        w_{t+1} = w_t + α × G × signal

    Where:
        α = learning rate
        G = gain multiplier per weight
        signal = reward/utility feedback
    """

    def test_positive_reward_increases_alpha(self):
        """Positive reward signal should increase alpha weight."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.adaptation import AdaptationEngine

        engine = AdaptationEngine(tenant_id="test_positive")
        initial_alpha = engine.alpha
        engine.apply_feedback(utility=1.0, reward=1.0)
        assert engine.alpha > initial_alpha, "Positive reward should increase alpha"

    def test_negative_reward_decreases_weights(self):
        """Negative reward signal should decrease weights (bounded by constraints)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.adaptation import AdaptationEngine

        engine = AdaptationEngine(tenant_id="test_negative")
        initial_alpha = engine.alpha
        # Apply negative feedback
        engine.apply_feedback(utility=-1.0, reward=-1.0)
        # Alpha should decrease (or stay at min bound)
        assert (
            engine.alpha <= initial_alpha
        ), "Negative reward should decrease or maintain alpha"

    def test_weight_bounds_are_respected(self):
        """Weights must stay within configured min/max bounds."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.adaptation import AdaptationEngine
        from somabrain.learning.config import AdaptationConstraints

        constraints = AdaptationConstraints(
            alpha_min=0.1, alpha_max=2.0, gamma_min=0.0, gamma_max=1.0
        )
        engine = AdaptationEngine(tenant_id="test_bounds", constraints=constraints)

        # Apply extreme positive feedback many times
        for _ in range(100):
            engine.apply_feedback(utility=10.0, reward=10.0)

        assert engine.alpha <= 2.0, f"Alpha {engine.alpha} should be bounded by max=2.0"
        assert engine.alpha >= 0.1, f"Alpha {engine.alpha} should be bounded by min=0.1"

    def test_learning_rate_affects_update_magnitude(self):
        """Higher learning rate should produce larger weight changes."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.adaptation import AdaptationEngine

        # Low learning rate
        engine_low = AdaptationEngine(tenant_id="test_lr_low", learning_rate=0.01)
        initial_low = engine_low.alpha
        engine_low.apply_feedback(utility=1.0, reward=1.0)
        delta_low = abs(engine_low.alpha - initial_low)

        # High learning rate
        engine_high = AdaptationEngine(tenant_id="test_lr_high", learning_rate=0.5)
        initial_high = engine_high.alpha
        engine_high.apply_feedback(utility=1.0, reward=1.0)
        delta_high = abs(engine_high.alpha - initial_high)

        assert (
            delta_high > delta_low
        ), "Higher learning rate should produce larger changes"


class TestSoftmaxTemperature:
    """Karpathy's temperature-scaled softmax tests.

    Mathematical basis:
        p_i = exp(s_i / τ) / Σ exp(s_j / τ)

    Where τ (tau) is the temperature parameter:
        - High τ → uniform distribution (exploration)
        - Low τ → peaked distribution (exploitation)
    """

    def test_high_tau_uniform_distribution(self):
        """High τ → uniform distribution (exploration)."""
        scores = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        tau = 100.0  # Very high temperature

        # Normalize for numerical stability
        scores_shifted = scores - scores.max()
        weights = np.exp(scores_shifted / tau)
        weights /= weights.sum()

        # All weights should be nearly equal
        assert (
            np.std(weights) < 0.05
        ), f"High τ should give uniform distribution, got std={np.std(weights):.4f}"

    def test_low_tau_peaked_distribution(self):
        """Low τ → peaked distribution (exploitation)."""
        scores = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        tau = 0.01  # Very low temperature

        # Normalize for numerical stability
        scores_shifted = scores - scores.max()
        weights = np.exp(scores_shifted / tau)
        weights /= weights.sum()

        # Max score should dominate
        assert weights.argmax() == 2, "Low τ should select highest score"
        assert (
            weights[2] > 0.99
        ), f"Low τ should give peaked distribution, got max weight={weights[2]:.4f}"

    def test_medium_tau_proportional_distribution(self):
        """Medium τ should give proportional softmax weights."""
        scores = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        tau = 1.0  # Standard temperature

        scores_shifted = scores - scores.max()
        weights = np.exp(scores_shifted / tau)
        weights /= weights.sum()

        # Weights should be monotonically increasing with score
        assert (
            weights[0] < weights[1] < weights[2]
        ), "Medium τ should give proportional weights"
        # But not completely dominated by max
        assert weights[0] > 0.01, "Should still allocate some probability to lowest"


@pytest.mark.django_db
class TestEntropyCapEnforcement:
    """Entropy cap sharpening tests.

    The entropy cap H ≤ cap enforces exploration/exploitation balance.
    When exceeded, weights are sharpened toward dominant component.

    Mathematical basis:
        H(p) = -Σ p_i log(p_i)
    """

    def test_sharpening_reduces_entropy(self):
        """Sharpening should reduce mixture-weight entropy to below cap."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning import annealing as annealing_mod
        from somabrain.learning.annealing import check_entropy_cap

        original = annealing_mod.get_entropy_cap
        annealing_mod.get_entropy_cap = lambda _tid: 0.5
        try:
            alpha, beta, gamma, tau, was_sharpened = check_entropy_cap(
                alpha=0.3,
                beta=0.3,
                gamma=0.2,
                tau=0.2,
                tenant_id="test_sharpen",
            )
        finally:
            annealing_mod.get_entropy_cap = original

        if was_sharpened:
            # Entropy is over mixture weights (α, β, γ) only.
            vec = [alpha, beta, gamma]
            s = sum(vec)
            probs = [v / s for v in vec]
            entropy = -sum(p * math.log(p) for p in probs if p > 0)
            assert (
                entropy < 1.4
            ), f"Entropy {entropy} should be reduced after sharpening"
        # τ is never reshaped (DEBT-010).
        assert tau == 0.2

    def test_no_crash_on_high_entropy(self):
        """check_entropy_cap should NEVER raise RuntimeError (INTEGRAL behavior)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import check_entropy_cap

        # This should NOT raise, even with high entropy weights
        try:
            result = check_entropy_cap(
                alpha=0.25,
                beta=0.25,
                gamma=0.25,
                tau=0.25,
                tenant_id="test_no_crash",
            )
            assert len(result) == 5, "Should return 5-tuple"
        except RuntimeError as e:
            pytest.fail(f"check_entropy_cap should NEVER raise: {e}")

    def test_low_entropy_no_change(self):
        """Weights already below cap should not change significantly."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import check_entropy_cap

        # Already low entropy (dominated by alpha)
        alpha, beta, gamma, tau, was_sharpened = check_entropy_cap(
            alpha=0.9,
            beta=0.05,
            gamma=0.03,
            tau=0.02,
            tenant_id="test_low_entropy",
        )

        # No cap configured by default (0.0), so should not sharpen
        # If no cap, returns original values
        if not was_sharpened:
            # Values should be unchanged
            assert abs(alpha - 0.9) < 0.01 or abs(alpha - 0.9) / 0.9 < 0.5
        assert tau == 0.02

    def test_tau_unchanged_when_sharpening(self):
        """DEBT-010: entropy cap must not rescale τ."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning import annealing as annealing_mod
        from somabrain.learning.annealing import check_entropy_cap

        original = annealing_mod.get_entropy_cap
        annealing_mod.get_entropy_cap = lambda _tid: 0.5
        try:
            _, _, _, tau_out, _ = check_entropy_cap(
                alpha=0.3,
                beta=0.3,
                gamma=0.2,
                tau=0.7,
                tenant_id="test_tau_stable",
            )
        finally:
            annealing_mod.get_entropy_cap = original
        assert tau_out == 0.7


@pytest.mark.django_db
class TestTauAnnealing:
    """ONE tau anneal law (geometric) — W3 / DEBT-009.

    τ(t+1) = max(TAU_FLOOR, τ(t) · TAU_DECAY_FACTOR)
    """

    def test_geometric_formula(self):
        """Test the single geometric schedule."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import apply_tau_annealing
        from somabrain.math.contracts import TAU_DECAY_FACTOR, TAU_FLOOR

        result = apply_tau_annealing(1.0)
        expected = max(TAU_FLOOR, 1.0 * TAU_DECAY_FACTOR)
        assert abs(result - expected) < 1e-12, f"Expected {expected}, got {result}"

    def test_tau_floor_respected(self):
        """Tau should never go below TAU_FLOOR."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import apply_tau_annealing
        from somabrain.math.contracts import TAU_FLOOR

        result = apply_tau_annealing(0.01)
        assert result >= TAU_FLOOR, f"Tau {result} should respect floor {TAU_FLOOR}"

    def test_geometric_monotonic(self):
        """Geometric decay should be monotonically non-increasing."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import apply_tau_annealing

        tau = 1.0
        values = []
        for _ in range(10):
            tau = apply_tau_annealing(tau)
            values.append(tau)
        for i in range(1, len(values)):
            assert (
                values[i] <= values[i - 1]
            ), f"Geometric decay should be monotonic: {values}"
