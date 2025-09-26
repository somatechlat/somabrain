"""Pure HRR reference implementation (test-only).

This module provides a minimal PureLayer implementing the canonical HRR algebra:
- bind = irfft(rfft(a) * rfft(b))
- unbind = irfft(rfft(c) / rfft(b)) with exact division and raise on zero frequency

It is intentionally small and avoids any heuristics. Use for tests/benchmarks only.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable

import numpy as np


def _seed_from_text(text: str, global_seed: int = 0) -> np.random.Generator:
    h = hashlib.blake2b(text.encode("utf8"), digest_size=8).digest()
    seed = int.from_bytes(h, "little") ^ (global_seed & 0xFFFFFFFFFFFFFFFF)
    return np.random.default_rng(np.uint64(seed))


def normalize(v: np.ndarray, dtype: np.dtype) -> np.ndarray:
    # L2 norm with float64 accumulation
    v64 = v.astype(np.float64)
    n = float(np.linalg.norm(v64))
    tiny = max(np.finfo(dtype).eps * np.sqrt(v.size), np.finfo(dtype).eps)
    if n < tiny:
        raise ValueError("vector norm below tiny floor in pure reference")
    return (v64 / n).astype(dtype)


class PureLayer:
    """Minimal pure HRR layer.

    Methods mirror the public surface used by the existing benchmarks:
    - encode_text(key) -> np.ndarray
    - bind(a,b), unbind(c,b)
    - permute(v,k), superpose(*vs), cleanup(query, anchors)
    """

    def __init__(self, cfg):
        self.dim = int(cfg.dim)
        self.dtype = np.dtype(cfg.dtype)
        self.seed = int(getattr(cfg, "seed", 0) or 0)

    def random_vector(self) -> np.ndarray:
        rng = np.random.default_rng(np.uint64(self.seed))
        v = rng.standard_normal(self.dim).astype(self.dtype)
        return normalize(v, self.dtype)

    def encode_text(self, text: str) -> np.ndarray:
        rng = _seed_from_text(text, self.seed)
        v = rng.standard_normal(self.dim).astype(self.dtype)
        return normalize(v, self.dtype)

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        if a.shape != (self.dim,) or b.shape != (self.dim,):
            raise ValueError("input vectors must match layer dim")
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        # compute in complex128 for accuracy
        fc = fa.astype(np.complex128) * fb.astype(np.complex128)
        c = np.fft.irfft(fc, n=self.dim)
        return normalize(c, self.dtype)

    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        if c.shape != (self.dim,) or b.shape != (self.dim,):
            raise ValueError("input vectors must match layer dim")
        fc = np.fft.rfft(c).astype(np.complex128)
        fb = np.fft.rfft(b).astype(np.complex128)
        # exact division: raise if any frequency is exactly zero
        zero_mask = fb == 0
        if np.any(zero_mask):
            raise ZeroDivisionError("zero frequency in divisor in pure unbind")
        fa_est = fc / fb
        a_est = np.fft.irfft(fa_est, n=self.dim)
        return normalize(a_est, self.dtype)

    def permute(self, v: np.ndarray, k: int = 1) -> np.ndarray:
        return normalize(np.roll(v, k), self.dtype)

    def superpose(self, *vs: Iterable[np.ndarray]) -> np.ndarray:
        arrs = [np.asarray(v, dtype=self.dtype) for v in vs]
        s = np.sum(np.stack(arrs, axis=0).astype(np.float64), axis=0)
        return normalize(s, self.dtype)

    def cleanup(
        self, query: np.ndarray, anchors: Dict[str, np.ndarray], top_k: int = 1
    ):
        q = np.asarray(query, dtype=self.dtype)
        best = []
        for k, v in anchors.items():
            v = np.asarray(v, dtype=self.dtype)
            score = float(np.dot(q, v))  # assumes unit vectors
            best.append((k, score))
        best.sort(key=lambda x: x[1], reverse=True)
        if top_k == 1:
            return best[0]
        return best[:top_k]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a.astype(np.float64), b.astype(np.float64)))
