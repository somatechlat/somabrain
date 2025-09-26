import numpy as np
import scipy.sparse as sp
from transport.bridge import heat_kernel_expmv, schrodinger_bridge, bridge_reach_prob

def test_heat_kernel_expmv():
    n = 6
    L = sp.eye(n, format='csr')
    v = np.ones(n)
    out = heat_kernel_expmv(L, v, beta=0.5)
    assert out.shape == (n,)
    assert np.all(out > 0)

def test_schrodinger_bridge():
    n = 6
    L = sp.eye(n, format='csr')
    mu0 = np.ones(n) / n
    mu1 = np.zeros(n)
    mu1[-1] = 1.0
    u, v, K = schrodinger_bridge(L, mu0, mu1, beta=0.5, n_iter=5)
    assert u.shape == (n,)
    assert v.shape == (n,)
    p = bridge_reach_prob(u, v, K)
    assert p.shape == (n,)
    assert np.all(p >= 0)
