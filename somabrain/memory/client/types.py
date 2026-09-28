from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RecallHit:
    """Represents a normalized memory recall hit from the SFM service."""

    payload: dict[str, Any]
    score: float | None = None
    coordinate: tuple[float, float, float] | None = None
    raw: dict[str, Any] | None = None
