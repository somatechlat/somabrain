"""
HRR Context Module for SomaBrain

This module implements Hyperdimensional Representation (HRR) based context tracking
for the SomaBrain system. It maintains a dynamic context vector that represents
the current cognitive state and provides cleanup memory for robust pattern recognition.

Key Features:
- Dynamic context vector using HRR superposition
- LRU-cached anchor vectors for cleanup memory
- Novelty detection based on context similarity
- Multi-tenant context isolation
- Efficient vector operations using quantum layer

The HRR (Holographic Reduced Representations) approach allows for:
- Distributed representation of context
- Robust pattern completion and recognition
- Efficient similarity-based retrieval
- Compositional semantics through vector operations

Classes:
    HRRContextConfig: Configuration for HRR context parameters
    HRRContext: Main context tracking class with superposition and cleanup
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .quantum import QuantumLayer


@dataclass
class HRRContextConfig:
    max_anchors: int = 10000


class HRRContext:
    """Tenant-scoped HRR working context: superposed context vector + cleanup anchors.

    - context: superposition of admitted item vectors
    - anchors: limited-size dict of id->vector for cleanup/nearest neighbor
    """

    def __init__(self, q: QuantumLayer, cfg: HRRContextConfig):
        self.q = q
        self.cfg = cfg
        self.context = np.zeros((q.cfg.dim,), dtype="float32")
        self._anchors: OrderedDict[str, np.ndarray] = OrderedDict()

    def admit(self, anchor_id: str, vec: np.ndarray) -> None:
        # update context by superposition and renormalize
        self.context = self.q.superpose(self.context, vec)
        # maintain anchors as LRU capped by max_anchors
        self._anchors[anchor_id] = vec
        self._anchors.move_to_end(anchor_id)
        while len(self._anchors) > self.cfg.max_anchors:
            self._anchors.popitem(last=False)

    def novelty(self, vec: np.ndarray) -> float:
        return max(0.0, 1.0 - self.q.cosine(vec, self.context))

    def cleanup(self, query: np.ndarray) -> Tuple[str, float]:
        return self.q.cleanup(query, self._anchors)

    def stats(self) -> tuple[int, int]:
        """Return (anchor_count, max_anchors)."""
        return (len(self._anchors), int(self.cfg.max_anchors))
