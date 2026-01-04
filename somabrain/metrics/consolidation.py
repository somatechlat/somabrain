"""Consolidation and Supervisor Metrics for SomaBrain.

This module provides metrics for sleep/consolidation cycles and supervisor
free-energy tracking.

Metrics:
- CONSOLIDATION_RUNS: Counter for consolidation runs by phase
- REPLAY_STRENGTH: Histogram for replay reinforcement weights
- REM_SYNTHESIZED: Counter for REM synthesized semantic memories
- FREE_ENERGY: Histogram for free-energy proxy values
- SUPERVISOR_MODULATION: Histogram for neuromodulator adjustments
"""

from __future__ import annotations

from somabrain.metrics.core import get_counter, get_histogram

# Consolidation / Sleep metrics
CONSOLIDATION_RUNS = get_counter(
    "somabrain_consolidation_runs_total",
    "Consolidation runs by phase",
    labelnames=["phase"],
)
REPLAY_STRENGTH = get_histogram(
    "somabrain_consolidation_replay_strength",
    "Distribution of replay reinforcement weights",
)
REM_SYNTHESIZED = get_counter(
    "somabrain_consolidation_rem_synthesized_total",
    "Count of REM synthesized semantic memories",
)

# Supervisor / Energy metrics
FREE_ENERGY = get_histogram(
    "somabrain_free_energy",
    "Free-energy proxy values",
)
SUPERVISOR_MODULATION = get_histogram(
    "somabrain_supervisor_modulation",
    "Magnitude of neuromodulator adjustments",
)

__all__ = [
    "CONSOLIDATION_RUNS",
    "REPLAY_STRENGTH",
    "REM_SYNTHESIZED",
    "FREE_ENERGY",
    "SUPERVISOR_MODULATION",
]