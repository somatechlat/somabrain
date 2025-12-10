"""Memory type definitions for SomaBrain.

This module contains data classes and type definitions used by the memory
client and related components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class RecallHit:
    """Represents a normalized memory recall hit from the SFM service.

    Attributes:
        payload: The memory payload dictionary containing the stored data.
        score: Optional similarity/relevance score from the recall operation.
        coordinate: Optional 3D coordinate tuple (x, y, z) in [-1, 1]^3.
        raw: Optional raw response data from the memory service.
    """

    payload: Dict[str, Any]
    score: float | None = None
    coordinate: Tuple[float, float, float] | None = None
    raw: Dict[str, Any] | None = None
