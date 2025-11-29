"""Salience computation utilities and FD-backed sketching helpers.

Two pathways are exposed:

* FD sketching (new): maintains a low-rank Frequent-Directions sketch of the
  incoming working-memory vectors and exposes residual energy as an additional
  salience feature.

The FD sketch is designed to stay lightweight (rank ``r`` \u226a ``D``) while
still capturing \u226590% spectral energy, allowing downstream modules to boost
salience when a vector lies outside the dominant subspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from .math import FrequentDirections

EPS = 1e-12


@dataclass
class SalienceWeights:
    """Weights for dense salience components."""

    novelty: float = 0.6
    error: float = 0.4
    fd: float = 0.0


def compute_salience(novelty: float, error: float, w: SalienceWeights) -> float:
    """Dense salience combination clamped to [0, 1]."""

    s = (w.novelty * float(novelty)) + (w.error * float(error))
    return max(0.0, min(1.0, s))


class FDSalienceSketch:
    """Maintain an FD sketch and expose residual/capture energy metrics."""

    def __init__(
        self,
        dim: int,
        rank: int,
        decay: float = 1.0,
    ):
        if dim <= 0:
            raise ValueError("dim must be positive")
        if rank <= 0:
            raise ValueError("rank must be positive")
        self.dim = int(dim)
        self.rank = int(rank)
        self.decay = float(decay)
        if not (0.0 < self.decay <= 1.0):
            raise ValueError("decay must be in (0, 1]")

        self._fd = FrequentDirections(self.dim, self.rank)
        self._total_energy = 0.0
        self._captured_energy = 0.0
        self._basis: Optional[np.ndarray] = None
        self._alpha: Optional[np.ndarray] = None
        self._trace_norm_error: float = 0.0
        self._psd_ok: bool = True

    def observe(self, vector: np.ndarray) -> Tuple[float, float]:
        """Stream ``vector`` and return (residual_ratio, capture_ratio)."""

        v = np.asarray(vector, dtype=float).reshape(-1)
        if v.shape[0] != self.dim:
            raise ValueError(f"vector has dim {v.shape[0]} but expected {self.dim}")

        energy = float(np.dot(v, v))
        if energy <= EPS:
            self._apply_decay()
            return 0.0, self.capture_ratio

        residual_before = self._residual_energy(v)
        residual_ratio = max(0.0, min(1.0, residual_before / max(energy, EPS)))

        self._apply_decay()
        self._total_energy += energy
        self._fd.insert(v)
        self._refresh_low_rank()
        return residual_ratio, self.capture_ratio

    def _apply_decay(self) -> None:
        if self.decay >= 0.9999:
            return
        if self._fd.S.size:
            self._fd.S *= np.sqrt(self.decay)
        self._captured_energy *= self.decay
        self._total_energy *= self.decay

    def _residual_energy(self, vector: np.ndarray) -> float:
        if self._basis is None or self._alpha is None:
            return float(np.dot(vector, vector))
        if self._basis.size == 0:
            return float(np.dot(vector, vector))
        proj = self._basis.T @ vector
        captured = float(np.dot(proj, proj))
        total = float(np.dot(vector, vector))
        return max(0.0, total - captured)

    def _refresh_low_rank(self) -> None:
        if self._fd.S.size == 0:
            self._basis = None
            self._alpha = None
            self._captured_energy = 0.0
            self._trace_norm_error = 0.0
            self._psd_ok = True
            return
        try:
            _, s, Vt = np.linalg.svd(self._fd.S, full_matrices=False)
        except np.linalg.LinAlgError:
            self._basis = None
            self._alpha = None
            self._captured_energy = 0.0
            self._trace_norm_error = 0.0
            self._psd_ok = False
            return
        if s.size == 0:
            self._basis = None
            self._alpha = None
            self._captured_energy = 0.0
            self._trace_norm_error = 0.0
            self._psd_ok = True
            return

        r = min(self.rank, s.size)
        basis_raw = np.asarray(Vt[:r, :].T, dtype=float)
        alpha_raw = np.maximum(np.asarray(s[:r], dtype=float) ** 2, 0.0)
        captured = float(np.sum(alpha_raw))
        self._captured_energy = captured

        basis = np.zeros((self.dim, self.rank), dtype=float)
        basis[:, :r] = basis_raw
        alpha_norm = np.zeros(self.rank, dtype=float)
        if captured > EPS:
            alpha_norm[:r] = alpha_raw / captured
            trace_error = float(abs(np.sum(alpha_norm) - 1.0))
        else:
            trace_error = 0.0

        self._basis = basis
        self._alpha = alpha_norm
        self._trace_norm_error = trace_error
        self._psd_ok = bool(np.all(alpha_norm >= -1e-12))

    @property
    def capture_ratio(self) -> float:
        if self._total_energy <= EPS:
            return 1.0
        ratio = self._captured_energy / max(self._total_energy, EPS)
        return max(0.0, min(1.0, float(ratio)))

    def covariance(self) -> np.ndarray:
        """Return the FD covariance approximation built from the sketch."""

        if self._basis is None or self._alpha is None:
            return np.zeros((self.dim, self.dim), dtype=float)
        diag = np.diag(self._alpha)
        return self._basis @ diag @ self._basis.T

    def project(self, vector: np.ndarray) -> np.ndarray:
        """Project ``vector`` into the FD subspace via the low-rank factor."""

        v = np.asarray(vector, dtype=float).reshape(-1)
        if v.shape[0] != self.dim:
            raise ValueError(f"vector has dim {v.shape[0]} but expected {self.dim}")
        if self._basis is None or self._alpha is None:
            return np.zeros((self.rank,), dtype=float)
        coords = self._basis.T @ v
        weights = np.sqrt(np.maximum(self._alpha, 0.0))
        return weights * coords

    @property
    def total_energy(self) -> float:
        return float(self._total_energy)

    @property
    def captured_energy(self) -> float:
        return float(self._captured_energy)

    @property
    def trace_norm_error(self) -> float:
        return float(self._trace_norm_error)

    @property
    def psd_ok(self) -> bool:
        return bool(self._psd_ok)

    def stats(self) -> Dict[str, float | bool]:
        """Return a dict of sketch health stats for diagnostics."""

        return {
            "total_energy": self.total_energy,
            "captured_energy": self.captured_energy,
            "capture_ratio": self.capture_ratio,
            "trace_norm_error": self.trace_norm_error,
            "psd_ok": self.psd_ok,
        }
