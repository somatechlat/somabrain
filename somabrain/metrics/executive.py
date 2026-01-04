"""Executive Controller and Microcircuit Metrics for SomaBrain.

This module provides metrics for executive controller decisions,
bandit arm selection, and microcircuit voting.

Metrics:
- EXEC_CONFLICT: Histogram for executive conflict proxy
- EXEC_USE_GRAPH: Counter for graph augmentation usage
- EXEC_BANDIT_ARM: Counter for bandit arm selections
- EXEC_BANDIT_REWARD: Histogram for bandit rewards
- EXEC_K_SELECTED: Histogram for final top_k selection
- MICRO_VOTE_ENTROPY: Histogram for column vote entropy
- MICRO_COLUMN_ADMIT: Counter for column admissions
- MICRO_COLUMN_BEST: Counter for best-column selections
- ATTENTION_LEVEL: Gauge for current attention level
"""

from __future__ import annotations

from somabrain.metrics.core import (
    Counter,
    Gauge,
    Histogram,
    registry,
)

# Executive Controller metrics
EXEC_CONFLICT = Histogram(
    "somabrain_exec_conflict",
    "Executive conflict proxy (1-mean recall strength)",
    registry=registry,
)
EXEC_USE_GRAPH = Counter(
    "somabrain_exec_use_graph_total",
    "Times executive controller enabled graph augmentation",
    registry=registry,
)
EXEC_BANDIT_ARM = Counter(
    "somabrain_exec_bandit_arm_total",
    "Executive bandit arm selection counts",
    ["arm"],
    registry=registry,
)
EXEC_BANDIT_REWARD = Histogram(
    "somabrain_exec_bandit_reward",
    "Executive bandit observed rewards",
    registry=registry,
)
EXEC_K_SELECTED = Histogram(
    "somabrain_exec_k_selected",
    "Final top_k selected by executive/policy",
    registry=registry,
)

# Microcircuits
MICRO_VOTE_ENTROPY = Histogram(
    "somabrain_micro_vote_entropy",
    "Entropy of column vote distribution",
    registry=registry,
)
MICRO_COLUMN_ADMIT = Counter(
    "somabrain_micro_column_admit_total",
    "Admissions per microcircuit column",
    ["column"],
    registry=registry,
)
MICRO_COLUMN_BEST = Counter(
    "somabrain_micro_column_best_total",
    "Recall best-column selection counts",
    ["column"],
    registry=registry,
)

# Attention level
ATTENTION_LEVEL = Gauge(
    "somabrain_attention_level",
    "Current attention level as tracked by thalamus (0..1)",
    registry=registry,
)

__all__ = [
    "EXEC_CONFLICT",
    "EXEC_USE_GRAPH",
    "EXEC_BANDIT_ARM",
    "EXEC_BANDIT_REWARD",
    "EXEC_K_SELECTED",
    "MICRO_VOTE_ENTROPY",
    "MICRO_COLUMN_ADMIT",
    "MICRO_COLUMN_BEST",
    "ATTENTION_LEVEL",
]