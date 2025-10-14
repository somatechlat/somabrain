"""Unitary role generation helpers.

Creates unitary (energy-preserving) role vectors whose spectrum has unit
magnitude, ensuring exact invertibility via conjugate-multiply in frequency
domain. Deterministic when a seed is provided.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from . import numerics as _num, seed as _seed


def make_unitary_role(
    dim: int, seed: Optional[int | str | bytes] = None, dtype=np.float32
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (time_domain_vector, rfft_spectrum) for a unitary role.

    The returned `time_domain_vector` has shape (dim,) and dtype `dtype`.
    The returned `rfft_spectrum` is the unitary frequency representation
    produced by `_num.rfft_norm` and has shape appropriate for rfft
    (dim//2+1,).
    """
    rng = _seed.rng_from_seed(seed)
    # Start from gaussian and transform to spectrum
    v = rng.standard_normal(size=(dim,)).astype(dtype)
    # Compute unitary spectrum
    V = _num.rfft_norm(v, n=dim, axis=-1)
    # Normalize magnitude to 1 (preserve phase)
    mag = np.abs(V)
    # Avoid division by zero: replace zeros with 1 before dividing
    mag_safe = np.where(mag == 0.0, 1.0, mag)
    U = V / mag_safe
    # Enforce exact unit magnitude
    U = U / np.abs(U)
    # Synthesize back to time domain using unitary inverse
    u_time = _num.irfft_norm(U, n=dim, axis=-1).astype(dtype)
    # Recompute spectrum to return canonical rfft representation with unit magnitude.
    U_canon = _num.rfft_norm(u_time, n=dim, axis=-1)
    mag = np.abs(U_canon)
    mag_safe = np.where(mag == 0.0, 1.0, mag)
    U_canon = U_canon / mag_safe
    # Ensure exact unit magnitude (and avoid NaNs from zero divisions) by resetting non-finite bins.
    U_canon = np.where(np.isfinite(U_canon), U_canon, 1.0 + 0.0j)
    # Regenerate time-domain vector so it aligns with the adjusted spectrum.
    u_time = _num.irfft_norm(U_canon, n=dim, axis=-1).astype(dtype)
    return u_time, U_canon


def role_spectrum_from_seed(
    dim: int, seed: Optional[int | str | bytes] = None, dtype=np.float32
) -> np.ndarray:
    """Convenience: return only the rfft spectrum for a role."""
    _, spec = make_unitary_role(dim, seed=seed, dtype=dtype)
    return spec
