import numpy as np
import pytest

from somabrain.math.lanczos_chebyshev import estimate_spectral_interval, chebyshev_heat_apply, lanczos_expv


def _make_spd(k, seed=0):
    rng = np.random.default_rng(seed)
    M = rng.normal(0, 1, size=(k, k))
    A = M @ M.T  # symmetric PSD
    # Shift + scale to moderate spectrum
    return A / np.linalg.norm(A, ord=2)

@pytest.mark.parametrize("k", [24, 48])
@pytest.mark.parametrize("t", [0.1, 0.25])
def test_chebyshev_vs_lanczos_heat(k, t):
    A = _make_spd(k)
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, size=k)

    def apply_A(v):
        return A @ v

    a, b = estimate_spectral_interval(apply_A, k, m=12)
    y_cheb = chebyshev_heat_apply(apply_A, x, t, K=24, a=a, b=b)
    y_lanc = lanczos_expv(apply_A, x, t, m=32)

    # Relative L2 difference should be small
    diff = np.linalg.norm(y_cheb - y_lanc) / (np.linalg.norm(y_lanc) + 1e-12)
    assert diff < 0.05, f"heat kernel approximation diff {diff} too large"

    # Heat kernel decreases norm for positive semidefinite A: ||exp(-tA)x|| <= ||x||
    assert np.linalg.norm(y_cheb) <= np.linalg.norm(x) + 1e-6
    assert np.linalg.norm(y_lanc) <= np.linalg.norm(x) + 1e-6
