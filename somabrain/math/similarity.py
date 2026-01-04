"""Canonical similarity functions - SINGLE SOURCE OF TRUTH.

Mathematical Foundation:
    cosine(a, b) = (a · b) / (||a|| × ||b||)

    where:
    - a · b is the dot product (inner product)
    - ||x|| is the L2 norm (Euclidean norm)

Numerical Considerations:
    - Use float64 for intermediate calculations to minimize rounding error
    - Handle zero-norm vectors explicitly (return 0.0, not NaN)
    - Clamp result to [-1, 1] to handle floating-point edge cases

VIBE Compliance:
    - This is the ONLY implementation of cosine similarity in the codebase
    - All other implementations must be removed and redirect here
    - Property tests verify mathematical correctness (see tests/unit/test_math_similarity.py)
"""

from __future__ import annotations

from typing import Union

import numpy as np

# Epsilon for numerical stability - chosen to be above float64 machine epsilon
# but small enough to not affect meaningful computations
_EPS = 1e-12

ArrayLike = Union[np.ndarray, list, tuple]


def cosine_similarity(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector (any array-like)
        b: Second vector (any array-like)

    Returns:
        Cosine similarity in [-1, 1], or 0.0 if either vector has zero norm.

    Mathematical Properties (VERIFIED BY PROPERTY TESTS):
        1. Symmetric: cosine(a, b) == cosine(b, a)
        2. Self-similarity: cosine(a, a) == 1.0 for non-zero a
        3. Bounded: -1.0 <= cosine(a, b) <= 1.0
        4. Zero handling: cosine(0, x) == 0.0
        5. Orthogonality: cosine(a, b) == 0.0 when a ⊥ b

    Numerical Stability:
        - Uses float64 intermediate calculations
        - Handles denormalized floats via epsilon threshold
        - Clamps output to handle floating-point edge cases

    Raises:
        ValueError: If vectors have different lengths

    Examples:
        >>> cosine_similarity([1, 0, 0], [1, 0, 0])
        1.0
        >>> cosine_similarity([1, 0, 0], [0, 1, 0])
        0.0
        >>> cosine_similarity([1, 0, 0], [-1, 0, 0])
        -1.0
        >>> cosine_similarity([0, 0, 0], [1, 2, 3])
        0.0
    """
    # Convert to float64 for numerical stability
    a_arr = np.asarray(a, dtype=np.float64).ravel()
    b_arr = np.asarray(b, dtype=np.float64).ravel()

    # Validate dimensions
    if a_arr.shape[0] != b_arr.shape[0]:
        raise ValueError(
            f"Vector dimension mismatch: {a_arr.shape[0]} vs {b_arr.shape[0]}"
        )

    # Compute norms using float64
    na = np.linalg.norm(a_arr)
    nb = np.linalg.norm(b_arr)

    # Handle zero-norm vectors
    if na <= _EPS or nb <= _EPS:
        return 0.0

    # Compute similarity with numerical clamping
    # The clamp handles edge cases where floating-point arithmetic
    # produces values slightly outside [-1, 1]
    dot = np.dot(a_arr, b_arr)
    sim = dot / (na * nb)

    return float(np.clip(sim, -1.0, 1.0))


def cosine_error(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine error (1 - similarity) bounded to [0, 1].

    This is the standard error metric for vector comparison where:
    - 0.0 = identical vectors (perfect match)
    - 1.0 = orthogonal vectors (no similarity)
    - Values > 1.0 (opposite vectors) are clamped to 1.0

    Note: We clamp to [0, 1] because negative similarity (opposite vectors)
    is treated as maximum error for most cognitive applications.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine error in [0, 1]
    """
    sim = cosine_similarity(a, b)
    # Clamp to [0, 1] - opposite vectors (sim < 0) are maximum error
    return float(max(0.0, min(1.0, 1.0 - sim)))


def cosine_distance(a: ArrayLike, b: ArrayLike) -> float:
    """Compute cosine distance (1 - similarity) in [0, 2].

    Unlike cosine_error, this preserves the full range:
    - 0.0 = identical vectors
    - 1.0 = orthogonal vectors
    - 2.0 = opposite vectors

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine distance in [0, 2]
    """
    sim = cosine_similarity(a, b)
    return float(1.0 - sim)


def batch_cosine_similarity(
    query: ArrayLike, candidates: np.ndarray, axis: int = -1
) -> np.ndarray:
    """Compute cosine similarity between a query and multiple candidates.

    Optimized for batch operations - more efficient than calling
    cosine_similarity in a loop.

    Args:
        query: Query vector of shape (dim,)
        candidates: Array of candidate vectors, shape (..., dim) or (dim, ...)
        axis: Axis along which candidates are stored (default -1, last axis)

    Returns:
        Array of similarities with shape matching candidates minus the axis dimension

    Example:
        >>> query = np.array([1.0, 0.0, 0.0])
        >>> candidates = np.array([[1, 0, 0], [0, 1, 0], [0.5, 0.5, 0]])
        >>> batch_cosine_similarity(query, candidates)
        array([1.        , 0.        , 0.70710678])
    """
    q = np.asarray(query, dtype=np.float64).ravel()
    c = np.asarray(candidates, dtype=np.float64)

    # Compute query norm
    q_norm = np.linalg.norm(q)
    if q_norm <= _EPS:
        return np.zeros(c.shape[:-1] if axis == -1 else c.shape[1:])

    # Compute candidate norms along axis
    c_norms = np.linalg.norm(c, axis=axis, keepdims=True)

    # Compute dot products
    dots = np.tensordot(c, q, axes=([axis], [0]))

    # Handle zero-norm candidates
    c_norms_squeezed = np.squeeze(c_norms, axis=axis)
    mask = c_norms_squeezed > _EPS

    # Compute similarities
    result = np.zeros_like(c_norms_squeezed)
    result[mask] = dots[mask] / (c_norms_squeezed[mask] * q_norm)

    return np.clip(result, -1.0, 1.0)