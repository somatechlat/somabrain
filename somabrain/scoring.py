"""Unified scoring utilities combining cosine, FD projection, and recency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .math import cosine_similarity
from .salience import FDSalienceSketch

_EPS = 1e-12

# Import settings at the top to avoid E402 import order violations.
from django.conf import settings

try:
    from . import metrics as M
except Exception:
    M = None


@dataclass
class ScorerWeights:
    w_cosine: float
    w_fd: float
    w_recency: float


def _gain_setting(name: str) -> float:
    """Fetch required float setting from shared settings or environment."""
    env_name = f"SOMABRAIN_SCORER_{name.upper()}"
    value = getattr(settings, env_name, None)
    if value is not None:
        return float(value)
    raise RuntimeError(f"Required scorer setting '{env_name}' not configured")


class UnifiedScorer:
    """Combine multiple similarity signals.

    Components:
    - Cosine similarity in the base space
    - FD subspace cosine (projection via Frequent-Directions sketch)
    - Recency boost based on admission age (exponential decay)
    """

    def __init__(
        self,
        *,
        w_cosine: float,
        w_fd: float,
        w_recency: float,
        weight_min: float,
        weight_max: float,
        recency_tau: float,
        fd_backend: Optional[FDSalienceSketch] = None,
    ) -> None:
        lo, hi = sorted((float(weight_min), float(weight_max)))
        cosine_val = _gain_setting("w_cosine")
        fd_val = _gain_setting("w_fd")
        recency_val = _gain_setting("w_recency")
        tau_val = _gain_setting("recency_tau")

        self._weights = ScorerWeights(
            w_cosine=self._clamp("cosine", cosine_val, lo, hi),
            w_fd=self._clamp("fd", fd_val, lo, hi),
            w_recency=self._clamp("recency", recency_val, lo, hi),
        )
        self._recency_tau = max(tau_val, _EPS)
        self._fd = fd_backend
        self._weight_bounds = (lo, hi)

    def _clamp(self, component: str, value: float, lo: float, hi: float) -> float:
        v = float(value)
        if v < lo:
            if M:
                M.SCORER_WEIGHT_CLAMPED.labels(component=component, bound="min").inc()
            return lo
        if v > hi:
            if M:
                M.SCORER_WEIGHT_CLAMPED.labels(component=component, bound="max").inc()
            return hi
        return v

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        """Delegate to canonical cosine_similarity implementation."""
        return cosine_similarity(a, b)

    def _fd_component(self, query: np.ndarray, candidate: np.ndarray) -> float:
        if self._fd is None:
            return 0.0
        q_proj = self._fd.project(query)
        c_proj = self._fd.project(candidate)
        # Use canonical cosine_similarity for FD-projected vectors
        return cosine_similarity(q_proj, c_proj)

    def _recency_component(self, recency_steps: Optional[int]) -> float:
        if recency_steps is None:
            return 0.0
        age = max(0.0, float(recency_steps))
        tau = max(self._recency_tau, _EPS)
        val = float(np.exp(-age / tau))
        return max(0.0, min(1.0, val))

    def score(
        self,
        query: np.ndarray,
        candidate: np.ndarray,
        *,
        recency_steps: Optional[int] = None,
        cosine: Optional[float] = None,
    ) -> float:
        q = np.asarray(query, dtype=float).reshape(-1)
        c = np.asarray(candidate, dtype=float).reshape(-1)
        cos = float(cosine) if cosine is not None else self._cosine(q, c)
        fd = self._fd_component(q, c)
        rec = self._recency_component(recency_steps)

        if M:
            M.SCORER_COMPONENT.labels(component="cosine").observe(cos)
            M.SCORER_COMPONENT.labels(component="fd").observe(fd)
            M.SCORER_COMPONENT.labels(component="recency").observe(rec)

        total = (
            self._weights.w_cosine * cos
            + self._weights.w_fd * fd
            + self._weights.w_recency * rec
        )
        total_score = max(0.0, min(1.0, float(total)))

        if M:
            M.SCORER_FINAL.observe(total_score)

        return total_score

    def stats(self) -> dict[str, float | dict[str, float | bool]]:
        info: dict[str, float | dict[str, float | bool]] = {
            "w_cosine": self._weights.w_cosine,
            "w_fd": self._weights.w_fd,
            "w_recency": self._weights.w_recency,
            "recency_tau": self._recency_tau,
            "weight_min": float(self._weight_bounds[0]),
            "weight_max": float(self._weight_bounds[1]),
        }
        if self._fd is not None:
            info["fd"] = self._fd.stats()
        return info
