"""Numeric helpers shared by the adaptation engine and its property tests."""

from __future__ import annotations


def clamp(value: float, lower: float, upper: float) -> float:
    """Return ``value`` restricted to ``[lower, upper]``."""
    return min(max(value, lower), upper)


def weight_delta(learning_rate: float, gain: float, signal: float) -> float:
    """Return the signed adaptation step ``lr × gain × signal``."""
    return float(learning_rate) * float(gain) * float(signal)
