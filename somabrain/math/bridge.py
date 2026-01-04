"""High-level Sinkhorn bridge wrapper for two distributions using graph kernels.

This module provides a convenience function to build cost matrices from kernel
vectors (or pairwise distances) and compute an OT plan using sinkhorn.
"""

import numpy as np
from somabrain.math.sinkhorn import sinkhorn_log_stabilized

# Use unified settings for configuration defaults
from django.conf import settings


def sinkhorn_bridge_from_embeddings(
    X: np.ndarray, Y: np.ndarray, eps: float = None, tol: float = None
):
    """Compute Sinkhorn transport between point clouds X (n x d) and Y (m x d).

    Uses squared Euclidean as cost by default.
    Returns transport matrix P and error.
    """
    n = X.shape[0]
    m = Y.shape[0]
    # costs (squared Euclidean)
    XX = np.sum(X * X, axis=1)[:, None]
    YY = np.sum(Y * Y, axis=1)[None, :]
    C = XX + YY - 2 * (X @ Y.T)
    a = np.ones(n) / n
    b = np.ones(m) / m
    # resolve defaults from truth-budget if not provided
    if eps is None or tol is None:
        cfg = settings
        if eps is None:
            eps = getattr(cfg, "truth_sinkhorn_eps", 1e-2)
        if tol is None:
            tol = getattr(cfg, "truth_sinkhorn_tol", 1e-6)
        maxiter = getattr(cfg, "truth_sinkhorn_maxiter", 5000)
    else:
        maxiter = 5000

    P, err = sinkhorn_log_stabilized(C, a, b, eps=eps, niter=maxiter, tol=tol)
    return P, err