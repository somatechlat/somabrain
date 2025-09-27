import numpy as np
from somabrain.math import LearnedUnitaryRoles, FrequentDirections, estimate_spectral_interval, chebyshev_heat_apply


def test_learned_roles_roundtrip():
    d = 128
    lr = LearnedUnitaryRoles(d)
    lr.init_role('r1', seed=0)
    x = np.random.RandomState(1).randn(d)
    y = lr.bind('r1', x)
    xhat = lr.unbind('r1', y)
    err = np.linalg.norm(x - xhat) / np.linalg.norm(x)
    assert err < 1e-6


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
    y_approx = chebyshev_heat_apply(apply_A, x, t=1.0, K=8, a=a, b=b)
    y_true = np.exp(-A) @ x
    rel = np.linalg.norm(y_true - y_approx) / np.linalg.norm(y_true)
    assert rel < 0.2
