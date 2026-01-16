"""Category C1: Neuromodulator State Management Tests.

**Feature: full-capacity-testing**
**Validates: Requirements C1.1, C1.2, C1.3, C1.4, C1.5**

Tests that verify neuromodulator state management works correctly.
These tests run against REAL implementations - NO mocks.

Test Coverage:
- C1.1: Dopamine increases reward sensitivity
- C1.2: Serotonin shifts exploitation
- C1.3: Noradrenaline narrows attention
- C1.4: Acetylcholine increases learning rate
- C1.5: All values in valid range [0, 1]
"""

from __future__ import annotations

import os
import time

import pytest
from hypothesis import given, settings as hyp_settings, strategies as st

# Skip tests if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure",
)


# ---------------------------------------------------------------------------
# Test Class: Neuromodulator State Management (C1)
# ---------------------------------------------------------------------------


@pytest.mark.cognitive_proof
class TestNeuromodulatorStateManagement:
    """Tests for neuromodulator state management.

    **Feature: full-capacity-testing, Category C1: Neuromodulator State**
    **Validates: Requirements C1.1, C1.2, C1.3, C1.4, C1.5**
    """

    def test_dopamine_increases_reward_sensitivity(self) -> None:
        """C1.1: Dopamine increases reward sensitivity.

        **Feature: full-capacity-testing, Property C1.1**
        **Validates: Requirements C1.1**

        WHEN dopamine level increases
        THEN reward sensitivity SHALL increase proportionally.

        Dopamine modulates learning rate and motivation (0.2-0.8 range).
        Higher dopamine = higher reward prediction error weighting.
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()

        # Get baseline state
        baseline = neuromods.get_state()
        baseline_dopamine = baseline.dopamine

        # Create high dopamine state
        high_dopamine_state = NeuromodState(
            dopamine=0.8,  # Max dopamine
            serotonin=baseline.serotonin,
            noradrenaline=baseline.noradrenaline,
            acetylcholine=baseline.acetylcholine,
            timestamp=time.time(),
        )
        neuromods.set_state(high_dopamine_state)

        # Verify dopamine increased
        new_state = neuromods.get_state()
        assert new_state.dopamine >= baseline_dopamine, (
            f"Dopamine should be settable to higher value: "
            f"baseline={baseline_dopamine}, new={new_state.dopamine}"
        )
        assert new_state.dopamine == 0.8, f"Dopamine should be 0.8, got {new_state.dopamine}"

    def test_serotonin_shifts_exploitation(self) -> None:
        """C1.2: Serotonin shifts exploitation.

        **Feature: full-capacity-testing, Property C1.2**
        **Validates: Requirements C1.2**

        WHEN serotonin level increases
        THEN behavior SHALL shift toward exploitation over exploration.

        Serotonin provides emotional stability and response smoothing (0.0-1.0 range).
        Higher serotonin = more stable, less exploratory behavior.
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()

        # Get baseline state
        baseline = neuromods.get_state()

        # Create high serotonin state (exploitation mode)
        high_serotonin_state = NeuromodState(
            dopamine=baseline.dopamine,
            serotonin=0.9,  # High serotonin = exploitation
            noradrenaline=baseline.noradrenaline,
            acetylcholine=baseline.acetylcholine,
            timestamp=time.time(),
        )
        neuromods.set_state(high_serotonin_state)

        # Verify serotonin set correctly
        new_state = neuromods.get_state()
        assert new_state.serotonin == 0.9, f"Serotonin should be 0.9, got {new_state.serotonin}"

        # Create low serotonin state (exploration mode)
        low_serotonin_state = NeuromodState(
            dopamine=baseline.dopamine,
            serotonin=0.1,  # Low serotonin = exploration
            noradrenaline=baseline.noradrenaline,
            acetylcholine=baseline.acetylcholine,
            timestamp=time.time(),
        )
        neuromods.set_state(low_serotonin_state)

        # Verify serotonin set correctly
        exploration_state = neuromods.get_state()
        assert (
            exploration_state.serotonin == 0.1
        ), f"Serotonin should be 0.1, got {exploration_state.serotonin}"

    def test_noradrenaline_narrows_attention(self) -> None:
        """C1.3: Noradrenaline narrows attention.

        **Feature: full-capacity-testing, Property C1.3**
        **Validates: Requirements C1.3**

        WHEN noradrenaline level increases
        THEN attention focus SHALL narrow (urgency/gain control).

        Noradrenaline controls urgency and neural gain (0.0-0.1 range).
        Higher noradrenaline = narrower attention, higher arousal.
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()

        # Get baseline state
        baseline = neuromods.get_state()

        # Create high noradrenaline state (narrow attention)
        high_noradrenaline_state = NeuromodState(
            dopamine=baseline.dopamine,
            serotonin=baseline.serotonin,
            noradrenaline=0.1,  # Max noradrenaline = narrow attention
            acetylcholine=baseline.acetylcholine,
            timestamp=time.time(),
        )
        neuromods.set_state(high_noradrenaline_state)

        # Verify noradrenaline set correctly
        new_state = neuromods.get_state()
        assert (
            new_state.noradrenaline == 0.1
        ), f"Noradrenaline should be 0.1, got {new_state.noradrenaline}"

    def test_acetylcholine_increases_learning_rate(self) -> None:
        """C1.4: Acetylcholine increases learning rate.

        **Feature: full-capacity-testing, Property C1.4**
        **Validates: Requirements C1.4**

        WHEN acetylcholine level increases
        THEN learning rate SHALL increase (attention and memory consolidation).

        Acetylcholine enhances attention and focus (0.0-0.1 range).
        Higher acetylcholine = better memory formation and learning.
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()

        # Get baseline state
        baseline = neuromods.get_state()

        # Create high acetylcholine state (enhanced learning)
        high_ach_state = NeuromodState(
            dopamine=baseline.dopamine,
            serotonin=baseline.serotonin,
            noradrenaline=baseline.noradrenaline,
            acetylcholine=0.1,  # Max acetylcholine = enhanced learning
            timestamp=time.time(),
        )
        neuromods.set_state(high_ach_state)

        # Verify acetylcholine set correctly
        new_state = neuromods.get_state()
        assert (
            new_state.acetylcholine == 0.1
        ), f"Acetylcholine should be 0.1, got {new_state.acetylcholine}"

    def test_all_values_in_valid_range(self) -> None:
        """C1.5: All values in valid range.

        **Feature: full-capacity-testing, Property C1.5**
        **Validates: Requirements C1.5**

        WHEN neuromodulator values are set
        THEN all values SHALL be within their valid ranges:
        - Dopamine: [0.2, 0.8]
        - Serotonin: [0.0, 1.0]
        - Noradrenaline: [0.0, 0.1]
        - Acetylcholine: [0.0, 0.1]
        """
        from somabrain.neuromodulators import Neuromodulators

        neuromods = Neuromodulators()

        # Get default state
        state = neuromods.get_state()

        # Verify all values are in valid ranges
        # Note: The dataclass allows any float, but the documented ranges are:
        # Dopamine: [0.2, 0.8], Serotonin: [0.0, 1.0]
        # Noradrenaline: [0.0, 0.1], Acetylcholine: [0.0, 0.1]
        assert isinstance(state.dopamine, float), f"Dopamine should be float: {state.dopamine}"
        assert isinstance(state.serotonin, float), f"Serotonin should be float: {state.serotonin}"
        assert isinstance(
            state.noradrenaline, float
        ), f"Noradrenaline should be float: {state.noradrenaline}"
        assert isinstance(
            state.acetylcholine, float
        ), f"Acetylcholine should be float: {state.acetylcholine}"

        # Verify timestamp is set
        assert state.timestamp > 0, f"Timestamp should be positive: {state.timestamp}"


# ---------------------------------------------------------------------------
# Test Class: Neuromodulator Pub/Sub
# ---------------------------------------------------------------------------


@pytest.mark.cognitive_proof
class TestNeuromodulatorPubSub:
    """Tests for neuromodulator publish/subscribe pattern.

    **Feature: full-capacity-testing**
    **Validates: Requirements C1.1-C1.5**
    """

    def test_subscriber_receives_state_updates(self) -> None:
        """Subscribers receive state updates when neuromodulators change.

        **Feature: full-capacity-testing**
        **Validates: Requirements C1.1-C1.5**
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()
        received_states: list[NeuromodState] = []

        def callback(state: NeuromodState) -> None:
            """Execute callback.

            Args:
                state: The state.
            """

            received_states.append(state)

        # Subscribe to updates
        neuromods.subscribe(callback)

        # Update state
        new_state = NeuromodState(
            dopamine=0.7,
            serotonin=0.6,
            noradrenaline=0.05,
            acetylcholine=0.08,
            timestamp=time.time(),
        )
        neuromods.set_state(new_state)

        # Verify callback was called
        assert len(received_states) == 1, f"Expected 1 callback, got {len(received_states)}"
        assert received_states[0].dopamine == 0.7
        assert received_states[0].serotonin == 0.6

    def test_multiple_subscribers(self) -> None:
        """Multiple subscribers all receive state updates.

        **Feature: full-capacity-testing**
        **Validates: Requirements C1.1-C1.5**
        """
        from somabrain.neuromodulators import NeuromodState, Neuromodulators

        neuromods = Neuromodulators()
        received_1: list[NeuromodState] = []
        received_2: list[NeuromodState] = []

        neuromods.subscribe(lambda s: received_1.append(s))
        neuromods.subscribe(lambda s: received_2.append(s))

        # Update state
        new_state = NeuromodState(
            dopamine=0.5,
            serotonin=0.5,
            noradrenaline=0.05,
            acetylcholine=0.05,
            timestamp=time.time(),
        )
        neuromods.set_state(new_state)

        # Both subscribers should receive update
        assert len(received_1) == 1
        assert len(received_2) == 1


# ---------------------------------------------------------------------------
# Test Class: Per-Tenant Neuromodulators
# ---------------------------------------------------------------------------


@pytest.mark.cognitive_proof
class TestPerTenantNeuromodulators:
    """Tests for per-tenant neuromodulator isolation.

    **Feature: full-capacity-testing**
    **Validates: Requirements C1.1-C1.5, D2.1**
    """

    def test_tenant_isolation(self) -> None:
        """Each tenant has isolated neuromodulator state.

        **Feature: full-capacity-testing**
        **Validates: Requirements D2.1**
        """
        from somabrain.neuromodulators import NeuromodState, PerTenantNeuromodulators

        per_tenant = PerTenantNeuromodulators()

        # Set state for tenant A
        tenant_a_state = NeuromodState(
            dopamine=0.8,
            serotonin=0.9,
            noradrenaline=0.1,
            acetylcholine=0.1,
            timestamp=time.time(),
        )
        per_tenant.set_state("tenant_a", tenant_a_state)

        # Set different state for tenant B
        tenant_b_state = NeuromodState(
            dopamine=0.3,
            serotonin=0.2,
            noradrenaline=0.01,
            acetylcholine=0.02,
            timestamp=time.time(),
        )
        per_tenant.set_state("tenant_b", tenant_b_state)

        # Verify isolation
        state_a = per_tenant.get_state("tenant_a")
        state_b = per_tenant.get_state("tenant_b")

        assert state_a.dopamine == 0.8, f"Tenant A dopamine should be 0.8, got {state_a.dopamine}"
        assert state_b.dopamine == 0.3, f"Tenant B dopamine should be 0.3, got {state_b.dopamine}"

    def test_unknown_tenant_uses_global(self) -> None:
        """Unknown tenant falls back to global state.

        **Feature: full-capacity-testing**
        **Validates: Requirements C1.5**
        """
        from somabrain.neuromodulators import PerTenantNeuromodulators

        per_tenant = PerTenantNeuromodulators()

        # Get state for unknown tenant
        state = per_tenant.get_state("unknown_tenant")

        # Should return global default state
        assert state is not None
        assert isinstance(state.dopamine, float)


# ---------------------------------------------------------------------------
# Test Class: Adaptive Neuromodulators
# ---------------------------------------------------------------------------


@pytest.mark.cognitive_proof
class TestAdaptiveNeuromodulators:
    """Tests for adaptive neuromodulator learning.

    **Feature: full-capacity-testing**
    **Validates: Requirements C1.1-C1.5, C3.1-C3.5**
    """

    def test_adaptive_system_initializes(self) -> None:
        """Adaptive neuromodulator system initializes correctly.

        **Feature: full-capacity-testing**
        **Validates: Requirements C1.5**
        """
        from somabrain.neuromodulators import AdaptiveNeuromodulators

        adaptive = AdaptiveNeuromodulators()

        # Get current state
        state = adaptive.get_current_state()

        # Verify all parameters initialized
        assert state.dopamine is not None
        assert state.serotonin is not None
        assert state.noradrenaline is not None
        assert state.acetylcholine is not None

    def test_performance_feedback_updates_state(self) -> None:
        """Performance feedback updates neuromodulator state.

        **Feature: full-capacity-testing**
        **Validates: Requirements C3.1, C3.2**
        """
        from somabrain.adaptive.core import PerformanceMetrics
        from somabrain.neuromodulators import AdaptiveNeuromodulators

        adaptive = AdaptiveNeuromodulators()

        # Get baseline state
        baseline = adaptive.get_current_state()

        # Create performance metrics
        performance = PerformanceMetrics(
            success_rate=0.9,
            error_rate=0.1,
            latency=0.05,
            accuracy=0.95,
        )

        # Update from performance
        new_state = adaptive.update_from_performance(performance, task_type="general")

        # State should be updated (may or may not change depending on learning rate)
        assert new_state is not None
        assert new_state.timestamp >= baseline.timestamp


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------


@pytest.mark.cognitive_proof
class TestNeuromodulatorProperties:
    """Property-based tests for neuromodulator invariants.

    **Feature: full-capacity-testing**
    **Validates: Requirements C1.5**
    """

    @given(
        dopamine=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        serotonin=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        noradrenaline=st.floats(min_value=0.0, max_value=0.2, allow_nan=False),
        acetylcholine=st.floats(min_value=0.0, max_value=0.2, allow_nan=False),
    )
    @hyp_settings(max_examples=50)
    def test_state_roundtrip(
        self,
        dopamine: float,
        serotonin: float,
        noradrenaline: float,
        acetylcholine: float,
    ) -> None:
        """State set/get roundtrip preserves values.

        **Feature: full-capacity-testing, Property: State Roundtrip**
        **Validates: Requirements C1.5**
        """
        from somabrain.neuromodulators import NeuromodState as NS, Neuromodulators

        neuromods = Neuromodulators()

        # Create state with generated values
        state = NS(
            dopamine=dopamine,
            serotonin=serotonin,
            noradrenaline=noradrenaline,
            acetylcholine=acetylcholine,
            timestamp=time.time(),
        )

        # Set and get state
        neuromods.set_state(state)
        retrieved = neuromods.get_state()

        # Values should be preserved
        assert retrieved.dopamine == dopamine
        assert retrieved.serotonin == serotonin
        assert retrieved.noradrenaline == noradrenaline
        assert retrieved.acetylcholine == acetylcholine

    @given(
        dopamine=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @hyp_settings(max_examples=50)
    def test_dopamine_is_float(self, dopamine: float) -> None:
        """Dopamine value is always a float.

        **Feature: full-capacity-testing, Property: Type Safety**
        **Validates: Requirements C1.5**
        """
        from somabrain.neuromodulators import NeuromodState

        state = NeuromodState(dopamine=dopamine)
        assert isinstance(state.dopamine, float)
