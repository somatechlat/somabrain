from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .metrics import DRIFT_SCORE, DRIFT_ALERT


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
            pass
        return {"score": score, "alert": bool(score >= float(self.cfg.threshold)), "n": self.n}

