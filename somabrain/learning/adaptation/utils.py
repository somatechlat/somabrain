"""Numeric helpers shared by the adaptation engine and its property tests."""

from __future__ import annotations

import math


def clamp(value: float, lower: float, upper: float) -> float:
    """Return ``value`` restricted to ``[lower, upper]``. Non-finite → lower."""
    v = float(value)
    if not math.isfinite(v):
        return float(lower)
    return min(max(v, lower), upper)


def weight_delta(learning_rate: float, gain: float, signal: float) -> float:
    """Return the signed adaptation step ``lr × gain × signal`` (finite or 0)."""
    lr = float(learning_rate)
    g = float(gain)
    s = float(signal)
    if not (math.isfinite(lr) and math.isfinite(g) and math.isfinite(s)):
        return 0.0
    return lr * g * s
