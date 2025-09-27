import numpy as np
import scipy.sparse as sp
from transport.flow_opt import solve_flows, update_conductances


def test_solve_flows_and_update_conductances():
    n = 5
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]
    L = sp.lil_matrix((n, n))
    for i, j in edges:
        L[i, i] += 1
        L[j, j] += 1
        L[i, j] -= 1
        L[j, i] -= 1
    L = L.tocsr()
    sources = [0]
    sinks = [3]
    x = solve_flows(L, sources, sinks)
    assert x.shape == (n,)
    C = np.ones(len(edges))
    Q = np.random.randn(len(edges))
    L_e = np.ones(len(edges))
    C_new = update_conductances(C, Q, L_e)
    assert C_new.shape == (len(edges),)
    assert np.all(C_new >= 1e-9) and np.all(C_new <= 1e3)
