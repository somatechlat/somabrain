"""Property-based tests for Cosine Similarity functions.

**Feature: global-architecture-refactor, Properties 1-4**
**Validates: Requirements 4.5, 11.1**
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings as hyp_settings, strategies as st

from somabrain.math.similarity import (
    cosine_similarity,
    cosine_error,
    cosine_distance,
    batch_cosine_similarity,
)


dim_strategy = st.integers(min_value=2, max_value=2048)


class TestCosineSimilaritySymmetry:
    """Property 1: Cosine Similarity Symmetry."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_symmetry_random_vectors(self, dim: int) -> None:
        """Verify cosine(a, b) == cosine(b, a)."""
        rng = np.random.default_rng()
        a = rng.uniform(-100, 100, size=dim)
        b = rng.uniform(-100, 100, size=dim)

        sim_ab = cosine_similarity(a, b)
        sim_ba = cosine_similarity(b, a)

        assert abs(sim_ab - sim_ba) < 1e-10

    def test_symmetry_edge_cases(self) -> None:
        """Verify symmetry for edge case vectors."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        assert cosine_similarity(a, b) == cosine_similarity(b, a)


class TestCosineSelfSimilarity:
    """Property 2: Cosine Self-Similarity."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_self_similarity_random_vectors(self, dim: int) -> None:
        """Verify cosine(v, v) == 1.0 for non-zero vectors."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)
        if np.linalg.norm(v) < 1e-10:
            v[0] = 1.0

        sim = cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-10

    def test_self_similarity_standard_basis(self) -> None:
        """Verify self-similarity for standard basis vectors."""
        for dim in [2, 3, 10, 100]:
            v = np.zeros(dim)
            v[0] = 1.0
            sim = cosine_similarity(v, v)
            assert abs(sim - 1.0) < 1e-12


class TestCosineBoundedness:
    """Property 3: Cosine Boundedness."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_boundedness_random_vectors(self, dim: int) -> None:
        """Verify -1 <= cosine(a, b) <= 1."""
        rng = np.random.default_rng()
        a = rng.uniform(-100, 100, size=dim)
        b = rng.uniform(-100, 100, size=dim)

        sim = cosine_similarity(a, b)
        assert -1.0 <= sim <= 1.0

    def test_boundedness_achieves_extremes(self) -> None:
        """Verify that -1 and +1 are achievable."""
        v = np.array([1.0, 2.0, 3.0])
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-10
        assert abs(cosine_similarity(v, -v) - (-1.0)) < 1e-10


class TestZeroVectorHandling:
    """Property 4: Zero Vector Handling."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_zero_first_argument(self, dim: int) -> None:
        """Verify cosine(zero, v) == 0.0."""
        rng = np.random.default_rng()
        zero = np.zeros(dim)
        v = rng.uniform(-100, 100, size=dim)

        sim = cosine_similarity(zero, v)
        assert sim == 0.0

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_zero_second_argument(self, dim: int) -> None:
        """Verify cosine(v, zero) == 0.0."""
        rng = np.random.default_rng()
        zero = np.zeros(dim)
        v = rng.uniform(-100, 100, size=dim)

        sim = cosine_similarity(v, zero)
        assert sim == 0.0

    def test_both_zero(self) -> None:
        """Verify cosine(zero, zero) == 0.0."""
        zero = np.zeros(10)
        sim = cosine_similarity(zero, zero)
        assert sim == 0.0


class TestCosineErrorProperties:
    """Properties for cosine_error function."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_error_bounded_zero_one(self, dim: int) -> None:
        """Verify cosine_error is always in [0, 1]."""
        rng = np.random.default_rng()
        a = rng.uniform(-100, 100, size=dim)
        b = rng.uniform(-100, 100, size=dim)

        error = cosine_error(a, b)
        assert 0.0 <= error <= 1.0

    def test_error_identical_is_zero(self) -> None:
        """Verify cosine_error(v, v) == 0.0."""
        v = np.array([1.0, 2.0, 3.0])
        error = cosine_error(v, v)
        assert abs(error) < 1e-10


class TestCosineDistanceProperties:
    """Properties for cosine_distance function."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_distance_bounded_zero_two(self, dim: int) -> None:
        """Verify cosine_distance is always in [0, 2]."""
        rng = np.random.default_rng()
        a = rng.uniform(-100, 100, size=dim)
        b = rng.uniform(-100, 100, size=dim)

        dist = cosine_distance(a, b)
        assert 0.0 <= dist <= 2.0

    def test_distance_opposite_is_two(self) -> None:
        """Verify cosine_distance for opposite vectors is 2.0."""
        v = np.array([1.0, 2.0, 3.0])
        dist = cosine_distance(v, -v)
        assert abs(dist - 2.0) < 1e-10


class TestBatchCosineSimilarity:
    """Properties for batch_cosine_similarity function."""

    @given(
        dim=st.integers(min_value=2, max_value=256),
        n_candidates=st.integers(min_value=1, max_value=50),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_batch_matches_individual(self, dim: int, n_candidates: int) -> None:
        """Verify batch computation matches individual computations."""
        rng = np.random.default_rng()
        query = rng.uniform(-10, 10, size=dim)
        candidates = rng.uniform(-10, 10, size=(n_candidates, dim))

        batch_results = batch_cosine_similarity(query, candidates)
        individual_results = np.array([cosine_similarity(query, c) for c in candidates])

        assert np.allclose(batch_results, individual_results, atol=1e-10)

    @given(
        dim=st.integers(min_value=2, max_value=256),
        n_candidates=st.integers(min_value=1, max_value=50),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_batch_bounded(self, dim: int, n_candidates: int) -> None:
        """Verify all batch results are in [-1, 1]."""
        rng = np.random.default_rng()
        query = rng.uniform(-10, 10, size=dim)
        candidates = rng.uniform(-10, 10, size=(n_candidates, dim))

        results = batch_cosine_similarity(query, candidates)
        assert np.all(results >= -1.0) and np.all(results <= 1.0)