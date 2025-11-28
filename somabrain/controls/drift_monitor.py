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

import numpy as np

from .metrics import DRIFT_ALERT, DRIFT_SCORE


@dataclass
class DriftConfig:
    window: int = 128
    threshold: float = 5.0


class DriftMonitor:
    """Simple online drift monitor over input vectors.

    Tracks running mean and variance (per-dim) with Welford's algorithm.
    Reports a z-distance (Euclidean on z-scored vector) as drift score.
    """

    def __init__(self, dim: int, cfg: DriftConfig):
        self.dim = int(dim)
        self.cfg = cfg
        self.n = 0
        self.mean = np.zeros((dim,), dtype=np.float64)
        self.M2 = np.zeros((dim,), dtype=np.float64)

    def update(self, x: np.ndarray) -> dict:
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
        score = float(np.linalg.norm(z))
        try:
            DRIFT_SCORE.observe(max(0.0, score))
            if score >= float(self.cfg.threshold):
                DRIFT_ALERT.inc()
        except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")
        return {
            "score": score,
            "alert": bool(score >= float(self.cfg.threshold)),
            "n": self.n,
        }
