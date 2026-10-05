"""BHDC (Binary Hyperdimensional Computing) - Rust Bridge.

This module provides Python wrapper classes around the Rust implementation
of BHDC in somabrain_rs. The Rust implementation is 18x faster than pure Python.

All CPU-bound vector operations are in Rust, this module only provides
the NumPy interface expected by QuantumLayer. The pure-Python fallbacks
implement the **same** formulas as `rust_core/src/bhdc.rs` /
`rust_core/src/mathcore.rs` (Wiener unbind, FWHT mix, λ*).

Wiener λ* helpers and BHDC constants live in ``somabrain.math.contracts``
(single home).  This module imports them so existing call sites keep working
without a re-export facade — the definition is in contracts only.
"""

from __future__ import annotations

from typing import Union

import numpy as np

from somabrain.core.rust_bridge import get_rust_module, is_rust_available
from somabrain.math.contracts import (
    PRODUCTION_SPARSITY_P,
    compute_wiener_lambda,
    production_sparsity,
    production_wiener_lambda,
)

_SeedLike = Union[int, str, None]


def _active_count(dim: int, sparsity: float) -> int:
    """Return the exact number of active dimensions for a sparse vector."""
    return max(1, min(dim, int(round(float(sparsity) * dim))))


def fwht(values) -> list[float]:
    """Orthonormal Fast Walsh–Hadamard Transform (scale 1/√n).

    Matches `somabrain_rs.fwht` / `rust_core/src/mathcore.rs::fwht_inplace`.

    Raises:
        ValueError: if the input length is not a power of two. Never a
            silent no-op.
    """
    v = [float(x) for x in values]
    n = len(v)
    if n == 0 or (n & (n - 1)) != 0:
        raise ValueError(f"FWHT requires a power-of-two length, got {n}")
    h = 1
    while h < n:
        for i in range(0, n, 2 * h):
            for j in range(i, i + h):
                x = v[j]
                y = v[j + h]
                v[j] = x + y
                v[j + h] = x - y
        h *= 2
    scale = 1.0 / (n**0.5)
    return [x * scale for x in v]


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
    """Deterministic Python fallback for permutation-based binding.

    Mirrors `rust_core/src/bhdc.rs::PermutationBinder` exactly:
    bind applies `π(b)`, elementwise product, optional FWHT, L2 norm;
    unbind applies optional FWHT (self-inverse) then the Wiener rule
    `v̂ = (c ⊙ π(b)) / (π(b)² + λ)` with `λ = lambda_reg` and L2 norm.
    """

    def __init__(
        self,
        *,
        dim: int,
        seed: int,
        mix: str = "none",
        lambda_reg: float | None = None,
        p: float | None = None,
    ) -> None:
        if mix not in ("none", "hadamard"):
            raise ValueError(f"mix must be 'none' or 'hadamard', got {mix!r}")
        if mix == "hadamard" and (dim == 0 or (dim & (dim - 1)) != 0):
            raise ValueError(f"mix='hadamard' requires a power-of-two dim, got {dim}")
        self._dim = dim
        self._mix = mix
        if lambda_reg is None:
            self._lambda_reg = compute_wiener_lambda(
                production_sparsity() if p is None else p, 8
            )
        else:
            self._lambda_reg = float(lambda_reg)
        rng = np.random.default_rng(np.uint64(seed))
        self._perm = rng.permutation(dim)
        self._inverse_perm = np.argsort(self._perm)

    @property
    def lambda_reg(self) -> float:
        return self._lambda_reg

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
        """Bind: permute b, elementwise multiply, optional FWHT, L2 norm."""
        a_vec = np.asarray(a, dtype=np.float64)
        b_vec = self._permute(np.asarray(b, dtype=np.float64), 1)
        result = a_vec * b_vec
        if self._mix == "hadamard":
            result = np.asarray(fwht(result.tolist()), dtype=np.float64)
        norm = float(np.sqrt(np.sum(result * result)))
        if norm > 1e-10:
            result = result / norm
        return result.tolist()

    def unbind(self, c, b) -> list[float]:
        """Wiener unbind: optional FWHT, then (c ⊙ π(b)) / (π(b)² + λ)."""
        work = np.asarray(c, dtype=np.float64)
        if self._mix == "hadamard":
            work = np.asarray(fwht(work.tolist()), dtype=np.float64)
        b_vec = self._permute(np.asarray(b, dtype=np.float64), 1)
        result = (work * b_vec) / (b_vec * b_vec + self._lambda_reg)
        norm = float(np.sqrt(np.sum(result * result)))
        if norm > 1e-10:
            result = result / norm
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
        sparsity: float,
        base_seed: int,
        dtype: str | np.dtype = "float32",
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

    Wraps somabrain_rs.PermutationBinder with NumPy interface. The Python
    fallback implements the identical Wiener unbind and FWHT mix.
    """

    def __init__(
        self,
        *,
        dim: int,
        seed: int,
        dtype: str | np.dtype = "float32",
        mix: str = "none",
        lambda_reg: float | None = None,
        p: float | None = None,
    ) -> None:
        self._dim = dim
        self._dtype = np.dtype(dtype)
        # Resolve the Wiener ridge once so Rust and Python backends share it.
        # Default: λ* = compute_wiener_lambda(p, 8) at the production sparsity.
        if lambda_reg is None:
            self._lambda_reg = compute_wiener_lambda(
                production_sparsity() if p is None else p, 8
            )
        else:
            self._lambda_reg = float(lambda_reg)
        if is_rust_available():
            rust = get_rust_module()
            self._rs = rust.PermutationBinder(
                dim=dim,
                seed=seed,
                mix=mix,
                lambda_reg=self._lambda_reg,
            )
        else:
            self._rs = _PythonPermutationBinder(
                dim=dim,
                seed=seed,
                mix=mix,
                lambda_reg=self._lambda_reg,
            )

    @property
    def lambda_reg(self) -> float:
        """Wiener ridge λ actually in use (λ* = Δ²/(12 p (1−p)))."""
        return self._lambda_reg

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Bind two vectors: permute b, then elementwise multiply."""
        result = self._rs.bind(a.tolist(), b.tolist())
        return np.array(result, dtype=self._dtype)

    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Wiener unbind: v̂ = (c ⊙ π(b)) / (π(b)² + λ*)."""
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
