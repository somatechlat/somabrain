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
    
    # Create a random phase spectrum
    phase = rng.uniform(-np.pi, np.pi, size=(dim // 2 + 1,))
    
    # Create a unitary spectrum with unit magnitude
    U_canon = np.exp(1j * phase).astype(np.complex64)
    
    # Synthesize to time domain
    u_time = _num.irfft_norm(U_canon, n=dim, axis=-1).astype(dtype)
    
    # Renormalize in time domain to ensure unit norm
    u_time = _num.normalize_array(u_time)
    
    return u_time, U_canon


def role_spectrum_from_seed(
    dim: int, seed: Optional[int | str | bytes] = None, dtype=np.float32
) -> np.ndarray:
    """Convenience: return only the rfft spectrum for a role."""
    _, spec = make_unitary_role(dim, seed=seed, dtype=dtype)
    return spec
