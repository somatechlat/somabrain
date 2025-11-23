"""Adaptive core primitives for SomaBrain.

Provides a minimal but functional adaptive parameter and performance metrics
structure used by neuromodulators and any learning components that want
bounded, incremental updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Lightweight performance signal container.

    Attributes:
        success_rate: float in [0,1]
        error_rate: float in [0,1]
        latency: positive float (seconds)
        accuracy: float in [0,1]
    """

    success_rate: float = 0.0
    error_rate: float = 0.0
    latency: float = 1.0
    accuracy: float = 0.0

    def clamp(self) -> "PerformanceMetrics":
        self.success_rate = min(max(self.success_rate, 0.0), 1.0)
        self.error_rate = min(max(self.error_rate, 0.0), 1.0)
        self.latency = max(self.latency, 1e-6)
        self.accuracy = min(max(self.accuracy, 0.0), 1.0)
        return self


class AdaptiveParameter:
    """Bounded parameter with simple incremental updates."""

    def __init__(
        self,
        name: str,
        initial_value: float,
        min_value: float,
        max_value: float,
        learning_rate: float = 0.01,
    ) -> None:
        self.name = name
        self.min_value = float(min_value)
        self.max_value = float(max_value)
        self.learning_rate = float(learning_rate)
        self.current_value = float(initial_value)
        self._clamp()

    def _clamp(self) -> None:
        self.current_value = min(
            max(self.current_value, self.min_value), self.max_value
        )

    def update(self, perf: PerformanceMetrics, delta: float) -> float:
        """Apply an update scaled by learning_rate; returns new value."""
        perf.clamp()
        self.current_value += self.learning_rate * float(delta)
        self._clamp()
        return self.current_value

    def stats(self) -> dict:
        return {
            "name": self.name,
            "value": self.current_value,
            "min": self.min_value,
            "max": self.max_value,
            "lr": self.learning_rate,
        }


# NOTE: Historically the codebase referenced an ``AdaptiveCore`` class that
# provided a higher‑level interface to the adaptive subsystem.  The current
# implementation only defines ``AdaptiveParameter`` and ``PerformanceMetrics``.
# To maintain backward compatibility (e.g. ``debug_adaptive_system.py`` and
# ``demo_adaptive_transformation.py`` import ``AdaptiveCore``), we expose a thin
# wrapper that forwards to ``AdaptiveIntegrator``.  This keeps the public API
# stable without re‑implementing the full original functionality.


class AdaptiveCore:
    """Compatibility shim for the legacy ``AdaptiveCore`` API.

    The original ``AdaptiveCore`` coordinated multiple adaptive parameters and
    exposed ``observe``/``get_system_stats``/``get_scorer`` methods.  The new
    ``AdaptiveIntegrator`` already provides this behaviour, so ``AdaptiveCore``
    simply delegates to an internal ``AdaptiveIntegrator`` instance.
    """

    def __init__(self) -> None:
        # Lazy import to avoid circular dependencies.
        from .integration import AdaptiveIntegrator

        self._integrator = AdaptiveIntegrator()

    def observe(self, perf, delta: float = 0.0) -> None:  # pragma: no cover
        """Delegate to the underlying integrator's ``observe`` method."""
        self._integrator.observe(perf, delta)

    def get_system_stats(self) -> dict:  # pragma: no cover
        return self._integrator.get_system_stats()

    def get_scorer(self):  # pragma: no cover
        return self._integrator.get_scorer()
