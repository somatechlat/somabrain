"""Tests for the sleep state manager implementation.

These tests verify that the transition matrix matches the ROAMDP specification
and that the parameter scheduling logic respects the defined bounds.
"""

from somabrain.sleep import SleepState, SleepStateManager


def test_valid_transitions():
    """All allowed transitions should return ``True`` and disallowed ones ``False``.

    The ROAMDP plan defines the following directed graph:
        ACTIVE → LIGHT → DEEP → FREEZE → LIGHT
    ``FREEZE`` can only go back to ``LIGHT`` and ``ACTIVE`` can only go to
    ``LIGHT``. Any other pair is invalid.
    """
    manager = SleepStateManager()

    # Positive paths
    assert manager.can_transition(SleepState.ACTIVE, SleepState.LIGHT)
    assert manager.can_transition(SleepState.LIGHT, SleepState.DEEP)
    assert manager.can_transition(SleepState.DEEP, SleepState.FREEZE)
    assert manager.can_transition(SleepState.FREEZE, SleepState.LIGHT)

    # Reverse or unrelated transitions must be rejected
    for from_state in SleepState:
        for to_state in SleepState:
            if (from_state, to_state) in [
                (SleepState.ACTIVE, SleepState.LIGHT),
                (SleepState.LIGHT, SleepState.DEEP),
                (SleepState.DEEP, SleepState.FREEZE),
                (SleepState.FREEZE, SleepState.LIGHT),
            ]:
                continue
            assert not manager.can_transition(from_state, to_state), f"{from_state}->{to_state} should be invalid"


def test_compute_parameters_respects_bounds():
    """Parameter scaling must never drop below the configured minima.

    The ``SleepParameters`` dataclass defines ``K_min`` and ``t_min``. The
    ``compute_parameters`` implementation scales ``K`` and ``t`` per state and
    then clamps them to these minima.
    """
    manager = SleepStateManager()
    # Use the default parameters (K=100, t=10.0, K_min=1, t_min=0.1)
    for state in SleepState:
        params = manager.compute_parameters(state)
        assert params["K"] >= manager.parameters.K_min
        assert params["t"] >= manager.parameters.t_min
