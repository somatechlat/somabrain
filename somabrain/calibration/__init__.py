from .temperature_scaling import TemperatureScaler, compute_ece, compute_brier_score
from .calibration_metrics import CalibrationTracker
from common.logging import logger

"""
Calibration utilities for SomaBrain.

Provides temperature scaling, ECE (Expected Calibration Error), and Brier score
computations for predictor calibration.
"""


__all__ = [
    "TemperatureScaler",
    "compute_ece",
    "compute_brier_score",
    "CalibrationTracker",
]
