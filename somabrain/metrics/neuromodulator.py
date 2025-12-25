"""Neuromodulator Metrics for SomaBrain.

This module provides metrics for tracking neuromodulator levels
(dopamine, serotonin, noradrenaline, acetylcholine) and update counts.

Metrics:
- NEUROMOD_DOPAMINE: Current dopamine level
- NEUROMOD_SEROTONIN: Current serotonin level
- NEUROMOD_NORADRENALINE: Current noradrenaline level
- NEUROMOD_ACETYLCHOLINE: Current acetylcholine level
- NEUROMOD_UPDATE_COUNT: Total number of neuromodulator updates
"""

from __future__ import annotations

from prometheus_client import REGISTRY, Counter as _PromCounter, Gauge as _PromGauge

# ---------------------------------------------------------------------------
# Neuromodulator Value Gauges (ensure single registration)
# ---------------------------------------------------------------------------

if "neuromod_dopamine" in REGISTRY._names_to_collectors:
    NEUROMOD_DOPAMINE = REGISTRY._names_to_collectors["neuromod_dopamine"]
else:
    NEUROMOD_DOPAMINE = _PromGauge(
        "neuromod_dopamine",
        "Current dopamine level",
        registry=REGISTRY,
    )

if "neuromod_serotonin" in REGISTRY._names_to_collectors:
    NEUROMOD_SEROTONIN = REGISTRY._names_to_collectors["neuromod_serotonin"]
else:
    NEUROMOD_SEROTONIN = _PromGauge(
        "neuromod_serotonin",
        "Current serotonin level",
        registry=REGISTRY,
    )

if "neuromod_noradrenaline" in REGISTRY._names_to_collectors:
    NEUROMOD_NORADRENALINE = REGISTRY._names_to_collectors["neuromod_noradrenaline"]
else:
    NEUROMOD_NORADRENALINE = _PromGauge(
        "neuromod_noradrenaline",
        "Current noradrenaline level",
        registry=REGISTRY,
    )

if "neuromod_acetylcholine" in REGISTRY._names_to_collectors:
    NEUROMOD_ACETYLCHOLINE = REGISTRY._names_to_collectors["neuromod_acetylcholine"]
else:
    NEUROMOD_ACETYLCHOLINE = _PromGauge(
        "neuromod_acetylcholine",
        "Current acetylcholine level",
        registry=REGISTRY,
    )

if "neuromod_updates_total" in REGISTRY._names_to_collectors:
    NEUROMOD_UPDATE_COUNT = REGISTRY._names_to_collectors["neuromod_updates_total"]
else:
    NEUROMOD_UPDATE_COUNT = _PromCounter(
        "neuromod_updates_total",
        "Total number of neuromodulator updates",
        registry=REGISTRY,
    )

__all__ = [
    "NEUROMOD_DOPAMINE",
    "NEUROMOD_SEROTONIN",
    "NEUROMOD_NORADRENALINE",
    "NEUROMOD_ACETYLCHOLINE",
    "NEUROMOD_UPDATE_COUNT",
]
