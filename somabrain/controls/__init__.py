"""Lightweight stub for somabrain.controls used only for documentation builds.

This module provides simple, import-safe placeholders for symbols referenced by
autosummary. They intentionally avoid heavy dependencies and runtime behavior.
"""

from typing import Any


class Audit:
    """Placeholder Audit control for documentation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


def drift_monitor(*args: Any, **kwargs: Any) -> None:
    """Stub drift monitor function for docs."""
    return None


class Metrics:
    """Placeholder metrics collector for documentation."""

    def record(self, *args: Any, **kwargs: Any) -> None:
        return None


def middleware(handler: Any) -> Any:
    """Simple middleware wrapper stub."""

    def wrapper(*a: Any, **k: Any) -> Any:
        return handler(*a, **k)

    return wrapper


class Policy:
    """Placeholder policy object."""

    pass


class Provenance:
    """Placeholder provenance helpers."""

    def verify(self, *args: Any, **kwargs: Any) -> bool:
        return True


def reality_monitor(*args: Any, **kwargs: Any) -> None:
    """Stub reality monitor function for docs."""
    return None


# Expose module-level symbols that autosummary expects
audit = Audit
drift_monitor = drift_monitor
metrics = Metrics
middleware = middleware
policy = Policy
provenance = Provenance
reality_monitor = reality_monitor
# Controls package marker
