import numpy as np
from somabrain.math.sinkhorn import sinkhorn_log_stabilized


def test_sinkhorn_marginals_uniform_small():
    n = 16
    m = 12
    rng = np.random.default_rng(0)
    X = rng.normal(0, 1, size=(n, 4))
    Y = rng.normal(0, 1, size=(m, 4))
    # Cost matrix (squared euclidean)
    C = ((X[:, None, :] - Y[None, :, :]) ** 2).sum(axis=2)
    a = np.full(n, 1.0 / n)
    b = np.full(m, 1.0 / m)
    P, err = sinkhorn_log_stabilized(C, a, b, eps=5e-2, niter=2000, tol=1e-7)
    # Check marginals
    r = P.sum(axis=1)
    c = P.sum(axis=0)
    assert np.max(np.abs(r - a)) < 5e-6
    assert np.max(np.abs(c - b)) < 5e-6
    assert err < 5e-6
    # Transport matrix is non-negative
    assert np.min(P) >= 0.0


def test_sinkhorn_random_marginals():
    n = 20
    m = 20
    rng = np.random.default_rng(1)
    C = rng.random((n, m))
    a_raw = rng.random(n)
    a = a_raw / a_raw.sum()
    b_raw = rng.random(m)
    b = b_raw / b_raw.sum()
    P, err = sinkhorn_log_stabilized(C, a, b, eps=1e-2, niter=3000, tol=1e-6)
    r = P.sum(axis=1)
    c = P.sum(axis=0)
    assert np.max(np.abs(r - a)) < 1e-5
    assert np.max(np.abs(c - b)) < 1e-5
    assert err < 1e-5
