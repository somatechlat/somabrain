"""Adaptation engine package.

``utils`` (clamp / weight_delta) and ``types`` (RetrievalWeights) are pure and
import without Django.  ``AdaptationEngine`` is loaded lazily so those helpers
stay usable from Django-free property tests.
"""

from __future__ import annotations

from typing import Any

from .types import RetrievalWeights
from .utils import clamp, weight_delta

__all__ = ["AdaptationEngine", "RetrievalWeights", "clamp", "weight_delta"]


def __getattr__(name: str) -> Any:
    if name == "AdaptationEngine":
        from .engine import AdaptationEngine

        globals()[name] = AdaptationEngine
        return AdaptationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
