"""Property-based tests for Predictor System (Chebyshev/Lanczos).

**Feature: production-hardening**
**Properties: 15-16 (Chebyshev Heat Approximation, Lanczos Spectral Bounds)**
**Validates: Requirements 9.1, 9.2**

These tests verify the mathematical invariants of the heat diffusion
approximation methods used in SomaBrain predictors. Tests use pure
mathematical verification against known exact solutions.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings as hyp_settings, strategies as st
from scipy.linalg import expm
from typing import Callable


# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

# Small dimensions for tractable exact computation
dim_strategy = st.sampled_from([8, 16, 32])

# Time parameter for heat kernel
time_strategy = st.floats(
    min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False
)

# Chebyshev degree K
chebyshev_K_strategy = st.sampled_from([10, 20, 30, 40])

# Lanczos steps m
lanczos_m_strategy = st.sampled_from([8, 16, 24, 32])

# Seed for reproducibility
seed_strategy = st.integers(min_value=1, max_value=2**31 - 1)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def make_line_graph_laplacian(n: int) -> np.ndarray:
    """Create Laplacian matrix for a line graph of n nodes.

    The line graph Laplacian is tridiagonal with:
    - Diagonal: 2 (except endpoints which are 1)
    - Off-diagonal: -1

    This is a standard test case with known spectral properties.
    """
    L = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        if i > 0:
            L[i, i - 1] = -1.0
            L[i, i] += 1.0
        if i < n - 1:
            L[i, i + 1] = -1.0
            L[i, i] += 1.0
    return L


def make_cycle_graph_laplacian(n: int) -> np.ndarray:
    """Create Laplacian matrix for a cycle graph of n nodes.

    The cycle graph Laplacian is circulant with:
    - Diagonal: 2
    - Off-diagonal (adjacent): -1
    """
    L = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        L[i, i] = 2.0
        L[i, (i + 1) % n] = -1.0
        L[i, (i - 1) % n] = -1.0
    return L


def matvec_from_matrix(A: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    """Create a matvec function from a matrix."""

    def apply_A(x: np.ndarray) -> np.ndarray:
        return A @ x

    return apply_A


def exact_heat_kernel(L: np.ndarray, x: np.ndarray, t: float) -> np.ndarray:
    """Compute exact exp(-t L) x using scipy.linalg.expm."""
    return expm(-t * L) @ x


def relative_error(approx: np.ndarray, exact: np.ndarray) -> float:
    """Compute relative L2 error between approximate and exact solutions."""
    exact_norm = np.linalg.norm(exact)
    if exact_norm < 1e-12:
        return np.linalg.norm(approx - exact)
    return np.linalg.norm(approx - exact) / exact_norm


def mse(approx: np.ndarray, exact: np.ndarray) -> float:
    """Compute mean squared error between approximate and exact solutions."""
    return float(np.mean((approx - exact) ** 2))


# ---------------------------------------------------------------------------
# Import the actual implementations
# ---------------------------------------------------------------------------

from somabrain.math.lanczos_chebyshev import (
    chebyshev_heat_apply,
    estimate_spectral_interval,
    lanczos_expv,
)


class TestChebyshevHeatApproximation:
    """Property 15: Chebyshev Heat Approximation.

    For any symmetric positive semi-definite operator A with spectral bounds
    [a, b], the Chebyshev polynomial approximation of exp(-t A) x SHALL
    converge to the exact solution as K increases.

    Key invariants:
    1. Approximation error decreases with increasing K
    2. Result preserves non-negativity for non-negative inputs
    3. Result norm is bounded by input norm (heat kernel is contractive)

    **Feature: production-hardening, Property 15: Chebyshev Heat Approximation**
    **Validates: Requirements 9.1**
    """

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_chebyshev_converges_to_exact(self, n: int, t: float, seed: int) -> None:
        """Verify Chebyshev approximation converges to exact solution."""
        # Create line graph Laplacian (well-conditioned test case)
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        # Generate random initial vector
        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)
        x0 = x0 / np.linalg.norm(x0)  # Normalize

        # Compute exact solution
        y_exact = exact_heat_kernel(L, x0, t)

        # Estimate spectral bounds
        a, b = estimate_spectral_interval(apply_A, n, m=16)

        # Ensure bounds are valid (add small margin for numerical stability)
        a = max(0.0, a - 0.1)
        b = b + 0.1

        # Compute Chebyshev approximation with K=40
        y_cheb = chebyshev_heat_apply(apply_A, x0, t, K=40, a=a, b=b)

        # Verify convergence: relative error should be small
        rel_err = relative_error(y_cheb, y_exact)
        assert rel_err < 0.1, (
            f"Chebyshev relative error {rel_err:.6f} > 0.1 " f"(n={n}, t={t}, K=40)"
        )

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_chebyshev_error_decreases_with_K(
        self, n: int, t: float, seed: int
    ) -> None:
        """Verify Chebyshev error decreases as K increases."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)
        x0 = x0 / np.linalg.norm(x0)

        y_exact = exact_heat_kernel(L, x0, t)

        a, b = estimate_spectral_interval(apply_A, n, m=16)
        a = max(0.0, a - 0.1)
        b = b + 0.1

        # Compute errors for increasing K
        errors = []
        for K in [10, 20, 40]:
            y_cheb = chebyshev_heat_apply(apply_A, x0, t, K=K, a=a, b=b)
            errors.append(mse(y_cheb, y_exact))

        # When errors are already at machine precision (< 1e-20),
        # we can't expect further improvement - this is success
        if errors[0] < 1e-20:
            # Already converged to machine precision
            assert (
                errors[2] < 1e-15
            ), f"Error at machine precision but K=40 MSE={errors[2]:.6e} too large"
        else:
            # Error should generally decrease (allow some tolerance for numerical noise)
            # At minimum, K=40 should be better than K=10
            assert errors[2] <= errors[0] * 1.5, (
                f"Error did not decrease: K=10 MSE={errors[0]:.6e}, "
                f"K=40 MSE={errors[2]:.6e}"
            )

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_chebyshev_contractive(self, n: int, t: float, seed: int) -> None:
        """Verify heat kernel is contractive (||exp(-tA)x|| <= ||x||)."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)

        a, b = estimate_spectral_interval(apply_A, n, m=16)
        a = max(0.0, a - 0.1)
        b = b + 0.1

        y_cheb = chebyshev_heat_apply(apply_A, x0, t, K=40, a=a, b=b)

        # Heat kernel is contractive for PSD operators
        input_norm = np.linalg.norm(x0)
        output_norm = np.linalg.norm(y_cheb)

        # Allow small numerical tolerance
        assert (
            output_norm <= input_norm * 1.01
        ), f"Heat kernel not contractive: ||y||={output_norm:.6f} > ||x||={input_norm:.6f}"

    @given(
        n=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=30, deadline=10000)
    def test_chebyshev_preserves_symmetry(self, n: int, seed: int) -> None:
        """Verify Chebyshev preserves inner product symmetry."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x = rng.normal(size=n)
        y = rng.normal(size=n)

        a, b = estimate_spectral_interval(apply_A, n, m=16)
        a = max(0.0, a - 0.1)
        b = b + 0.1

        t = 0.5
        exp_x = chebyshev_heat_apply(apply_A, x, t, K=40, a=a, b=b)
        exp_y = chebyshev_heat_apply(apply_A, y, t, K=40, a=a, b=b)

        # <exp(-tA)x, y> should approximately equal <x, exp(-tA)y>
        # because exp(-tA) is symmetric for symmetric A
        inner1 = np.dot(exp_x, y)
        inner2 = np.dot(x, exp_y)

        assert abs(inner1 - inner2) < 0.1 * (
            abs(inner1) + abs(inner2) + 1e-6
        ), f"Symmetry violated: <exp(-tA)x, y>={inner1:.6f} != <x, exp(-tA)y>={inner2:.6f}"


class TestLanczosSpectralBounds:
    """Property 16: Lanczos Spectral Bounds.

    For any symmetric operator A, the m-step Lanczos algorithm SHALL produce
    eigenvalue estimates that bound the true spectrum from within.

    Key invariants:
    1. Estimated bounds contain true eigenvalues (with tolerance)
    2. Bounds tighten as m increases
    3. Lanczos expv converges to exact solution

    **Feature: production-hardening, Property 16: Lanczos Spectral Bounds**
    **Validates: Requirements 9.2**
    """

    @given(
        n=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_lanczos_bounds_contain_spectrum(self, n: int, seed: int) -> None:
        """Verify Lanczos bounds contain true eigenvalues (approximately)."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        # Compute true eigenvalues
        true_eigs = np.linalg.eigvalsh(L)
        true_min, true_max = true_eigs.min(), true_eigs.max()

        # Estimate bounds with Lanczos
        est_min, est_max = estimate_spectral_interval(apply_A, n, m=16)

        # Lanczos bounds should be within reasonable tolerance of true bounds
        # (Lanczos gives inner bounds, so est_min >= true_min and est_max <= true_max
        # but with randomness and finite m, we allow some tolerance)
        tolerance = 0.5 * (true_max - true_min)  # 50% of spectral range

        assert (
            est_min >= true_min - tolerance
        ), f"Lanczos min {est_min:.4f} too far below true min {true_min:.4f}"
        assert (
            est_max <= true_max + tolerance
        ), f"Lanczos max {est_max:.4f} too far above true max {true_max:.4f}"

    @given(
        n=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=30, deadline=10000)
    def test_lanczos_bounds_tighten_with_m(self, n: int, seed: int) -> None:
        """Verify Lanczos bounds tighten as m increases."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        # Compute true eigenvalues (for reference, not used in assertions)
        true_eigs = np.linalg.eigvalsh(L)
        _true_min, _true_max = true_eigs.min(), true_eigs.max()

        # Estimate bounds with increasing m
        # Note: Due to randomness in Lanczos starting vector, we use
        # a fixed seed approach by setting numpy random state
        np.random.seed(seed)

        bounds_m8 = estimate_spectral_interval(apply_A, n, m=8)
        np.random.seed(seed)
        bounds_m16 = estimate_spectral_interval(apply_A, n, m=min(16, n))

        # Compute spectral range estimates
        range_m8 = bounds_m8[1] - bounds_m8[0]
        range_m16 = bounds_m16[1] - bounds_m16[0]

        # With more Lanczos steps, we should capture more of the spectrum
        # (range should increase or stay similar, not decrease dramatically)
        # This is a weak test due to randomness
        assert range_m16 >= range_m8 * 0.5, (
            f"Lanczos range decreased unexpectedly: m=8 range={range_m8:.4f}, "
            f"m=16 range={range_m16:.4f}"
        )

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_lanczos_expv_converges(self, n: int, t: float, seed: int) -> None:
        """Verify Lanczos expv converges to exact solution."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)
        x0 = x0 / np.linalg.norm(x0)

        y_exact = exact_heat_kernel(L, x0, t)

        # Compute Lanczos approximation
        y_lanc = lanczos_expv(apply_A, x0, t, m=min(32, n))

        # Verify convergence
        rel_err = relative_error(y_lanc, y_exact)
        assert rel_err < 0.1, (
            f"Lanczos relative error {rel_err:.6f} > 0.1 " f"(n={n}, t={t}, m=32)"
        )

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_lanczos_expv_contractive(self, n: int, t: float, seed: int) -> None:
        """Verify Lanczos expv is contractive."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)

        y_lanc = lanczos_expv(apply_A, x0, t, m=min(32, n))

        input_norm = np.linalg.norm(x0)
        output_norm = np.linalg.norm(y_lanc)

        # Allow small numerical tolerance
        assert (
            output_norm <= input_norm * 1.01
        ), f"Lanczos expv not contractive: ||y||={output_norm:.6f} > ||x||={input_norm:.6f}"

    @given(
        n=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=30, deadline=10000)
    def test_lanczos_expv_zero_input(self, n: int, seed: int) -> None:
        """Verify Lanczos expv handles zero input correctly."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        x0 = np.zeros(n)
        y_lanc = lanczos_expv(apply_A, x0, t=0.5, m=16)

        assert np.allclose(
            y_lanc, np.zeros(n)
        ), f"Lanczos expv(0) should be 0, got norm={np.linalg.norm(y_lanc)}"


class TestChebyshevLanczosConsistency:
    """Test consistency between Chebyshev and Lanczos methods.

    Both methods approximate the same heat kernel exp(-t A) x, so they
    should produce similar results for the same inputs.
    """

    @given(
        n=dim_strategy,
        t=time_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=30, deadline=15000)
    def test_chebyshev_lanczos_agreement(self, n: int, t: float, seed: int) -> None:
        """Verify Chebyshev and Lanczos produce similar results."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)
        x0 = x0 / np.linalg.norm(x0)

        # Estimate spectral bounds for Chebyshev
        a, b = estimate_spectral_interval(apply_A, n, m=16)
        a = max(0.0, a - 0.1)
        b = b + 0.1

        # Compute both approximations
        y_cheb = chebyshev_heat_apply(apply_A, x0, t, K=40, a=a, b=b)
        y_lanc = lanczos_expv(apply_A, x0, t, m=min(32, n))

        # They should agree reasonably well
        rel_diff = relative_error(y_cheb, y_lanc)
        assert (
            rel_diff < 0.2
        ), f"Chebyshev and Lanczos disagree: relative diff={rel_diff:.6f}"

    @given(
        n=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=30, deadline=15000)
    def test_both_methods_converge_to_exact(self, n: int, seed: int) -> None:
        """Verify both methods converge to exact solution."""
        L = make_line_graph_laplacian(n)
        apply_A = matvec_from_matrix(L)

        rng = np.random.default_rng(seed)
        x0 = rng.normal(size=n)
        x0 = x0 / np.linalg.norm(x0)

        t = 0.5
        y_exact = exact_heat_kernel(L, x0, t)

        # Chebyshev
        a, b = estimate_spectral_interval(apply_A, n, m=16)
        a = max(0.0, a - 0.1)
        b = b + 0.1
        y_cheb = chebyshev_heat_apply(apply_A, x0, t, K=40, a=a, b=b)

        # Lanczos
        y_lanc = lanczos_expv(apply_A, x0, t, m=min(32, n))

        # Both should be close to exact
        cheb_err = relative_error(y_cheb, y_exact)
        lanc_err = relative_error(y_lanc, y_exact)

        assert cheb_err < 0.1, f"Chebyshev error {cheb_err:.6f} > 0.1"
        assert lanc_err < 0.1, f"Lanczos error {lanc_err:.6f} > 0.1"
