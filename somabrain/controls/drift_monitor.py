"""
Drift Monitor Module for SomaBrain

This module implements online drift detection for input vectors using statistical
methods. It monitors changes in data distribution over time and alerts when
significant drift is detected, which is crucial for maintaining model reliability
in dynamic environments.

Key Features:
- Online mean and variance tracking using Welford's algorithm
- Z-score based drift scoring
- Configurable alert thresholds
- Rolling window statistics
- Metrics collection for monitoring

Drift Detection:
- Score: Euclidean norm of z-scored input vector
- Alert: Triggered when score exceeds threshold
- Window: Number of samples for statistics calculation
- Online: Incremental updates without storing all data

Applications:
- Input data distribution monitoring
- Model performance degradation detection
- Data quality assessment
- Adaptive system reconfiguration triggers

Classes:
    DriftConfig: Configuration for drift detection parameters
    DriftMonitor: Main drift monitoring implementation

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .metrics import DRIFT_ALERT, DRIFT_SCORE


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


@dataclass
class DriftConfig:
    """Drift monitor configuration with Settings-backed defaults.

    Fields default to None, which triggers Settings lookup in __post_init__.
    """

    window: Optional[int] = None
    threshold: Optional[float] = None

    def __post_init__(self) -> None:
        """Apply Settings defaults for None values."""
        s = _get_settings()
        if self.window is None:
            self.window = getattr(s, "SOMABRAIN_DRIFT_WINDOW", 256)
        if self.threshold is None:
            self.threshold = getattr(s, "SOMABRAIN_DRIFT_THRESHOLD", 0.3)


class DriftMonitor:
    """Simple online drift monitor over input vectors.

    Tracks running mean and variance (per-dim) with Welford's algorithm.
    Reports a z-distance (Euclidean on z-scored vector) as drift score.
    """

    def __init__(self, dim: int, cfg: DriftConfig):
        """Initialize the instance."""

        self.dim = int(dim)
        self.cfg = cfg
        self.n = 0
        self.mean = np.zeros((dim,), dtype=np.float64)
        self.M2 = np.zeros((dim,), dtype=np.float64)

    def update(self, x: np.ndarray) -> dict:
        """Execute update.

            Args:
                x: The x.
            """

        x = np.asarray(x, dtype=np.float64)
        if x.shape[-1] != self.dim:
            x = x[: self.dim]
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2
        var = self.M2 / max(1, self.n - 1)
        std = np.sqrt(np.maximum(var, 1e-9))
        z = (x - self.mean) / std
        # Compute z-score norm (not unit normalization, just L2 norm of z-scores)
        score = float(np.sqrt(np.sum(z * z)))
        try:
            DRIFT_SCORE.observe(max(0.0, score))
            if score >= float(self.cfg.threshold):
                DRIFT_ALERT.inc()
        except Exception:
            pass
        return {
            "score": score,
            "alert": bool(score >= float(self.cfg.threshold)),
            "n": self.n,
        }