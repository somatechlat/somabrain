"""Unified scoring utilities combining cosine, FD projection, and recency."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from somabrain.math.recency import stretched_exponential_recency

from .math import cosine_similarity
from .salience import FDSalienceSketch

_EPS = 1e-12

try:
    from . import metrics as M
except Exception:
    M = None


@dataclass
class ScorerWeights:
    """Scorerweights class implementation."""

    w_cosine: float
    w_fd: float
    w_recency: float


class UnifiedScorer:
    """Combine multiple similarity signals.

    Components:
    - Cosine similarity in the base space
    - FD subspace cosine (projection via Frequent-Directions sketch)
    - Recency boost via the canonical stretched-exponential kernel

    Weights come from the constructor arguments (the factory reads settings and
    passes them in). This class never re-reads settings.
    """

    def __init__(
        self,
        *,
        w_cosine: float,
        w_fd: float,
        w_recency: float,
        weight_min: float,
        weight_max: float,
        recency_scale: float,
        recency_sharpness: float = 1.2,
        recency_floor: float = 0.05,
        fd_backend: FDSalienceSketch | None = None,
    ) -> None:
        """Initialize the instance."""

        lo, hi = sorted((float(weight_min), float(weight_max)))
        self._weights = ScorerWeights(
            w_cosine=self._clamp("cosine", w_cosine, lo, hi),
            w_fd=self._clamp("fd", w_fd, lo, hi),
            w_recency=self._clamp("recency", w_recency, lo, hi),
        )
        self._recency_scale = max(float(recency_scale), _EPS)
        self._recency_sharpness = float(recency_sharpness)
        self._recency_floor = float(recency_floor)
        self._fd = fd_backend
        self._weight_bounds = (lo, hi)

    def _clamp(self, component: str, value: float, lo: float, hi: float) -> float:
        """Execute clamp.

        Args:
            component: The component.
            value: The value.
            lo: The lo.
            hi: The hi.
        """

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
        """Execute fd component.

        Args:
            query: The query.
            candidate: The candidate.
        """

        if self._fd is None:
            return 0.0
        q_proj = self._fd.project(query)
        c_proj = self._fd.project(candidate)
        # Use canonical cosine_similarity for FD-projected vectors
        return cosine_similarity(q_proj, c_proj)

    def _recency_component(self, age_seconds: float | None) -> float:
        """Canonical stretched-exponential recency for an admission age."""

        if age_seconds is None:
            return 0.0
        return stretched_exponential_recency(
            float(age_seconds),
            scale=self._recency_scale,
            sharpness=self._recency_sharpness,
            floor=self._recency_floor,
        )

    def score(
        self,
        query: np.ndarray,
        candidate: np.ndarray,
        *,
        age_seconds: float | None = None,
        cosine: float | None = None,
    ) -> float:
        """Score a candidate. Max achievable score is 1.0.

        Args:
            query: The query.
            candidate: The candidate.
            age_seconds: Admission age in seconds, or None when unknown.
            cosine: Optional precomputed cosine in [-1, 1].
        """

        q = np.asarray(query, dtype=float).reshape(-1)
        c = np.asarray(candidate, dtype=float).reshape(-1)
        cos = float(cosine) if cosine is not None else self._cosine(q, c)
        fd = self._fd_component(q, c)
        rec = self._recency_component(age_seconds)

        if M:
            M.SCORER_COMPONENT.labels(component="cosine").observe(cos)
            M.SCORER_COMPONENT.labels(component="fd").observe(fd)
            M.SCORER_COMPONENT.labels(component="recency").observe(rec)

        # Renormalise over active components so the ceiling is always 1.0.
        terms: list[tuple[float, float]] = [(self._weights.w_cosine, cos)]
        if self._fd is not None:
            terms.append((self._weights.w_fd, fd))
        if age_seconds is not None:
            terms.append((self._weights.w_recency, rec))
        active_weight = sum(w for w, _ in terms)
        if active_weight <= _EPS:
            total_score = 0.0
        else:
            total = sum(w * v for w, v in terms) / active_weight
            total_score = max(0.0, min(1.0, float(total)))

        if M:
            M.SCORER_FINAL.observe(total_score)

        return total_score

    def stats(self) -> dict[str, float | dict[str, float | bool]]:
        """Execute stats."""

        info: dict[str, float | dict[str, float | bool]] = {
            "w_cosine": self._weights.w_cosine,
            "w_fd": self._weights.w_fd,
            "w_recency": self._weights.w_recency,
            "recency_scale": self._recency_scale,
            "recency_sharpness": self._recency_sharpness,
            "recency_floor": self._recency_floor,
            "weight_min": float(self._weight_bounds[0]),
            "weight_max": float(self._weight_bounds[1]),
        }
        if self._fd is not None:
            info["fd"] = self._fd.stats()
        return info
