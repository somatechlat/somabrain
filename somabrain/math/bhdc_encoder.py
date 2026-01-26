"""BHDC (Binary Hyperdimensional Computing) - Rust Bridge.

This module provides Python wrapper classes around the Rust implementation
of BHDC in somabrain_rs. The Rust implementation is 18x faster than pure Python.

All CPU-bound vector operations are in Rust, this module only provides
the NumPy interface expected by QuantumLayer.
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np

import somabrain_rs as _rs

_SeedLike = Union[int, str, None]


def _seed_to_uint64(s: _SeedLike) -> int:
    """Convert seed-like value to uint64."""
    if s is None:
        return 0
    if isinstance(s, int):
        return s & 0xFFFFFFFFFFFFFFFF
    # Hash string to int
    import hashlib
    h = hashlib.sha256(str(s).encode()).digest()
    return int.from_bytes(h[:8], 'little')


class BHDCEncoder:
    """Binary Hyperdimensional Computing Encoder - Rust accelerated.

    Wraps somabrain_rs.BHDCEncoder with NumPy interface.
    """

    def __init__(
        self,
        *,
        dim: int,
        sparsity: Union[int, float],
        base_seed: int,
        dtype: Union[str, np.dtype] = "float32",
        extra_seed: _SeedLike = None,
        tenant_id: _SeedLike = None,
        model_version: _SeedLike = None,
        binary_mode: str = "pm_one",
    ) -> None:
        self._dim = dim
        self._dtype = np.dtype(dtype)
        self._sparsity = float(sparsity) if isinstance(sparsity, float) else sparsity / dim

        # Create Rust encoder
        self._rs = _rs.BHDCEncoder(
            dim=dim,
            sparsity=self._sparsity,
            base_seed=base_seed,
            extra_seed=str(extra_seed) if extra_seed else None,
            tenant_id=str(tenant_id) if tenant_id else None,
            model_version=str(model_version) if model_version else None,
            binary_mode=binary_mode,
        )

    def random_vector(self) -> np.ndarray:
        """Generate random sparse vector."""
        return np.array(self._rs.random_vector(), dtype=self._dtype)

    def vector_for_key(self, key: str) -> np.ndarray:
        """Generate deterministic vector for key."""
        return np.array(self._rs.vector_for_key(key), dtype=self._dtype)

    def vector_for_token(self, token: str) -> np.ndarray:
        """Alias for vector_for_key."""
        return self.vector_for_key(token)


class PermutationBinder:
    """Permutation-based binder - Rust accelerated.

    Wraps somabrain_rs.PermutationBinder with NumPy interface.
    """

    def __init__(
        self,
        *,
        dim: int,
        seed: int,
        dtype: Union[str, np.dtype] = "float32",
        mix: str = "none",
        lambda_reg: float = 2.05e-5,  # GMD Theorem 3: λ* = (2/255)²/3
    ) -> None:
        self._dim = dim
        self._dtype = np.dtype(dtype)
        self._lambda_reg = lambda_reg
        self._rs = _rs.PermutationBinder(
            dim=dim, seed=seed, mix=mix, lambda_reg=lambda_reg
        )

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Bind two vectors: permute b, then elementwise multiply."""
        result = self._rs.bind(a.tolist(), b.tolist())
        return np.array(result, dtype=self._dtype)

    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Unbind: inverse of bind."""
        result = self._rs.unbind(c.tolist(), b.tolist())
        return np.array(result, dtype=self._dtype)

    def permute(self, vec: np.ndarray, times: int = 1) -> np.ndarray:
        """Permute vector n times."""
        result = self._rs.permute(vec.tolist(), times)
        return np.array(result, dtype=self._dtype)

    @property
    def permutation(self) -> np.ndarray:
        """Get permutation indices."""
        return np.array(self._rs.permutation(), dtype=np.int64)

    @property
    def inverse_permutation(self) -> np.ndarray:
        """Get inverse permutation indices."""
        return np.array(self._rs.inverse_permutation(), dtype=np.int64)


def ensure_binary(values) -> np.ndarray:
    """Ensure values are binary {-1, +1}."""
    arr = np.asarray(values)
    return np.where(arr >= 0, 1.0, -1.0)
