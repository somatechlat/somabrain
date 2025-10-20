from __future__ import annotations

from typing import Optional, List, Tuple, Dict


class MemoryService:
    """Thin wrapper around MultiTenantMemory client with universe helpers.

    Keeps app routes cleaner and centralizes scoping and small policies.
    """

    def __init__(self, mt_memory, namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace

    def client(self):
        return self.mt_memory.for_namespace(self.namespace)

    def remember(self, key: str, payload: dict, universe: Optional[str] = None) -> None:
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        self.client().remember(key, payload)

    async def aremember(self, key: str, payload: dict, universe: Optional[str] = None) -> None:
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        if hasattr(self.client(), 'aremember'):
            await self.client().aremember(key, payload)
        else:
            self.client().remember(key, payload)

    def link(self, from_coord: Tuple[float, float, float], to_coord: Tuple[float, float, float], link_type: str = "related", weight: float = 1.0) -> None:
        self.client().link(from_coord, to_coord, link_type=link_type, weight=weight)

    async def alink(self, from_coord: Tuple[float, float, float], to_coord: Tuple[float, float, float], link_type: str = "related", weight: float = 1.0) -> None:
        if hasattr(self.client(), 'alink'):
            await self.client().alink(from_coord, to_coord, link_type=link_type, weight=weight)
        else:
            self.client().link(from_coord, to_coord, link_type=link_type, weight=weight)

    def coord_for_key(self, key: str, universe: Optional[str] = None):
        return self.client().coord_for_key(key, universe=universe)

    def links_from(self, start: Tuple[float, float, float], type_filter: Optional[str] = None, limit: int = 50) -> List[Dict]:
        return self.client().links_from(start, type_filter=type_filter, limit=limit)

    def payloads_for_coords(self, coords: List[Tuple[float, float, float]], universe: Optional[str] = None) -> List[dict]:
        return self.client().payloads_for_coords(coords, universe=universe)

