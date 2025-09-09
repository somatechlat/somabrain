"""
Canonical numeric primitives for SomaBrain.

- compute_tiny_floor: eps * sqrt(D) default (strategy='sqrt')
- rfft_norm / irfft_norm: unitary real-FFT wrappers (norm='ortho')
- normalize_array: safe L2 normalization; deterministic fallback for subtiny slices
"""
from __future__ import annotations

from typing import Optional, Union, Sequence, Any
import numpy as np

_ArrayLike = Union[np.ndarray, Sequence]

TINY_MIN = {
    np.dtype(np.float32): 1e-6,
    np.dtype(np.float64): 1e-12,
}


def compute_tiny_floor(dim_or_array: Union[int, np.ndarray],
                       dtype: Any = np.float32,
                       strategy: str = "sqrt",
                       scale: float = 1.0) -> float:
    """Compute machine-eps * sqrt(D) (default) or alternative strategies.

    Returns a dtype-aware tiny-floor clamped to a small dtype-specific min.
    """
    # Handle integer inputs quickly, otherwise infer dimension from shape or len
    if isinstance(dim_or_array, (int, np.integer)):
        D = int(dim_or_array)
    else:
        # Try shape[-1], then len(), then product of shape, finally fallback to 1
        shape = getattr(dim_or_array, "shape", None)
        if shape is not None:
            try:
                D = int(shape[-1])
            except Exception:
                D = int(np.prod(shape))
        else:
            try:
                D = int(len(dim_or_array))
            except Exception:
                D = 1

    dt = np.dtype(dtype)
    eps = np.finfo(dt).eps
    if strategy == "sqrt":
        base = float(eps * np.sqrt(max(1, D)) * float(scale))
    elif strategy == "linear":
        base = float(eps * max(1, D) * float(scale))
    elif strategy == "absolute":
        base = float(eps * float(scale))
    else:
        raise ValueError(f"unknown tiny-floor strategy: {strategy}")
    return max(base, TINY_MIN.get(dt, base))


def rfft_norm(x: _ArrayLike, n: Optional[int] = None, axis: int = -1) -> np.ndarray:
    """Unitary real FFT (rfft) wrapper using norm='ortho'."""
    x = np.asarray(x)
    return np.fft.rfft(x, n=n, axis=axis, norm="ortho")


def irfft_norm(X: _ArrayLike, n: int, axis: int = -1) -> np.ndarray:
    """Unitary inverse real FFT (irfft) wrapper using norm='ortho'."""
    return np.fft.irfft(np.asarray(X), n=n, axis=axis, norm="ortho")


def _baseline_unit(shape: Sequence[int], axis: int = -1, dtype: Any = np.float32) -> np.ndarray:
    """Deterministic baseline unit-vector (ones / sqrt(D)) broadcastable to `shape`."""
    axis_norm = axis if axis >= 0 else len(shape) + axis
    D = shape[axis_norm]
    baseline_1d = np.ones((D,), dtype=np.dtype(dtype)) / np.sqrt(float(D))
    bshape = [1] * len(shape)
    bshape[axis_norm] = D
    return baseline_1d.reshape(tuple(bshape))


def normalize_array(x: _ArrayLike,
                    axis: int = -1,
                    keepdims: bool = False,
                    tiny_floor_strategy: str = "sqrt",
                    dtype: Any = np.float32,
                    strict: bool = False) -> np.ndarray:
    """
    L2-normalize `x` along axis in a numerically safe way.

    Robust (default): if norm < tiny_floor, return deterministic baseline unit-vector.
    Strict: raise ValueError on subtiny norms.
    """
    arr = np.asarray(x)
    if arr.size == 0:
        return arr.astype(arr.dtype)

    ndim = arr.ndim
    axis_norm = axis if axis >= 0 else ndim + axis
    D = arr.shape[axis_norm]

    tiny = compute_tiny_floor(D, dtype=dtype, strategy=tiny_floor_strategy)

    sq = np.sum(np.abs(arr) ** 2, axis=axis, keepdims=keepdims)
    denom = np.sqrt(sq + tiny)
    result = arr / denom

    sq_nokeep = np.sum(np.abs(arr) ** 2, axis=axis, keepdims=False)
    mask_subtiny = sq_nokeep < tiny

    if np.any(mask_subtiny):
        if strict:
            raise ValueError("vector norm below tiny_floor in strict mode")
        baseline = _baseline_unit(arr.shape, axis=axis, dtype=arr.dtype)
        baseline_full = np.broadcast_to(baseline, arr.shape)
        if mask_subtiny.ndim == 0:
            if bool(mask_subtiny):
                result = baseline_full.astype(result.dtype)
        else:
            it = np.nditer(mask_subtiny, flags=['multi_index'])
            while not it.finished:
                if bool(it[0]):
                    sel = list(it.multi_index)
                    sel_full = []
                    m_idx = 0
                    for ax in range(arr.ndim):
                        if ax == axis_norm:
                            sel_full.append(slice(None))
                        else:
                            sel_full.append(sel[m_idx])
                            m_idx += 1
                    sel_tuple = tuple(sel_full)
                    result[sel_tuple] = baseline_full[sel_tuple]
                it.iternext()

    result = np.asarray(result, dtype=arr.dtype)
    if not np.all(np.isfinite(result)):
        baseline_full = np.broadcast_to(_baseline_unit(arr.shape, axis=axis, dtype=arr.dtype), arr.shape)
        result = np.where(np.isfinite(result), result, baseline_full)

    return result
