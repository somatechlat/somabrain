from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple
import numpy as np


def _seed64(text: str) -> int:
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big")


@dataclass
class HRRConfig:
    dim: int = 8192
    seed: int = 42


class QuantumLayer:
    """Hyperdimensional ops (HRR) with deterministic seeding and FFT binding.

    - superpose: normalized sum
    - bind: circular convolution via FFT
    - unbind: circular correlation via FFT (inverse binding)
    - permute: fixed random permutation (seeded)
    - cleanup: nearest by cosine against anchor dictionary
    """

    def __init__(self, cfg: HRRConfig):
        self.cfg = cfg
        self._rng = np.random.default_rng(cfg.seed)
        self._perm = self._rng.permutation(cfg.dim)
        self._perm_inv = np.argsort(self._perm)
        # cache random base vectors for tokens if needed later
        self._token_cache: Dict[str, np.ndarray] = {}

    def random_vector(self) -> np.ndarray:
        v = self._rng.normal(0.0, 1.0, size=self.cfg.dim).astype("float32")
        n = np.linalg.norm(v)
        return v / max(1e-9, n)

    def encode_text(self, text: str) -> np.ndarray:
        # Deterministic encoding: seeded RNG based on text
        rng = np.random.default_rng(_seed64(text) ^ self.cfg.seed)
        v = rng.normal(0.0, 1.0, size=self.cfg.dim).astype("float32")
        n = np.linalg.norm(v)
        return v / max(1e-9, n)

    def superpose(self, *vectors: Iterable[np.ndarray]) -> np.ndarray:
        s = None
        for v in vectors:
            for x in v if isinstance(v, (list, tuple)) else [v]:
                s = x if s is None else (s + x)
        if s is None:
            return np.zeros((self.cfg.dim,), dtype="float32")
        n = np.linalg.norm(s)
        return s / max(1e-9, n)

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        prod = fa * fb
        conv = np.fft.irfft(prod, n=len(a)).astype("float32")
        n = np.linalg.norm(conv)
        return conv / max(1e-9, n)

    def unbind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        # correlation uses conjugate of one factor
        prod = fa * np.conjugate(fb)
        corr = np.fft.irfft(prod, n=len(a)).astype("float32")
        n = np.linalg.norm(corr)
        return corr / max(1e-9, n)

    def permute(self, a: np.ndarray, times: int = 1) -> np.ndarray:
        if times >= 0:
            idx = self._perm
            for _ in range(times):
                a = a[idx]
            return a
        # negative times means inverse
        idx = self._perm_inv
        for _ in range(-times):
            a = a[idx]
        return a

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 0 or nb <= 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def cleanup(self, q: np.ndarray, anchors: Dict[str, np.ndarray]) -> Tuple[str, float]:
        best_id = ""
        best = -1.0
        for k, v in anchors.items():
            s = self.cosine(q, v)
            if s > best:
                best = s
                best_id = k
        return best_id, max(0.0, best)

