"""Datetime utilities for SomaBrain.

Provides standardized functions for handling timestamps and conversions.
"""

from __future__ import annotations

import datetime
from typing import Any


def coerce_to_epoch_seconds(value: Any) -> float:
    """Convert a client-supplied timestamp into Unix epoch seconds.

    Accepts floats/ints (assumed seconds), ISO 8601 strings, numeric strings,
    and :class:`datetime.datetime` objects. Raises ``ValueError`` for
    unsupported types or malformed values so callers can surface a 400 error
    to API clients.
    """
    if value is None:
        raise ValueError("timestamp cannot be null")

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("timestamp string cannot be empty")
        # Fast-path numeric parsing (seconds since epoch).
        try:
            return float(stripped)
        except ValueError:
            pass
        try:
            dt = datetime.datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "Unsupported timestamp format; expected seconds since epoch or ISO 8601"
            ) from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()

    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()

    raise ValueError(
        f"Unsupported timestamp type {type(value)!r}; expected float, int, str, or datetime"
    )
