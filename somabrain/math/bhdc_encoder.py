"""Binary Hyperdimensional Computing (BHDC) primitives.

Provides deterministic binary/sparse hypervector generation alongside a
permutation-based binder/unbinder. This replaces prior FFT or mask-based
composers with hardware-friendly elementwise products.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, Union

import numpy as np

from somabrain.seed import seed_to_uint64


_SeedLike = Union[int, str, None]


@dataclass(frozen=True)
class _SeedBundle:
    prefix: bytes
    base_seed: np.uint64


def _build_seed_bundle(
    *,
    label: str,
    base_seed: int,
    extra_seed: _SeedLike,
    tenant_id: _SeedLike,
    model_version: _SeedLike,
) -> _SeedBundle:
    parts = [
        label,
        str(base_seed),
        str(extra_seed or ""),
        str(tenant_id or ""),
        str(model_version or ""),
    ]
    prefix = "|".join(parts).encode("ascii")
    return _SeedBundle(prefix=prefix, base_seed=np.uint64(seed_to_uint64(prefix)))


def _active_count(dim: int, sparsity: Union[int, float]) -> int:
    if isinstance(sparsity, (int, np.integer)):
        count = int(sparsity)
    else:
        if not 0.0 < float(sparsity) <= 1.0:
            raise ValueError("sparsity ratio must be in (0, 1]")
        count = int(round(float(sparsity) * dim))
    return max(1, min(dim, count))


def _fwht(vec: np.ndarray) -> np.ndarray:
    """In-place Walsh–Hadamard transform returning the transformed view."""

    n = vec.shape[0]
    if n & (n - 1) != 0:
        raise ValueError("Walsh–Hadamard transform requires power-of-two dimension")
    h = 1
    out = vec
    while h < n:
        for i in range(0, n, h * 2):
            first = out[i : i + h]
            second = out[i + h : i + 2 * h]
            temp = first.copy()
            out[i : i + h] = temp + second
            out[i + h : i + 2 * h] = temp - second
        h *= 2
    norm = 1.0 / math.sqrt(n)
    out *= norm
    return out


class BHDCEncoder:
    """Generate deterministic binary/sparse hypervectors."""

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
        self._dim = int(dim)
        if self._dim <= 0:
            raise ValueError("dimension must be positive")
        self._dtype = np.dtype(dtype)
        self._active = _active_count(self._dim, sparsity)
        mode = binary_mode.lower()
        if mode not in {"pm_one", "zero_one"}:
            raise ValueError("binary_mode must be 'pm_one' or 'zero_one'")
        self._mode = mode
        self._seeds = _build_seed_bundle(
            label="bhdc_v1",
            base_seed=base_seed,
            extra_seed=extra_seed,
            tenant_id=tenant_id,
            model_version=model_version,
        )
        self._rng = np.random.default_rng(self._seeds.base_seed)
        self._cache: Dict[int, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Vector generation
    # ------------------------------------------------------------------
    def random_vector(self) -> np.ndarray:
        return self._vector_from_rng(self._rng)

    def vector_for_key(self, key: str) -> np.ndarray:
        seed = seed_to_uint64(self._seeds.prefix + key.encode("utf-8"))
        return self._vector_from_seed(np.uint64(seed))

    def vector_for_token(self, token: str) -> np.ndarray:
        return self.vector_for_key(f"role::{token}")

    def _vector_from_seed(self, seed: np.uint64) -> np.ndarray:
        cached = self._cache.get(int(seed))
        if cached is not None:
            return cached
        rng = np.random.default_rng(np.uint64(int(seed) ^ int(self._seeds.base_seed)))
        vec = self._vector_from_rng(rng)
        vec.setflags(write=False)
        self._cache[int(seed)] = vec
        return vec

    def _vector_from_rng(self, rng: np.random.Generator) -> np.ndarray:
        indices = rng.choice(self._dim, size=self._active, replace=False)
        if self._mode == "pm_one":
            vec = np.full(self._dim, -1.0, dtype=self._dtype)
            vec[indices] = 1.0
        else:
            vec = np.zeros(self._dim, dtype=self._dtype)
            vec[indices] = 1.0
            mean = np.mean(vec)
            vec = (vec - mean).astype(self._dtype, copy=False)
        return vec


class PermutationBinder:
    """Permutation + elementwise-product binder with optional mixing."""

    def __init__(
        self,
        *,
        dim: int,
        seed: int,
        dtype: Union[str, np.dtype] = "float32",
        mix: str = "none",
    ) -> None:
        self._dim = int(dim)
        if self._dim <= 0:
            raise ValueError("dimension must be positive")
        self._dtype = np.dtype(dtype)
        rng = np.random.default_rng(np.uint64(seed))
        self._perm = rng.permutation(self._dim)
        self._perm_inv = np.argsort(self._perm)
        mix_mode = mix.lower()
        if mix_mode not in {"none", "hadamard"}:
            raise ValueError("mix must be 'none' or 'hadamard'")
        self._mix = mix_mode
        self._eps = 1e-8

    # ------------------------------------------------------------------
    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_arr = np.asarray(a, dtype=self._dtype)
        b_arr = np.asarray(b, dtype=self._dtype)
        return a_arr * b_arr

    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        c_arr = np.asarray(c, dtype=self._dtype)
        b_arr = np.asarray(b, dtype=self._dtype)
        denom_abs = np.abs(b_arr)
        if np.any(denom_abs < self._eps):
            raise ValueError(
                "PermutationBinder cannot unbind with zero-valued role components"
            )
        return c_arr / b_arr

    # ------------------------------------------------------------------
    def permute(self, vec: np.ndarray, times: int = 1) -> np.ndarray:
        arr = np.asarray(vec, dtype=self._dtype)
        return np.roll(arr, times)

    # ------------------------------------------------------------------
    def _permute_operand(
        self, operand: np.ndarray, *, expected_shape: Tuple[int, ...]
    ) -> np.ndarray:
        b_arr = np.asarray(operand, dtype=self._dtype)
        if b_arr.shape != expected_shape:
            raise ValueError("operands must have the same shape for binding")
        if self._mix == "hadamard":
            b_arr = _fwht(b_arr.astype(np.float64, copy=True)).astype(self._dtype)
        perm_b = b_arr[self._perm]
        return perm_b

    @property
    def permutation(self) -> np.ndarray:
        return self._perm

    @property
    def inverse_permutation(self) -> np.ndarray:
        return self._perm_inv


def ensure_binary(values: Iterable[float]) -> np.ndarray:
    """Project arbitrary values to {-1, +1} by sign (zeros map to +1)."""

    arr = np.asarray(list(values), dtype=float)
    signs = np.where(arr >= 0.0, 1.0, -1.0)
    return signs
