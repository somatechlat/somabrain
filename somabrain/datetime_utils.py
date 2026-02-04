"""
Datetime utilities for SomaBrain.

Provides standardized functions for handling timestamps and conversions.
"""

from __future__ import annotations

import datetime
from typing import Union


def coerce_to_epoch_seconds(value: Union[datetime.datetime, float, int, str, None]) -> float:
    """
    Coerce a value to epoch seconds (float).

    Handles:
    - datetime objects (converted using .timestamp())
    - int/float (assumed to be already seconds)
    - None (returns 0.0)
    - str (tries to parse ISO format if possible, else 0.0)
    """
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, datetime.datetime):
        # Ensure we have timezone info if possible, usually assume UTC if naive
        if value.tzinfo is None:
             value = value.replace(tzinfo=datetime.timezone.utc)
        return value.timestamp()

    if isinstance(value, str):
        try:
            dt = datetime.datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.timestamp()
        except ValueError:
            pass

    return 0.0
