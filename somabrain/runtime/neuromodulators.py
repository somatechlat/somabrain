"""
Neuromodulators — the single neuromodulatory state store for SomaBrain.

This module is THE implementation of neuromodulator state. Every consumer
(``/act``, ``/neuromod/*``, AdaptationEngine DA→LR, amygdala couplings,
Supervisor) reads and writes through it. There is no second tree.

Neuromodulator roles and ranges (the clamp table is
``somabrain.math.contracts.NEURO_BOUNDS`` — one source):

- Dopamine (DA)      [0.2, 0.8] — motivation / reward weighting; scales
  AdaptationEngine's dynamic learning rate.
- Serotonin (5-HT)   [0.0, 1.0] — emotional stability and **response
  smoothing**. Consumed by ``AmygdalaSalience``: higher 5-HT increases gate
  hysteresis and soft-gate temperature so decisions flap less.
- Noradrenaline (NE) [0.0, 0.1] — urgency / arousal; raises amygdala gate
  thresholds.
- Acetylcholine (ACh)[0.0, 0.1] — **attention demand**. THE ACh law (shared
  by this module's adaptive feedback and ``runtime/supervisor.Supervisor``)::

      δ_ACh = Π_ACh( 0.5·novelty + 0.3·pred_error + 0.2·memory_load )

  Novelty and prediction error (uncertainty) raise attention demand; memory
  load raises it further. ``acetylcholine_target`` is the only definition.

Homeostatic update law (W2.3 / DEBT-004), used by every adaptive path::

    m_i ← Π( m_i + η_i (δ_i − m_i) )

``δ_i`` is a *target level* in the modulator's bounds, not a velocity.
Parameters are pulled toward the target and can fall on adverse evidence;
they cannot saturate at a bound by monotone drift.

Bounds projection ``Π`` is ``project``. Boundary validation (reject NaN/inf
and out-of-box values) is ``checked_value`` — used by the HTTP API.

Classes:
    NeuromodState: Container for neuromodulator values and timestamp
    Neuromodulators: Publish/subscribe hub for neuromodulator state management
    PerTenantNeuromodulators: Process-wide per-tenant store (see
        ``bootstrap.singletons.get_neuromodulators``)
    AdaptiveNeuromodulators / AdaptivePerTenantNeuromodulators: homeostatic
        performance-driven layer
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from somabrain.adaptive.core import AdaptiveParameter, PerformanceMetrics
from somabrain.math.contracts import NEURO_BOUNDS
from somabrain.metrics.neuromodulator import (
    NEUROMOD_ACETYLCHOLINE,
    NEUROMOD_DOPAMINE,
    NEUROMOD_NORADRENALINE,
    NEUROMOD_SEROTONIN,
    NEUROMOD_UPDATE_COUNT,
)

logger = logging.getLogger(__name__)

from somabrain.core.rust_bridge import get_rust_module, is_rust_available

__all__ = [
    "NeuromodState",
    "Neuromodulators",
    "PerTenantNeuromodulators",
    "AdaptiveNeuromodulators",
    "AdaptivePerTenantNeuromodulators",
    "NeuromodValueError",
    "NEURO_BOUNDS",
    "project",
    "checked_value",
    "acetylcholine_target",
    "serotonin_target",
    "dopamine_target",
    "noradrenaline_target",
    "get_adaptive_per_tenant_neuromods",
]


class NeuromodValueError(ValueError):
    """Raised at the API boundary for non-finite or out-of-box neuromod values."""


def _unit(x: float) -> float:
    """Clamp a signal to [0, 1]."""
    return min(1.0, max(0.0, float(x)))


def project(name: str, value: float) -> float:
    """Π: project ``value`` onto ``NEURO_BOUNDS[name]``."""
    lo, hi = NEURO_BOUNDS[name]
    return min(hi, max(lo, float(value)))


def checked_value(name: str, value: float) -> float:
    """Boundary validation for one neuromodulator value.

    Returns the finite value unchanged when it lies inside
    ``NEURO_BOUNDS[name]``; raises :class:`NeuromodValueError` on NaN/inf or
    out-of-box input. The HTTP API rejects; it never silently stores garbage.
    """
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise NeuromodValueError(f"{name}: not a float: {value!r}") from exc
    if not math.isfinite(v):
        raise NeuromodValueError(f"{name}: not finite: {v!r}")
    lo, hi = NEURO_BOUNDS[name]
    if v < lo or v > hi:
        raise NeuromodValueError(
            f"{name}={v} outside documented bounds [{lo}, {hi}]"
        )
    return v


def acetylcholine_target(
    novelty: float, pred_error: float, memory_load: float = 0.0
) -> float:
    """THE ACh law: attention demand, projected onto the ACh range.

    ``δ_ACh = Π_ACh( 0.5·novelty + 0.3·pred_error + 0.2·memory_load )``

    Shared by the adaptive feedback path and ``Supervisor.adjust`` so every
    caller drives ACh the same way.
    """
    from somabrain.math.contracts import ACH_DEMAND_WEIGHTS

    w_nov, w_err, w_load = ACH_DEMAND_WEIGHTS
    demand = w_nov * _unit(novelty) + w_err * _unit(pred_error) + w_load * _unit(memory_load)
    lo, hi = NEURO_BOUNDS["acetylcholine"]
    return lo + (hi - lo) * demand


def serotonin_target(pred_error: float) -> float:
    """THE 5-HT law: emotional stability = 1 − prediction error.

    ``δ_5HT = 1 − clamp(pred_error, 0, 1)`` projected onto the 5-HT range.
    Accurate predictions raise 5-HT (stability); errors lower it.
    """
    lo, hi = NEURO_BOUNDS["serotonin"]
    return lo + (hi - lo) * (1.0 - _unit(pred_error))


def dopamine_target(success: float) -> float:
    """δ_DA: reward/success level, projected onto the dopamine range."""
    lo, hi = NEURO_BOUNDS["dopamine"]
    return lo + (hi - lo) * _unit(success)


def noradrenaline_target(arousal: float) -> float:
    """δ_NE: arousal demand (urgency / fast latency), projected onto NE range."""
    lo, hi = NEURO_BOUNDS["noradrenaline"]
    return lo + (hi - lo) * _unit(arousal)


@dataclass
class NeuromodState:
    """
    Represents the neuromodulatory state for cognitive control.

    Attributes
    ----------
    dopamine : float
        Motivation and error weighting, bounds [0.2, 0.8].
    serotonin : float
        Stability / response smoothing, bounds [0.0, 1.0].
    noradrenaline : float
        Urgency/gain, bounds [0.0, 0.1].
    acetylcholine : float
        Attention demand, bounds [0.0, 0.1].
    timestamp : float
        Time of last update.

    Bounds are the shared table ``NEURO_BOUNDS``. Use :meth:`clamped` (or
    ``PerTenantNeuromodulators.set_state``, which clamps) to project values.
    """

    dopamine: float = field(
        default_factory=lambda: float(
            getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BASE")
        )
    )
    serotonin: float = field(
        default_factory=lambda: float(
            getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_BASE")
        )
    )
    noradrenaline: float = field(
        default_factory=lambda: float(
            getattr(settings, "SOMABRAIN_NEURO_NORAD_BASE")
        )
    )
    acetylcholine: float = field(
        default_factory=lambda: float(
            getattr(settings, "SOMABRAIN_NEURO_ACETYL_BASE")
        )
    )
    timestamp: float = field(default_factory=lambda: time.time())

    def clamped(self) -> NeuromodState:
        """Π: return a copy with every value inside ``NEURO_BOUNDS``."""
        return NeuromodState(
            dopamine=project("dopamine", self.dopamine),
            serotonin=project("serotonin", self.serotonin),
            noradrenaline=project("noradrenaline", self.noradrenaline),
            acetylcholine=project("acetylcholine", self.acetylcholine),
            timestamp=self.timestamp,
        )


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
        self._subs: list[Callable[[NeuromodState], None]] = []

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
        """Set the current neuromodulator state (projected onto NEURO_BOUNDS).

        Subscribers are notified of the change.
        """
        self._state = s.clamped()
        s = self._state
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

        self._states: dict[str, NeuromodState] = {}
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
        """Set state for ``tenant_id``, projected onto NEURO_BOUNDS (Π).

        Args:
            tenant_id: The tenant_id.
            state: The state.
        """

        self._states[tenant_id] = state.clamped()
        state = self._states[tenant_id]
        # Notify any global subscribers of the change for this tenant if needed
        # (subscribers receive the raw NeuromodState; they can filter by tenant themselves)
        for cb in self._global._subs:
            try:
                cb(state)
            except Exception as cb_exc:
                logger.debug(
                    "Per-tenant neuromod subscriber callback failed: %s", cb_exc
                )


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
            initial_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BASE"),
            min_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_MIN"),
            max_value=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_MAX"),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_LR"),
        )
        self.serotonin_param = AdaptiveParameter(
            name="serotonin",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_BASE"),
            min_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_MIN"),
            max_value=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_MAX"),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_SEROTONIN_LR"),
        )
        self.noradrenaline_param = AdaptiveParameter(
            name="noradrenaline",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_BASE"),
            min_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_MIN"),
            max_value=getattr(settings, "SOMABRAIN_NEURO_NORAD_MAX"),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_NORAD_LR"),
        )
        self.acetylcholine_param = AdaptiveParameter(
            name="acetylcholine",
            initial_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_BASE"),
            min_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_MIN"),
            max_value=getattr(settings, "SOMABRAIN_NEURO_ACETYL_MAX"),
            learning_rate=getattr(settings, "SOMABRAIN_NEURO_ACETYL_LR"),
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

    def get_adaptation_stats(self) -> dict[str, Any]:
        """Get adaptation statistics for verification."""
        return {
            "dopamine": self.dopamine_param.stats(),
            "serotonin": self.serotonin_param.stats(),
            "noradrenaline": self.noradrenaline_param.stats(),
            "acetylcholine": self.acetylcholine_param.stats(),
        }

    def update_from_performance(
        self,
        performance: PerformanceMetrics,
        task_type: str = "general",
        *,
        novelty: float = 0.0,
        pred_error: float | None = None,
    ) -> NeuromodState:
        """Homeostatic update from performance (and optional attention signals).

        Each modulator is pulled toward its target level ``δ_i`` via
        ``m ← Π(m + η (δ − m))``. ``novelty`` / ``pred_error`` feed the shared
        ACh law; when ``pred_error`` is omitted it defaults to
        ``performance.error_rate``.
        """
        pe = performance.error_rate if pred_error is None else float(pred_error)

        component_perfs = {
            "dopamine": _calculate_dopamine_feedback(performance, task_type),
            "serotonin": _calculate_serotonin_feedback(performance, task_type),
            "noradrenaline": _calculate_noradrenaline_feedback(performance, task_type),
            "acetylcholine": _calculate_acetylcholine_feedback(
                performance, task_type, novelty=novelty, pred_error=pe
            ),
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
    """δ_DA target: reward/success level (biased; projected to DA bounds)."""
    boost = (
        getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST")
        if task_type == "reward_learning"
        else 0.0
    )
    success = (
        performance.success_rate
        + getattr(settings, "SOMABRAIN_NEURO_DOPAMINE_BIAS")
        + boost
    )
    return dopamine_target(success)


def _calculate_serotonin_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """δ_5HT target: emotional stability — the shared ``serotonin_target`` law."""
    return serotonin_target(performance.error_rate)


def _calculate_noradrenaline_feedback(
    performance: PerformanceMetrics, task_type: str
) -> float:
    """δ_NE target: arousal demand from latency pressure and urgency."""
    urgency_factor = (
        getattr(settings, "SOMABRAIN_NEURO_URGENCY_FACTOR")
        if task_type == "urgent"
        else 0.0
    )
    floor = max(
        0.0, min(1.0, float(getattr(settings, "SOMABRAIN_NEURO_LATENCY_FLOOR")))
    )
    latency_term = (1.0 / max(floor, performance.latency)) * getattr(
        settings, "SOMABRAIN_NEURO_LATENCY_SCALE", 0.01
    )
    return noradrenaline_target(latency_term + urgency_factor)


def _calculate_acetylcholine_feedback(
    performance: PerformanceMetrics,
    task_type: str,
    *,
    novelty: float = 0.0,
    pred_error: float | None = None,
) -> float:
    """δ_ACh target: the shared ``acetylcholine_target`` attention-demand law."""
    pe = performance.error_rate if pred_error is None else pred_error
    memory_load = (
        getattr(settings, "SOMABRAIN_NEURO_MEMORY_FACTOR")
        if task_type == "memory"
        else 0.0
    )
    return acetylcholine_target(novelty, pred_error=pe, memory_load=memory_load)


class AdaptivePerTenantNeuromodulators:
    """Per-tenant adaptive neuromodulator system."""

    def __init__(self):
        """Initialize the instance."""

        self._adaptive_systems: dict[str, AdaptiveNeuromodulators] = {}
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
        *,
        novelty: float = 0.0,
        pred_error: float | None = None,
    ) -> NeuromodState:
        """Adapt neuromodulators based on performance for specific tenant."""
        system = self.get_adaptive_system(tenant_id)
        return system.update_from_performance(
            performance, task_type, novelty=novelty, pred_error=pred_error
        )

    def get_adaptation_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get adaptation statistics."""
        if tenant_id is None:
            return self._global.get_adaptation_stats()
        return self.get_adaptive_system(tenant_id).get_adaptation_stats()


# Lazy registry for the shared adaptive neuromodulator system.
_neuromod_registry: AdaptivePerTenantNeuromodulators | None = None
_neuromod_lock = threading.Lock()


def get_adaptive_per_tenant_neuromods() -> AdaptivePerTenantNeuromodulators:
    """Return the shared AdaptivePerTenantNeuromodulators registry.

    The registry is created lazily on first call and cached for the lifetime of
    the process. This avoids module-level side effects and keeps import time
    deterministic.
    """
    global _neuromod_registry
    if _neuromod_registry is None:
        with _neuromod_lock:
            if _neuromod_registry is None:
                _neuromod_registry = AdaptivePerTenantNeuromodulators()
    return _neuromod_registry
