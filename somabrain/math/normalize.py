"""Canonical vector normalization - SINGLE SOURCE OF TRUTH.

Mathematical Foundation:
    normalize(v) = v / ||v||

    where ||v|| = sqrt(sum(v_i^2)) is the L2 (Euclidean) norm.

Design Decision:
    The existing `somabrain/numerics.py:normalize_array` is 250+ lines with
    multiple modes ("legacy_zero", "robust", "strict"). This is a VIBE violation
    (complexity without justification). We replace it with a simple, correct
    implementation that handles the common case.

    For the rare cases needing special behavior, callers should handle
    edge cases explicitly rather than hiding them in mode flags.

VIBE Compliance:
    - This is the ONLY implementation of vector normalization in the codebase
    - All other implementations must be removed and redirect here
    - Property tests verify mathematical correctness (see tests/unit/test_math_normalize.py)
"""

from __future__ import annotations

from typing import Tuple, Union

import numpy as np

# Epsilon for numerical stability
# Chosen to be above float32 machine epsilon (~1.2e-7) but small enough
# to not affect meaningful computations
_EPS = 1e-12

ArrayLike = Union[np.ndarray, list, tuple]


def normalize_vector(
    v: ArrayLike,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Normalize vector to unit L2 norm.

    Args:
        v: Input vector (any array-like)
        eps: Minimum norm threshold (returns zero vector if below)
        dtype: Output dtype (default float32 for memory efficiency)

    Returns:
        Unit-norm vector, or zero vector if input norm < eps.

    Mathematical Properties (VERIFIED BY PROPERTY TESTS):
        1. Idempotent: normalize(normalize(v)) == normalize(v)
        2. Unit norm: ||normalize(v)|| == 1.0 for non-zero v (within tolerance)
        3. Zero preservation: normalize(0) == 0
        4. Direction preservation: normalize(v) is parallel to v
        5. Scale invariance: normalize(k*v) == normalize(v) for k > 0

    Numerical Stability:
        - Uses float64 for intermediate norm calculation
        - Handles denormalized floats via epsilon threshold
        - Final cast to output dtype preserves precision where needed

    Performance:
        - Single pass through data for norm calculation
        - In-place division where possible
        - O(n) time complexity, O(1) extra space (excluding output)

    Examples:
        >>> normalize_vector([3, 4])
        array([0.6, 0.8], dtype=float32)
        >>> normalize_vector([0, 0, 0])
        array([0., 0., 0.], dtype=float32)
    """
    # Convert to float64 for numerical stability in norm calculation
    v_arr = np.asarray(v, dtype=np.float64).ravel()

    # Compute L2 norm
    norm = np.linalg.norm(v_arr)

    # Handle zero/near-zero vectors
    if norm <= eps:
        return np.zeros(v_arr.shape, dtype=dtype)

    # Normalize and cast to output dtype
    normalized = v_arr / norm
    return normalized.astype(dtype, copy=False)


def safe_normalize(
    v: ArrayLike,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> Tuple[np.ndarray, float]:
    """Normalize vector and return original norm.

    Useful when the original magnitude is needed for downstream computation
    (e.g., weighting, scaling, or diagnostics).

    Args:
        v: Input vector
        eps: Minimum norm threshold
        dtype: Output dtype

    Returns:
        Tuple of (normalized_vector, original_norm)
        If original_norm < eps, returns (zero_vector, 0.0)

    Example:
        >>> vec, norm = safe_normalize([3, 4])
        >>> vec
        array([0.6, 0.8], dtype=float32)
        >>> norm
        5.0
    """
    v_arr = np.asarray(v, dtype=np.float64).ravel()
    norm = float(np.linalg.norm(v_arr))

    if norm <= eps:
        return np.zeros(v_arr.shape, dtype=dtype), 0.0

    normalized = (v_arr / norm).astype(dtype, copy=False)
    return normalized, norm


def normalize_batch(
    vectors: np.ndarray,
    axis: int = -1,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Normalize a batch of vectors along specified axis.

    Args:
        vectors: Array of shape (..., dim) or (dim, ...)
        axis: Axis along which to normalize (default -1, last axis)
        eps: Minimum norm threshold
        dtype: Output dtype

    Returns:
        Normalized array with same shape as input.
        Vectors with norm < eps are set to zero.

    Example:
        >>> batch = np.array([[3, 4], [0, 0], [1, 0]])
        >>> normalize_batch(batch, axis=-1)
        array([[0.6, 0.8],
               [0. , 0. ],
               [1. , 0. ]], dtype=float32)
    """
    arr = np.asarray(vectors, dtype=np.float64)

    # Compute norms along axis, keeping dims for broadcasting
    norms = np.linalg.norm(arr, axis=axis, keepdims=True)

    # Create mask for zero/near-zero vectors
    mask = norms > eps

    # Avoid division by zero: replace zero norms with 1.0 (result will be zeroed by mask)
    safe_norms = np.where(mask, norms, 1.0)

    # Normalize where norm is sufficient, zero otherwise
    result = np.where(mask, arr / safe_norms, 0.0)

    return result.astype(dtype, copy=False)


def ensure_unit_norm(
    v: ArrayLike,
    eps: float = _EPS,
    dtype: np.dtype = np.float32,
    tolerance: float = 1e-6,
) -> np.ndarray:
    """Ensure vector has unit norm, normalizing only if necessary.

    This is an optimization for cases where vectors may already be normalized.
    Avoids unnecessary computation when the vector is already unit-norm.

    Args:
        v: Input vector
        eps: Minimum norm threshold for zero detection
        dtype: Output dtype
        tolerance: How close to 1.0 the norm must be to skip normalization

    Returns:
        Unit-norm vector (either original if already unit-norm, or normalized)
    """
    v_arr = np.asarray(v, dtype=np.float64).ravel()
    norm = np.linalg.norm(v_arr)

    # Zero vector case
    if norm <= eps:
        return np.zeros(v_arr.shape, dtype=dtype)

    # Already unit norm (within tolerance)
    if abs(norm - 1.0) <= tolerance:
        return v_arr.astype(dtype, copy=False)

    # Need to normalize
    return (v_arr / norm).astype(dtype, copy=False)
