from __future__ import annotations
from typing import Tuple
import numpy as np
from . import numerics as _num

"""Batching helpers for HRR numeric kernels.

Small helpers to reshape, stack, and perform batched rfft/irfft with unitary
normalization to ensure efficient, low-allocation bindings.
"""






def ensure_batch(x: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Ensure x has a leading batch dimension; returns (x_batched, was_scalar).

    If input already has ndim >= 2, returns it unchanged with was_scalar=False.
    If input is 1D, returns x[None, :] and was_scalar=True so callers can undo.
    """
    arr = np.asarray(x)
    if arr.ndim == 1:
        return arr[None, :], True
    return arr, False


def batched_rfft(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Compute rfft with unitary normalization for batched inputs."""
    return _num.rfft_norm(x, axis=axis)


def batched_irfft(X: np.ndarray, n: int, axis: int = -1) -> np.ndarray:
    """Compute inverse rfft with unitary normalization for batched spectra."""
    return _num.irfft_norm(X, n=n, axis=axis)
