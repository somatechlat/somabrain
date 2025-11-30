from __future__ import annotations
from typing import Any, Optional, Sequence, Union
import numpy as np
from common.logging import logger
from typing import Any as _Any, cast as _cast
from . import roles as _roles
from . import roles as _roles

"""
Canonical numeric primitives for SomaBrain.

- compute_tiny_floor: eps * sqrt(D) default (strategy='sqrt')
- rfft_norm / irfft_norm: unitary real-FFT wrappers (norm='ortho')
- normalize_array: safe L2 normalization; deterministic alternative for subtiny slices
"""




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
    scale: float = 1.0, ) -> float:
        pass
    """Compute a dtype-aware *amplitude* tiny-floor (L2-norm units).

    This function returns a small positive scalar in units of the L2 norm
    (i.e., the same units as ||x||_2). Callers that need power-domain
    floors for FFT bins should square this and divide by D
    (power_per_bin = tiny_amp**2 / D).

    The returned value is cached on canonical primitive keys to avoid
    lru_cache errors with unhashable args.
    """
    # Canonicalize input into (D:int, dt:np.dtype)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        dt_try = np.dtype(_cast(_Any, dim_or_array))
        is_dtype_like = True
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
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
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    D = int(shape[-1])
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    D = int(np.prod(shape))
            else:
                try:
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    D = int(len(dim_or_array))  # type: ignore[arg-type]
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
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
    **kwargs, ) -> np.ndarray:
        pass
    """
    L2-normalize `x` along axis in a numerically safe way.

    Robust (default): if norm < tiny_floor, return deterministic baseline unit-vector.
    Strict: raise ValueError on subtiny norms.
    """
    # Legacy compatibility:
        pass
    # - allow old keyword `raise_on_subtiny` -> strict
    # - tolerate callers that passed `dim` as the axis (e.g. axis >= arr.ndim)
    if "raise_on_subtiny" in kwargs:
        strict = bool(kwargs.pop("raise_on_subtiny"))
        raise ValueError(f"unknown normalize mode: {mode}")

    arr = np.asarray(x)
    if arr.size == 0:
        return arr.astype(arr.dtype)

    ndim = arr.ndim
    # If callers passed a dimension (D) instead of an axis index, detect it later
    axis_param = axis
    axis_norm = axis if axis >= 0 else ndim + axis
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        D = arr.shape[axis_norm]
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            D = int(axis_param)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            D = arr.shape[-1]
        # use last axis for normalization in this compatibility case
        axis = -1
        axis_norm = ndim - 1
    if not isinstance(keepdims, (bool,)):
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            # caller passed dtype as the second positional argument
            dtype = np.dtype(keepdims)
            keepdims = False
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            keepdims = bool(keepdims)

    tiny = compute_tiny_floor(D, dtype=dtype, strategy=tiny_floor_strategy)

    # If caller passed a requested dimension D (compat mode) and the array
    # length along the normalization axis doesn't match, pad with zeros or
    # truncate to match D. This supports schema normalization which passes
    # dim as the second argument.
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        cur_len = arr.shape[axis_norm]
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
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

    keepdims_bool = bool(keepdims)
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
                        sel_full: list[Any] = []
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
                        sel_full2: list[Any] = []
                        m_idx = 0
                        for ax in range(arr.ndim):
                            if ax == axis_norm:
                                sel_full2.append(slice(None))
                            else:
                                sel_full2.append(sel[m_idx])
                                m_idx += 1
                        sel_tuple = tuple(sel_full2)
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


# Backwards-compatible wrappers: tests and older code expect `make_unitary_role`
# to accept a token/name and keyword args like `D` and `global_seed`. The
# canonical implementation lives in `somabrain.roles` which uses a (dim, seed)


def make_unitary_role(
    token_or_dim, D=None, global_seed=None, seed=None, dtype=np.float32, **kwargs
):
    """Legacy-compatible wrapper that lazily imports `somabrain.roles`.

    Accepts either (dim:int, ...) or (token:str, D=dim, global_seed=...),
    normalizes into (dim, seed) and calls the canonical implementation.
    Returns the time-domain role vector (numpy array).
    """
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as e:  # pragma: no cover - import failure
        raise ImportError(
            "make_unitary_role is unavailable; failed to import somabrain.roles"
        ) from e

    if isinstance(token_or_dim, str):
        dim = int(D or kwargs.get("dim") or 1024)
        seed_val = global_seed if global_seed is not None else seed
    else:
        dim = int(token_or_dim)
        seed_val = seed if seed is not None else global_seed

    u_time, _spec = _roles.make_unitary_role(dim, seed=seed_val, dtype=dtype)
    return u_time


def role_spectrum_from_seed(
    token_or_dim, D=None, global_seed=None, seed=None, dtype=np.float32, **kwargs
):
    """Legacy-compatible wrapper returning the rfft spectrum; lazy-imports roles."""
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as e:  # pragma: no cover - import failure
        raise ImportError(
            "role_spectrum_from_seed is unavailable; failed to import somabrain.roles"
        ) from e

    if isinstance(token_or_dim, str):
        dim = int(D or kwargs.get("dim") or 1024)
        seed_val = global_seed if global_seed is not None else seed
    else:
        dim = int(token_or_dim)
        seed_val = seed if seed is not None else global_seed

    return _roles.role_spectrum_from_seed(dim, seed=seed_val, dtype=dtype)


def spectral_floor_from_tiny(tiny_amplitude: float, dim: int) -> float:
    """Convert an amplitude tiny-floor (L2 units) to a per-frequency-bin power floor.

    The amplitude tiny is in units of ||x||_2. For FFT-based spectral routines where
    spectral power per bin = |X_k|^2 and Parseval's theorem gives sum_k |X_k|^2 = D * ||x||_2^2
    (with unitary FFT normalization used in this project), convert the amplitude floor
    to a per-bin power floor using tiny_amplitude**2 / dim.

    This helper is intentionally simple and exact; callers may further max() it against
    other configured epsilons.
    """
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        D = int(dim)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        D = int(getattr(dim, "__len__", lambda: dim)())
    # convert amplitude floor (||x||_2 units) to per-frequency-bin power floor
    tiny_amp = float(tiny_amplitude)
    if D <= 0:
        raise ValueError("dim must be positive")
    return (tiny_amp**2) / float(D)
