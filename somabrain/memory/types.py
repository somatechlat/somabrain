"""Memory type definitions for SomaBrain.

This module contains data classes and type definitions used by the memory
client and related components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BulkStoreResult:
    """Result of a bulk store operation.

    Per Requirements F1.3-F1.5:
    - Tracks succeeded/failed counts
    - Lists coordinates of successfully stored items
    - Lists indices of failed items for retry
    - Records latency and success rate metrics
    """

    succeeded: int
    failed: int
    coordinates: List[Tuple[float, float, float]]
    failed_items: List[int] = field(default_factory=list)
    request_id: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    success_rate: float = 0.0


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