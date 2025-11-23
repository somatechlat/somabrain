"""
Adaptive Neuromodulators Module for TRUE LEARNING

This module replaces static neuromodulator values with adaptive parameters
that learn from performance feedback, eliminating the mock brain behavior.

Key Features:
- Adaptive dopamine levels based on reward prediction errors
- Dynamic serotonin based on emotional stability feedback
- Learning noradrenaline based on urgency/arousal needs
- Adaptive acetylcholine based on attention/memory formation success
- Per-tenant neuromodulator personalization
- Performance-driven parameter evolution

Classes:
    AdaptiveNeuromodulators: Main adaptive neuromodulator system
    AdaptivePerTenantNeuromodulators: Per-tenant adaptive neuromodulation
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional
from .adaptive.core import AdaptiveParameter, PerformanceMetrics
from .neuromodulators import NeuromodState
from common.config.settings import settings


class AdaptiveNeuromodulators:
    """True learning neuromodulator system with adaptive parameters."""

    def __init__(self):
        if not settings.enable_advanced_learning:
            raise RuntimeError(
                "Advanced learning is disabled; enable SOMABRAIN_ENABLE_ADVANCED_LEARNING to init adaptive neuromodulators."
            )
        # Initialize adaptive parameters with learning bounds
        self.dopamine_param = AdaptiveParameter(
            name="dopamine",
            initial_value=settings.neuromod_dopamine_base,
            min_value=settings.neuromod_dopamine_min,
            max_value=settings.neuromod_dopamine_max,
            learning_rate=settings.neuromod_dopamine_lr,
        )
        self.serotonin_param = AdaptiveParameter(
            name="serotonin",
            initial_value=settings.neuromod_serotonin_base,
            min_value=settings.neuromod_serotonin_min,
            max_value=settings.neuromod_serotonin_max,
            learning_rate=settings.neuromod_serotonin_lr,
        )
        self.noradrenaline_param = AdaptiveParameter(
            name="noradrenaline",
            initial_value=settings.neuromod_noradrenaline_base,
            min_value=settings.neuromod_noradrenaline_min,
            max_value=settings.neuromod_noradrenaline_max,
            learning_rate=settings.neuromod_noradrenaline_lr,
        )
        self.acetylcholine_param = AdaptiveParameter(
            name="acetylcholine",
            initial_value=settings.neuromod_acetylcholine_base,
            min_value=settings.neuromod_acetylcholine_min,
            max_value=settings.neuromod_acetylcholine_max,
            learning_rate=settings.neuromod_acetylcholine_lr,
        )

    def get_current_state(self) -> NeuromodState:
        """Get current neuromodulator state from adaptive parameters."""
        return NeuromodState(
            dopamine=self.dopamine_param.current_value,
            serotonin=self.serotonin_param.current_value,
            noradrenaline=self.noradrenaline_param.current_value,
            acetylcholine=self.acetylcholine_param.current_value,
            timestamp=time.time(),
        )

    def update_from_performance(
        self, performance: PerformanceMetrics, task_type: str = "general"
    ) -> NeuromodState:
        """Update neuromodulators based on performance feedback."""

        # Calculate component-specific feedback
        component_perfs = {
            "dopamine": _calculate_dopamine_feedback(performance, task_type),
            "serotonin": _calculate_serotonin_feedback(performance, task_type),
            "noradrenaline": _calculate_noradrenaline_feedback(performance, task_type),
            "acetylcholine": _calculate_acetylcholine_feedback(performance, task_type),
        }

        # Update each parameter
        self.dopamine_param.update(performance, component_perfs["dopamine"])
        self.serotonin_param.update(performance, component_perfs["serotonin"])
        self.noradrenaline_param.update(performance, component_perfs["noradrenaline"])
        self.acetylcholine_param.update(performance, component_perfs["acetylcholine"])

        return self.get_current_state()

    def get_adaptation_stats(self) -> Dict[str, any]:
        """Get adaptation statistics for verification."""
        return {
            "dopamine": self.dopamine_param.get_stats(),
            "serotonin": self.serotonin_param.get_stats(),
            "noradrenaline": self.noradrenaline_param.get_stats(),
            "acetylcholine": self.acetylcholine_param.get_stats(),
        }


class AdaptivePerTenantNeuromodulators:
    """Per-tenant adaptive neuromodulator system."""

    def __init__(self):
        self._adaptive_systems: Dict[str, AdaptiveNeuromodulators] = {}
        self._global = AdaptiveNeuromodulators()

    def get_adaptive_system(self, tenant_id: str) -> AdaptiveNeuromodulators:
        """Get or create adaptive system for tenant."""
        if tenant_id not in self._adaptive_systems:
            self._adaptive_systems[tenant_id] = AdaptiveNeuromodulators()
        return self._adaptive_systems[tenant_id]

    def get_state(self, tenant_id: Optional[str] = None) -> NeuromodState:
        """Get current neuromodulator state."""
        if tenant_id is None:
            return self._global.get_current_state()
        return self.get_adaptive_system(tenant_id).get_current_state()

    def adapt_from_performance(
        self,
        tenant_id: str,
        performance: PerformanceMetrics,
        task_type: str = "general",
    ) -> NeuromodState:
        """Adapt neuromodulators based on performance for specific tenant."""
        system = self.get_adaptive_system(tenant_id)
        return system.update_from_performance(performance, task_type)

    def get_adaptation_stats(self, tenant_id: Optional[str] = None) -> Dict[str, any]:
        """Get adaptation statistics."""
        if tenant_id is None:
            return self._global.get_adaptation_stats()
        return self.get_adaptive_system(tenant_id).get_adaptation_stats()


def _calculate_dopamine_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate dopamine feedback based on reward prediction errors."""
    # Higher dopamine for successful reward-based learning
    return (
        performance.success_rate - 0.5 + (0.1 if task_type == "reward_learning" else 0)
    )


def _calculate_serotonin_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate serotonin feedback based on emotional stability."""
    # Higher serotonin for stable, consistent performance
    return 1.0 - performance.error_rate


def _calculate_noradrenaline_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate noradrenaline feedback based on urgency/arousal needs."""
    # Higher noradrenaline for high-stakes/time-critical tasks
    urgency_factor = settings.neuromod_urgency_factor if task_type == "urgent" else 0.0
    return min(
        settings.neuromod_noradrenaline_max,
        (1.0 / max(0.1, performance.latency)) * 0.05 + urgency_factor,
    )


def _calculate_acetylcholine_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate acetylcholine feedback based on attention/memory formation."""
    # Higher acetylcholine for memory-intensive tasks
    memory_factor = settings.neuromod_memory_factor if task_type == "memory" else 0.0
    return performance.accuracy * 0.1 + memory_factor


# Global adaptive neuromodulator system
adaptive_neuromods = AdaptivePerTenantNeuromodulators()
