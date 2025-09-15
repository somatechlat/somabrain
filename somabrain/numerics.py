"""Numeric primitives and small math contract for SomaBrain.

This module provides a small, explicit numeric contract used across the HRR
code-paths in this project. The goal is to be short, auditable and to state
the invariants used by the implementation:

- FFTs are unitary for energy preservation: use rfft/irfft with norm='ortho'.
- The "tiny" floor is an amplitude (L2) threshold. When working in the
  spectral domain (per-FFT-bin), callers must convert amplitude -> power by
  squaring and dividing by D (bins): power_per_bin = tiny_amp**2 / D.
- Normalization is done with float64 accumulation and deterministic fallbacks
  (baseline = ones / sqrt(D)) when the slice energy is below the tiny floor.
- Role vectors created from random phases are renormalized in the time domain
  to ensure unit L2 (isometry) after inverse-FFT.

These decisions keep HRR binding/unbinding numerically stable and deterministic
across machines and numpy versions.
"""

import hashlib
import math
from typing import Any

import numpy as np

# Small per-dtype minimums to avoid underflow on extremely small dims.
_TINY_MIN = {
    np.float32: 1e-6,
    np.float64: 1e-12,
}


def compute_tiny_floor(
    D: int | np.dtype | type,
    dtype: Any = np.float32,
    scale: float = 1.0,
    strategy: str = "sqrt",
) -> float:
    """Return an amplitude "tiny" threshold (L2 units) for dimension D.

    Implementation note:
    - Use machine epsilon scaled by sqrt(D) so the tiny threshold grows with
      vector length (L2 sensible). The `scale` factor is conservative.
    - The returned value is an amplitude (L2 norm). For spectral (power)
      thresholds convert with tiny_amp**2 / D.
    """
    # Backwards-compatible argument handling: callers may pass (dtype, D)
    # or (D, dtype). Accept both orders gracefully.
    # If `dtype` is actually an integer, swap.
    if isinstance(D, (np.dtype, type)) and not isinstance(dtype, (np.dtype, type)):
        # signature called as compute_tiny_floor(dtype, D)
        dtype_val = D
        D_val = dtype
    else:
        dtype_val = dtype
        D_val = D

    try:
        dt = np.dtype(dtype_val)
    except Exception:
        # fallback: if dtype_val looks like a string
        dt = np.dtype(str(dtype_val))

    if not isinstance(D_val, (int, np.integer)):
        D_val = int(D_val)

    eps = float(np.finfo(dt).eps)
    tiny_min = _TINY_MIN.get(dt.type, 1e-12)
    if strategy == "linear":
        val = eps * float(D_val) * scale
    else:
        val = eps * math.sqrt(float(D_val)) * scale
    return float(max(tiny_min, val))


def spectral_floor_from_tiny(tiny_amp: float, D: int) -> float:
    """Return per-FFT-bin power floor (float64) from amplitude tiny_amp.

    The canonical conversion used across the codebase is:
        power_per_bin = (tiny_amp ** 2) / D

    The function always returns a Python float (float64) suitable for
    comparing against spectral power arrays.
    """
    try:
        D_val = int(D)
    except Exception:
        D_val = int(float(D))
    return float((float(tiny_amp) ** 2) / float(D_val))


def rfft_norm(x: np.ndarray, n: int | None = None, axis: int = -1):
    """Unitary real-FFT wrapper (norm='ortho').

    Using norm='ortho' makes the transform an isometry (up to machine error):
    ||x||_2 == ||rfft_norm(x)||_2 (with the appropriate complex norm).
    This simplifies reasoning about binding as multiplication in the spectral domain.
    """
    return np.fft.rfft(x, n=n, axis=axis, norm="ortho")


def irfft_norm(X: np.ndarray, n: int, axis: int = -1):
    """Inverse unitary real-FFT wrapper (norm='ortho')."""
    return np.fft.irfft(X, n=n, axis=axis, norm="ortho")


def normalize_array(
    x: np.ndarray,
    axis: int = -1,
    keepdims: bool = False,
    tiny_floor_strategy: str = "sqrt",
    dtype: Any = np.float32,
    strict: bool = False,
    # Default to 'robust' for production: deterministic baseline instead of zeros
    mode: str = "robust",
    **kwargs,
):
    """Numerically-safe L2 normalization along an axis.

    Contract summary:
    - Compute slice energy in float64: E = sum(|x|^2).
    - Compare with tiny_amp**2 (tiny is amplitude). If E >= tiny_amp**2 -> normal
      normalization: x / sqrt(E + tiny_amp**2).
    - If E < tiny_amp**2 -> fallback behavior depends on `mode`:
       * 'legacy_zero' : return zero-vector for that slice (preserves old behavior)
       * 'robust'      : return deterministic baseline vector ones/sqrt(D)
       * 'strict'      : raise ValueError

    All accumulation is done in float64 to be conservative. Non-finite results
    are replaced by the baseline vector.
    """
    arr = np.asarray(x)
    if arr.size == 0:
        return arr.astype(arr.dtype)

    # Backwards-compatibility: callers sometimes pass (arr, D, dtype, ...)
    # Detect if `axis` was actually used to pass D (e.g. axis >= arr.shape[-1])
    ndim = arr.ndim
    # Handle legacy raise_on_subtiny kw: False -> legacy_zero, True -> strict
    if "raise_on_subtiny" in kwargs:
        val = kwargs.pop("raise_on_subtiny")
        if bool(val):
            strict = True
        else:
            mode = "legacy_zero"

    axis_norm = axis if axis >= 0 else ndim + axis
    # If axis looks like a dimension count (>= arr.shape[-1]) and keepdims is a dtype
    if isinstance(axis, (int, np.integer)) and axis >= arr.shape[-1]:
        # Legacy signature normalize_array(x, D, dtype, ...)
        D = int(axis)
        # interpret keepdims param as dtype when it appears to be one
        if isinstance(keepdims, (type, np.dtype)):
            dtype = keepdims
            keepdims = False
        axis_norm = ndim - 1
    else:
        try:
            D = arr.shape[axis_norm]
        except Exception:
            D = arr.shape[-1]

    tiny_amp = compute_tiny_floor(int(D), dtype=dtype, strategy=tiny_floor_strategy)
    arr_f64 = arr.astype(np.float64)
    # Use the computed axis_norm for all reductions to support legacy D-as-arg
    sq = np.sum(np.abs(arr_f64) ** 2, axis=axis_norm, keepdims=keepdims)
    tiny_sq = float(tiny_amp) ** 2
    denom = np.sqrt(sq + tiny_sq)
    if not keepdims:
        denom_b = np.expand_dims(denom, axis=axis_norm)
    else:
        denom_b = denom
    result = (arr_f64 / denom_b).astype(arr.dtype)

    # Handle slices whose energy is below the tiny threshold
    sq_nokeep = np.sum(np.abs(arr_f64) ** 2, axis=axis_norm, keepdims=False)
    mask_subtiny = sq_nokeep < tiny_sq

    if np.any(mask_subtiny):
        if strict or mode == "strict":
            raise ValueError("vector norm below tiny_floor in strict mode")
        if mode == "legacy_zero":
            # Preserve legacy behavior: replace subtiny slices with zero
            if mask_subtiny.ndim == 0:
                if bool(mask_subtiny):
                    result = np.zeros_like(arr, dtype=arr.dtype)
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
                        result[sel_tuple] = 0
                    it.iternext()
        else:
            # 'robust': deterministic baseline vector of unit L2: ones/sqrt(D)
            baseline = np.ones((D,), dtype=arr.dtype) / np.sqrt(float(D))
            if mask_subtiny.ndim == 0:
                if bool(mask_subtiny):
                    result = np.broadcast_to(baseline, arr.shape).astype(arr.dtype)
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
                        result[sel_tuple] = np.broadcast_to(baseline, (D,)).astype(
                            arr.dtype
                        )
                    it.iternext()

    # Final per-slice L2 correction to ensure unit norm (guard against tiny rounding)
    res_f64 = np.asarray(result, dtype=np.float64)
    norm64 = np.sqrt(np.sum(np.abs(res_f64) ** 2, axis=axis_norm, keepdims=True))
    norm_safe = np.where(norm64 == 0, 1.0, norm64)
    res_f64 = res_f64 / norm_safe
    result = np.asarray(res_f64, dtype=arr.dtype)

    # Replace non-finite entries with baseline
    if not np.all(np.isfinite(result)):
        baseline_full = np.broadcast_to(
            np.ones((D,), dtype=arr.dtype) / np.sqrt(float(D)), arr.shape
        )
        result = np.where(np.isfinite(result), result, baseline_full)

    return result


def _seed_from_name(global_seed: int, name: str) -> int:
    """Deterministic small integer seed from a (global_seed, name) pair."""
    h = hashlib.blake2b(digest_size=16)
    h.update(str(global_seed).encode("utf-8"))
    h.update(b":")
    h.update(name.encode("utf-8"))
    return int.from_bytes(h.digest(), "little")


def role_spectrum_from_seed(name: str, *, D: int, global_seed: int, dtype=np.float32):
    """Return a unit-magnitude frequency spectrum H for a deterministic role.

    The spectrum is constructed by drawing uniform random phases for the
    non-redundant rFFT bins and forcing DC (and Nyquist when present) to be real.
    This yields a spectrum with |H_k| == 1 which, when used with unitary FFTs,
    makes binding with that role isometric (before any explicit renormalization).
    """
    rng = np.random.default_rng(_seed_from_name(global_seed, name))
    n_bins = D // 2 + 1
    phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins)
    H = np.exp(1j * phases).astype(
        np.complex64 if dtype == np.float32 else np.complex128
    )
    H[0] = 1.0 + 0.0j
    if D % 2 == 0:
        H[-1] = 1.0 + 0.0j
    return H


def make_unitary_role(name: str, *, D: int, global_seed: int, dtype=np.float32):
    """Create a deterministic time-domain role vector with unit L2.

    Steps:
    1. Build unit-magnitude frequency spectrum H (phases from seeded RNG).
    2. Compute time-domain real vector via unitary inverse FFT (irfft with norm='ortho').
    3. Renormalize to unit L2 in the time domain (defensive: preserves isometry
       across FFT convention changes and machine epsilon differences).
    """
    H = role_spectrum_from_seed(name, D=D, global_seed=global_seed, dtype=dtype)
    r = irfft_norm(H, n=D).astype(dtype)
    r = normalize_array(r, mode="robust")  # enforce unit L2 baseline
    return r
