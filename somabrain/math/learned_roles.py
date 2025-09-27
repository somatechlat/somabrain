"""Learned unitary role matrices for HRR-like binding via Fourier phases

Provides a compact, testable implementation of parametrized unitary roles.
Two interfaces are provided:

- LearnedUnitaryRoles: manages per-role phase vectors (theta) and applies
  the unitary in Fourier space: R_hat = exp(i * theta) (elementwise), so
  binding becomes fft^{-1}(R_hat * fft(x)). This guarantees exact
  invertibility by conjugation.
- bind_fft / unbind_fft: helpers to bind/unbind vectors using phase vectors.

The implementation is intentionally dependency-light: only numpy is used.
"""

import numpy as np
from typing import Dict


def bind_fft(x: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Bind vector x by phase vector theta in Fourier domain.

    x: real vector (d,)
    theta: real phase vector (d,) representing angle per FFT bin
    returns: real vector (d,)
    """
    X = np.fft.rfft(x)
    R = np.exp(1j * theta[: X.shape[0]])
    Y = X * R
    y = np.fft.irfft(Y, n=x.shape[0])
    return y


def unbind_fft(y: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Unbind vector y by inverse phase (conjugate) in Fourier domain."""
    Y = np.fft.rfft(y)
    R = np.exp(-1j * theta[: Y.shape[0]])
    X = Y * R
    x = np.fft.irfft(X, n=y.shape[0])
    return x


class LearnedUnitaryRoles:
    """Manage learned phase vectors for a set of roles.

    Attributes:
        d: ambient vector dimension
        phases: dict mapping role name to phase vector (real, length d//2+1 for rfft bins)
    """

    def __init__(self, d: int):
        self.d = int(d)
        self._store: Dict[str, np.ndarray] = {}

    def init_role(self, name: str, scale: float = 0.1, seed: int | None = None):
        rng = np.random.default_rng(seed)
        # Store full-length phase vector for convenience; rfft uses d//2+1 bins
        theta = rng.normal(scale=scale, size=(self.d // 2 + 1,))
        self._store[name] = theta.astype(float)

    def set_role(self, name: str, theta: np.ndarray):
        self._store[name] = np.asarray(theta, dtype=float)

    def get_role(self, name: str) -> np.ndarray:
        return self._store[name]

    def bind(self, name: str, x: np.ndarray) -> np.ndarray:
        theta = self.get_role(name)
        return bind_fft(x, theta)

    def unbind(self, name: str, y: np.ndarray) -> np.ndarray:
        theta = self.get_role(name)
        return unbind_fft(y, theta)
