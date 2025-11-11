"""Lightweight adapter to use the canonical MemoryClient for context building.

Provides a minimal interface with `search_text` (and a disabled `search` that
fails fast) so existing
ContextBuilder code can consume results without knowing about MemoryClient details.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from somabrain.config import get_config
from somabrain.memory_client import MemoryClient


class MemoryRecallClient:
    """Adapter exposing a MemoryClient-compatible interface for context building.

    Methods:
        - search_text(query, top_k=10, filters=None) -> List[Dict]
        - search(embedding, top_k=10) -> List[Dict] (not implemented; fails fast)
    """

    def __init__(self, namespace: Optional[str] = None) -> None:
        cfg = get_config()
        if namespace:
            try:
                cfg.namespace = namespace
            except Exception:
                pass
        self._client = MemoryClient(cfg=cfg)

    def search_text(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        hits = self._client.recall_with_scores(query=query, top_k=int(top_k))
        results: List[Dict[str, Any]] = []
        tenant = None
        if isinstance(filters, dict):
            tenant = filters.get("tenant")
        for i, hit in enumerate(hits):
            payload = hit.payload if isinstance(hit.payload, dict) else {}
            if tenant and payload.get("tenant") not in (tenant, None):
                # honor tenant filter when present
                continue
            score = hit.score if isinstance(hit.score, (int, float)) else 0.0
            coord = payload.get("coordinate") or payload.get("coord") or None
            results.append(
                {
                    "id": coord or f"mem-{i}",
                    "score": float(score) if score is not None else 0.0,
                    "metadata": payload,
                    # embedding optional; MemoryClient does not return embeddings
                    "embedding": None,
                }
            )
        return results

    def search(self, embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        # Legacy vector-search path is not supported via MemoryClient.
        # ContextBuilder will catch exceptions and gracefully return [].
        raise NotImplementedError("Vector search not supported; use search_text")
