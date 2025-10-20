from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple
import numpy as np


@dataclass
class WMItem:
    vector: np.ndarray
    payload: dict


class WorkingMemory:
    def __init__(self, capacity: int, dim: int):
        self.capacity = int(capacity)
        self.dim = int(dim)
        self._items: List[WMItem] = []

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 0 or nb <= 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def admit(self, vector: np.ndarray, payload: dict) -> None:
        if vector.shape[-1] != self.dim:
            if vector.shape[-1] < self.dim:
                pad = np.zeros((self.dim - vector.shape[-1],), dtype=vector.dtype)
                vector = np.concatenate([vector, pad])
            else:
                vector = vector[: self.dim]
        self._items.append(WMItem(vector=vector.astype("float32"), payload=dict(payload)))
        if len(self._items) > self.capacity:
            self._items = self._items[-self.capacity :]

    def recall(self, query_vec: np.ndarray, top_k: int = 3) -> List[Tuple[float, dict]]:
        scored: List[Tuple[float, dict]] = []
        for it in self._items:
            s = self._cosine(query_vec, it.vector)
            scored.append((s, it.payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[: max(0, int(top_k))]

    def novelty(self, query_vec: np.ndarray) -> float:
        if not self._items:
            return 1.0
        best = 0.0
        for it in self._items:
            best = max(best, self._cosine(query_vec, it.vector))
        return max(0.0, 1.0 - best)

