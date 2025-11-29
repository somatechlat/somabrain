"""Utility helpers for working with timestamps in SomaBrain APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ISO_Z_SUFFIX = "Z"


def coerce_to_epoch_seconds(value: Any) -> float:
    """Convert a client-supplied timestamp into Unix epoch seconds.

    Accepts floats/ints (assumed seconds), ISO 8601 strings, numeric strings,
    and :class:`datetime` objects. Raises ``ValueError`` for unsupported types
    or malformed values so callers can surface a 400 error to API clients.
    """

    if value is None:
        raise ValueError("timestamp cannot be null")

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("timestamp string cannot be empty")
        # Try fast-path numeric parsing first to avoid datetime parsing cost.
        try:
            return float(stripped)
        except ValueError:
        try:
            dt = datetime.fromisoformat(stripped.replace(ISO_Z_SUFFIX, "+00:00"))
        except ValueError as exc:  # pragma: no cover - message propagated upstream
            raise ValueError(
                "Unsupported timestamp format; expected seconds since epoch or ISO 8601"
            ) from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

    raise ValueError(
        f"Unsupported timestamp type {type(value)!r}; expected float, int, str, or datetime"
    )
