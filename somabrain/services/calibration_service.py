"""Lightweight prediction calibration tracker.

Provides a minimal yet real implementation used by predictor_state/agent/action
to record prediction outcomes and surface basic calibration telemetry.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Tuple

from django.conf import settings

from somabrain.calibration.calibration_metrics import CalibrationTracker


@dataclass
class CalibrationService:
    """Service for managing predictor calibration."""

    enabled: bool = field(
        default_factory=lambda: getattr(settings, "CALIBRATION_ENABLED", False)
    )
    trackers: Dict[str, CalibrationTracker] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _counts: Dict[Tuple[str, str], int] = field(default_factory=dict, init=False)
    _temperature: Dict[Tuple[str, str], float] = field(default_factory=dict, init=False)

    def record_prediction(
        self, domain: str, tenant: str, confidence: float, correct: bool
    ) -> None:
        """Execute record prediction.

        Args:
            domain: The domain.
            tenant: The tenant.
            confidence: The confidence.
            correct: The correct.
        """

        if not self.enabled:
            return
        key = (domain, tenant)
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            # Simple temperature heuristic: move toward 1.0 when correct, 0.7 when wrong
            tgt = 1.0 if correct else 0.7
            prev = self._temperature.get(key, 1.0)
            self._temperature[key] = 0.9 * prev + 0.1 * tgt

    def get_calibration_status(self, domain: str, tenant: str) -> dict:
        """Retrieve calibration status.

        Args:
            domain: The domain.
            tenant: The tenant.
        """

        key = (domain, tenant)
        with self._lock:
            return {
                "enabled": self.enabled,
                "seen": self._counts.get(key, 0),
                "temperature": self._temperature.get(key, 1.0),
            }

    def get_all_calibration_status(self) -> dict:
        """Retrieve all calibration status."""

        with self._lock:
            return {
                f"{d}:{t}": {
                    "seen": c,
                    "temperature": self._temperature.get((d, t), 1.0),
                }
                for (d, t), c in self._counts.items()
            }

    def export_reliability_data(self, domain: str, tenant: str) -> dict:
        """Export reliability data for a domain and tenant."""
        return self.get_calibration_status(domain, tenant)


# Lazy-load singleton to avoid import-time failures
_calibration_service_instance = None


def get_calibration_service() -> CalibrationService:
    """Get or create the calibration service singletonمیں"""
    global _calibration_service_instance
    if _calibration_service_instance is None:
        _calibration_service_instance = CalibrationService()
    return _calibration_service_instance


# For backwards compatibility
calibration_service = property(lambda self: get_calibration_service())
