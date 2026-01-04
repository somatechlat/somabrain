"""Category A2: Vector Similarity Mathematical Correctness Proofs.

**Feature: full-capacity-testing**
**Validates: Requirements A2.1, A2.2, A2.3, A2.4, A2.5**

Property-based tests that PROVE the mathematical correctness of cosine
similarity computations. Uses Hypothesis for exhaustive property testing.

Mathematical Properties Verified:
- Property 5: Symmetry - cos(a, b) = cos(b, a)
- Property 6: Self-similarity - cos(a, a) = 1.0 for non-zero a
- Property 7: Boundedness - -1.0 ≤ cos(a, b) ≤ 1.0
- Property 8: Normalization - ||normalize(a)||_2 = 1.0 ± 1e-12
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st, assume

from somabrain.math.similarity import (
    cosine_similarity,
    cosine_error,
    cosine_distance,
    batch_cosine_similarity,
)
from somabrain.numerics import normalize_array


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------


@st.composite
def vector_strategy(draw: st.DrawFn, dim: int = 128) -> np.ndarray:
    """Generate random vectors for testing."""
    vec = draw(
        st.lists(
            st.floats(
                min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False
            ),
            min_size=dim,
            max_size=dim,
        )
    )
    return np.array(vec, dtype=np.float64)


@st.composite
def nonzero_vector_strategy(draw: st.DrawFn, dim: int = 128) -> np.ndarray:
    """Generate non-zero vectors for testing."""
    vec = draw(vector_strategy(dim=dim))
    # Ensure non-zero by adding small value if needed
    if np.linalg.norm(vec) < 1e-10:
        vec[0] = 1.0
    return vec


@st.composite
def unit_vector_strategy(draw: st.DrawFn, dim: int = 128) -> np.ndarray:
    """Generate unit-normalized vectors."""
    vec = draw(nonzero_vector_strategy(dim=dim))
    return vec / np.linalg.norm(vec)


# ---------------------------------------------------------------------------
# Test Class: Similarity Mathematical Correctness
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestSimilarityMathematicalCorrectness:
    """Property-based tests for similarity mathematical correctness.

    **Feature: full-capacity-testing, Property 5-8: Vector Similarity**
    """

    @given(vector_strategy(), vector_strategy())
    @settings(max_examples=200, deadline=None)
    def test_symmetry(self, a: np.ndarray, b: np.ndarray) -> None:
        """A2.1: Cosine similarity is symmetric.

        **Feature: full-capacity-testing, Property 5: Cosine Similarity Symmetry**
        **Validates: Requirements A2.1**

        For any vectors a and b, cosine similarity SHALL be symmetric:
        cos(a, b) = cos(b, a).
        """
        sim_ab = cosine_similarity(a, b)
        sim_ba = cosine_similarity(b, a)

        assert (
            abs(sim_ab - sim_ba) < 1e-10
        ), f"Symmetry violated: cos(a,b)={sim_ab}, cos(b,a)={sim_ba}"

    @given(nonzero_vector_strategy())
    @settings(max_examples=200, deadline=None)
    def test_self_similarity(self, a: np.ndarray) -> None:
        """A2.2: Self-similarity equals 1.0 for non-zero vectors.

        **Feature: full-capacity-testing, Property 6: Self-Similarity Identity**
        **Validates: Requirements A2.2**

        For any non-zero vector a, self-similarity SHALL equal 1.0:
        cos(a, a) = 1.0.
        """
        # Ensure vector is non-zero
        assume(np.linalg.norm(a) > 1e-10)

        sim = cosine_similarity(a, a)

        assert abs(sim - 1.0) < 1e-10, f"Self-similarity not 1.0: {sim}"

    @given(vector_strategy(), vector_strategy())
    @settings(max_examples=200, deadline=None)
    def test_boundedness(self, a: np.ndarray, b: np.ndarray) -> None:
        """A2.3: Cosine similarity is bounded in [-1.0, 1.0].

        **Feature: full-capacity-testing, Property 7: Similarity Boundedness**
        **Validates: Requirements A2.3**

        For any vectors a and b, cosine similarity SHALL be bounded:
        -1.0 ≤ cos(a, b) ≤ 1.0.
        """
        sim = cosine_similarity(a, b)

        assert -1.0 <= sim <= 1.0, f"Boundedness violated: {sim}"

    @given(vector_strategy())
    @settings(max_examples=200, deadline=None)
    def test_zero_handling(self, a: np.ndarray) -> None:
        """A2.4: Zero vectors return 0.0 without NaN or infinity.

        **Feature: full-capacity-testing, Property 7 (edge case): Zero Handling**
        **Validates: Requirements A2.4**

        When zero vectors are involved, the system SHALL return 0.0
        without NaN or infinity.
        """
        zero = np.zeros_like(a)

        # Zero with any vector should return 0.0
        sim = cosine_similarity(zero, a)

        assert sim == 0.0, f"Zero handling failed: {sim}"
        assert not np.isnan(sim), "NaN returned for zero vector"
        assert not np.isinf(sim), "Infinity returned for zero vector"

    @given(nonzero_vector_strategy())
    @settings(max_examples=200, deadline=None)
    def test_normalization(self, a: np.ndarray) -> None:
        """A2.5: Normalized vectors have L2 norm = 1.0 ± 1e-12.

        **Feature: full-capacity-testing, Property 8: Normalization Unit Norm**
        **Validates: Requirements A2.5**

        For any vector a, after normalization the L2 norm SHALL equal
        1.0 ± 1e-12.
        """
        # Ensure non-zero
        assume(np.linalg.norm(a) > 1e-10)

        # Normalize
        normalized = normalize_array(a, axis=-1, keepdims=False)
        norm = float(np.linalg.norm(normalized))

        assert abs(norm - 1.0) < 1e-12, f"Normalization failed: norm={norm}"


# ---------------------------------------------------------------------------
# Additional Tests for Derived Functions
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestSimilarityDerivedFunctions:
    """Tests for cosine_error, cosine_distance, and batch operations."""

    @given(unit_vector_strategy(), unit_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_cosine_error_bounds(self, a: np.ndarray, b: np.ndarray) -> None:
        """Cosine error is bounded in [0, 1]."""
        error = cosine_error(a, b)

        assert 0.0 <= error <= 1.0, f"Error out of bounds: {error}"

    @given(unit_vector_strategy(), unit_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_cosine_distance_bounds(self, a: np.ndarray, b: np.ndarray) -> None:
        """Cosine distance is bounded in [0, 2]."""
        dist = cosine_distance(a, b)

        assert 0.0 <= dist <= 2.0, f"Distance out of bounds: {dist}"

    @given(unit_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_cosine_error_self_is_zero(self, a: np.ndarray) -> None:
        """Cosine error with self is 0."""
        error = cosine_error(a, a)

        assert abs(error) < 1e-10, f"Self-error not zero: {error}"

    @given(unit_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_cosine_distance_self_is_zero(self, a: np.ndarray) -> None:
        """Cosine distance with self is 0."""
        dist = cosine_distance(a, a)

        assert abs(dist) < 1e-10, f"Self-distance not zero: {dist}"

    def test_batch_cosine_similarity_matches_individual(self) -> None:
        """Batch similarity matches individual computations."""
        rng = np.random.default_rng(42)
        query = rng.standard_normal(128)
        query = query / np.linalg.norm(query)

        candidates = rng.standard_normal((10, 128))
        candidates = candidates / np.linalg.norm(candidates, axis=1, keepdims=True)

        # Batch computation
        batch_sims = batch_cosine_similarity(query, candidates)

        # Individual computations
        individual_sims = [cosine_similarity(query, c) for c in candidates]

        # Compare
        for i, (batch, indiv) in enumerate(zip(batch_sims, individual_sims)):
            assert (
                abs(batch - indiv) < 1e-10
            ), f"Batch mismatch at {i}: batch={batch}, individual={indiv}"


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestSimilarityEdgeCases:
    """Edge case tests for similarity functions."""

    def test_opposite_vectors(self) -> None:
        """Opposite vectors have similarity -1.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([-1.0, 0.0, 0.0])

        sim = cosine_similarity(a, b)
        assert abs(sim - (-1.0)) < 1e-10, f"Opposite vectors: {sim}"

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors have similarity 0.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])

        sim = cosine_similarity(a, b)
        assert abs(sim) < 1e-10, f"Orthogonal vectors: {sim}"

    def test_identical_vectors(self) -> None:
        """Identical vectors have similarity 1.0."""
        a = np.array([1.0, 2.0, 3.0])

        sim = cosine_similarity(a, a)
        assert abs(sim - 1.0) < 1e-10, f"Identical vectors: {sim}"

    def test_dimension_mismatch_raises(self) -> None:
        """Dimension mismatch raises ValueError."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0])

        with pytest.raises(ValueError, match="dimension mismatch"):
            cosine_similarity(a, b)

    def test_very_small_vectors(self) -> None:
        """Very small vectors are handled correctly."""
        a = np.array([1e-15, 1e-15, 1e-15])
        b = np.array([1.0, 0.0, 0.0])

        sim = cosine_similarity(a, b)
        # Should return 0.0 for near-zero vectors
        assert sim == 0.0, f"Small vector handling: {sim}"

    def test_large_dimension_vectors(self) -> None:
        """Large dimension vectors work correctly."""
        rng = np.random.default_rng(42)
        dim = 10000
        a = rng.standard_normal(dim)
        b = rng.standard_normal(dim)

        sim = cosine_similarity(a, b)

        assert -1.0 <= sim <= 1.0, f"Large dim out of bounds: {sim}"
        assert not np.isnan(sim), "NaN for large dimension"