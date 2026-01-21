"""Constitution and Utility Metrics for SomaBrain.

This module provides metrics for constitution verification
and utility guard decisions.

Metrics:
- CONSTITUTION_VERIFIED: Constitution verification status (1=verified, 0=unverified)
- CONSTITUTION_VERIFY_LATENCY: Time spent verifying constitution signatures
- UTILITY_NEGATIVE: Times utility guard rejected a request (U < 0)
- UTILITY_VALUE: Last computed utility value (per process)
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Gauge, Histogram, registry

# ---------------------------------------------------------------------------
# Constitution Metrics (baseline)
# ---------------------------------------------------------------------------

CONSTITUTION_VERIFIED = Gauge(
    "somabrain_constitution_verified",
    "Constitution verification status (1=verified, 0=unverified)",
    registry=registry,
)

CONSTITUTION_VERIFY_LATENCY = Histogram(
    "somabrain_constitution_verify_latency_seconds",
    "Time spent verifying constitution signatures on startup",
    registry=registry,
)

# ---------------------------------------------------------------------------
# Utility Metrics (Phase A)
# ---------------------------------------------------------------------------

UTILITY_NEGATIVE = Counter(
    "somabrain_utility_negative_total",
    "Times utility guard rejected a request (U < 0)",
    registry=registry,
)

UTILITY_VALUE = Gauge(
    "somabrain_utility_value",
    "Last computed utility value (per process)",
    registry=registry,
)

__all__ = [
    "CONSTITUTION_VERIFIED",
    "CONSTITUTION_VERIFY_LATENCY",
    "UTILITY_NEGATIVE",
    "UTILITY_VALUE",
]
