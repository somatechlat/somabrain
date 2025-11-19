"""Property‑based tests for :class:`somabrain.sleep.SleepStateManager`.

These tests avoid hard‑coded numbers. They generate random ``SleepParameters``
instances (bounded by the dataclass defaults) and verify that the
``compute_parameters`` method:

1. Never produces a ``K`` smaller than ``K_min``.
2. Never produces a ``t`` smaller than ``t_min``.
3. Returns a dictionary with exactly the six expected keys.
4. Applies a monotonic scaling rule across states (ACTIVE → LIGHT → DEEP →
   FREEZE) – each subsequent state must have ``K`` less‑or‑equal and ``t``
   greater‑or‑equal compared to the previous state.

The test uses the ``hypothesis`` library to explore a wide range of input
values while keeping the execution time short (max examples = 20).
"""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from somabrain.sleep import SleepState, SleepStateManager, SleepParameters


@settings(max_examples=20)
@given(
    K=st.integers(min_value=1, max_value=500),
    t=st.floats(min_value=0.1, max_value=100.0),
    tau=st.floats(min_value=0.1, max_value=10.0),
    eta=st.floats(min_value=0.0, max_value=0.2),
    lambda_=st.floats(min_value=0.0, max_value=0.05),
    B=st.floats(min_value=0.0, max_value=1.0),
)
def test_compute_parameters_respects_bounds_and_keys(K, t, tau, eta, lambda_, B):
    """Validate that ``compute_parameters`` respects the configured minima.

    The test constructs a ``SleepParameters`` instance with the generated
    values, injects it into a ``SleepStateManager`` and then checks the four
    invariants listed in the module docstring.
    """
    params = SleepParameters(
        K=K,
        t=t,
        tau=tau,
        eta=eta,
        lambda_=lambda_,
        B=B,
    )
    manager = SleepStateManager()
    # Override the manager's default parameters with our generated ones.
    manager.parameters = params

    # Compute for each state and collect the results.
    results = {state: manager.compute_parameters(state) for state in SleepState}

    # 1. All result dicts must contain exactly the six expected keys.
    expected_keys = {"K", "t", "tau", "eta", "lambda", "B"}
    for state, out in results.items():
        assert set(out.keys()) == expected_keys, f"Missing keys for {state}"

        # 2. ``K`` and ``t`` must respect the minima defined in the dataclass.
        assert out["K"] >= manager.parameters.K_min
        assert out["t"] >= manager.parameters.t_min

    # 3. Verify monotonic scaling across the state graph.
    #   ACTIVE -> LIGHT -> DEEP -> FREEZE
    order = [SleepState.ACTIVE, SleepState.LIGHT, SleepState.DEEP, SleepState.FREEZE]
    for prev, nxt in zip(order, order[1:]):
        prev_res = results[prev]
        nxt_res = results[nxt]
        # K should never increase when moving deeper.
        assert nxt_res["K"] <= prev_res["K"]
        # t should never decrease when moving deeper.
        assert nxt_res["t"] >= prev_res["t"]
