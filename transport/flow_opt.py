import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve_flows(L, sources, sinks):
    """
    Solve Kirchhoff flows on a graph Laplacian L.
    sources, sinks: arrays of node indices (same length)
    Returns: flow vector Q (per edge)
    """
    n = L.shape[0]
    b = np.zeros(n)
    for s, t in zip(sources, sinks):
        b[s] += 1
        b[t] -= 1
    # Solve L x = b (with nullspace fix)
    x = spla.lsmr(L + sp.eye(n) * 1e-8, b)[0]
    return x


def update_conductances(
    C, Q, L_e, eta=0.02, alpha=1.4, lamb=0.003, C_min=1e-9, C_max=1e3
):
    """
    Update edge conductances C given flows Q and edge costs L_e.
    C, Q, L_e: arrays of shape (num_edges,)
    Returns: updated C
    """
    dC = eta * (np.abs(Q) ** alpha - lamb * L_e * C)
    C_new = np.clip(C + dC, C_min, C_max)
    return C_new
