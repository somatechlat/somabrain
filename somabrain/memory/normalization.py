"""Coordinate normalization utilities for SomaBrain Memory.

This module parses coordinates returned by the memory service. The hash that
derives a coordinate lives in exactly one place in this repo —
``somabrain.memory.client.serialization._stable_coord`` (T-2). Do not
redefine it here.
"""

from __future__ import annotations

from typing import Any

from .client.serialization import _stable_coord


def _parse_coord_string(s: str) -> tuple[float, float, float] | None:
    """Parse a comma-separated coordinate string into a tuple.

    Args:
        s: A string like "0.5, -0.3, 0.8" representing x, y, z coordinates.

    Returns:
        A tuple (x, y, z) if parsing succeeds, None otherwise.
    """
    try:
        parts = [float(x.strip()) for x in str(s).split(",")]
        if len(parts) >= 3:
            return (parts[0], parts[1], parts[2])
    except Exception:
        return None
    return None


def _extract_memory_coord(
    resp: Any,
    idempotency_key: str | None = None,
) -> tuple[float, float, float] | None:
    """Try to derive a coordinate tuple from the memory-service response.

    This function attempts to extract coordinates from various locations
    in the response structure, falling back to generating a stable coordinate
    from the memory ID or idempotency key if no explicit coordinate is found.

    Args:
        resp: The response from the memory service (dict, httpx.Response, etc.)
        idempotency_key: Optional key to use for generating a fallback coordinate.

    Returns:
        A tuple (x, y, z) if a coordinate can be derived, None otherwise.
    """
    if not resp:
        return None

    data = resp
    json_attr = getattr(resp, "json", None)
    if callable(json_attr):
        try:
            data = json_attr()
        except (ValueError, TypeError):
            data = resp

    data_dict = data if isinstance(data, dict) else None

    if data_dict is not None:
        # Check top-level coord/coordinate fields
        for key in ("coord", "coordinate"):
            value = data_dict.get(key)
            parsed: tuple[float, float, float] | None = None
            if isinstance(value, str):
                parsed = _parse_coord_string(value)
            elif isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    parsed = (float(value[0]), float(value[1]), float(value[2]))
                except (TypeError, ValueError):
                    parsed = None
            if parsed:
                return parsed

        # Check nested memory section
        mem_section = data_dict.get("memory")
        if isinstance(mem_section, dict):
            for key in ("coordinate", "coord", "location"):
                value = mem_section.get(key)
                parsed = None
                if isinstance(value, str):
                    parsed = _parse_coord_string(value)
                elif isinstance(value, (list, tuple)) and len(value) >= 3:
                    try:
                        parsed = (float(value[0]), float(value[1]), float(value[2]))
                    except (TypeError, ValueError):
                        parsed = None
                if parsed:
                    return parsed

            # Fall back to memory ID
            mid = mem_section.get("id") or mem_section.get("memory_id")
            if mid is not None:
                try:
                    return _stable_coord(str(mid))
                except (TypeError, ValueError):
                    pass

        # Fall back to top-level ID
        mid = data_dict.get("id") or data_dict.get("memory_id")
        if mid is not None:
            try:
                return _stable_coord(str(mid))
            except (TypeError, ValueError):
                pass

    # Last resort: use idempotency key
    if idempotency_key:
        try:
            return _stable_coord(f"idempotency:{idempotency_key}")
        except (TypeError, ValueError):
            return None
    return None
