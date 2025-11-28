"""
Neuromodulators Module for SomaBrain

This module implements a neuromodulatory system that simulates key neurotransmitters
and their effects on cognitive processing. Neuromodulators play crucial roles in
learning, motivation, attention, and adaptive behavior in biological brains.

Key Features:
- Dopamine: Motivation, reward prediction, and error weighting
- Serotonin: Emotional stability and smoothing of neural responses
- Noradrenaline: Urgency, arousal, and gain control
- Acetylcholine: Attention, focus, and memory consolidation
- Publish/subscribe pattern for state changes
- Timestamped state tracking

Neuromodulator Functions:
- Dopamine: Modulates learning rate and motivation (0.2-0.8 range)
- Serotonin: Provides emotional stability and response smoothing (0.0-1.0 range)
- Noradrenaline: Controls urgency and neural gain (0.0-0.1 range)
- Acetylcholine: Enhances attention and focus (0.0-0.1 range)

Integration:
- Affects salience computation in amygdala
- Modulates learning rates in various systems
- Influences decision thresholds in executive control
- Adapts behavior based on internal state and external feedback

Classes:
    NeuromodState: Container for neuromodulator values and timestamp
    Neuromodulators: Publish/subscribe hub for neuromodulator state management

Biological Inspiration:
- Mesolimbic dopamine system for reward and motivation
- Serotonergic system for mood and emotional regulation
- Locus coeruleus noradrenergic system for arousal
- Cholinergic system for attention and memory
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List
from .adaptive.core import AdaptiveParameter, PerformanceMetrics
from common.config.settings import settings


@dataclass
class NeuromodState:
    """
    Represents the neuromodulatory state for cognitive control.

    Attributes
    ----------
    dopamine : float
        Motivation and error weighting [0.2, 0.8].
    serotonin : float
        Smoothing and stability [0.0, 1.0].
    noradrenaline : float
        Urgency/gain [0, 0.1].
    acetylcholine : float
        Focus [0, 0.1].
    timestamp : float
        Time of last update.
    """

    dopamine: float = field(
        default_factory=lambda: float(getattr(settings, "neuromod_dopamine_base", 0.4))
    )
    serotonin: float = field(
        default_factory=lambda: float(getattr(settings, "neuromod_serotonin_base", 0.5))
    )
    noradrenaline: float = field(
        default_factory=lambda: float(
            getattr(settings, "neuromod_noradrenaline_base", 0.0)
        )
    )
    acetylcholine: float = field(
        default_factory=lambda: float(
            getattr(settings, "neuromod_acetylcholine_base", 0.0)
        )
    )
    timestamp: float = field(default_factory=lambda: time.time())


class Neuromodulators:
    """
    Publish/subscribe hub for NeuromodState updates.

    Allows components to subscribe to neuromodulator changes for adaptive control.
    """

    def __init__(self):
        self._state = NeuromodState(
            dopamine=settings.neuromod_dopamine_base,
            serotonin=settings.neuromod_serotonin_base,
            noradrenaline=settings.neuromod_noradrenaline_base,
            acetylcholine=settings.neuromod_acetylcholine_base,
            timestamp=time.time(),
        )
        self._subs: List[Callable[[NeuromodState], None]] = []

    def get_state(self) -> NeuromodState:
        return self._state

    def set_state(self, s: NeuromodState) -> None:
        """Set the current neuromodulator state.

        Subscribers are notified of the change.
        """
        self._state = s
        for cb in self._subs:
            try:
                cb(s)
            except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")
        # Update Prometheus metrics for neuromodulator values and count updates
        try:
            from . import metrics as _mx

            _mx.NEUROMOD_DOPAMINE.set(s.dopamine)
            _mx.NEUROMOD_SEROTONIN.set(s.serotonin)
            _mx.NEUROMOD_NORADRENALINE.set(s.noradrenaline)
            _mx.NEUROMOD_ACETYLCHOLINE.set(s.acetylcholine)
            _mx.NEUROMOD_UPDATE_COUNT.inc()
        except Exception:
            # Metrics optional – ignore failures during state update
raise NotImplementedError("Placeholder removed per VIBE rules")

    def subscribe(self, cb: Callable[[NeuromodState], None]) -> None:
        self._subs.append(cb)


# Per‑tenant neuromodulator store
class PerTenantNeuromodulators:
    """Simple container that keeps a NeuromodState per tenant.

    If a tenant has no stored state, the global Neuromodulators instance is used as a default.
    """

    def __init__(self):
        self._states: Dict[str, NeuromodState] = {}
        self._global = Neuromodulators()

    def get_state(self, tenant_id: str | None = None) -> NeuromodState:
        if tenant_id is None:
            return self._global.get_state()
        return self._states.get(tenant_id, self._global.get_state())

    def set_state(self, tenant_id: str, state: NeuromodState) -> None:
        self._states[tenant_id] = state
        # Notify any global subscribers of the change for this tenant if needed
        # (subscribers receive the raw NeuromodState; they can filter by tenant themselves)
        for cb in self._global._subs:
            try:
                cb(state)
            except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")


@dataclass
class AdaptiveNeuromodulators:
    """True learning neuromodulator system with adaptive parameters."""

    dopamine_param: AdaptiveParameter
    serotonin_param: AdaptiveParameter
    noradrenaline_param: AdaptiveParameter
    acetylcholine_param: AdaptiveParameter

    def __init__(self):
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


def _calculate_dopamine_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate dopamine feedback based on reward prediction errors."""
    # Higher dopamine for successful reward-based learning
    boost = settings.neuromod_dopamine_reward_boost if task_type == "reward_learning" else 0.0
    return performance.success_rate + settings.neuromod_dopamine_bias + boost


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
    floor = max(0.0, min(1.0, float(settings.neuromod_latency_floor or 0.1)))
    latency_term = (1.0 / max(floor, performance.latency)) * settings.neuromod_latency_scale
    return min(settings.neuromod_noradrenaline_max, latency_term + urgency_factor)


def _calculate_acetylcholine_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """Calculate acetylcholine feedback based on attention/memory formation."""
    # Higher acetylcholine for memory-intensive tasks
    memory_factor = settings.neuromod_memory_factor if task_type == "memory" else 0.0
    return performance.accuracy * settings.neuromod_accuracy_scale + memory_factor


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

    def get_state(self, tenant_id: str | None = None) -> NeuromodState:
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


# Global adaptive neuromodulator system
adaptive_per_tenant_neuromods = AdaptivePerTenantNeuromodulators()
