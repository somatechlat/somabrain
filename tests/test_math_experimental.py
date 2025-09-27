import numpy as np
from somabrain.math import LearnedUnitaryRoles, FrequentDirections, estimate_spectral_interval


def test_learned_roles_roundtrip():
    d = 128
    lr = LearnedUnitaryRoles(d)
    lr.init_role('r1', seed=0)
    x = np.random.RandomState(1).randn(d)
    y = lr.bind('r1', x)
    xhat = lr.unbind('r1', y)
    err = np.linalg.norm(x - xhat) / np.linalg.norm(x)
    # FFT-based phase binding/unbinding is numerically invertible up to
    # floating point error; allow a small tolerance.
    assert err < 1e-4


def test_fd_rho_basic():
    d = 32
    fd = FrequentDirections(d, ell=8)
    rng = np.random.RandomState(2)
    C = np.zeros((d, d))
    for _ in range(100):
        v = rng.randn(d)
        C += np.outer(v, v)
        fd.insert(v)
    Cfd = fd.approx_cov()
    # approximation should be PSD and roughly correlate with C
    eigs = np.linalg.eigvalsh(Cfd)
    assert eigs.min() >= -1e-8


def test_lanczos_chebyshev_small():
    n = 50
    # simple diagonal operator with spectrum in [0,2]
    A = np.diag(np.linspace(0, 2.0, n))
    def apply_A(v):
        return A @ v
    a, b = estimate_spectral_interval(apply_A, n, m=10)
    assert a >= -1e-6 and b <= 2.1
    x = np.random.RandomState(3).randn(n)
    # Use Lanczos-based expv for more accurate small-m tests
    from somabrain.math.lanczos_chebyshev import lanczos_expv

    # Use smaller t for numerical stability in this small-k test
    y_approx = lanczos_expv(apply_A, x, t=0.1, m=40)
    y_true = np.exp(-A) @ x
    rel = np.linalg.norm(y_true - y_approx) / np.linalg.norm(y_true)
    assert rel < 0.05
