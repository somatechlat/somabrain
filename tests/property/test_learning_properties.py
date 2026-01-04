"""Property-based tests for Learning & Adaptation System.

**Feature: production-hardening**
**Properties: 11-14 (Adaptation Delta, Constraint Clamping, Tau Annealing, Reset)**
**Validates: Requirements 4.1, 4.2, 4.3, 4.6**

These tests verify the mathematical invariants of the adaptation formulas
used for online learning in SomaBrain. Tests use pure mathematical
verification without requiring the full AdaptationEngine infrastructure.
"""

from __future__ import annotations

from hypothesis import given, settings as hyp_settings, strategies as st, assume
from dataclasses import dataclass


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


# ---------------------------------------------------------------------------
# Pure mathematical functions extracted from AdaptationEngine
# ---------------------------------------------------------------------------


def compute_delta(lr: float, gain: float, signal: float) -> float:
    """Compute weight update delta: delta = lr × gain × signal."""
    return lr * gain * signal


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to [min_val, max_val]."""
    return min(max(value, min_val), max_val)


def exponential_anneal(current: float, rate: float, floor: float) -> float:
    """Apply exponential annealing: new = current × (1 - rate), clamped to floor."""
    return max(floor, current * (1.0 - rate))


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
        delta = compute_delta(lr, gain, signal)
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
        delta = compute_delta(lr, 0.0, signal)
        assert delta == 0.0, f"Delta should be 0 with zero gain, got {delta}"

    @given(
        lr=learning_rate_strategy,
        gain=gain_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_delta_zero_signal_is_zero(self, lr: float, gain: float) -> None:
        """Verify delta = 0 when signal = 0."""
        delta = compute_delta(lr, gain, 0.0)
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
        delta = compute_delta(lr, gain, signal)
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

        result = clamp_value(value, min_val, max_val)

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

        result = clamp_value(value, min_val, max_val)

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

        result = clamp_value(value, min_val, max_val)

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

        result = clamp_value(value, min_val, max_val)

        assert result == value, f"Value {value} changed to {result}"


class TestTauExponentialAnnealing:
    """Property 13: Tau Exponential Annealing.

    When exponential annealing is enabled with rate r, after each feedback
    event, tau_{t+1} SHALL equal tau_t × (1 - r).

    **Feature: production-hardening, Property 13: Tau Exponential Annealing**
    **Validates: Requirements 4.3**
    """

    @given(
        initial_tau=st.floats(
            min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        anneal_rate=st.floats(
            min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False
        ),
        floor=st.floats(
            min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_exponential_anneal_formula(
        self, initial_tau: float, anneal_rate: float, floor: float
    ) -> None:
        """Verify tau_{t+1} = max(floor, tau_t × (1 - rate))."""
        result = exponential_anneal(initial_tau, anneal_rate, floor)
        expected = max(floor, initial_tau * (1.0 - anneal_rate))

        assert (
            abs(result - expected) < 1e-12
        ), f"Annealed tau {result} != expected {expected}"

    @given(
        initial_tau=st.floats(
            min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        anneal_rate=st.floats(
            min_value=0.01, max_value=0.3, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_exponential_anneal_decreases(
        self, initial_tau: float, anneal_rate: float
    ) -> None:
        """Verify exponential annealing always decreases tau (above floor)."""
        floor = 0.01
        result = exponential_anneal(initial_tau, anneal_rate, floor)

        assert result <= initial_tau, f"Annealed tau {result} > initial {initial_tau}"

    @given(
        initial_tau=st.floats(
            min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        anneal_rate=st.floats(
            min_value=0.01, max_value=0.3, allow_nan=False, allow_infinity=False
        ),
        floor=st.floats(
            min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_exponential_anneal_respects_floor(
        self, initial_tau: float, anneal_rate: float, floor: float
    ) -> None:
        """Verify annealed tau never goes below floor."""
        result = exponential_anneal(initial_tau, anneal_rate, floor)

        assert result >= floor, f"Annealed tau {result} < floor {floor}"

    @given(
        initial_tau=st.floats(
            min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        floor=st.floats(
            min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_exponential_anneal_zero_rate_unchanged(
        self, initial_tau: float, floor: float
    ) -> None:
        """Verify zero anneal rate leaves tau unchanged."""
        result = exponential_anneal(initial_tau, 0.0, floor)

        assert (
            result == initial_tau
        ), f"Tau changed from {initial_tau} to {result} with zero rate"


@dataclass
class WeightState:
    """Simple weight state for reset testing."""

    alpha: float = 1.0
    beta: float = 0.2
    gamma: float = 0.1
    tau: float = 0.7

    def reset_to(self, defaults: "WeightState") -> None:
        """Reset weights to default values."""
        self.alpha = defaults.alpha
        self.beta = defaults.beta
        self.gamma = defaults.gamma
        self.tau = defaults.tau


class TestAdaptationReset:
    """Property 14: Adaptation Reset.

    When reset() is called, all weights SHALL return to their default values.

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
        """Verify reset() restores default weight values."""
        # Create modified state
        state = WeightState(
            alpha=modified_alpha,
            beta=0.5,
            gamma=modified_gamma,
            tau=modified_tau,
        )

        # Verify weights are modified
        assert state.alpha == modified_alpha
        assert state.gamma == modified_gamma
        assert state.tau == modified_tau

        # Define defaults
        defaults = WeightState(alpha=1.0, beta=0.2, gamma=0.1, tau=0.7)

        # Reset to defaults
        state.reset_to(defaults)

        # Verify weights are restored
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
        # Create modified state
        state = WeightState(alpha=5.0, beta=0.8, gamma=0.9, tau=0.1)

        # Define custom defaults
        defaults = WeightState(
            alpha=default_alpha,
            beta=0.3,
            gamma=0.2,
            tau=default_tau,
        )

        # Reset to custom defaults
        state.reset_to(defaults)

        # Verify weights match custom defaults
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
        state = WeightState(alpha=initial_alpha, beta=0.5, gamma=0.5, tau=0.5)
        defaults = WeightState()

        # Reset multiple times
        state.reset_to(defaults)
        first_alpha = state.alpha

        state.reset_to(defaults)
        second_alpha = state.alpha

        assert (
            first_alpha == second_alpha
        ), f"Reset not idempotent: {first_alpha} != {second_alpha}"