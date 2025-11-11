"""Deterministic seeding helpers.

Provides a small utility to convert arbitrary seeds (int/str/bytes/None)
into a stable uint64 and a NumPy Generator. Uses blake2b for text -> int
hashing to produce reproducible uint64 seeds.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Union

import numpy as np


def _hash_to_uint64(b: bytes) -> int:
    h = hashlib.blake2b(b, digest_size=8)
    return int.from_bytes(h.digest(), byteorder="little", signed=False)


def seed_to_uint64(seed: Optional[Union[int, str, bytes]]) -> int:
    """Convert seed to a deterministic uint64.

    - None => 0
    - int => masked to 64 bits
    - str/bytes => blake2b -> uint64
    """
    if seed is None:
        return 0
    if isinstance(seed, int):
        return int(seed) & ((1 << 64) - 1)
    if isinstance(seed, str):
        return _hash_to_uint64(seed.encode("utf-8"))
    if isinstance(seed, (bytes, bytearray)):
        return _hash_to_uint64(bytes(seed))
    # Alternative: coerce to string
    return _hash_to_uint64(str(seed).encode("utf-8"))


def rng_from_seed(seed: Optional[Union[int, str, bytes]] = None) -> np.random.Generator:
    """Return a numpy Generator seeded deterministically from `seed`."""
    s64 = seed_to_uint64(seed)
    return np.random.default_rng(s64)


def random_unit_vector(
    dim: int, seed: Optional[Union[int, str, bytes]] = None, dtype=np.float32
) -> np.ndarray:
    """Return a random unit-length vector (L2-normalized) of shape (dim,)."""
    rng = rng_from_seed(seed)
    v = rng.standard_normal(size=(dim,)).astype(dtype)
    norm = float(np.linalg.norm(v))
    if norm == 0:
        v[0] = 1.0
        norm = 1.0
    return (v / norm).astype(dtype)
