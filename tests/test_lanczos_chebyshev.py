import numpy as np
from somabrain.math.lanczos_chebyshev import (
    lanczos_expv,
    chebyshev_heat_apply,
    estimate_spectral_interval,
)


def test_lanczos_expv_small_symmetric():
    rng = np.random.default_rng(1)
    n = 64
    # small symmetric positive semidefinite matrix (M @ M.T)
    M = rng.normal(size=(n, 8))
    full = M @ M.T

    def apply_A(x):
        return full @ x

    x = rng.normal(size=(n,))
    t = 0.5
    y = lanczos_expv(apply_A, x, t, m=32)
    # reference via direct expm (dense) on small n
    # full symmetric PSD matrix constructed above
    # compute exp(-t full) via eigendecomposition
    evals, evecs = np.linalg.eigh(full)
    ref = evecs @ (np.exp(-t * evals) * (evecs.T @ x))
    # check relative norm difference
    rel = np.linalg.norm(y - ref) / (np.linalg.norm(ref) + 1e-12)
    assert rel < 1e-1  # Lanczos approximation should be reasonably close for m=32


def test_chebyshev_heat_apply_consistency():
    rng = np.random.default_rng(2)
    n = 64
    A = rng.normal(size=(n, n))
    A = A + A.T + n * np.eye(n)  # make symmetric positive definite

    def apply_A(x):
        return A @ x

    # estimate interval
    a, b = estimate_spectral_interval(apply_A, n=n, m=20)
    x = rng.normal(size=(n,))
    t = 0.1
    K = 40
    y = chebyshev_heat_apply(apply_A, x, t, K, a, b)
    # reference via eigen-decomposition
    evals, evecs = np.linalg.eigh(A)
    ref = evecs @ (np.exp(-t * evals) * (evecs.T @ x))
    rel = np.linalg.norm(y - ref) / (np.linalg.norm(ref) + 1e-12)
    assert rel < 5e-2
