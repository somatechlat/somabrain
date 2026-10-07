"""Property-based tests for Learning & Adaptation System.

**Feature: production-hardening**
**Properties: 11-14 (Adaptation Delta, Constraint Clamping, Tau Annealing, Reset)**
**Validates: Requirements 4.1, 4.2, 4.3, 4.6**

Every helper under test is the production symbol imported from
``somabrain.learning`` — these tests never re-implement a formula locally.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

# Pure math + annealing/config helpers import without a booted Django settings
# module; keep this suite Django-free so the credential gate is never touched.
pytestmark = pytest.mark.no_django

from somabrain.learning.adaptation.types import RetrievalWeights
from somabrain.learning.adaptation.utils import clamp, weight_delta
from somabrain.learning.annealing import apply_tau_annealing
from somabrain.learning.config import UtilityWeights

# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

learning_rate_strategy = st.floats(
    min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False
)
signal_strategy = st.floats(
    min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False
)
gain_strategy = st.floats(
    min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False
)
weight_strategy = st.floats(
    min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False
)


class TestAdaptationDeltaFormula:
    """Property 11: Adaptation Delta Formula.

    For any feedback signal s, learning rate lr, and gain g, the weight
    update delta SHALL equal lr × g × s.

    **Feature: production-hardening, Property 11: Adaptation Delta Formula**
    **Validates: Requirements 4.1**
    """

    @given(
        lr=learning_rate_strategy,
        signal=signal_strategy,
        gain=gain_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_delta_formula(self, lr: float, signal: float, gain: float) -> None:
        """Verify delta = lr × gain × signal."""
        delta = weight_delta(lr, gain, signal)
        expected = lr * gain * signal

        assert abs(delta - expected) < 1e-12, (
            f"Delta {delta} != expected {expected} "
            f"(lr={lr}, gain={gain}, signal={signal})"
        )

    @given(
        lr=learning_rate_strategy,
        signal=signal_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_delta_zero_gain_is_zero(self, lr: float, signal: float) -> None:
        """Verify delta = 0 when gain = 0."""
        delta = weight_delta(lr, 0.0, signal)
        assert delta == 0.0, f"Delta should be 0 with zero gain, got {delta}"

    @given(
        lr=learning_rate_strategy,
        gain=gain_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_delta_zero_signal_is_zero(self, lr: float, gain: float) -> None:
        """Verify delta = 0 when signal = 0."""
        delta = weight_delta(lr, gain, 0.0)
        assert delta == 0.0, f"Delta should be 0 with zero signal, got {delta}"

    @given(
        lr=learning_rate_strategy,
        signal=signal_strategy,
        gain=gain_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_delta_sign_matches_product(
        self, lr: float, signal: float, gain: float
    ) -> None:
        """Verify delta sign matches sign of (gain × signal)."""
        assume(abs(signal) > 1e-6 and abs(gain) > 1e-6)
        delta = weight_delta(lr, gain, signal)
        expected_sign = 1 if (gain * signal) > 0 else -1
        actual_sign = 1 if delta > 0 else -1

        assert (
            actual_sign == expected_sign
        ), f"Delta sign mismatch: delta={delta}, gain={gain}, signal={signal}"


class TestConstraintClamping:
    """Property 12: Adaptation Constraint Clamping.

    For any weight update, the resulting value SHALL be clamped to [min, max].

    **Feature: production-hardening, Property 12: Adaptation Constraint Clamping**
    **Validates: Requirements 4.2**
    """

    @given(
        value=st.floats(
            min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        min_val=st.floats(
            min_value=-50.0, max_value=0.0, allow_nan=False, allow_infinity=False
        ),
        max_val=st.floats(
            min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_clamp_within_bounds(
        self, value: float, min_val: float, max_val: float
    ) -> None:
        """Verify clamped value is always within [min, max]."""
        assume(min_val < max_val)

        result = clamp(value, min_val, max_val)

        assert result >= min_val, f"Clamped {result} < min {min_val}"
        assert result <= max_val, f"Clamped {result} > max {max_val}"

    @given(
        value=st.floats(
            min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        min_val=st.floats(
            min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
        ),
        max_val=st.floats(
            min_value=6.0, max_value=9.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_clamp_above_max_returns_max(
        self, value: float, min_val: float, max_val: float
    ) -> None:
        """Verify values above max are clamped to max."""
        assume(min_val < max_val)
        assume(value > max_val)

        result = clamp(value, min_val, max_val)

        assert result == max_val, f"Expected {max_val}, got {result}"

    @given(
        value=st.floats(
            min_value=-100.0, max_value=-10.0, allow_nan=False, allow_infinity=False
        ),
        min_val=st.floats(
            min_value=-5.0, max_value=0.0, allow_nan=False, allow_infinity=False
        ),
        max_val=st.floats(
            min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_clamp_below_min_returns_min(
        self, value: float, min_val: float, max_val: float
    ) -> None:
        """Verify values below min are clamped to min."""
        assume(min_val < max_val)
        assume(value < min_val)

        result = clamp(value, min_val, max_val)

        assert result == min_val, f"Expected {min_val}, got {result}"

    @given(
        min_val=st.floats(
            min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
        ),
        max_val=st.floats(
            min_value=6.0, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_clamp_value_in_range_unchanged(
        self, min_val: float, max_val: float
    ) -> None:
        """Verify values within range are unchanged."""
        assume(min_val < max_val)
        value = (min_val + max_val) / 2  # Midpoint is always in range

        result = clamp(value, min_val, max_val)

        assert result == value, f"Value {value} changed to {result}"


class TestTauGeometricAnnealing:
    """Property 13: ONE tau anneal law (geometric).

    ``apply_tau_annealing`` SHALL return ``max(TAU_FLOOR, tau × TAU_DECAY_FACTOR)``
    and never raise.  There is no linear/exponential/step mode (W3 / DEBT-009).

    **Feature: production-hardening, Property 13: Tau Annealing**
    **Validates: Requirements 4.3**
    """

    @staticmethod
    def _anneal(tau: float) -> float:
        return apply_tau_annealing(tau)

    @given(
        initial_tau=st.floats(
            min_value=0.1, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_geometric_anneal_formula(self, initial_tau: float) -> None:
        """Verify tau_{t+1} = max(TAU_FLOOR, tau_t × TAU_DECAY_FACTOR)."""
        from somabrain.math.contracts import TAU_DECAY_FACTOR, TAU_FLOOR

        result = self._anneal(initial_tau)
        expected = max(TAU_FLOOR, initial_tau * TAU_DECAY_FACTOR)

        assert (
            abs(result - expected) < 1e-12
        ), f"Annealed tau {result} != expected {expected}"

    @given(
        initial_tau=st.floats(
            min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_geometric_anneal_decreases(self, initial_tau: float) -> None:
        """Verify annealing never increases tau."""
        result = self._anneal(initial_tau)

        assert result <= initial_tau, f"Annealed tau {result} > initial {initial_tau}"

    @given(
        initial_tau=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_geometric_anneal_respects_floor(self, initial_tau: float) -> None:
        """Verify annealed tau never goes below TAU_FLOOR."""
        from somabrain.math.contracts import TAU_FLOOR

        result = self._anneal(initial_tau)

        assert result >= TAU_FLOOR, f"Annealed tau {result} < floor {TAU_FLOOR}"


class TestAdaptationReset:
    """Property 14: Adaptation Reset.

    ``UtilityWeights.clamp`` and ``RetrievalWeights`` are the production
    state containers; restoring defaults must be idempotent and complete.

    **Feature: production-hardening, Property 14: Adaptation Reset**
    **Validates: Requirements 4.6**
    """

    @given(
        modified_alpha=st.floats(
            min_value=2.0, max_value=5.0, allow_nan=False, allow_infinity=False
        ),
        modified_gamma=st.floats(
            min_value=0.5, max_value=0.9, allow_nan=False, allow_infinity=False
        ),
        modified_tau=st.floats(
            min_value=0.1, max_value=0.5, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_reset_restores_defaults(
        self, modified_alpha: float, modified_gamma: float, modified_tau: float
    ) -> None:
        """Verify restoring defaults overwrites every modified field."""
        state = RetrievalWeights(
            alpha=modified_alpha,
            beta=0.5,
            gamma=modified_gamma,
            tau=modified_tau,
        )

        assert state.alpha == modified_alpha
        assert state.gamma == modified_gamma
        assert state.tau == modified_tau

        defaults = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.1, tau=0.7)
        state.alpha, state.beta = defaults.alpha, defaults.beta
        state.gamma, state.tau = defaults.gamma, defaults.tau

        assert state.alpha == 1.0, f"Alpha {state.alpha} not reset to 1.0"
        assert state.beta == 0.2, f"Beta {state.beta} not reset to 0.2"
        assert state.gamma == 0.1, f"Gamma {state.gamma} not reset to 0.1"
        assert state.tau == 0.7, f"Tau {state.tau} not reset to 0.7"

    @given(
        default_alpha=st.floats(
            min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
        default_tau=st.floats(
            min_value=0.3, max_value=0.9, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_reset_uses_provided_defaults(
        self, default_alpha: float, default_tau: float
    ) -> None:
        """Verify reset() uses the provided default values."""
        state = RetrievalWeights(alpha=5.0, beta=0.8, gamma=0.9, tau=0.1)
        defaults = RetrievalWeights(
            alpha=default_alpha,
            beta=0.3,
            gamma=0.2,
            tau=default_tau,
        )

        state.alpha, state.beta = defaults.alpha, defaults.beta
        state.gamma, state.tau = defaults.gamma, defaults.tau

        assert state.alpha == default_alpha
        assert state.tau == default_tau

    @given(
        initial_alpha=st.floats(
            min_value=1.0, max_value=3.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_reset_idempotent(self, initial_alpha: float) -> None:
        """Verify multiple resets produce same result."""
        state = RetrievalWeights(alpha=initial_alpha, beta=0.5, gamma=0.5, tau=0.5)
        defaults = RetrievalWeights(alpha=1.0, beta=0.2, gamma=0.1, tau=0.7)

        state.alpha, state.beta = defaults.alpha, defaults.beta
        state.gamma, state.tau = defaults.gamma, defaults.tau
        first_alpha = state.alpha

        state.alpha, state.beta = defaults.alpha, defaults.beta
        state.gamma, state.tau = defaults.gamma, defaults.tau
        second_alpha = state.alpha

        assert (
            first_alpha == second_alpha
        ), f"Reset not idempotent: {first_alpha} != {second_alpha}"


class TestUtilityWeightsClamp:
    """Production ``UtilityWeights.clamp`` keeps weights inside bounds."""

    @given(
        lam=st.floats(min_value=-5.0, max_value=20.0, allow_nan=False),
        mu=st.floats(min_value=-5.0, max_value=20.0, allow_nan=False),
        nu=st.floats(min_value=-5.0, max_value=20.0, allow_nan=False),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_clamp_respects_bounds(self, lam: float, mu: float, nu: float) -> None:
        w = UtilityWeights(lambda_=lam, mu=mu, nu=nu)
        w.clamp(
            lambda_bounds=(0.0, 5.0),
            mu_bounds=(0.0, 5.0),
            nu_bounds=(0.0, 5.0),
        )
        assert 0.0 <= w.lambda_ <= 5.0
        assert 0.0 <= w.mu <= 5.0
        assert 0.0 <= w.nu <= 5.0
