"""Feature Flags Service for SomaBrain (Django Version).

Provides a centralized interface for feature toggles, backed by Django settings.
Replaces the legacy Pydantic base-settings and compatibility shims.
"""

from __future__ import annotations
from typing import Dict, List, Any
from django.conf import settings


class FeatureFlags:
    """Centralized feature flag management."""

    # Canonical list of feature keys
    KEYS = [
        "minimal_public_api",
        "allow_anonymous_tenants",
        "kill_switch",
        "allow_tiny_embedder",
        "enable_cog_threads",
        "enable_sleep",
        "consolidation_enabled",
        "use_planner",
        "use_focus_state",
        "use_microcircuits",
        "use_hrr",
        "use_meta_brain",
        "use_exec_controller",
        "use_drift_monitor",
        "use_sdr_prefilter",
        "use_graph_augment",
    ]

    @classmethod
    def get_status(cls) -> Dict[str, bool]:
        """Return the current status of all feature flags."""
        return {
            "minimal_public_api": getattr(
                settings, "SOMABRAIN_MINIMAL_PUBLIC_API", False
            ),
            "allow_anonymous_tenants": getattr(
                settings, "SOMABRAIN_ALLOW_ANONYMOUS_TENANTS", False
            ),
            "kill_switch": getattr(settings, "SOMABRAIN_KILL_SWITCH", False),
            "allow_tiny_embedder": getattr(
                settings, "SOMABRAIN_ALLOW_TINY_EMBEDDER", False
            ),
            "enable_cog_threads": getattr(settings, "ENABLE_COG_THREADS", False),
            "enable_sleep": getattr(settings, "SOMABRAIN_ENABLE_SLEEP", True),
            "consolidation_enabled": getattr(
                settings, "SOMABRAIN_CONSOLIDATION_ENABLED", True
            ),
            "use_planner": getattr(settings, "SOMABRAIN_USE_PLANNER", False),
            "use_focus_state": getattr(settings, "SOMABRAIN_USE_FOCUS_STATE", True),
            "use_microcircuits": getattr(
                settings, "SOMABRAIN_USE_MICROCIRCUITS", False
            ),
            "use_hrr": getattr(settings, "SOMABRAIN_USE_HRR", False),
            "use_meta_brain": getattr(settings, "SOMABRAIN_USE_META_BRAIN", False),
            "use_exec_controller": getattr(
                settings, "SOMABRAIN_USE_EXEC_CONTROLLER", False
            ),
            "use_drift_monitor": getattr(
                settings, "SOMABRAIN_USE_DRIFT_MONITOR", False
            ),
            "use_sdr_prefilter": getattr(
                settings, "SOMABRAIN_USE_SDR_PREFILTER", False
            ),
            "use_graph_augment": getattr(
                settings, "SOMABRAIN_USE_GRAPH_AUGMENT", False
            ),
        }

    @classmethod
    def get_overrides(cls) -> Dict[str, Any]:
        """Return dynamic overrides (currently disabled in enterprise mode)."""
        return {}

    @classmethod
    def set_overrides(cls, disabled: List[str]) -> bool:
        """Set dynamic overrides (currently disabled)."""
        return False
