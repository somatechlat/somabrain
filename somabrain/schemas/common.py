"""
Common utilities and base types for schemas.

Vector normalization and shared constants.
"""

from __future__ import annotations

import numpy as np

from somabrain.core.utils.nano_profile import HRR_DIM, HRR_DTYPE


def normalize_vector(vec_like, dim: int = HRR_DIM):
    """
    Convert an input sequence/array to a unit-norm float32 list of length `dim`.
    Raises ValueError on invalid inputs.
    """
    from somabrain.apps.core.numerics import normalize_array

    arr = np.asarray(vec_like, dtype=HRR_DTYPE)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    if arr.size < dim:
        padded = np.zeros((dim,), dtype=HRR_DTYPE)
        padded[: arr.size] = arr
        arr = padded
    elif arr.size > dim:
        arr = arr[:dim]

    normed = normalize_array(arr, axis=-1, keepdims=False, dtype=HRR_DTYPE)
    return normed.tolist()
