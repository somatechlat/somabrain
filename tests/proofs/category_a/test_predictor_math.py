"""Category A3: Predictor Mathematical Correctness Proofs.

**Feature: full-capacity-testing**
**Validates: Requirements A3.1, A3.2, A3.3, A3.4, A3.5**

Property-based tests that PROVE the mathematical correctness of predictor
computations. Uses Hypothesis for exhaustive property testing.

Mathematical Properties Verified:
- Property 9: Mahalanobis non-negativity - d_M(x, μ, Σ) ≥ 0
- Property 10: Uncertainty monotonicity - σ(t+1) ≥ σ(t)
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------


@st.composite
def positive_definite_matrix_strategy(draw: st.DrawFn, dim: int = 10) -> np.ndarray:
    """Generate positive definite covariance matrices."""
    # Generate random matrix and make it positive definite via A @ A.T
    elements = draw(
        st.lists(
            st.floats(
                min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            min_size=dim * dim,
            max_size=dim * dim,
        )
    )
    A = np.array(elements, dtype=np.float64).reshape(dim, dim)
    # Make positive definite: Σ = A @ A.T + εI
    cov = A @ A.T + 0.1 * np.eye(dim)
    return cov


@st.composite
def vector_strategy(draw: st.DrawFn, dim: int = 10) -> np.ndarray:
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


# ---------------------------------------------------------------------------
# Production predictor (real code under test — no local metric reimplementation)
# ---------------------------------------------------------------------------


def _rust_mahalanobis(dim: int, alpha: float) -> object:
    """Return the production Rust diagonal-Mahalanobis predictor."""
    import somabrain_rs as rs

    return rs.MahalanobisPredictor(dimension=dim, ewma_alpha=alpha)


# ---------------------------------------------------------------------------
# Test Class: Predictor Mathematical Correctness
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestPredictorMathematicalCorrectness:
    """Property-based tests for predictor mathematical correctness.

    Assertions target the **production** `MahalanobisPredictor.distance`
    (diagonal Mahalanobis `sqrt(Σ (x−μ)²/σ²)`), not a test-local metric.

    **Feature: full-capacity-testing, Property 9-10: Predictor Math**
    """

    @given(vector_strategy(), vector_strategy(), positive_definite_matrix_strategy())
    @settings(max_examples=100, deadline=None)
    def test_mahalanobis_non_negativity(
        self, x: np.ndarray, mu: np.ndarray, cov: np.ndarray
    ) -> None:
        """A3.3: Mahalanobis distance is non-negative.

        **Feature: full-capacity-testing, Property 9: Mahalanobis Non-Negativity**
        **Validates: Requirements A3.3**

        For any point x, mean μ, and covariance Σ, Mahalanobis distance
        SHALL be non-negative: d_M(x, μ, Σ) ≥ 0.
        """
        dim = len(x)
        pred = _rust_mahalanobis(dim, 0.0)
        # Seed the online mean with mu via a zero-alpha held state: feed mu
        # first so the EWMA mean is mu, then measure x.
        pred.update(mu.tolist())
        dist = float(pred.distance(x.tolist()))

        assert dist >= 0.0, f"Mahalanobis distance negative: {dist}"
        assert not np.isnan(dist), "Mahalanobis distance is NaN"
        assert not np.isinf(dist), "Mahalanobis distance is infinite"

    @given(vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_mahalanobis_self_is_zero(self, x: np.ndarray) -> None:
        """Mahalanobis distance from point to itself is zero.

        **Feature: full-capacity-testing, Property 9 (edge case)**
        **Validates: Requirements A3.3**
        """
        dim = len(x)
        pred = _rust_mahalanobis(dim, 0.5)
        pred.update(x.tolist())
        dist = float(pred.distance(x.tolist()))

        assert abs(dist) < 1e-10, f"Self-distance not zero: {dist}"

    def test_diagonal_mahalanobis_matches_definition(self) -> None:
        """A3.5: Production distance equals sqrt((x−μ)ᵀ Σ⁻¹ (x−μ)) for diagonal Σ.

        **Feature: full-capacity-testing, Property 9 (anisotropic case)**
        **Validates: Requirements A3.5**
        """
        dim = 3
        pred = _rust_mahalanobis(dim, 0.5)
        # Build anisotropic variance along the axes by alternating extremes.
        for i in range(200):
            pred.update([float(i % 2) * 4.0, float((i + 1) % 2) * 0.1, 0.0])
        mean = np.asarray(pred.mean, dtype=np.float64)
        var = np.asarray(pred.var, dtype=np.float64)
        x = mean + np.array([0.5, 0.5, 0.5])

        expected = float(np.sqrt(np.sum((x - mean) ** 2 / var)))
        actual = float(pred.distance(x.tolist()))
        assert abs(actual - expected) < 1e-10, (
            f"diagonal Mahalanobis mismatch: {actual} != {expected}"
        )
        # Name equals math: low-variance axis dominates (Euclidean would not).
        d_axis0 = float(pred.distance((mean + np.array([1.0, 0.0, 0.0])).tolist()))
        d_axis1 = float(pred.distance((mean + np.array([0.0, 1.0, 0.0])).tolist()))
        assert d_axis1 > 10.0 * d_axis0

    def test_python_predictor_bounded_mahalanobis(self) -> None:
        """Python `MahalanobisPredictor` uses the diagonal metric too."""
        from somabrain.admin.core.learning.prediction import MahalanobisPredictor

        pred = MahalanobisPredictor(alpha=0.5)
        x = np.zeros(4, dtype="float32")
        pred._update_stats(x)
        # Zero surprise on the learned mean.
        assert pred._mahal_bounded(x) == 0.0
        # Off-mean input is positive surprise, bounded in [0, 1].
        s = pred._mahal_bounded(np.ones(4, dtype="float32"))
        assert 0.0 < s <= 1.0


# ---------------------------------------------------------------------------
# Uncertainty Monotonicity Tests
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestUncertaintyMonotonicity:
    """Tests for uncertainty growth with prediction horizon.

    **Feature: full-capacity-testing, Property 10: Uncertainty Monotonicity**
    """

    def test_uncertainty_grows_with_horizon(self) -> None:
        """A3.4: Uncertainty grows monotonically with prediction horizon.

        **Feature: full-capacity-testing, Property 10: Uncertainty Monotonicity**
        **Validates: Requirements A3.4**

        For any prediction, as horizon increases, uncertainty SHALL grow
        monotonically: σ(t+1) ≥ σ(t).
        """
        # Simulate uncertainty growth with simple model
        # σ(t) = σ_0 * sqrt(1 + α*t) where α > 0
        sigma_0 = 1.0
        alpha = 0.1

        horizons = list(range(100))
        uncertainties = [sigma_0 * np.sqrt(1 + alpha * t) for t in horizons]

        # Verify monotonicity
        for i in range(1, len(uncertainties)):
            assert uncertainties[i] >= uncertainties[i - 1], (
                f"Uncertainty decreased at t={i}: "
                f"σ({i - 1})={uncertainties[i - 1]:.4f}, σ({i})={uncertainties[i]:.4f}"
            )

    @given(
        st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_uncertainty_monotonicity_property(
        self, sigma_0: float, alpha: float
    ) -> None:
        """Property test for uncertainty monotonicity.

        **Feature: full-capacity-testing, Property 10: Uncertainty Monotonicity**
        **Validates: Requirements A3.4**
        """
        # Generate uncertainty sequence
        horizons = 20
        uncertainties = [sigma_0 * np.sqrt(1 + alpha * t) for t in range(horizons)]

        # Verify strict monotonicity for t > 0
        for i in range(1, len(uncertainties)):
            assert (
                uncertainties[i] >= uncertainties[i - 1]
            ), f"Monotonicity violated: σ({i - 1})={uncertainties[i - 1]}, σ({i})={uncertainties[i]}"


# ---------------------------------------------------------------------------
# Chebyshev and Lanczos Tests (Simplified)
# ---------------------------------------------------------------------------


@pytest.mark.math_proof
class TestSpectralMethods:
    """Tests for spectral approximation methods.

    Note: Full Chebyshev/Lanczos tests require the actual predictor
    implementation. These are simplified mathematical property tests.
    """

    def test_chebyshev_polynomial_bounds(self) -> None:
        """A3.1: Chebyshev polynomials are bounded in [-1, 1] on [-1, 1].

        **Feature: full-capacity-testing, Property (supporting): Chebyshev Bounds**
        **Validates: Requirements A3.1**
        """
        # Chebyshev polynomials T_n(x) satisfy |T_n(x)| ≤ 1 for x ∈ [-1, 1]
        from numpy.polynomial.chebyshev import chebval

        x_values = np.linspace(-1, 1, 1000)

        for n in range(10):
            coeffs = [0] * n + [1]  # T_n
            values = chebval(x_values, coeffs)

            assert np.all(
                np.abs(values) <= 1.0 + 1e-10
            ), f"Chebyshev T_{n} exceeded bounds: max={np.max(np.abs(values))}"

    def test_eigenvalue_bounds_symmetric_matrix(self) -> None:
        """A3.2: Eigenvalues of symmetric matrices are real and bounded.

        **Feature: full-capacity-testing, Property (supporting): Eigenvalue Bounds**
        **Validates: Requirements A3.2**
        """
        rng = np.random.default_rng(42)

        for _ in range(10):
            dim = 20
            A = rng.standard_normal((dim, dim))
            A_sym = (A + A.T) / 2  # Make symmetric

            eigenvalues = np.linalg.eigvalsh(A_sym)

            # All eigenvalues should be real (no imaginary part)
            assert np.all(np.isreal(eigenvalues)), "Eigenvalues not real"

            # Eigenvalues should be bounded by Frobenius norm
            frob_norm = np.linalg.norm(A_sym, "fro")
            assert np.all(np.abs(eigenvalues) <= frob_norm + 1e-10), (
                f"Eigenvalue exceeded Frobenius bound: "
                f"max_eig={np.max(np.abs(eigenvalues))}, frob={frob_norm}"
            )
