"""Canonical recency kernel (stretched exponential).

Single implementation of the recency family used by recall ranking, the
unified scorer, working-memory salience/eviction, and context temporal decay:

    R(age) = clamp(exp(-(age / scale) ** sharpness), floor, 1)

``scale`` is the one recency time scale (``SOMABRAIN_WM_RECENCY_TIME_SCALE``).
"""

from __future__ import annotations

import math

_EPS = 1e-6
_MIN_SHARPNESS = 1e-3


def stretched_exponential_recency(
    age_seconds: float,
    *,
    scale: float,
    sharpness: float,
    floor: float,
) -> float:
    """Return the recency factor for ``age_seconds``.

    Args:
        age_seconds: Non-negative age in seconds. Values <= 0 yield 1.0.
            NaN yields ``floor`` (unknown age is maximally stale).
        scale: Recency time scale in seconds (must be > 0).
        sharpness: Stretch exponent (must be > 0).
        floor: Lower clamp for the result, in [0, 1).

    Returns:
        Recency factor in ``[floor, 1]``.
    """
    age = float(age_seconds)
    fl = float(floor)
    if not math.isfinite(fl) or fl < 0.0:
        fl = 0.0
    fl = min(fl, 0.99)
    # NaN age is unknown, treat as maximally stale → floor (never 1.0).
    if math.isnan(age):
        return fl
    if age <= 0.0:
        return 1.0
    s = float(scale)
    if not math.isfinite(s) or s <= 0.0:
        s = _EPS
    p = float(sharpness)
    if not math.isfinite(p) or p <= 0.0:
        p = _MIN_SHARPNESS
    else:
        p = max(p, _MIN_SHARPNESS)
    try:
        damp = math.exp(-((age / s) ** p))
    except Exception:
        damp = 0.0
    return max(fl, min(1.0, damp))


def recency_steps(
    age_seconds: float,
    *,
    scale: float,
    sharpness: float,
    cap: float,
) -> float:
    """Return the monotone step feature ``min(log1p(age/scale)*sharpness, cap)``."""
    age = float(age_seconds)
    c = float(cap)
    if not math.isfinite(c) or c <= 0.0:
        c = 1000.0
    # NaN age is unknown, treat as maximally stale → cap.
    if math.isnan(age):
        return float(c)
    if age <= 0.0:
        return 0.0
    s = float(scale)
    if not math.isfinite(s) or s <= 0.0:
        s = _EPS
    p = float(sharpness)
    if not math.isfinite(p) or p <= 0.0:
        p = _MIN_SHARPNESS
    normalised = age / s
    steps = math.log1p(normalised) * p
    return float(min(steps, c))


def recency_features(
    age_seconds: float,
    *,
    scale: float,
    sharpness: float,
    floor: float,
    cap: float,
) -> tuple[float, float]:
    """Return ``(recency_steps, recency_boost)`` for a non-negative age."""
    steps = recency_steps(age_seconds, scale=scale, sharpness=sharpness, cap=cap)
    boost = stretched_exponential_recency(
        age_seconds, scale=scale, sharpness=sharpness, floor=floor
    )
    return steps, boost
