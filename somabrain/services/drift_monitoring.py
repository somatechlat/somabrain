"""Compatibility shim for drift monitoring service.

Provides the expected import path for tests by re-exporting the centralized
DriftMonitoringService implemented in monitoring.drift_detector.
"""

from somabrain.monitoring.drift_detector import DriftMonitoringService  # re-export

__all__ = ["DriftMonitoringService"]
