"""
Memory Service Module for SomaBrain

This module provides a high-level service layer for memory operations in SomaBrain.
It wraps the MultiTenantMemory client with additional helpers for universe scoping,
asynchronous operations, and cleaner API integration.

Key Features:
- Universe-aware memory operations
- Synchronous and asynchronous memory access
- Link management between memories
- Coordinate-based memory retrieval
- Namespace isolation through service wrapper

Operations:
- Remember: Store episodic and semantic memories
- Link: Create associations between memories
- Coordinate lookup: Convert keys to memory coordinates
- Links traversal: Navigate memory associations
- Bulk retrieval: Get multiple memories by coordinates

Integration:
- FastAPI route handlers integration
- Universe/context scoping
- Async/await support for non-blocking operations
- Error handling and graceful degradation

Classes:
    MemoryService: Main memory service wrapper

Functions:
    None (service-based implementation)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class MemoryService:
    """Thin wrapper around MultiTenantMemory client with universe helpers.

    Keeps app routes cleaner and centralizes scoping and small policies.
    """

    def __init__(self, mt_memory, namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace

    def client(self):
        return self.mt_memory.for_namespace(self.namespace)

    def remember(self, key: str, payload: dict, universe: Optional[str] = None):
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        # Perform store, then return deterministic coordinate
        res = self.client().remember(key, payload)
        try:
            return self.coord_for_key(key, universe=universe)
        except Exception:
            return res

    async def aremember(self, key: str, payload: dict, universe: Optional[str] = None):
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        client = self.client()
        mode = getattr(client, "_mode", None)
        # Only use async aremember for true HTTP mode; for local/stub call sync remember
        if mode == "http" and hasattr(client, "aremember"):
            _ = await client.aremember(key, payload)  # type: ignore[attr-defined]
        else:
            _ = client.remember(key, payload)
        try:
            return self.coord_for_key(key, universe=universe)
        except Exception:
            return None

    def link(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
    ) -> None:
        self.client().link(from_coord, to_coord, link_type=link_type, weight=weight)

    async def alink(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
    ) -> None:
        if hasattr(self.client(), "alink"):
            await self.client().alink(
                from_coord, to_coord, link_type=link_type, weight=weight
            )
        else:
            self.client().link(from_coord, to_coord, link_type=link_type, weight=weight)

    def coord_for_key(self, key: str, universe: Optional[str] = None):
        return self.client().coord_for_key(key, universe=universe)

    def links_from(
        self,
        start: Tuple[float, float, float],
        type_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        return self.client().links_from(start, type_filter=type_filter, limit=limit)

    def payloads_for_coords(
        self, coords: List[Tuple[float, float, float]], universe: Optional[str] = None
    ) -> List[dict]:
        return self.client().payloads_for_coords(coords, universe=universe)
