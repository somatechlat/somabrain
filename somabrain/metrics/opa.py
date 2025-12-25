"""OPA and Reward Gate Metrics for SomaBrain.

This module provides metrics for OPA (Open Policy Agent) enforcement
and Reward Gate decisions.

Metrics:
- OPA_ALLOW_TOTAL: Requests allowed by OPA
- OPA_DENY_TOTAL: Requests denied by OPA
- REWARD_ALLOW_TOTAL: Requests allowed by Reward Gate
- REWARD_DENY_TOTAL: Requests denied by Reward Gate
"""

from __future__ import annotations

from somabrain.metrics.core import get_counter

# ---------------------------------------------------------------------------
# OPA Enforcement Metrics
# ---------------------------------------------------------------------------

OPA_ALLOW_TOTAL = get_counter(
    "somabrain_opa_allow_total",
    "Number of requests allowed by OPA",
)

OPA_DENY_TOTAL = get_counter(
    "somabrain_opa_deny_total",
    "Number of requests denied by OPA",
)

# ---------------------------------------------------------------------------
# Reward Gate Metrics
# ---------------------------------------------------------------------------

REWARD_ALLOW_TOTAL = get_counter(
    "somabrain_reward_allow_total",
    "Number of requests allowed by Reward Gate",
)

REWARD_DENY_TOTAL = get_counter(
    "somabrain_reward_deny_total",
    "Number of requests denied by Reward Gate",
)

__all__ = [
    "OPA_ALLOW_TOTAL",
    "OPA_DENY_TOTAL",
    "REWARD_ALLOW_TOTAL",
    "REWARD_DENY_TOTAL",
]
