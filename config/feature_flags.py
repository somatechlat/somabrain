"""
Feature flags view derived from central modes.

Source of truth: `somabrain.runtime.modes` + Django settings
(``SOMABRAIN_FEATURE_DISABLED``). Operator law: no file presets, no env secrets.
"""

from __future__ import annotations

from typing import Any

from somabrain.runtime.modes import feature_enabled, mode_config


class FeatureFlags:
    """Computed feature flag status (Django/DB only)."""

    KEYS: list[str] = [
        "hmm_segmentation",
        "fusion_normalization",
        "calibration",
        "consistency_checks",
        "drift_detection",
        "auto_rollback",
    ]

    @staticmethod
    def _load_overrides() -> list[str]:
        """Disabled keys from Django settings (comma-separated). No files."""
        from django.conf import settings

        try:
            raw = str(getattr(settings, "SOMABRAIN_FEATURE_DISABLED", "") or "")
        except Exception:
            raw = ""
        if not raw.strip():
            return []
        return [x.strip().lower() for x in raw.split(",") if x.strip()]

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        """Retrieve status."""

        cfg = mode_config()
        disabled = cls._load_overrides()

        def resolved(k: str) -> bool:
            mapping = {
                "hmm_segmentation": "hmm_segmentation",
                "fusion_normalization": "fusion_normalization",
                "calibration": "calibration",
                "consistency_checks": "consistency_checks",
                "drift_detection": "drift",
                "auto_rollback": "auto_rollback",
            }
            fk = mapping.get(k, k)
            val = feature_enabled(fk)
            return val and (k not in disabled)

        return {k: resolved(k) for k in cls.KEYS}

    @classmethod
    def set_overrides(cls, disabled: list[str]) -> None:
        """No-op file write — manage flags via Django settings / BrainSetting."""
        return None
