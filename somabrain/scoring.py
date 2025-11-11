"""Unified scoring utilities combining cosine, FD projection, and recency."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .salience import FDSalienceSketch

_EPS = 1e-12

try:  # optional shared settings
    from common.config.settings import settings as shared_settings  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    shared_settings = None  # type: ignore

try:  # metrics are optional during lightweight imports
    from . import metrics as M
except Exception:  # pragma: no cover - metrics optional
    M = None  # type: ignore


@dataclass
class ScorerWeights:
    w_cosine: float
    w_fd: float
    w_recency: float


def _gain_setting(name: str) -> float:
    """Fetch a float setting from shared settings or environment.

    In strict mode the setting **must** be defined; otherwise a ``RuntimeError``
    is raised so that mis‑configuration is caught early.
    """

    if shared_settings is not None:
        try:
            value = getattr(shared_settings, f"scorer_{name}")
            if value is not None:
                return float(value)
        except Exception as exc:
            raise RuntimeError(f"Scorer setting '{name}' missing or invalid: {exc}") from exc
    env_name = f"SOMABRAIN_SCORER_{name.upper()}"
    env_val = os.getenv(env_name)
    if env_val is not None:
        try:
            return float(env_val)
        except Exception as exc:
            raise RuntimeError(f"Scorer env var '{env_name}' invalid: {exc}") from exc
    raise RuntimeError(f"Scorer setting '{name}' not configured")


class UnifiedScorer:
    """Combine multiple similarity signals with bounded weights.

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
        self._default_weights = ScorerWeights(
            w_cosine=w_cosine,
            w_fd=w_fd,
            w_recency=w_recency,
        )
        # In strict mode, use env settings if available, otherwise use constructor params
        try:
            cosine_val = _gain_setting("w_cosine")
        except RuntimeError:
            cosine_val = w_cosine
        try:
            fd_val = _gain_setting("w_fd")
        except RuntimeError:
            fd_val = w_fd
        try:
            recency_val = _gain_setting("w_recency")
        except RuntimeError:
            recency_val = w_recency
        try:
            tau_val = _gain_setting("recency_tau")
        except RuntimeError:
            tau_val = recency_tau
            
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
                try:
                    M.SCORER_WEIGHT_CLAMPED.labels(
                        component=component, bound="min"
                    ).inc()
                except Exception:
                    pass
            return lo
        if v > hi:
            if M:
                try:
                    M.SCORER_WEIGHT_CLAMPED.labels(
                        component=component, bound="max"
                    ).inc()
                except Exception:
                    pass
            return hi
        return v

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= _EPS or nb <= _EPS:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _fd_component(self, query: np.ndarray, candidate: np.ndarray) -> float:
        if self._fd is None:
            return 0.0
        try:
            q_proj = self._fd.project(query)
            c_proj = self._fd.project(candidate)
        except Exception:
            return 0.0
        nq = float(np.linalg.norm(q_proj))
        nc = float(np.linalg.norm(c_proj))
        if nq <= _EPS or nc <= _EPS:
            return 0.0
        return float(np.dot(q_proj, c_proj) / (nq * nc))

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
            try:
                M.SCORER_COMPONENT.labels(component="cosine").observe(cos)
                M.SCORER_COMPONENT.labels(component="fd").observe(fd)
                M.SCORER_COMPONENT.labels(component="recency").observe(rec)
            except Exception:
                pass

        total = (
            self._weights.w_cosine * cos
            + self._weights.w_fd * fd
            + self._weights.w_recency * rec
        )
        total = max(0.0, min(1.0, float(total)))

        if M:
            try:
                M.SCORER_FINAL.observe(total)
            except Exception:
                pass
        return total

    def stats(self) -> dict[str, float | dict[str, float | bool]]:
        """Expose scorer configuration and FD health for diagnostics."""

        info: dict[str, float | dict[str, float | bool]] = {
            "w_cosine": self._weights.w_cosine,
            "w_fd": self._weights.w_fd,
            "w_recency": self._weights.w_recency,
            "recency_tau": self._recency_tau,
            "weight_min": float(self._weight_bounds[0]),
            "weight_max": float(self._weight_bounds[1]),
            "defaults": {
                "w_cosine": self._default_weights.w_cosine,
                "w_fd": self._default_weights.w_fd,
                "w_recency": self._default_weights.w_recency,
            },
        }
        if self._fd is not None:
            try:
                info["fd"] = self._fd.stats()
            except Exception:
                info["fd"] = {"error": True}
        return info
