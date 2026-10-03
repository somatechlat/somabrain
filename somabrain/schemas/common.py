"""
Common utilities and base types for schemas.

Vector normalization and shared constants.
"""

from __future__ import annotations

import numpy as np

from django.conf import settings

from somabrain.embed_dim import resolve_embed_dim


def normalize_vector(vec_like, dim: int | None = None):
    """
    Convert an input sequence/array to a unit-norm list of length ``dim``.

    ``dim`` defaults to the configured embed dimension. It is resolved through
    ``resolve_embed_dim`` rather than a literal here: the vector dimension is
    configuration (``SOMABRAIN_EMBED_DIM``, checked against the seam contract),
    and a hardcoded one would silently diverge from the rest of the triad.
    """
    from somabrain.admin.core.numerics import normalize_array

    if dim is None:
        dim = resolve_embed_dim()
    dtype = np.dtype(settings.SOMABRAIN_HRR_DTYPE)

    arr = np.asarray(vec_like, dtype=dtype)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    if arr.size < dim:
        padded = np.zeros((dim,), dtype=dtype)
        padded[: arr.size] = arr
        arr = padded
    elif arr.size > dim:
        arr = arr[:dim]

    normed = normalize_array(arr, axis=-1, keepdims=False, dtype=dtype)
    return normed.tolist()
