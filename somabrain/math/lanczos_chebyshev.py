"""Helpers: short Lanczos for spectral bounds + Chebyshev apply for heat kernel.

This module contains utilities to estimate an operator spectral interval
via a short Lanczos run and then apply a Chebyshev polynomial approximation
of exp(-t L) to a vector using that interval.
"""

import numpy as np
from typing import Callable, Tuple, Optional

# lazy config import to read truth-budget defaults when needed
from somabrain.config import get_config


def estimate_spectral_interval(
    apply_A: Callable[[np.ndarray], np.ndarray], n: int, m: int = 16
) -> Tuple[float, float]:
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


def chebyshev_heat_apply(
    apply_A: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    t: float,
    K: Optional[int],
    a: float,
    b: float,
) -> np.ndarray:
    """Approximate y = exp(-t A) x using Chebyshev polynomial of degree K.

    apply_A: function to apply A
    x: input vector
    t: time parameter in heat kernel
    K: degree
    a,b: spectral interval bounds of A
    """
    n = x.shape[0]
    if K is None:
        cfg = get_config()
        K = int(getattr(cfg, "truth_chebyshev_K", 32))
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


def lanczos_expv(
    apply_A: Callable[[np.ndarray], np.ndarray], x: np.ndarray, t: float, m: int = 32
) -> np.ndarray:
    """Approximate y = exp(-t A) x using Lanczos / Krylov method.

    This is robust for small-to-moderate m and avoids needing Chebyshev
    coefficient estimation. Returns ||x|| * V * exp(-t T) e1.
    """
    n = x.shape[0]
    normx = np.linalg.norm(x)
    if normx == 0:
        return np.zeros_like(x)
    v = x / normx
    V = np.zeros((n, m), dtype=float)
    alphas = np.zeros(m, dtype=float)
    betas = np.zeros(m, dtype=float)
    V[:, 0] = v
    w = apply_A(v)
    alphas[0] = np.dot(v, w)
    w = w - alphas[0] * v
    betas[0] = np.linalg.norm(w)
    k = 1
    for j in range(1, m):
        if betas[j - 1] == 0:
            k = j
            break
        v_next = w / betas[j - 1]
        V[:, j] = v_next
        w = apply_A(v_next) - betas[j - 1] * V[:, j - 1]
        alphas[j] = np.dot(v_next, w)
        w = w - alphas[j] * v_next
        betas[j] = np.linalg.norm(w)
        k = j + 1
    # Build tridiagonal T of size k
    T = np.zeros((k, k), dtype=float)
    for i in range(k):
        T[i, i] = alphas[i]
        if i + 1 < k:
            T[i, i + 1] = betas[i]
            T[i + 1, i] = betas[i]
    # Compute exp(-t T) via eigendecomposition (k small)
    evals, evecs = np.linalg.eigh(T)
    expT = evecs @ np.diag(np.exp(-t * evals)) @ evecs.T
    e1 = np.zeros(k)
    e1[0] = 1.0
    yk = expT @ e1
    y = normx * (V[:, :k] @ yk)
    return y
