"""
Calibration utilities for SomaBrain.

Provides temperature scaling, ECE (Expected Calibration Error), and Brier score
computations for predictor calibration.
"""

from .calibration_metrics import CalibrationTracker
from .temperature_scaling import TemperatureScaler, compute_brier_score, compute_ece

__all__ = [
    "CalibrationTracker",
    "TemperatureScaler",
    "compute_brier_score",
    "compute_ece",
]
