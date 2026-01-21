"""Frequent-Directions sketch for online covariance approximation.

This implementation provides the minimal FD sketch to maintain a small
matrix S such that S^T S approximates the covariance of streamed vectors.
It supports inserting vectors and extracting a low-rank approximation.
"""

from typing import Optional

import numpy as np


class FrequentDirections:
    """A small, readable FD sketch implementation.

    Args:
        d: ambient dimension
        ell: sketch size (rows)
    """

    def __init__(self, d: int, ell: int):
        """Initialize the instance."""

        self.d = int(d)
        self.ell = int(ell)
        # S matrix stores at most ell rows
        self.S = np.zeros((0, d), dtype=float)

    def insert(self, v: np.ndarray):
        """Execute insert.

        Args:
            v: The v.
        """

        v = np.asarray(v, dtype=float).reshape(1, -1)
        self.S = np.vstack([self.S, v])
        if self.S.shape[0] > self.ell:
            self._compress()

    def _compress(self):
        # compute SVD of current S, shrink singular values
        """Execute compress."""

        U, s, Vt = np.linalg.svd(self.S, full_matrices=False)
        # shrink by smallest singular value s[-1]
        delta = s[-1] ** 2
        s2 = np.sqrt(np.maximum(s**2 - delta, 0.0))
        # keep top ell-1 components
        k = min(self.ell, len(s2))
        Snew = np.diag(s2[:k]) @ Vt[:k, :]
        self.S = Snew

    def approx_cov(self) -> np.ndarray:
        """Return S^T S as the FD covariance approximation."""
        return self.S.T @ self.S

    def top_components(self, r: Optional[int] = None):
        """Execute top components.

        Args:
            r: The r.
        """

        C = self.approx_cov()
        U, s, Vt = np.linalg.svd(C)
        if r is None:
            return U, s
        return U[:, :r], s[:r]


def sketch_from_matrix(X: np.ndarray, ell: int) -> "FrequentDirections":
    """Stream rows of X into an FD sketch and return the sketch.

    X: array-like of shape (n, d)
    ell: sketch size
    """
    fd = FrequentDirections(d=X.shape[1], ell=ell)
    for row in X:
        fd.insert(row)
    return fd


def topk_eigenvalues_from_sketch(fd: "FrequentDirections", k: int) -> np.ndarray:
    """Return the top-k eigenvalues (as a 1-D array) from the FD sketch.

    Note: the FD `top_components` returns singular values of the approximated
    covariance matrix; since those are singular values of the covariance, they
    are already eigenvalues (non-negative).
    """
    _, s = fd.top_components(r=k)
    return np.asarray(s, dtype=float)
