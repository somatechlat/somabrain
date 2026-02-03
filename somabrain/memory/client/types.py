from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional

@dataclass
class RecallHit:
    """Represents a normalized memory recall hit from the SFM service."""
    payload: Dict[str, Any]
    score: float | None = None
    coordinate: Tuple[float, float, float] | None = None
    raw: Dict[str, Any] | None = None
