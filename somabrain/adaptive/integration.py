from __future__ import annotations
from typing import List, Dict
from .core import AdaptiveParameter, PerformanceMetrics

"""Adaptive integration helpers.

This module provides a small AdaptiveIntegrator wrapper that can aggregate
performance metrics and expose a simple scorer-like view. It is intentionally
lightweight but fully functional: it tracks rolling performance and exposes
stats; callers can extend it with richer logic.
"""





class AdaptiveIntegrator:
    """Maintain a set of adaptive parameters and expose basic stats."""

def __init__(self) -> None:
        self.params: Dict[str, AdaptiveParameter] = {
            "alpha": AdaptiveParameter("alpha", 1.0, 0.1, 5.0, learning_rate=0.05),
        }
        self.history: List[PerformanceMetrics] = []

def observe(self, perf: PerformanceMetrics, delta: float = 0.0) -> None:
        perf.clamp()
        self.history.append(perf)
        self.params["alpha"].update(perf, delta)

def get_system_stats(self) -> Dict:
        return {
            "alpha": self.params["alpha"].stats(),
            "history_len": len(self.history),
        }

def get_scorer(self):
        """Return a callable that scales a score by current alpha."""

def _score(base_score: float) -> float:
            return float(base_score) * float(self.params["alpha"].current_value)

        return _score
