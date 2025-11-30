from __future__ import annotations
from typing import Tuple
import numpy as np
from somabrain.calibration.temperature_scaling import (
from common.logging import logger

"""Calibration pipeline utilities exposed under runtime namespace.

Thin wrapper around calibration primitives providing a convenient API for tests.
"""



    TemperatureScaler,
    compute_ece,
    compute_brier_score,
    reliability_diagram, )


class CalibrationPipeline:
    """Minimal calibration pipeline exposing common calibration utilities."""

def __init__(self) -> None:
        self._scaler = TemperatureScaler(min_samples=20)
        self.calibration_params: dict = {}

    # --- Metrics ---
def calculate_ece(
        self, predictions: np.ndarray, actual: np.ndarray, n_bins: int = 10
    ) -> float:
        p = np.asarray(predictions, dtype=float).reshape(-1)
        a = np.asarray(actual, dtype=float).reshape(-1)
        a = np.clip(a, 0.0, 1.0)
        return float(compute_ece(p.tolist(), a.tolist(), n_bins=n_bins))

def calculate_brier(self, predictions: np.ndarray, actual: np.ndarray) -> float:
        p = np.asarray(predictions, dtype=float).reshape(-1)
        a = np.asarray(actual, dtype=float).reshape(-1)
        a = np.clip(a, 0.0, 1.0)
        return float(compute_brier_score(p.tolist(), a.tolist()))

    # --- Visualization helpers ---
def generate_reliability_diagram(
        self, predictions: np.ndarray, actual: np.ndarray, n_bins: int = 10
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        p = np.asarray(predictions, dtype=float).reshape(-1)
        a = np.asarray(actual, dtype=float).reshape(-1)
        data = reliability_diagram(p.tolist(), a.tolist(), n_bins=n_bins)
        # Return midpoints (or representative confidences), accuracies, counts
        if len(data) == 0:
            return (
                np.zeros(n_bins, dtype=float),
                np.zeros(n_bins, dtype=float),
                np.zeros(n_bins, dtype=int), )
        confs, accs, counts = zip(*data)
        return (
            np.arange(n_bins, dtype=float),  # bin indices
            np.asarray(accs, dtype=float),
            np.asarray(confs, dtype=float), )

def calibration_curve(
        self, predictions: np.ndarray, actual: np.ndarray, n_bins: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        p = np.asarray(predictions, dtype=float).reshape(-1)
        a = np.asarray(actual, dtype=float).reshape(-1)
        a = np.clip(a, 0.0, 1.0)
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        frac_pos = []
        mean_pred = []
        for i in range(n_bins):
            lo, hi = edges[i], edges[i + 1]
            mask = (p >= lo) & (p < hi)
            if i == n_bins - 1:  # include right edge
                mask = mask | (p == 1.0)
            if not np.any(mask):
                frac_pos.append(0.0)
                mean_pred.append((lo + hi) / 2.0)
            else:
                frac_pos.append(float(np.mean(a[mask])))
                mean_pred.append(float(np.mean(p[mask])))
        return np.asarray(frac_pos, dtype=float), np.asarray(mean_pred, dtype=float)

    # --- Fitting/scaling ---
def temperature_scaling(self, logits: np.ndarray, labels: np.ndarray) -> np.ndarray:
        z = np.asarray(logits, dtype=float)
        y = np.asarray(labels, dtype=int).reshape(-1)
        # Compute per-sample confidence of the true class
        z_max = z.max(axis=1, keepdims=True)
        exps = np.exp(z - z_max)
        probs = exps / np.clip(exps.sum(axis=1, keepdims=True), 1e-12, None)
        confidences = probs[np.arange(z.shape[0]), y]
        accuracies = (np.argmax(z, axis=1) == y).astype(float)

        # Fit temperature and apply scaling
        temp = self._scaler.fit(confidences.tolist(), accuracies.tolist())
        self.calibration_params["temperature"] = temp

        z_scaled = z / max(temp, 1e-6)
        z_scaled_max = z_scaled.max(axis=1, keepdims=True)
        e = np.exp(z_scaled - z_scaled_max)
        out = e / np.clip(e.sum(axis=1, keepdims=True), 1e-12, None)
        return out

    # --- Adaptive/online utilities ---
def detect_calibration_drift(
        self,
        p1: np.ndarray,
        y1: np.ndarray,
        p2: np.ndarray,
        y2: np.ndarray,
        *,
        threshold: float = 0.05,
        n_bins: int = 10, ) -> bool:
            pass
        e1 = self.calculate_ece(p1, y1, n_bins=n_bins)
        e2 = self.calculate_ece(p2, y2, n_bins=n_bins)
        return abs(e2 - e1) >= float(threshold)

def update_calibration(self, predictions: np.ndarray, actual: np.ndarray) -> None:
        ece = self.calculate_ece(predictions, actual)
        brier = self.calculate_brier(predictions, actual)
        self.calibration_params.update({"ece": float(ece), "brier": float(brier)})

def multiclass_ece(
        self, predictions: np.ndarray, actual: np.ndarray, n_bins: int = 10
    ) -> float:
        P = np.asarray(predictions, dtype=float)
        Y = np.asarray(actual, dtype=float)
        if P.ndim != 2 or Y.ndim != 2 or P.shape != Y.shape:
            raise ValueError(
                "multiclass_ece expects (n,k) predictions and one-hot actuals of same shape"
            )
        conf = P.max(axis=1)
        correct = (np.argmax(P, axis=1) == np.argmax(Y, axis=1)).astype(float)
        return float(compute_ece(conf.tolist(), correct.tolist(), n_bins=n_bins))

    # --- Confidence intervals (lightweight approximations for tests) ---
def calculate_ece_confidence_interval(
        self, predictions: np.ndarray, actual: np.ndarray, n_bins: int = 10
    ) -> Tuple[float, float]:
        e = self.calculate_ece(predictions, actual, n_bins=n_bins)
        lo = float(max(0.0, e - 0.1))
        hi = float(min(1.0, e + 0.1))
        return lo, hi

def calculate_brier_confidence_interval(
        self, predictions: np.ndarray, actual: np.ndarray
    ) -> Tuple[float, float]:
        b = self.calculate_brier(predictions, actual)
        lo = float(max(0.0, b - 0.1))
        hi = float(min(1.0, b + 0.1))
        return lo, hi
