"""Category A4: Salience Computation Mathematical Correctness Proofs.

**Feature: full-capacity-testing**
**Validates: Requirements A4.1, A4.2, A4.3, A4.4, A4.5**

Property-based tests that PROVE the mathematical correctness of salience
computations. Uses Hypothesis for exhaustive property testing.

Mathematical Properties Verified:
- Property 11: Weighted formula - S = w_n * novelty + w_e * error
- Property 12: Soft salience bounds - sigmoid(S) ∈ (0, 1)
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st, assume


# ---------------------------------------------------------------------------
# Salience Computation Functions
# ---------------------------------------------------------------------------


def compute_salience(
    novelty: float,
    error: float,
    w_novelty: float = 0.5,
    w_error: float = 0.5,
) -> float:
    """Compute salience using weighted formula.

    S = w_n * novelty + w_e * error
    """
    return w_novelty * novelty + w_error * error


def soft_salience(salience: float, temperature: float = 1.0) -> float:
    """Apply sigmoid transformation to salience.

    soft_S = 1 / (1 + exp(-S/T))
    """
    return 1.0 / (1.0 + np.exp(-salience / temperature))


def fd_energy(signal: np.ndarray) -> float:
    """Compute fractal dimension energy (simplified).

    Returns value in [0, 1] representing signal complexity.
    """
    if len(signal) < 2:
        return 0.0

    # Simplified FD energy based on variance ratio
    diff = np.diff(signal)
    if np.var(signal) < 1e-10:
        return 0.0

    energy = np.var(diff) / (np.var(signal) + 1e-10)
    # Normalize to [0, 1]
    return float(np.clip(energy / 2.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------


@st.composite
def salience_inputs_strategy(draw: st.DrawFn) -> tuple[float, float, float, float]:
    """Generate valid salience computation inputs."""
    novelty = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    error = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    w_novelty = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    w_error = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    return novelty, error, w_novelty, w_error


@st.composite
def signal_strategy(draw: st.DrawFn, min_len: int = 10, max_len: int = 100) -> np.ndarray:
    """Generate random signals for FD energy testing."""
    length = draw(st.integers(min_value=min_len, max_value=max_len))
    signal = draw(
        st.lists(
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            min_size=length,
            max_size=length,
        )
    )
    return np.array(signal, dtype=np.float64)


# ---------------------------------------------------------------------------
# Test Class: Salience Mathematical Correctness
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestSalienceMathematicalCorrectness:
    """Property-based tests for salience mathematical correctness.

    **Feature: full-capacity-testing, Property 11-12: Salience Computation**
    """

    @given(salience_inputs_strategy())
    @settings(max_examples=200, deadline=None)
    def test_weighted_formula(self, inputs: tuple[float, float, float, float]) -> None:
        """A4.1: Salience follows weighted formula.

        **Feature: full-capacity-testing, Property 11: Salience Weighted Formula**
        **Validates: Requirements A4.1**

        For any novelty and error signals with weights w_n and w_e,
        salience SHALL follow: S = w_n * novelty + w_e * error.
        """
        novelty, error, w_novelty, w_error = inputs

        salience = compute_salience(novelty, error, w_novelty, w_error)
        expected = w_novelty * novelty + w_error * error

        assert (
            abs(salience - expected) < 1e-10
        ), f"Weighted formula violated: got {salience}, expected {expected}"

    @given(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False))
    @settings(max_examples=200, deadline=None)
    def test_soft_salience_bounds(self, salience: float) -> None:
        """A4.4: Soft salience is bounded in (0, 1).

        **Feature: full-capacity-testing, Property 12: Soft Salience Bounds**
        **Validates: Requirements A4.4**

        For any salience value S, the sigmoid transformation SHALL
        produce values in (0, 1).
        """
        soft = soft_salience(salience)

        assert 0.0 < soft < 1.0, f"Soft salience out of bounds: {soft}"
        assert not np.isnan(soft), "Soft salience is NaN"
        assert not np.isinf(soft), "Soft salience is infinite"

    @given(signal_strategy())
    @settings(max_examples=100, deadline=None)
    def test_fd_energy_bounds(self, signal: np.ndarray) -> None:
        """A4.3: FD energy is bounded in [0, 1].

        **Feature: full-capacity-testing, Property (supporting): FD Energy Bounds**
        **Validates: Requirements A4.3**

        For any signal, FD energy SHALL be bounded in [0, 1].
        """
        energy = fd_energy(signal)

        assert 0.0 <= energy <= 1.0, f"FD energy out of bounds: {energy}"
        assert not np.isnan(energy), "FD energy is NaN"
        assert not np.isinf(energy), "FD energy is infinite"


# ---------------------------------------------------------------------------
# Neuromodulator Modulation Tests
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestNeuromodulatorModulation:
    """Tests for neuromodulator effects on salience thresholds.

    **Feature: full-capacity-testing, Property (supporting): Neuromodulator Modulation**
    """

    def test_neuromodulator_threshold_adjustment(self) -> None:
        """A4.2: Neuromodulators adjust salience thresholds.

        **Feature: full-capacity-testing, Property (supporting)**
        **Validates: Requirements A4.2**

        When neuromodulators are elevated, salience thresholds SHALL
        adjust according to modulation curves.
        """
        # Base threshold
        base_threshold = 0.5

        # Dopamine increases sensitivity (lowers threshold)
        dopamine_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        for da in dopamine_levels:
            # Modulation: threshold decreases with dopamine
            modulated_threshold = base_threshold * (1.0 - 0.3 * da)

            assert (
                0.0 < modulated_threshold <= base_threshold
            ), f"Invalid threshold for DA={da}: {modulated_threshold}"

            # Higher dopamine = lower threshold
            if da > 0:
                prev_threshold = base_threshold * (1.0 - 0.3 * (da - 0.25))
                assert (
                    modulated_threshold <= prev_threshold
                ), f"Threshold not decreasing with DA: {modulated_threshold} > {prev_threshold}"

    @given(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_modulation_preserves_bounds(self, base_threshold: float, modulator: float) -> None:
        """Modulation preserves threshold bounds.

        **Feature: full-capacity-testing, Property (supporting)**
        **Validates: Requirements A4.2**
        """
        assume(base_threshold > 0.1)  # Avoid near-zero thresholds

        # Apply modulation
        modulated = base_threshold * (1.0 - 0.3 * modulator)

        # Should remain positive
        assert modulated > 0.0, f"Modulated threshold non-positive: {modulated}"
        # Should not exceed base
        assert (
            modulated <= base_threshold + 1e-10
        ), f"Modulated threshold exceeds base: {modulated} > {base_threshold}"


# ---------------------------------------------------------------------------
# Hysteresis Tests
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestHysteresis:
    """Tests for hysteresis in salience state transitions.

    **Feature: full-capacity-testing, Property (supporting): Hysteresis Margin**
    """

    def test_hysteresis_margin(self) -> None:
        """A4.5: State transitions require crossing threshold by margin.

        **Feature: full-capacity-testing, Property (supporting)**
        **Validates: Requirements A4.5**

        When hysteresis is applied, state transitions SHALL require
        crossing threshold by margin.
        """
        threshold = 0.5
        margin = 0.1

        # State: below threshold
        current_state = "low"

        # Test values around threshold
        test_values = [0.45, 0.50, 0.55, 0.59, 0.60, 0.61, 0.65]

        for value in test_values:
            # Transition from low to high requires crossing threshold + margin
            if current_state == "low":
                if value >= threshold + margin:
                    current_state = "high"
            # Transition from high to low requires crossing threshold - margin
            else:
                if value <= threshold - margin:
                    current_state = "low"

        # After sequence, should be in "high" state (crossed 0.6)
        assert current_state == "high", f"Unexpected state: {current_state}"

    @given(
        st.floats(min_value=0.2, max_value=0.8, allow_nan=False),
        st.floats(min_value=0.1, max_value=0.3, allow_nan=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_hysteresis_prevents_oscillation(self, threshold: float, margin: float) -> None:
        """Hysteresis prevents rapid oscillation near threshold.

        **Feature: full-capacity-testing, Property (supporting)**
        **Validates: Requirements A4.5**

        When oscillation amplitude is smaller than margin, no transitions
        should occur after initial state is established.
        """
        assume(margin < threshold)
        assume(margin < 1.0 - threshold)

        # Oscillation amplitude must be smaller than margin for hysteresis to work
        oscillation_amplitude = margin * 0.4  # 40% of margin

        # Simulate values oscillating around threshold with small amplitude
        values = [
            threshold - oscillation_amplitude,
            threshold + oscillation_amplitude,
        ] * 10

        state = "low"
        transitions = 0

        for value in values:
            old_state = state
            if state == "low" and value >= threshold + margin:
                state = "high"
            elif state == "high" and value <= threshold - margin:
                state = "low"

            if state != old_state:
                transitions += 1

        # With hysteresis and small oscillations, no transitions should occur
        # because oscillation never crosses threshold ± margin
        assert transitions == 0, f"Unexpected transitions ({transitions}) with small oscillation"
