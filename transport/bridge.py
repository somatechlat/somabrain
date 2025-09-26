import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def heat_kernel_expmv(L, v, beta=1.0, tol=1e-6):
    """
    Compute exp(-beta*L) @ v using Krylov/expokit (sparse, fast for large graphs).
    L: Laplacian (n x n, sparse)
    v: (n,) vector
    Returns: (n,) vector
    """
    return spla.expm_multiply(-beta * L, v)

def schrodinger_bridge(L, mu0, mu1, beta=1.0, n_iter=20, tol=1e-6):
    """
    Sinkhorn scaling for graph Schrödinger bridge (heat kernel transport).
    L: Laplacian (n x n, sparse)
    mu0, mu1: initial/final marginals (n,)
    Returns: u, v (scaling vectors), K (heat kernel matrix as linear operator)
    """
    n = L.shape[0]
    def K(x):
        return heat_kernel_expmv(L, x, beta=beta)
    u = np.ones(n)
    v = np.ones(n)
    for _ in range(n_iter):
        Ku = K(u)
        v = mu1 / (Ku + 1e-12)
        Ktv = K(v)
        u = mu0 / (Ktv + 1e-12)
        if np.linalg.norm(u * Ku - mu1) < tol:
            break
    return u, v, K

def bridge_reach_prob(u, v, K, t=1.0):
    """
    Compute reach probability from u, v, K at time t.
    Returns: (n,) vector of probabilities.
    """
    return u * K(v)
