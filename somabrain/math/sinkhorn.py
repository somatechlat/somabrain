"""Entropy-regularized Sinkhorn transport (log-domain stabilized).

This module provides a compact, robust Sinkhorn solver for small-to-moderate
cost matrices. It returns a transport matrix P that approximately minimizes
<P, C> - eps * H(P) subject to marginals a,b.
"""

import numpy as np
from typing import Tuple


def sinkhorn_log_stabilized(
    C: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    eps: float = 1e-2,
    niter: int = 1000,
    tol: float = 1e-6,
) -> Tuple[np.ndarray, float]:
    """Return transport matrix P and final error.

    C: cost matrix (n, m)
    a: source marginal (n,)
    b: target marginal (m,)
    eps: entropy regularization
    niter: maximum iterations
    tol: convergence tolerance on marginals
    """
    n, m = C.shape
    if a.shape != (n,):
        raise ValueError(f"Source marginal shape {a.shape} does not match cost matrix rows ({n},)")
    if b.shape != (m,):
        raise ValueError(f"Target marginal shape {b.shape} does not match cost matrix cols ({m},)")
    # log-domain potentials
    K = -C / eps
    # For stability, work with log-K and use log-sum-exp updates
    u = np.zeros(n)
    v = np.zeros(m)

    def _lse_rows(v_vec: np.ndarray) -> np.ndarray:
        """Compute log-sum-exp over columns for each row: returns shape (n,)"""
        A = K + v_vec[None, :]
        M = np.max(A, axis=1)
        # subtract max for numerical stability
        return M + np.log(np.exp(A - M[:, None]).sum(axis=1))

    def _lse_cols(u_vec: np.ndarray) -> np.ndarray:
        """Compute log-sum-exp over rows for each column: returns shape (m,)"""
        A = K + u_vec[:, None]
        M = np.max(A, axis=0)
        return M + np.log(np.exp(A - M[None, :]).sum(axis=0))

    loga = np.log(a + 1e-300)
    logb = np.log(b + 1e-300)

    for it in range(niter):
        # update u so that rows sum to a: u = log a - logsumexp(K + v)
        logsum_rows = _lse_rows(v)
        u = loga - logsum_rows

        # update v similarly (over columns): v = log b - logsumexp(K + u)
        logsum_cols = _lse_cols(u)
        v = logb - logsum_cols

        # check marginals (approx)
        P = np.exp(K + u[:, None] + v[None, :])
        r = P.sum(axis=1)
        c = P.sum(axis=0)
        err = max(np.max(np.abs(r - a)), np.max(np.abs(c - b)))
        if err < tol:
            return P, err
    # final P
    P = np.exp(K + u[:, None] + v[None, :])
    r = P.sum(axis=1)
    c = P.sum(axis=0)
    err = max(np.max(np.abs(r - a)), np.max(np.abs(c - b)))
    return P, err
