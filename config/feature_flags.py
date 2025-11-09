"""
Feature flags for roadmap implementation.
Centralizes feature flag management for roadmap features.
"""

import os
from typing import Dict, Any


class FeatureFlags:
    """Centralized feature flag management.

    All roadmap feature flags default to ON unless explicitly disabled by setting the
    environment variable to one of {"0","false","off","no"}. This ensures full
    capability testing without manual export spam.
    """

    _NEG = {"0", "false", "off", "no"}

    @staticmethod
    def _is_enabled(name: str) -> bool:
        val = os.getenv(name)
        if val is None:  # default ON
            return True
        return val.strip().lower() not in FeatureFlags._NEG

    # HMM Segmentation
    ENABLE_HMM_SEGMENTATION = _is_enabled.__func__("ENABLE_HMM_SEGMENTATION")  # type: ignore

    # Fusion Normalization
    ENABLE_FUSION_NORMALIZATION = _is_enabled.__func__("ENABLE_FUSION_NORMALIZATION")  # type: ignore

    # Calibration Pipeline
    ENABLE_CALIBRATION = _is_enabled.__func__("ENABLE_CALIBRATION")  # type: ignore

    # Consistency Checks
    ENABLE_CONSISTENCY_CHECKS = _is_enabled.__func__("ENABLE_CONSISTENCY_CHECKS")  # type: ignore

    # Runtime Consolidation
    ENABLE_RUNTIME_CONSOLIDATION = _is_enabled.__func__("ENABLE_RUNTIME_CONSOLIDATION")  # type: ignore

    # Drift Detection
    ENABLE_DRIFT_DETECTION = _is_enabled.__func__("ENABLE_DRIFT_DETECTION")  # type: ignore

    # Auto Rollback
    ENABLE_AUTO_ROLLBACK = _is_enabled.__func__("ENABLE_AUTO_ROLLBACK")  # type: ignore
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get current feature flag status."""
        return {
            "hmm_segmentation": cls.ENABLE_HMM_SEGMENTATION,
            "fusion_normalization": cls.ENABLE_FUSION_NORMALIZATION,
            "calibration": cls.ENABLE_CALIBRATION,
            "consistency_checks": cls.ENABLE_CONSISTENCY_CHECKS,
            "runtime_consolidation": cls.ENABLE_RUNTIME_CONSOLIDATION,
            "drift_detection": cls.ENABLE_DRIFT_DETECTION,
            "auto_rollback": cls.ENABLE_AUTO_ROLLBACK,
        }
    
    @classmethod
    def enable_roadmap_features(cls) -> None:  # retained for explicit forcing
        """Force enable all roadmap features (idempotent)."""
        for k in [
            "ENABLE_HMM_SEGMENTATION",
            "ENABLE_FUSION_NORMALIZATION",
            "ENABLE_CALIBRATION",
            "ENABLE_CONSISTENCY_CHECKS",
            "ENABLE_RUNTIME_CONSOLIDATION",
            "ENABLE_DRIFT_DETECTION",
            "ENABLE_AUTO_ROLLBACK",
        ]:
            os.environ[k] = "1"
        cls.__init_subclass__()


# Re-export for backwards compatibility
ENABLE_HMM_SEGMENTATION = FeatureFlags.ENABLE_HMM_SEGMENTATION
ENABLE_FUSION_NORMALIZATION = FeatureFlags.ENABLE_FUSION_NORMALIZATION
ENABLE_CALIBRATION = FeatureFlags.ENABLE_CALIBRATION
ENABLE_CONSISTENCY_CHECKS = FeatureFlags.ENABLE_CONSISTENCY_CHECKS
ENABLE_RUNTIME_CONSOLIDATION = FeatureFlags.ENABLE_RUNTIME_CONSOLIDATION
ENABLE_DRIFT_DETECTION = FeatureFlags.ENABLE_DRIFT_DETECTION
ENABLE_AUTO_ROLLBACK = FeatureFlags.ENABLE_AUTO_ROLLBACK