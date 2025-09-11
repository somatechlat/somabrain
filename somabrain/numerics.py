"""
Canonical numeric primitives for SomaBrain.

- compute_tiny_floor: eps * sqrt(D) default (strategy='sqrt')
- rfft_norm / irfft_norm: unitary real-FFT wrappers (norm='ortho')
- normalize_array: safe L2 normalization; deterministic fallback for subtiny slices
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional, Sequence, Union

import numpy as np

_ArrayLike = Union[np.ndarray, Sequence]

TINY_MIN = {
    np.dtype(np.float32): 1e-6,
    np.dtype(np.float64): 1e-12,
}


# Internal cache keyed by canonical primitives to avoid unhashable args
_TINY_CACHE: dict = {}


def compute_tiny_floor(
    dim_or_array: Union[int, np.ndarray],
    dtype: Any = np.float32,
    strategy: str = "sqrt",
    scale: float = 1.0,
) -> float:
    """Compute a dtype-aware *amplitude* tiny-floor (L2-norm units).

    This function returns a small positive scalar in units of the L2 norm
    (i.e., the same units as ||x||_2). Callers that need power-domain
    floors for FFT bins should square this and divide by D
    (power_per_bin = tiny_amp**2 / D).

    Accepts the legacy flexible calling convention (dtype or dim first).
    The returned value is cached on canonical primitive keys to avoid
    lru_cache errors with unhashable args.
    """
    # Canonicalize input into (D:int, dt:np.dtype)
    try:
        dt_try = np.dtype(dim_or_array)
        is_dtype_like = True
    except Exception:
        is_dtype_like = False

    if is_dtype_like and isinstance(dtype, (int, np.integer)):
        dt = dt_try
        D = int(dtype)
    else:
        if isinstance(dim_or_array, (int, np.integer)):
            D = int(dim_or_array)
        else:
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

    key = (int(D), np.dtype(dt).name, strategy, float(scale))
    if key in _TINY_CACHE:
        return _TINY_CACHE[key]

    eps = np.finfo(dt).eps
    if strategy == "sqrt":
        base = float(eps * np.sqrt(max(1, D)) * float(scale))
    elif strategy == "linear":
        base = float(eps * max(1, D) * float(scale))
    elif strategy == "absolute":
        base = float(eps * float(scale))
    else:
        raise ValueError(f"unknown tiny-floor strategy: {strategy}")

    tiny_amp = max(base, TINY_MIN.get(dt, base))
    _TINY_CACHE[key] = tiny_amp
    return tiny_amp


def rfft_norm(x: _ArrayLike, n: Optional[int] = None, axis: int = -1) -> np.ndarray:
    """Unitary real FFT (rfft) wrapper using norm='ortho'."""
    x = np.asarray(x)
    return np.fft.rfft(x, n=n, axis=axis, norm="ortho")


def irfft_norm(X: _ArrayLike, n: int, axis: int = -1) -> np.ndarray:
    """Unitary inverse real FFT (irfft) wrapper using norm='ortho'."""
    return np.fft.irfft(np.asarray(X), n=n, axis=axis, norm="ortho")


def _baseline_unit(
    shape: Sequence[int], axis: int = -1, dtype: Any = np.float32
) -> np.ndarray:
    """Deterministic baseline unit-vector (ones / sqrt(D)) broadcastable to `shape`."""
    axis_norm = axis if axis >= 0 else len(shape) + axis
    D = shape[axis_norm]
    baseline_1d = np.ones((D,), dtype=np.dtype(dtype)) / np.sqrt(float(D))
    bshape = [1] * len(shape)
    bshape[axis_norm] = D
    return baseline_1d.reshape(tuple(bshape))


def normalize_array(
    x: _ArrayLike,
    axis: int = -1,
    keepdims: bool = False,
    tiny_floor_strategy: str = "sqrt",
    dtype: Any = np.float32,
    strict: bool = False,
    mode: str = "legacy_zero",
    **kwargs,
) -> np.ndarray:
    """
    L2-normalize `x` along axis in a numerically safe way.

    Robust (default): if norm < tiny_floor, return deterministic baseline unit-vector.
    Strict: raise ValueError on subtiny norms.
    """
    # Legacy compatibility:
    # - allow old keyword `raise_on_subtiny` -> strict
    # - tolerate callers that passed `dim` as the axis (e.g. axis >= arr.ndim)
    # - detect legacy positional usage: normalize_array(x, D, dtype, raise_on_subtiny=...)
    if "raise_on_subtiny" in kwargs:
        strict = bool(kwargs.pop("raise_on_subtiny"))
    # mode choices: 'legacy_zero' (default), 'robust' (baseline unit-vector), 'strict'
    if mode not in ("legacy_zero", "robust", "strict"):
        raise ValueError(f"unknown normalize mode: {mode}")

    arr = np.asarray(x)
    if arr.size == 0:
        return arr.astype(arr.dtype)

    ndim = arr.ndim
    # If callers passed a dimension (D) instead of an axis index, detect it later
    axis_param = axis
    axis_norm = axis if axis >= 0 else ndim + axis
    try:
        D = arr.shape[axis_norm]
    except Exception:
        # Treat axis param as D when it doesn't index into arr
        try:
            D = int(axis_param)
        except Exception:
            D = arr.shape[-1]
        # use last axis for normalization in this compatibility case
        axis = -1
        axis_norm = ndim - 1
    # Handle legacy positional dtype passed as `keepdims` (e.g. 'float32')
    if not isinstance(keepdims, (bool,)):
        try:
            # coerce string or dtype-like to numpy dtype
            dtype = np.dtype(keepdims)
            keepdims = False
        except Exception:
            # fallback: force keepdims to bool
            keepdims = bool(keepdims)

    tiny = compute_tiny_floor(D, dtype=dtype, strategy=tiny_floor_strategy)

    # If caller passed a requested dimension D (compat mode) and the array
    # length along the normalization axis doesn't match, pad with zeros or
    # truncate to match D. This supports schema normalization which passes
    # dim as the second argument.
    try:
        cur_len = arr.shape[axis_norm]
    except Exception:
        cur_len = None
    if cur_len is not None and cur_len != D:
        if cur_len < D:
            # pad with zeros on the right along axis_norm
            pad_width = [(0, 0)] * arr.ndim
            pad_width[axis_norm] = (0, D - cur_len)
            arr = np.pad(arr, pad_width, mode="constant", constant_values=0)
        else:
            # truncate along axis_norm
            sl = [slice(None)] * arr.ndim
            sl[axis_norm] = slice(0, D)
            arr = arr[tuple(sl)]

    # ensure keepdims is a bool when passed to numpy
    keepdims_bool = bool(keepdims)
    # Use float64 intermediates for accumulation to reduce round-off, then
    # cast result back to the array dtype at the end.
    arr_f64 = arr.astype(np.float64)
    # sum-of-squares (energy) per slice
    sq = np.sum(np.abs(arr_f64) ** 2, axis=axis, keepdims=keepdims_bool)
    # tiny is an amplitude threshold (||x||_2 units). Use tiny**2 when
    # combining with squared norms (sq), which are energy units.
    tiny_sq = float(tiny) ** 2
    denom = np.sqrt(sq + tiny_sq)
    # Broadcast denom to arr for division when keepdims=False
    if not keepdims_bool:
        denom_b = np.expand_dims(denom, axis=axis)
    else:
        denom_b = denom
    result = (arr_f64 / denom_b).astype(arr.dtype)

    sq_nokeep = np.sum(np.abs(arr_f64) ** 2, axis=axis, keepdims=False)
    # compare squared-norm to tiny squared for consistency
    mask_subtiny = sq_nokeep < tiny_sq

    if np.any(mask_subtiny):
        if strict or mode == "strict":
            raise ValueError("vector norm below tiny_floor in strict mode")
        if mode == "legacy_zero":
            # Legacy behaviour: return zero-vector for subtiny norms
            zero_full = np.zeros_like(arr, dtype=arr.dtype)
            if mask_subtiny.ndim == 0:
                if bool(mask_subtiny):
                    result = zero_full
            else:
                it = np.nditer(mask_subtiny, flags=["multi_index"])
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
                        result[sel_tuple] = zero_full[sel_tuple]
                    it.iternext()
        else:
            # robust: use deterministic baseline unit-vector replacement
            baseline = _baseline_unit(arr.shape, axis=axis, dtype=arr.dtype)
            baseline_full = np.broadcast_to(baseline, arr.shape)
            if mask_subtiny.ndim == 0:
                if bool(mask_subtiny):
                    result = baseline_full.astype(result.dtype)
            else:
                it = np.nditer(mask_subtiny, flags=["multi_index"])
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

    # Final numeric correction: enforce unit L2-norm per slice using float64
    res_f64 = np.asarray(result, dtype=np.float64)
    # compute per-slice norm with keepdims for broadcasting
    if keepdims_bool:
        norm64 = np.sqrt(np.sum(np.abs(res_f64) ** 2, axis=axis, keepdims=True))
    else:
        norm64 = np.sqrt(np.sum(np.abs(res_f64) ** 2, axis=axis, keepdims=True))
    # avoid division by zero
    norm_safe = np.where(norm64 == 0, 1.0, norm64)
    res_f64 = res_f64 / norm_safe
    result = np.asarray(res_f64, dtype=arr.dtype)

    # Replace any non-finite entries with the deterministic baseline
    if not np.all(np.isfinite(result)):
        baseline_full = np.broadcast_to(
            _baseline_unit(arr.shape, axis=axis, dtype=arr.dtype), arr.shape
        )
        result = np.where(np.isfinite(result), result, baseline_full)

    return result
