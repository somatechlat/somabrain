import numpy as np
from somabrain.math.sinkhorn import sinkhorn_log_stabilized


def test_sinkhorn_small_matrix():
    rng = np.random.default_rng(0)
    n = 5
    m = 6
    C = rng.random((n, m))
    a = np.ones(n) / n
    b = np.ones(m) / m
    P, err = sinkhorn_log_stabilized(C, a, b, eps=1e-2, niter=500, tol=1e-6)
    assert err < 1e-3
    # marginals close
    assert np.allclose(P.sum(axis=1), a, atol=1e-3)
    assert np.allclose(P.sum(axis=0), b, atol=1e-3)
