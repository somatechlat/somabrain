"""Typed interface for memory backends used by the brain.

This small Protocol defines the methods expected from a real
HTTP-backed memory client. Introducing this Protocol makes subsequent
refactors incremental and type-checkable without changing runtime
behavior.
"""

from __future__ import annotations

from typing import Protocol, Optional, List, Tuple, Any

Coordinate = Tuple[float, float, float]


class MemoryBackend(Protocol):
    """Protocol describing the minimal memory client surface.

    Methods are intentionally permissive (return types are left as Any for the
    first refactor pass) so callers can be migrated gradually.
    """

    def remember(self, key: str, payload: dict, *args, **kwargs) -> Any: ...

    async def aremember(self, key: str, payload: dict, *args, **kwargs) -> Any: ...

    def link(
        self,
        from_coord: Coordinate,
        to_coord: Coordinate,
        link_type: str = "related",
        weight: float = 1.0,
    ) -> None: ...

    async def alink(
        self,
        from_coord: Coordinate,
        to_coord: Coordinate,
        link_type: str = "related",
        weight: float = 1.0,
    ) -> None: ...

    def coord_for_key(self, key: str, universe: Optional[str] = None) -> Coordinate: ...

    def payloads_for_coords(
        self, coords: List[Coordinate], universe: Optional[str] = None
    ) -> List[dict]: ...

    def delete(self, coordinate: Coordinate) -> Any: ...

    def links_from(
        self, start: Coordinate, type_filter: Optional[str] = None, limit: int = 50
    ) -> List[dict]: ...
