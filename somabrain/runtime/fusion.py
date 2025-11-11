"""BHDC fusion layer utilities.

This module provides a minimal BHDCFusionLayer implementation sufficient for
tests that validate mathematical formulas and basic behavior. The layer offers:
- A configurable dimensionality (default 2048)
- An adaptive alpha parameter with clamped bounds
- A deterministic fuse() method that normalizes and averages inputs

The implementation avoids external dependencies beyond NumPy and is robust to
edge cases (e.g., zero vectors, large magnitudes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import numpy as np


@dataclass
class _AlphaBounds:
    min: float = 0.1
    max: float = 5.0


class BHDCFusionLayer:
    """Simple BHDC fusion layer with adaptive alpha and deterministic fusion.

    Parameters
    - dim: vector dimensionality expected by the layer.
    - alpha: initial alpha used in softmax weighting (if applicable).
    - epsilon: small constant for numerical stability in normalization.
    - bounds: clamping range for the adaptive alpha parameter.
    """

    def __init__(
        self,
        dim: int = 2048,
        *,
        alpha: float = 1.0,
        epsilon: float = 1e-8,
        bounds: _AlphaBounds | None = None,
    ) -> None:
        self.dim = int(dim)
        self._epsilon = float(epsilon)
        self._bounds = bounds or _AlphaBounds()
        # Clamp initial alpha into bounds
        self._alpha = float(np.clip(alpha, self._bounds.min, self._bounds.max))

    @property
    def alpha(self) -> float:
        return self._alpha

    def update_alpha(self, *, performance_score: float, target: float = 0.9, rate: float = 0.2) -> None:
        """Adapt alpha based on a performance signal.

        If performance is below target, increase alpha slightly to sharpen the
        weighting; otherwise decrease slightly. The adjustment is clamped to
        [bounds.min, bounds.max].
        """
        score = float(performance_score)
        delta = max(0.0, min(1.0, abs(score - target))) * rate
        if score < target:
            new_alpha = self._alpha * (1.0 + delta)
        else:
            new_alpha = self._alpha * (1.0 - delta)
        self._alpha = float(np.clip(new_alpha, self._bounds.min, self._bounds.max))

    def fuse(self, vectors: Iterable[np.ndarray]) -> np.ndarray:
        """Fuse a collection of vectors into a single vector of length `dim`.

        Behavior:
        - Each input vector is L2-normalized (safe for zero vectors).
        - The fused result is the mean of normalized inputs, re-normalized.
        - Deterministic for identical inputs across calls.
        """
        arrs: List[np.ndarray] = [self._as_vector(v) for v in vectors]
        if not arrs:
            return np.zeros(self.dim, dtype=np.float64)

        normed = [self._safe_l2_normalize(v) for v in arrs]
        stacked = np.vstack(normed)
        mean_vec = stacked.mean(axis=0)
        return self._safe_l2_normalize(mean_vec)

    # --- Helpers ---
    def _as_vector(self, v: np.ndarray) -> np.ndarray:
        a = np.asarray(v, dtype=np.float64).reshape(-1)
        if a.size != self.dim:
            raise ValueError(f"Expected vector of dim {self.dim}, got {a.size}")
        return a

    def _safe_l2_normalize(self, v: np.ndarray) -> np.ndarray:
        n = float(np.linalg.norm(v))
        if n <= self._epsilon:
            return np.zeros_like(v)
        return v / (n + self._epsilon)

    # Optional math utilities (not required by current tests)
    def normalized_error(self, errors: np.ndarray, mu: float, sigma: float) -> np.ndarray:
        """Compute e_norm = (errors - mu) / (sigma + eps)."""
        e = np.asarray(errors, dtype=np.float64)
        return (e - float(mu)) / (float(sigma) + self._epsilon)

    def softmax_weights(self, e_norm: np.ndarray) -> np.ndarray:
        """Compute w = softmax(-alpha * e_norm)."""
        x = -self._alpha * np.asarray(e_norm, dtype=np.float64)
        # Stable softmax
        x = x - np.max(x)
        ex = np.exp(x)
        s = ex.sum()
        if s <= self._epsilon:
            # Fallback to uniform if numerical issues occur
            return np.ones_like(ex) / ex.size
        return ex / s
