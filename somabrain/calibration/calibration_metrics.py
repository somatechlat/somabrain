"""
Calibration metrics tracking for SomaBrain predictors.

Tracks calibration performance over time for each predictor domain.
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
import json

from .temperature_scaling import TemperatureScaler, compute_ece, compute_brier_score


@dataclass
class CalibrationEntry:
    """Single calibration observation."""

    timestamp: float
    confidence: float
    accuracy: float
    domain: str
    tenant: str


class CalibrationTracker:
    """
    Tracks calibration metrics for predictors across domains and tenants.

    Maintains rolling windows of calibration data and computes:
    - ECE (Expected Calibration Error)
    - Brier Score
    - Temperature scaling parameters
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.calibration_data: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )
        self.temperature_scalers: Dict[str, Dict[str, TemperatureScaler]] = defaultdict(
            lambda: defaultdict(lambda: TemperatureScaler())
        )
        self.lock = threading.RLock()

    def add_observation(
        self, domain: str, tenant: str, confidence: float, accuracy: float
    ) -> None:
        """
        Add a calibration observation.

        Args:
            domain: Predictor domain ('state', 'agent', 'action')
            tenant: Tenant identifier
            confidence: Predicted confidence (0-1)
            accuracy: Actual accuracy (0-1)
        """
        with self.lock:
            entry = CalibrationEntry(
                timestamp=time.time(),
                confidence=confidence,
                accuracy=accuracy,
                domain=domain,
                tenant=tenant,
            )
            key = f"{domain}:{tenant}"
            self.calibration_data[key]["confidences"].append(confidence)
            self.calibration_data[key]["accuracies"].append(accuracy)

    def get_calibration_metrics(self, domain: str, tenant: str) -> Dict[str, float]:
        """
        Get current calibration metrics for a domain and tenant.

        Returns:
            Dictionary with ECE, Brier score, and temperature
        """
        key = f"{domain}:{tenant}"

        with self.lock:
            if key not in self.calibration_data:
                return {"ece": 0.0, "brier": 0.0, "temperature": 1.0, "samples": 0}

            confidences = list(self.calibration_data[key]["confidences"])
            accuracies = list(self.calibration_data[key]["accuracies"])

            if len(confidences) < 10:
                return {
                    "ece": 0.0,
                    "brier": 0.0,
                    "temperature": 1.0,
                    "samples": len(confidences),
                }

            ece = compute_ece(confidences, accuracies)
            brier = compute_brier_score(confidences, accuracies)

            # Update temperature scaler
            scaler = self.temperature_scalers[domain][tenant]
            temperature = scaler.fit(confidences, accuracies)

            return {
                "ece": ece,
                "brier": brier,
                "temperature": temperature,
                "samples": len(confidences),
            }

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get calibration metrics for all domains and tenants."""
        with self.lock:
            result = {}
            for key in self.calibration_data.keys():
                domain, tenant = key.split(":", 1)
                result[key] = self.get_calibration_metrics(domain, tenant)
            return result

    # Persistence helpers -------------------------------------------------
    def persist(self, path: str) -> None:
        """Persist fitted temperature parameters and sample counts.

        Only lightweight scalar data are stored; raw observation windows are
        not persisted (to keep file small). This allows warm restarts with
        previously learned temperatures while new observations accumulate.
        """
        import json
        import os

        data: Dict[str, Dict[str, float]] = {}
        with self.lock:
            for key in self.calibration_data.keys():
                domain, tenant = key.split(":", 1)
                metrics = self.get_calibration_metrics(domain, tenant)
                scaler = self.temperature_scalers[domain][tenant]
                data[key] = {
                    "temperature": float(getattr(scaler, "temperature", 1.0)),
                    "is_fitted": bool(getattr(scaler, "is_fitted", False)),
                    "samples": int(metrics.get("samples", 0)),
                }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "calibration": data}, f, indent=2)
        except Exception:
            # Fail-open: persistence is best-effort
            pass

    def load(self, path: str) -> None:
        """Load persisted temperature parameters if available."""
        import json

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        calib = payload.get("calibration") or {}
        if not isinstance(calib, dict):
            return
        with self.lock:
            for key, meta in calib.items():
                if not isinstance(meta, dict) or ":" not in key:
                    continue
                domain, tenant = key.split(":", 1)
                scaler = self.temperature_scalers[domain][tenant]
                try:
                    temp = float(meta.get("temperature", scaler.temperature))
                    fitted = bool(meta.get("is_fitted", False))
                    scaler.temperature = temp
                    scaler.is_fitted = fitted
                except Exception:
                    continue

    def should_calibrate(
        self, domain: str, tenant: str, ece_threshold: float = 0.1
    ) -> bool:
        """
        Determine if calibration is needed based on ECE.

        Args:
            domain: Predictor domain
            tenant: Tenant identifier
            ece_threshold: Maximum acceptable ECE

        Returns:
            True if calibration is recommended
        """
        metrics = self.get_calibration_metrics(domain, tenant)
        return metrics["ece"] > ece_threshold and metrics["samples"] >= 100

    def export_reliability_data(self, domain: str, tenant: str) -> Dict:
        """
        Export reliability diagram data for visualization.

        Returns:
            Dictionary with reliability diagram data
        """
        key = f"{domain}:{tenant}"

        with self.lock:
            if key not in self.calibration_data:
                return {"reliability": [], "samples": 0}

            from .temperature_scaling import reliability_diagram

            confidences = list(self.calibration_data[key]["confidences"])
            accuracies = list(self.calibration_data[key]["accuracies"])

            if len(confidences) == 0:
                return {"reliability": [], "samples": 0}

            diagram = reliability_diagram(confidences, accuracies)

            return {
                "reliability": diagram,
                "samples": len(confidences),
                "domain": domain,
                "tenant": tenant,
            }


# Global calibration tracker instance
calibration_tracker = CalibrationTracker()


def get_calibration_endpoint_data() -> Dict:
    """Get calibration data for API endpoints."""
    return calibration_tracker.get_all_metrics()
