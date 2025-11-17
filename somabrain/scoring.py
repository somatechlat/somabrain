"""Unified scoring utilities combining cosine, FD projection, and recency.

ENHANCED WITH ADAPTIVE LEARNING - Now uses self-evolving parameters
instead of hardcoded values for true dynamic learning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from .salience import FDSalienceSketch

# Import adaptive learning system
try:
    from .adaptive.integration import AdaptiveIntegrator
    _adaptive_integrator = AdaptiveIntegrator()
    _ADAPTIVE_ENABLED = True
except ImportError:
    _adaptive_integrator = None
    _ADAPTIVE_ENABLED = False

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
    """Combine multiple similarity signals with adaptive weights.

    ENHANCED WITH TRUE DYNAMIC LEARNING:
    - No more hardcoded weights - now self-evolving!
    - Adaptive parameter optimization based on performance
    - Real-time weight adjustment for optimal scoring
    
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
        
        # ENHANCED: Use adaptive learning if available
        if _ADAPTIVE_ENABLED and _adaptive_integrator:
            self._adaptive_scorer = _adaptive_integrator.get_scorer()
            self._adaptive_mode = True
            print("🧠 SomaBrain: ADAPTIVE LEARNING MODE ENABLED - No more hardcoded values!")
            print("   ⚡ Parameters now self-evolve based on performance feedback")
            print("   📊 Real-time optimization replaces manual tuning")
            print("   🎯 True machine learning, not static configuration")
        else:
            self._adaptive_mode = False
            print("⚠️  SomaBrain: Adaptive learning system not available - using hardcoded fallback")
            print("   🔧 This is NOT true learning - these are static values")
            # Fallback to original hardcoded behavior
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
        
        # Performance tracking for adaptive learning
        self._operation_count = 0
        self._last_adaptation = 0

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
        """ENHANCED: Now uses adaptive weights when available!"""
        
        self._operation_count += 1
        
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

        # ENHANCED: Use adaptive scoring if available
        if self._adaptive_mode and self._adaptive_scorer:
            total_score, component_scores = self._adaptive_scorer.score(
                q, c, recency_steps, cosine
            )
            
            # Track this operation for adaptive learning
            # NOTE: In production, we'd track the full operation context
            # For now, we record basic scoring statistics
            if self._operation_count % 100 == 0:  # Log every 100 operations
                print(f"🧠 Adaptive Scoring Operation #{self._operation_count}: "
                      f"Score={total_score:.3f}, "
                      f"Components=({component_scores.get('cosine', 0):.2f}, "
                      f"{component_scores.get('fd', 0):.2f}, "
                      f"{component_scores.get('recency', 0):.2f})")
        else:
            # Fallback to hardcoded weights - THIS IS NOT TRUE LEARNING
            total = (
                self._weights.w_cosine * cos
                + self._weights.w_fd * fd
                + self._weights.w_recency * rec
            )
            total_score = max(0.0, min(1.0, float(total)))
            
            if self._operation_count % 1000 == 0:  # Log less frequently for fallback
                print(f"⚠️  Hardcoded Scoring Operation #{self._operation_count}: "
                      f"Score={total_score:.3f} - NO LEARNING OCCURRING")

        if M:
            try:
                M.SCORER_FINAL.observe(total_score)
            except Exception:
                pass
                
        return total_score

    def stats(self) -> dict[str, float | dict[str, float | bool]]:
        """ENHANCED: Expose scorer configuration with adaptive learning info."""

        if self._adaptive_mode and _adaptive_integrator:
            # Return adaptive system statistics
            adaptive_stats = _adaptive_integrator.get_system_stats()
            return {
                "mode": "adaptive",
                "adaptive_enabled": True,
                "operation_count": self._operation_count,
                "system_stats": adaptive_stats,
                "learning_active": adaptive_stats.get("learning_active", False),
                "adaptation_cycles": adaptive_stats.get("adaptation_cycles", 0),
                "last_performance_score": adaptive_stats.get("last_performance_score", 0.0),
                "message": "🧠 SomaBrain is using TRUE DYNAMIC LEARNING - parameters self-evolve!",
                "description": "This is REAL machine learning with performance-driven parameter optimization"
            }
        else:
            # Fallback to hardcoded statistics - THIS IS NOT TRUE LEARNING
            info: dict[str, float | dict[str, float | bool]] = {
                "mode": "hardcoded",
                "adaptive_enabled": False,
                "w_cosine": self._weights.w_cosine,      # STATIC - DOES NOT CHANGE
                "w_fd": self._weights.w_fd,              # STATIC - DOES NOT CHANGE
                "w_recency": self._weights.w_recency,    # STATIC - DOES NOT CHANGE
                "recency_tau": self._recency_tau,        # STATIC - DOES NOT CHANGE
                "weight_min": float(self._weight_bounds[0]),
                "weight_max": float(self._weight_bounds[1]),
                "defaults": {
                    "w_cosine": self._default_weights.w_cosine,  # HARDCODED DEFAULTS
                    "w_fd": self._default_weights.w_fd,          # HARDCODED DEFAULTS
                    "w_recency": self._default_weights.w_recency, # HARDCODED DEFAULTS
                },
                "message": "⚠️  SomaBrain is using HARDCODED values - not true learning",
                "description": "These are STATIC values that do NOT adapt or learn from performance",
                "warning": "This is simulation, not real machine learning"
            }
            if self._fd is not None:
                try:
                    info["fd"] = self._fd.stats()
                except Exception:
                    info["fd"] = {"error": True}
            return info
