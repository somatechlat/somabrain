"""Pure HRR reference implementation (test-only).

This module provides a mathematically-pure HRR layer suitable for
verification, regression testing, and offline experiments. It follows the
canonical HRR algebra: bind = FFT(a) * FFT(b), unbind = FFT(c) / FFT(b) with
no ad-hoc regularizers. The pure unbind raises an explicit ZeroDivisionError
when any frequency component of the divisor is exactly zero.

Intended usage:
- Import `PureQuantumLayer` in tests or benchmarking scripts and compare
  results with the production `QuantumLayer` implemented in
  `somabrain.quantum`.

Notes:
- This module is test-only. Do NOT use `PureQuantumLayer` in production
  services because exact division is brittle under finite-precision arithmetic.
- Intermediates are computed in complex128 to reduce transient rounding error
  before casting results back to the configured runtime dtype.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from somabrain.numerics import normalize_array
from somabrain.quantum import HRRConfig, _seed64


class PureQuantumLayer:
    """A minimal, pure HRR implementation for verification.

    Behavioural contract:
    - bind(a,b) uses exact FFT-based circular convolution.
    - unbind(c,b) performs exact frequency-domain division and raises
      ZeroDivisionError if any divisor frequency is exactly zero.
    - All outputs are normalized via the canonical `normalize_array` helper.
    - Deterministic encoding mirrors `QuantumLayer.encode_text` semantics.
    """

    def __init__(self, cfg: HRRConfig):
        self.cfg = cfg
        # Use deterministic RNG for operations that need randomness
        self._rng = np.random.default_rng(cfg.seed)
        self._perm_seed = cfg.seed
        self._perm = self._rng.permutation(cfg.dim)
        self._perm_inv = np.argsort(self._perm)
        self._token_cache: Dict[str, np.ndarray] = {}

    def _ensure_vector(self, v: object, name: str = "vector") -> np.ndarray:
        if isinstance(v, np.ndarray):
            arr = v
        else:
            try:
                arr = np.asarray(v, dtype=self.cfg.dtype)
            except Exception as e:
                raise ValueError(f"{name}: cannot convert to ndarray: {e}")
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        if arr.shape[0] != self.cfg.dim:
            raise ValueError(f"{name} must be length {self.cfg.dim}")
        if arr.dtype != np.dtype(self.cfg.dtype):
            arr = arr.astype(self.cfg.dtype)
        return arr

    def _renorm(self, v: np.ndarray) -> np.ndarray:
        if not self.cfg.renorm:
            return v.astype(self.cfg.dtype, copy=False)
        return normalize_array(v, axis=self.cfg.dim, dtype=self.cfg.dtype)

    def random_vector(self) -> np.ndarray:
        v = self._rng.normal(0.0, 1.0, size=self.cfg.dim)
        return self._renorm(v)

    def encode_text(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(_seed64(text) ^ self.cfg.seed)
        v = rng.normal(0.0, 1.0, size=self.cfg.dim)
        return self._renorm(v)

    def superpose(self, *vectors) -> np.ndarray:
        s = None
        for v in vectors:
            if isinstance(v, (list, tuple)):
                for x in v:
                    xv = self._ensure_vector(x, name="superpose_item")
                    s = xv if s is None else s + xv
            else:
                xv = self._ensure_vector(v, name="superpose_item")
                s = xv if s is None else s + xv
        if s is None:
            return np.zeros((self.cfg.dim,), dtype=self.cfg.dtype)
        return self._renorm(s)

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a = self._ensure_vector(a, name="bind.a")
        b = self._ensure_vector(b, name="bind.b")
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        prod = (fa * fb).astype(np.complex128)
        conv = np.fft.irfft(prod, n=self.cfg.dim)
        return self._renorm(conv)

    def unbind(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        c = self._ensure_vector(c, name="unbind.c")
        b = self._ensure_vector(b, name="unbind.b")
        fc = np.fft.rfft(c).astype(np.complex128)
        fb = np.fft.rfft(b).astype(np.complex128)

        # Check for exact zeros in fb — pure algebra cannot divide by zero
        zero_mask = np.isclose(fb, 0 + 0j, atol=0.0)
        if np.any(zero_mask):
            # Provide diagnostic detail: indices of zeros
            idxs = np.nonzero(zero_mask)[0].tolist()
            raise ZeroDivisionError(
                f"Pure unbind: zero frequency components at indices {idxs}"
            )

        fa_est = fc / fb
        a_est = np.fft.irfft(fa_est, n=self.cfg.dim)
        return self._renorm(a_est)

    def permute(self, a: np.ndarray, times: int = 1) -> np.ndarray:
        a = self._ensure_vector(a, name="permute.a")
        if times >= 0:
            idx = self._perm
            for _ in range(times):
                a = a[idx]
            return a
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

    def cleanup(
        self, q: np.ndarray, anchors: Dict[str, np.ndarray]
    ) -> Tuple[str, float]:
        q = self._ensure_vector(q, name="cleanup.query")
        best_id = ""
        best = -1.0
        for k, v in anchors.items():
            try:
                vv = self._ensure_vector(v, name=f"cleanup.anchor[{k}]")
            except ValueError:
                continue
            s = self.cosine(q, vv)
            if s > best:
                best = s
                best_id = k
        return best_id, max(0.0, best)
