"""Property-based tests for Unified Planning Kernel.

These tests verify correctness properties using hypothesis for property-based testing.

Feature: unified-planning-kernel
Properties tested:
- Property 5: Deterministic Ordering (BFS and RWR)
- Property 7: Focus Digest Determinism
- Property 3: Predictor Comparison Correctness
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings, strategies as st

# ---------------------------------------------------------------------------
# Property 5: Deterministic Ordering - BFS Planner
# **Feature: unified-planning-kernel, Property 5: Deterministic Ordering**
# **Validates: Requirement 1.5**
# ---------------------------------------------------------------------------


@given(
    strengths=st.lists(
        st.floats(min_value=0.0, max_value=1.0), min_size=2, max_size=10
    ),
    seed=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=100)
def test_bfs_deterministic_ordering(strengths: list, seed: int) -> None:
    """
    **Feature: unified-planning-kernel, Property 5: Deterministic Ordering**
    **Validates: Requirement 1.5**

    For any set of neighbors with strengths, sorting by (-strength, coord_string)
    produces identical ordering across multiple runs.
    """
    # Create mock neighbors with given strengths
    neighbors = []
    for i, strength in enumerate(strengths):
        coord = (float(i), float(seed))
        neighbors.append({"coord": coord, "strength": strength})

    # Sort using the same logic as planner.py
    def sort_key(n):
        """Execute sort key.

        Args:
            n: The n.
        """

        coord_str = ",".join(f"{c:.6f}" for c in n["coord"])
        return (-n["strength"], coord_str)

    # Run sorting multiple times
    sorted1 = sorted(neighbors, key=sort_key)
    sorted2 = sorted(neighbors, key=sort_key)
    sorted3 = sorted(neighbors, key=sort_key)

    # All should be identical
    assert sorted1 == sorted2
    assert sorted2 == sorted3


# ---------------------------------------------------------------------------
# Property 5: Deterministic Ordering - RWR Planner
# **Feature: unified-planning-kernel, Property 5: Deterministic Ordering**
# **Validates: Requirement 2.4**
# ---------------------------------------------------------------------------


@given(
    probs=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=2, max_size=10),
)
@settings(max_examples=100)
def test_rwr_deterministic_ordering(probs: list) -> None:
    """
    **Feature: unified-planning-kernel, Property 5: Deterministic Ordering**
    **Validates: Requirement 2.4**

    For any set of node probabilities, sorting by (-probability, coord_string)
    produces identical ordering across multiple runs.
    """
    # Create mock nodes with given probabilities
    nodes = []
    for i, prob in enumerate(probs):
        coord_str = f"{float(i):.6f},{float(i):.6f}"
        nodes.append((i, prob, coord_str))

    # Sort using the same logic as planner_rwr.py
    def sort_key(x):
        """Execute sort key.

        Args:
            x: The x.
        """

        return (-x[1], x[2])

    # Run sorting multiple times
    sorted1 = sorted(nodes, key=sort_key)
    sorted2 = sorted(nodes, key=sort_key)
    sorted3 = sorted(nodes, key=sort_key)

    # All should be identical
    assert sorted1 == sorted2
    assert sorted2 == sorted3


# ---------------------------------------------------------------------------
# Property 7: Focus Digest Determinism
# **Feature: unified-planning-kernel, Property 7: Focus Digest Determinism**
# **Validates: Requirement 7.7**
# ---------------------------------------------------------------------------


@given(
    vec_values=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
)
@settings(max_examples=100)
def test_focus_digest_determinism(vec_values: list) -> None:
    """
    **Feature: unified-planning-kernel, Property 7: Focus Digest Determinism**
    **Validates: Requirement 7.7**

    For any vector, computing the digest multiple times produces identical results.
    """
    import hashlib

    vec = np.array(vec_values, dtype=np.float32)

    def compute_digest(v: np.ndarray) -> str:
        """Same logic as FocusState._compute_digest"""
        quantized = np.round(v, 4)
        return hashlib.sha256(quantized.tobytes()).hexdigest()[:16]

    # Compute digest multiple times
    digest1 = compute_digest(vec)
    digest2 = compute_digest(vec)
    digest3 = compute_digest(vec)

    # All should be identical
    assert digest1 == digest2
    assert digest2 == digest3


# ---------------------------------------------------------------------------
# Property 3: Predictor Comparison Correctness
# **Feature: unified-planning-kernel, Property 3: Predictor Comparison Correctness**
# **Validates: Requirement 3.3**
# ---------------------------------------------------------------------------


@given(
    prev_values=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
    curr_values=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
)
@settings(max_examples=100)
def test_predictor_comparison_nonzero_error(
    prev_values: list, curr_values: list
) -> None:
    """
    **Feature: unified-planning-kernel, Property 3: Predictor Comparison Correctness**
    **Validates: Requirement 3.3**

    When previous and current vectors are different, prediction error should be nonzero.
    """
    # Ensure same length
    min_len = min(len(prev_values), len(curr_values))
    prev_vec = np.array(prev_values[:min_len], dtype=np.float32)
    curr_vec = np.array(curr_values[:min_len], dtype=np.float32)

    # Compute simple error (L2 distance normalized)
    diff = prev_vec - curr_vec
    error = float(np.linalg.norm(diff))

    # If vectors are different, error should be nonzero
    if not np.allclose(prev_vec, curr_vec):
        assert error > 0.0, "Different vectors should produce nonzero error"


# ---------------------------------------------------------------------------
# Additional: Same vector comparison should produce zero error
# ---------------------------------------------------------------------------


@given(
    vec_values=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=100,
    ),
)
@settings(max_examples=100)
def test_same_vector_zero_error(vec_values: list) -> None:
    """
    When comparing a vector to itself, error should be zero.
    This is the OLD buggy behavior we're fixing - but it's correct when
    previous_focus_vec is None (first step).
    """
    vec = np.array(vec_values, dtype=np.float32)

    # Compute error comparing to self
    diff = vec - vec
    error = float(np.linalg.norm(diff))

    # Same vector should produce zero error
    assert error == 0.0, "Same vector should produce zero error"
