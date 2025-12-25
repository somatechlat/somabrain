"""Serialization utilities for SFM communication.

Per Requirements G1.1-G1.5:
- Converts Python types to JSON-compatible formats for SFM
- Handles tuples, numpy arrays, datetime objects, and epoch timestamps
"""

from __future__ import annotations

import datetime
from typing import Any, Dict


def serialize_for_sfm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a payload dict for SFM communication.

    Per Requirements G1.1-G1.5:
    - G1.1: Converts tuples to lists (JSON doesn't support tuples)
    - G1.2: Converts numpy arrays to lists
    - G1.3: Converts epoch timestamps to ISO 8601 strings
    - G1.4: Handles nested structures recursively
    - G1.5: Preserves None values and basic types

    Args:
        payload: Dictionary to serialize.

    Returns:
        JSON-compatible dictionary.
    """
    if payload is None:
        return {}
    return _serialize_value(payload)


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value for JSON compatibility.

    Handles:
    - dict: Recursively serialize all values
    - list/tuple: Convert to list, recursively serialize elements
    - numpy arrays: Convert to list
    - datetime: Convert to ISO 8601 string
    - float (epoch): Detect and convert to ISO 8601 if looks like timestamp
    - bytes: Decode to string (UTF-8)
    - Other: Return as-is
    """
    if value is None:
        return None

    # Handle dict
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}

    # Handle list/tuple - G1.1: Convert tuples to lists
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]

    # Handle numpy arrays - G1.2
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
    except ImportError:
        pass

    # Handle datetime objects - G1.3
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()

    # Handle bytes
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()

    # Handle float that looks like epoch timestamp - G1.3
    # Epoch timestamps are typically > 1e9 (year 2001+) and < 2e10 (year 2603)
    if isinstance(value, (int, float)):
        if 1_000_000_000 < value < 20_000_000_000:
            # Likely an epoch timestamp - convert to ISO 8601
            try:
                dt = datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
                return dt.isoformat()
            except (ValueError, OSError, OverflowError):
                # Not a valid timestamp, return as-is
                return value
        return value

    # Handle string, bool, None - return as-is
    if isinstance(value, (str, bool, type(None))):
        return value

    # Handle other numeric types
    if isinstance(value, (int, float)):
        return value

    # Fallback: try to convert to string
    try:
        return str(value)
    except Exception:
        return None


def deserialize_from_sfm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize a payload from SFM response.

    Converts ISO 8601 strings back to datetime objects where appropriate.
    This is the inverse of serialize_for_sfm.

    Args:
        payload: Dictionary from SFM response.

    Returns:
        Deserialized dictionary with Python types.
    """
    if payload is None:
        return {}
    return _deserialize_value(payload)


def _deserialize_value(value: Any) -> Any:
    """Recursively deserialize a value from SFM response."""
    if value is None:
        return None

    # Handle dict
    if isinstance(value, dict):
        return {k: _deserialize_value(v) for k, v in value.items()}

    # Handle list
    if isinstance(value, list):
        return [_deserialize_value(item) for item in value]

    # Handle ISO 8601 datetime strings
    if isinstance(value, str):
        # Check if it looks like an ISO 8601 datetime
        if len(value) >= 19 and "T" in value:
            try:
                # Try parsing as ISO 8601
                dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt
            except ValueError:
                pass
        return value

    return value


def serialize_coordinate(coord: tuple) -> str:
    """Convert a coordinate tuple to comma-separated string.

    Args:
        coord: Coordinate tuple (x, y, z) or similar.

    Returns:
        Comma-separated string like "1.0,2.0,3.0"
    """
    return ",".join(str(c) for c in coord)


def deserialize_coordinate(coord_str: str) -> tuple:
    """Convert a comma-separated string to coordinate tuple.

    Args:
        coord_str: Comma-separated string like "1.0,2.0,3.0"

    Returns:
        Coordinate tuple (1.0, 2.0, 3.0)
    """
    return tuple(float(c) for c in coord_str.split(","))
