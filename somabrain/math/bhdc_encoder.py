"""BHDC (Binary Hyperdimensional Computing) - Rust Bridge.

This module provides Python wrapper classes around the Rust implementation
of BHDC in somabrain_rs. The Rust implementation is 18x faster than pure Python.

All CPU-bound vector operations are in Rust, this module only provides
the NumPy interface expected by QuantumLayer.
"""

from __future__ import annotations

from typing import Union

import numpy as np

from somabrain.core.rust_bridge import get_rust_module, is_rust_available

_SeedLike = Union[int, str, None]


def _active_count(dim: int, sparsity: float) -> int:
    """Return the exact number of active dimensions for a sparse vector."""
    return max(1, min(dim, int(round(float(sparsity) * dim))))


class _PythonBHDCEngine:
    """Deterministic Python fallback for BHDC vector generation."""

    def __init__(
        self,
        *,
        dim: int,
        sparsity: float,
        base_seed: int,
        extra_seed: str | None,
        tenant_id: str | None,
        model_version: str | None,
        binary_mode: str,
    ) -> None:
        self._dim = dim
        self._sparsity = float(sparsity)
        self._base_seed = int(base_seed)
        self._extra_seed = extra_seed
        self._tenant_id = tenant_id
        self._model_version = model_version
        self._binary_mode = binary_mode
        self._rng = np.random.default_rng(np.uint64(self._base_seed))

    def _compose_seed(self, key: str | None = None) -> np.uint64:
        parts = [
            str(self._base_seed),
            self._extra_seed or "",
            self._tenant_id or "",
            self._model_version or "",
            key or "",
        ]
        return np.uint64(_seed_to_uint64("|".join(parts)))

    def _render_sparse_vector(self, rng: np.random.Generator) -> list[float]:
        active_count = _active_count(self._dim, self._sparsity)
        active = rng.choice(self._dim, size=active_count, replace=False)

        if self._binary_mode == "pm_one":
            vec = np.full(self._dim, -1.0, dtype=np.float32)
            vec[active] = 1.0
            return vec.tolist()

        vec = np.zeros(self._dim, dtype=np.float32)
        vec[active] = 1.0
        vec -= vec.mean()
        return vec.tolist()

    def random_vector(self) -> list[float]:
        """Generate a sparse random vector using the local RNG state."""
        return self._render_sparse_vector(self._rng)

    def vector_for_key(self, key: str) -> list[float]:
        """Generate a deterministic sparse vector for the given key."""
        rng = np.random.default_rng(self._compose_seed(key))
        return self._render_sparse_vector(rng)


class _PythonPermutationBinder:
    """Deterministic Python fallback for permutation-based binding."""

    def __init__(
        self,
        *,
        dim: int,
        seed: int,
        mix: str = "none",
        lambda_reg: float = 2.05e-5,
    ) -> None:
        self._dim = dim
        self._mix = mix
        self._lambda_reg = lambda_reg
        rng = np.random.default_rng(np.uint64(seed))
        self._perm = rng.permutation(dim)
        self._inverse_perm = np.argsort(self._perm)

    def _permute(self, vec: np.ndarray, times: int = 1) -> np.ndarray:
        result = np.asarray(vec, dtype=np.float64)
        if times >= 0:
            for _ in range(times):
                result = result[self._perm]
            return result

        for _ in range(-times):
            result = result[self._inverse_perm]
        return result

    def bind(self, a, b) -> list[float]:
        """Bind two vectors via permutation then elementwise multiplication."""
        a_vec = np.asarray(a, dtype=np.float64)
        b_vec = self._permute(np.asarray(b, dtype=np.float64), 1)
        result = a_vec * b_vec
        return result.tolist()

    def unbind(self, c, b) -> list[float]:
        """Invert bind by dividing by the permuted key."""
        c_vec = np.asarray(c, dtype=np.float64)
        b_vec = self._permute(np.asarray(b, dtype=np.float64), 1)
        tiny = np.where(b_vec >= 0.0, 1e-12, -1e-12)
        denom = np.where(np.abs(b_vec) < 1e-12, tiny, b_vec)
        result = c_vec / denom
        return result.tolist()

    def permute(self, vec, times: int = 1) -> list[float]:
        """Return the permuted vector."""
        return self._permute(np.asarray(vec, dtype=np.float64), times).tolist()

    def permutation(self) -> list[int]:
        """Return the forward permutation."""
        return self._perm.tolist()

    def inverse_permutation(self) -> list[int]:
        """Return the inverse permutation."""
        return self._inverse_perm.tolist()


def _seed_to_uint64(s: _SeedLike) -> int:
    """Convert seed-like value to uint64."""
    if s is None:
        return 0
    if isinstance(s, int):
        return s & 0xFFFFFFFFFFFFFFFF
    # Hash string to int
    import hashlib

    h = hashlib.sha256(str(s).encode()).digest()
    return int.from_bytes(h[:8], "little")


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
        self._sparsity = (
            float(sparsity) if isinstance(sparsity, float) else sparsity / dim
        )

        if is_rust_available():
            rust = get_rust_module()
            self._rs = rust.BHDCEncoder(
                dim=dim,
                sparsity=self._sparsity,
                base_seed=base_seed,
                extra_seed=str(extra_seed) if extra_seed else None,
                tenant_id=str(tenant_id) if tenant_id else None,
                model_version=str(model_version) if model_version else None,
                binary_mode=binary_mode,
            )
        else:
            self._rs = _PythonBHDCEngine(
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
        if is_rust_available():
            rust = get_rust_module()
            self._rs = rust.PermutationBinder(
                dim=dim, seed=seed, mix=mix, lambda_reg=lambda_reg
            )
        else:
            self._rs = _PythonPermutationBinder(
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
