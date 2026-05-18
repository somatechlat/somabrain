"""Runtime configuration helpers for hot-path lookups.

Several learning and persistence modules read lightweight knobs at runtime.
Those call sites expect a small module-level API instead of importing Django
settings directly so they can keep a consistent fallback order:

1. Explicit Django settings attributes.
2. Environment variables using the raw, upper-case, or ``SOMABRAIN_*`` names.
3. Caller-provided defaults.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional during early imports
    settings = None

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _candidate_names(key: str) -> tuple[str, ...]:
    base = str(key or "").strip()
    upper = base.upper()
    return (
        base,
        upper,
        f"SOMABRAIN_{upper}",
        f"SOMA_{upper}",
    )


def _read_raw(key: str) -> Any | None:
    for name in _candidate_names(key):
        if settings is not None and hasattr(settings, name):
            value = getattr(settings, name)
            if value not in (None, ""):
                return value
    for name in _candidate_names(key):
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return None


def get_str(key: str, default: str = "") -> str:
    """Return a runtime string knob."""
    value = _read_raw(key)
    if value is None:
        return default
    return str(value)


def get_float(key: str, default: float = 0.0) -> float:
    """Return a runtime float knob."""
    value = _read_raw(key)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def get_int(key: str, default: int = 0) -> int:
    """Return a runtime integer knob."""
    value = _read_raw(key)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def get_bool(key: str, default: bool = False) -> bool:
    """Return a runtime boolean knob."""
    value = _read_raw(key)
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return bool(default)
