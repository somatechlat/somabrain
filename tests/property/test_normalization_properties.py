"""Property-based tests for Vector Normalization functions.

**Feature: global-architecture-refactor, Properties 5-7**
**Validates: Requirements 4.3, 11.3**

These tests verify the mathematical invariants of the canonical normalization
implementation. All tests run against REAL implementations with no mocks.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings as hyp_settings, strategies as st

from somabrain.math.normalize import (
    normalize_vector,
    safe_normalize,
    normalize_batch,
    ensure_unit_norm,
)
from somabrain.math.similarity import cosine_similarity


dim_strategy = st.integers(min_value=2, max_value=2048)


class TestNormalizationIdempotence:
    """Property 5: Normalization Idempotence.

    normalize(normalize(v)) == normalize(v)

    **Feature: global-architecture-refactor, Property 5**
    **Validates: Requirements 4.3, 11.3**
    """

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_idempotence_random_vectors(self, dim: int) -> None:
        """Verify normalize(normalize(v)) == normalize(v)."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        once = normalize_vector(v)
        twice = normalize_vector(once)

        assert np.allclose(
            once, twice, atol=1e-6
        ), f"Idempotence violated: max diff = {np.max(np.abs(once - twice))}"

    @given(
        dim=st.integers(min_value=2, max_value=512),
        scale=st.floats(
            min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_idempotence_scaled_vectors(self, dim: int, scale: float) -> None:
        """Verify idempotence for scaled vectors."""
        rng = np.random.default_rng()
        v = rng.normal(0, 1, size=dim) * scale

        once = normalize_vector(v)
        twice = normalize_vector(once)

        assert np.allclose(once, twice, atol=1e-6)

    def test_idempotence_edge_cases(self) -> None:
        """Verify idempotence for edge case vectors."""
        # Standard basis
        for i in range(3):
            v = np.zeros(3)
            v[i] = 1.0
            once = normalize_vector(v)
            twice = normalize_vector(once)
            assert np.allclose(once, twice, atol=1e-10)

        # Zero vector stays zero
        zero = np.zeros(10)
        once = normalize_vector(zero)
        twice = normalize_vector(once)
        assert np.allclose(once, twice)


class TestNormalizationUnitNorm:
    """Property 6: Normalization Unit Norm.

    ||normalize(v)|| == 1.0 for non-zero v

    **Feature: global-architecture-refactor, Property 6**
    **Validates: Requirements 4.3, 11.3**
    """

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_unit_norm_random_vectors(self, dim: int) -> None:
        """Verify ||normalize(v)|| == 1.0 for non-zero vectors."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = 1.0

        normalized = normalize_vector(v)
        norm = np.linalg.norm(normalized)

        assert abs(norm - 1.0) < 1e-5, f"Norm {norm} != 1.0"

    @given(
        dim=st.integers(min_value=2, max_value=512),
        scale=st.floats(
            min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_unit_norm_scaled_vectors(self, dim: int, scale: float) -> None:
        """Verify unit norm regardless of input magnitude."""
        rng = np.random.default_rng()
        v = rng.normal(0, 1, size=dim) * scale

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = scale

        normalized = normalize_vector(v)
        norm = np.linalg.norm(normalized)

        assert abs(norm - 1.0) < 1e-5, f"Norm {norm} != 1.0 for scale={scale}"

    def test_unit_norm_standard_basis(self) -> None:
        """Verify unit norm for standard basis vectors."""
        for dim in [2, 3, 10, 100]:
            for i in range(min(dim, 5)):
                v = np.zeros(dim)
                v[i] = 1.0
                normalized = normalize_vector(v)
                norm = np.linalg.norm(normalized)
                assert abs(norm - 1.0) < 1e-10

    def test_zero_vector_has_zero_norm(self) -> None:
        """Verify zero vector normalizes to zero vector."""
        zero = np.zeros(10)
        normalized = normalize_vector(zero)
        norm = np.linalg.norm(normalized)
        assert norm == 0.0


class TestNormalizationDirectionPreservation:
    """Property 7: Normalization Direction Preservation.

    cosine(v, normalize(v)) == 1.0 for non-zero v

    **Feature: global-architecture-refactor, Property 7**
    **Validates: Requirements 4.3, 11.3**
    """

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_direction_preservation_random_vectors(self, dim: int) -> None:
        """Verify cosine(v, normalize(v)) == 1.0."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = 1.0

        normalized = normalize_vector(v)
        sim = cosine_similarity(v, normalized)

        assert abs(sim - 1.0) < 1e-6, f"Direction not preserved: cosine = {sim}"

    @given(
        dim=st.integers(min_value=2, max_value=512),
        scale=st.floats(
            min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_direction_preservation_scaled(self, dim: int, scale: float) -> None:
        """Verify direction preservation for scaled vectors."""
        rng = np.random.default_rng()
        v = rng.normal(0, 1, size=dim) * scale

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = scale

        normalized = normalize_vector(v)
        sim = cosine_similarity(v, normalized)

        assert abs(sim - 1.0) < 1e-6

    def test_direction_preservation_negative_scale(self) -> None:
        """Verify direction is preserved (not flipped) for positive vectors."""
        v = np.array([1.0, 2.0, 3.0])
        normalized = normalize_vector(v)

        # All components should have same sign as original
        assert np.all(np.sign(normalized) == np.sign(v))


class TestScaleInvariance:
    """Additional property: Scale Invariance.

    normalize(k*v) == normalize(v) for k > 0
    """

    @given(
        dim=st.integers(min_value=2, max_value=512),
        scale=st.floats(
            min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_scale_invariance(self, dim: int, scale: float) -> None:
        """Verify normalize(k*v) == normalize(v) for k > 0."""
        rng = np.random.default_rng()
        v = rng.normal(0, 1, size=dim)

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = 1.0

        norm_v = normalize_vector(v)
        norm_kv = normalize_vector(v * scale)

        assert np.allclose(
            norm_v, norm_kv, atol=1e-5
        ), f"Scale invariance violated: max diff = {np.max(np.abs(norm_v - norm_kv))}"


class TestSafeNormalize:
    """Properties for safe_normalize function."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_safe_normalize_returns_correct_norm(self, dim: int) -> None:
        """Verify safe_normalize returns correct original norm."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        normalized, norm = safe_normalize(v)
        expected_norm = np.linalg.norm(v)

        assert (
            abs(norm - expected_norm) < 1e-10
        ), f"Returned norm {norm} != expected {expected_norm}"

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_safe_normalize_vector_matches(self, dim: int) -> None:
        """Verify safe_normalize vector matches normalize_vector."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        safe_result, _ = safe_normalize(v)
        direct_result = normalize_vector(v)

        assert np.allclose(safe_result, direct_result, atol=1e-6)


class TestNormalizeBatch:
    """Properties for normalize_batch function."""

    @given(
        dim=st.integers(min_value=2, max_value=256),
        n_vectors=st.integers(min_value=1, max_value=50),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_batch_matches_individual(self, dim: int, n_vectors: int) -> None:
        """Verify batch normalization matches individual normalization."""
        rng = np.random.default_rng()
        vectors = rng.uniform(-100, 100, size=(n_vectors, dim))

        batch_result = normalize_batch(vectors, axis=-1)
        individual_results = np.array([normalize_vector(v) for v in vectors])

        assert np.allclose(batch_result, individual_results, atol=1e-5), (
            f"Batch doesn't match individual: max diff = "
            f"{np.max(np.abs(batch_result - individual_results))}"
        )

    @given(
        dim=st.integers(min_value=2, max_value=256),
        n_vectors=st.integers(min_value=1, max_value=50),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_batch_all_unit_norm(self, dim: int, n_vectors: int) -> None:
        """Verify all batch results have unit norm (or zero)."""
        rng = np.random.default_rng()
        vectors = rng.uniform(-100, 100, size=(n_vectors, dim))

        batch_result = normalize_batch(vectors, axis=-1)
        norms = np.linalg.norm(batch_result, axis=-1)

        # Each norm should be either 0 (zero input) or 1 (normalized)
        for i, norm in enumerate(norms):
            input_norm = np.linalg.norm(vectors[i])
            if input_norm > 1e-10:
                assert abs(norm - 1.0) < 1e-5, f"Vector {i} norm {norm} != 1.0"
            else:
                assert norm < 1e-10, f"Zero vector {i} has non-zero norm {norm}"


class TestEnsureUnitNorm:
    """Properties for ensure_unit_norm function."""

    @given(dim=dim_strategy)
    @hyp_settings(max_examples=100, deadline=5000)
    def test_ensure_unit_norm_result(self, dim: int) -> None:
        """Verify ensure_unit_norm produces unit norm vectors."""
        rng = np.random.default_rng()
        v = rng.uniform(-100, 100, size=dim)

        # Ensure non-zero
        if np.linalg.norm(v) < 1e-10:
            v[0] = 1.0

        result = ensure_unit_norm(v)
        norm = np.linalg.norm(result)

        assert abs(norm - 1.0) < 1e-5, f"ensure_unit_norm result norm {norm} != 1.0"

    def test_ensure_unit_norm_skips_already_normalized(self) -> None:
        """Verify ensure_unit_norm doesn't modify already-normalized vectors."""
        v = np.array([0.6, 0.8], dtype=np.float64)  # Already unit norm
        result = ensure_unit_norm(v, tolerance=1e-6)

        # Should be essentially unchanged
        assert np.allclose(result, v, atol=1e-6)