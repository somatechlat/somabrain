"""Helpers: short Lanczos for spectral bounds + Chebyshev apply for heat kernel.

This module contains utilities to estimate an operator spectral interval
via a short Lanczos run and then apply a Chebyshev polynomial approximation
of exp(-t L) to a vector using that interval.
"""

import numpy as np
from typing import Callable, Tuple


def estimate_spectral_interval(apply_A: Callable[[np.ndarray], np.ndarray],
                               n: int, m: int = 16) -> Tuple[float, float]:
    """Run m-step Lanczos to estimate the spectral interval of A on n-dim space.

    apply_A: function that applies A to a vector
    n: dimension
    m: number of Lanczos steps (small, e.g., 16)
    returns: (a,b) estimated min and max eigenvalues
    """
    if m <= 0:
        raise ValueError("m must be >= 1")
    q = np.zeros((n, m + 1), dtype=float)
    alphas = np.zeros(m, dtype=float)
    betas = np.zeros(m, dtype=float)
    rng = np.random.default_rng()
    q[:, 0] = rng.normal(size=n)
    q[:, 0] /= np.linalg.norm(q[:, 0])
    for j in range(m):
        z = apply_A(q[:, j])
        alpha = np.dot(q[:, j], z)
        z = z - alpha * q[:, j]
        if j > 0:
            z = z - betas[j - 1] * q[:, j - 1]
        beta = np.linalg.norm(z)
        alphas[j] = alpha
        betas[j] = beta
        if beta == 0:
            # early termination
            T = np.diag(alphas[: j + 1])
            eigs = np.linalg.eigvalsh(T)
            return eigs.min(), eigs.max()
        q[:, j + 1] = z / beta
    # build tridiagonal matrix
    T = np.diag(alphas) + np.diag(betas[:-1], 1) + np.diag(betas[:-1], -1)
    eigs = np.linalg.eigvalsh(T)
    return float(eigs.min()), float(eigs.max())


def chebyshev_heat_apply(apply_A: Callable[[np.ndarray], np.ndarray],
                         x: np.ndarray,
                         t: float,
                         K: int,
                         a: float,
                         b: float) -> np.ndarray:
    """Approximate y = exp(-t A) x using Chebyshev polynomial of degree K.

    apply_A: function to apply A
    x: input vector
    t: time parameter in heat kernel
    K: degree
    a,b: spectral interval bounds of A
    """
    n = x.shape[0]
    # map operator to [-1,1]: A' = (2A - (b+a)I)/(b-a)
    if b <= a:
        raise ValueError("Invalid spectral interval")
    def apply_Ap(v: np.ndarray) -> np.ndarray:
        return (2.0 * apply_A(v) - (b + a) * v) / (b - a)

    # coefficients for exp(-t * lambda) on [-1,1] can be approximated via
    # Chebyshev polynomial expansion; we'll use Clenshaw recurrence to apply
    # with coefficients computed by sampling (small K so it's fine).
    # sample Chebyshev nodes and compute interpolation coefficients
    ks = np.arange(K + 1)
    # compute Chebyshev coefficients c_k ~ (2/pi) * integral_{-1}^1 f(x) T_k(x)/sqrt(1-x^2) dx
    # approximate via discrete cosine transform on nodes
    nodes = np.cos((np.pi * (np.arange(1, K + 1) - 0.5)) / K)
    lambdas = (b - a) * nodes / 2.0 + (b + a) / 2.0
    fvals = np.exp(-t * lambdas)
    # dct-like coefficients
    coeffs = np.zeros(K + 1)
    for k in ks:
        coeffs[k] = (2.0 / K) * np.sum(fvals * np.cos(k * np.arccos(nodes)))
    coeffs[0] *= 0.5

    # Clenshaw recurrence to evaluate sum_k coeffs[k] T_k(A') x
    b_kplus1 = np.zeros(n)
    b_k = np.zeros(n)
    for k in range(K, 0, -1):
        tmp = b_k.copy()
        b_k = 2.0 * apply_Ap(b_k) - b_kplus1 + coeffs[k] * x
        b_kplus1 = tmp
    y = apply_Ap(b_k) - b_kplus1 + coeffs[0] * x
    return y
