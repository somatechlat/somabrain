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

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from django.conf import settings

from .adaptive.core import AdaptiveParameter, PerformanceMetrics
from .metrics.neuromodulator import (
    NEUROMOD_ACETYLCHOLINE,
    NEUROMOD_DOPAMINE,
    NEUROMOD_NORADRENALINE,
    NEUROMOD_SEROTONIN,
    NEUROMOD_UPDATE_COUNT,
)

logger = logging.getLogger(__name__)

from .core.rust_bridge import get_rust_module, is_rust_available


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
        default_factory=lambda: float(getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BASE", 0.4))
    )
    serotonin: float = field(
        default_factory=lambda: float(getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_BASE", 0.5))
    )
    noradrenaline: float = field(
        default_factory=lambda: float(getattr(settings, "SOMABRAIN_NEURO_NORAD_BASE", 0.0))
    )
    acetylcholine: float = field(
        default_factory=lambda: float(getattr(settings, "SOMABRAIN_NEURO_ACETYL_BASE", 0.0))
    )
    timestamp: float = field(default_factory=lambda: time.time())


class Neuromodulators:
    """
    Publish/subscribe hub for NeuromodState updates.

    Allows components to subscribe to neuromodulator changes for adaptive control.
    """

    def __init__(self):
        """Initialize the instance."""

        self._state = NeuromodState(
            dopamine=settings.SOMABRAIN_NEURO_DOPAMINE_BASE,
            serotonin=settings.SOMABRAIN_NEURO_SEROTONIN_BASE,
            noradrenaline=settings.SOMABRAIN_NEURO_NORAD_BASE,
            acetylcholine=settings.SOMABRAIN_NEURO_ACETYL_BASE,
            timestamp=time.time(),
        )
        self._subs: List[Callable[[NeuromodState], None]] = []

        # Initialize Rust backend if available
        self._rust_impl = None
        if is_rust_available():
            try:
                self._rust_impl = get_rust_module().Neuromodulators()
                # Sync initial state to Rust
                self._sync_to_rust()
            except Exception as e:
                logger.warning(f"Failed to initialize Rust Neuromodulators: {e}")

    def _sync_to_rust(self) -> None:
        """Sync current Python state to Rust backend."""
        if self._rust_impl:
            self._rust_impl.set_state(
                [
                    self._state.dopamine,
                    self._state.serotonin,
                    self._state.noradrenaline,
                    self._state.acetylcholine,
                ]
            )

    def _sync_from_rust(self) -> None:
        """Sync current Rust state to Python state."""
        if self._rust_impl:
            vals = self._rust_impl.get_state()
            if len(vals) == 4:
                self._state.dopamine = vals[0]
                self._state.serotonin = vals[1]
                self._state.noradrenaline = vals[2]
                self._state.acetylcholine = vals[3]

    def get_state(self) -> NeuromodState:
        """Retrieve state."""

        if self._rust_impl:
            self._sync_from_rust()
        return self._state

    def set_state(self, s: NeuromodState) -> None:
        """Set the current neuromodulator state.

        Subscribers are notified of the change.
        """
        self._state = s
        if self._rust_impl:
            self._sync_to_rust()
        for cb in self._subs:
            try:
                cb(s)
            except Exception as cb_exc:
                logger.debug("Neuromod subscriber callback failed: %s", cb_exc)
        # Update Prometheus metrics for neuromodulator values and count updates
        try:
            NEUROMOD_DOPAMINE.set(s.dopamine)
            NEUROMOD_SEROTONIN.set(s.serotonin)
            NEUROMOD_NORADRENALINE.set(s.noradrenaline)
            NEUROMOD_ACETYLCHOLINE.set(s.acetylcholine)
            NEUROMOD_UPDATE_COUNT.inc()
        except Exception as metric_exc:
            logger.debug("Failed to update neuromod metrics: %s", metric_exc)

    def subscribe(self, cb: Callable[[NeuromodState], None]) -> None:
        """Execute subscribe.

        Args:
            cb: The cb.
        """

        self._subs.append(cb)


# Per‑tenant neuromodulator store
class PerTenantNeuromodulators:
    """Simple container that keeps a NeuromodState per tenant.

    If a tenant has no stored state, the global Neuromodulators instance is used as a default.
    """

    def __init__(self):
        """Initialize the instance."""

        self._states: Dict[str, NeuromodState] = {}
        self._global = Neuromodulators()

    def get_state(self, tenant_id: str | None = None) -> NeuromodState:
        """Retrieve state.

        Args:
            tenant_id: The tenant_id.
        """

        if tenant_id is None:
            return self._global.get_state()
        return self._states.get(tenant_id, self._global.get_state())

    def set_state(self, tenant_id: str, state: NeuromodState) -> None:
        """Set state.

        Args:
            tenant_id: The tenant_id.
            state: The state.
        """

        self._states[tenant_id] = state
        # Notify any global subscribers of the change for this tenant if needed
        # (subscribers receive the raw NeuromodState; they can filter by tenant themselves)
        for cb in self._global._subs:
            try:
                cb(state)
            except Exception as cb_exc:
                logger.debug("Per-tenant neuromod subscriber callback failed: %s", cb_exc)


@dataclass
class AdaptiveNeuromodulators:
    """True learning neuromodulator system with adaptive parameters."""

    dopamine_param: AdaptiveParameter
    serotonin_param: AdaptiveParameter
    noradrenaline_param: AdaptiveParameter
    acetylcholine_param: AdaptiveParameter

    def __init__(self):
        # Initialize adaptive parameters with learning bounds
        """Initialize the instance."""

        self.dopamine_param = AdaptiveParameter(
            name="dopamine",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BASE", 0.4),
            min_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_MIN", 0.2),
            max_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_MAX", 0.8),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_LR", 0.01),
        )
        self.serotonin_param = AdaptiveParameter(
            name="serotonin",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_BASE", 0.5),
            min_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_MIN", 0.0),
            max_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_MAX", 1.0),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_LR", 0.01),
        )
        self.noradrenaline_param = AdaptiveParameter(
            name="noradrenaline",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_BASE", 0.0),
            min_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_MIN", 0.0),
            max_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_MAX", 0.1),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_NORAD_LR", 0.01),
        )
        self.acetylcholine_param = AdaptiveParameter(
            name="acetylcholine",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_BASE", 0.0),
            min_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_MIN", 0.0),
            max_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_MAX", 0.1),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_ACETYL_LR", 0.01),
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

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation statistics for verification."""
        return {
            "dopamine": self.dopamine_param.get_stats(),
            "serotonin": self.serotonin_param.get_stats(),
            "noradrenaline": self.noradrenaline_param.get_stats(),
            "acetylcholine": self.acetylcholine_param.get_stats(),
        }

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


def _calculate_dopamine_feedback(performance: PerformanceMetrics, task_type: str) -> float:
    """Calculate dopamine feedback based on reward prediction errors."""
    # Higher dopamine for successful reward-based learning
    boost = (
        getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST", 0.1)
        if task_type == "reward_learning"
        else 0.0
    )
    return (
        performance.success_rate + getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BIAS", 0.05) + boost
    )


def _calculate_serotonin_feedback(performance: PerformanceMetrics, task_type: str) -> float:
    """Calculate serotonin feedback based on emotional stability."""
    # Higher serotonin for stable, consistent performance
    return 1.0 - performance.error_rate


def _calculate_noradrenaline_feedback(performance: PerformanceMetrics, task_type: str) -> float:
    """Calculate noradrenaline feedback based on urgency/arousal needs."""
    # Higher noradrenaline for high-stakes/time-critical tasks
    urgency_factor = (
        getattr(settings, "SOMABRAIN_NEURO_URGENCY_FACTOR", 0.02) if task_type == "urgent" else 0.0
    )
    floor = max(0.0, min(1.0, float(getattr(settings, "SOMABRAIN_NEURO_LATENCY_FLOOR", 0.1))))
    latency_term = (1.0 / max(floor, performance.latency)) * getattr(
        settings, "SOMABRAIN_NEURO_LATENCY_SCALE", 0.01
    )
    return min(
        getattr(settings, "SOMABRAIN_NEURO_NORAD_MAX", 0.1),
        latency_term + urgency_factor,
    )


def _calculate_acetylcholine_feedback(performance: PerformanceMetrics, task_type: str) -> float:
    """Calculate acetylcholine feedback based on attention/memory formation."""
    # Higher acetylcholine for memory-intensive tasks
    memory_factor = (
        getattr(settings, "SOMABRAIN_NEURO_MEMORY_FACTOR", 0.02) if task_type == "memory" else 0.0
    )
    return (
        performance.accuracy * getattr(settings, "SOMABRAIN_NEURO_ACCURACY_SCALE", 0.05)
        + memory_factor
    )


class AdaptivePerTenantNeuromodulators:
    """Per-tenant adaptive neuromodulator system."""

    def __init__(self):
        """Initialize the instance."""

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

    def get_adaptation_stats(self, tenant_id: str | None = None) -> Dict[str, Any]:
        """Get adaptation statistics."""
        if tenant_id is None:
            return self._global.get_adaptation_stats()
        return self.get_adaptive_system(tenant_id).get_adaptation_stats()


# Global adaptive neuromodulator system
adaptive_per_tenant_neuromods = AdaptivePerTenantNeuromodulators()
