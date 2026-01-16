"""Typed interface for memory backends used by the brain.

This small Protocol defines the methods expected from a real
HTTP-backed memory client. Introducing this Protocol makes subsequent
refactors incremental and type-checkable without changing runtime
behavior.
"""

from __future__ import annotations

from typing import Protocol, Optional, Tuple, Any, List

Coordinate = Tuple[float, float, float]


class MemoryBackend(Protocol):
    """Protocol describing the minimal memory client surface.

    Methods are intentionally permissive (return types are left as Any for the
    first refactor pass) so callers can be migrated gradually.
    """

    def remember(self, key: str, payload: dict, *args, **kwargs) -> Any:
        """Execute remember.

        Args:
            key: The key.
            payload: The payload.
        """
        ...

    async def aremember(self, key: str, payload: dict, *args, **kwargs) -> Any:
        """Execute aremember.

        Args:
            key: The key.
            payload: The payload.
        """
        ...

    def recall(self, query: str, *args, **kwargs) -> List[Any]:
        """Execute recall.

        Args:
            query: The query.
        """
        ...

    async def arecall(self, query: str, *args, **kwargs) -> List[Any]:
        """Execute arecall.

        Args:
            query: The query.
        """
        ...

    def coord_for_key(self, key: str, universe: Optional[str] = None) -> Coordinate:
        """Execute coord for key.

        Args:
            key: The key.
            universe: The universe.
        """
        ...

    def fetch_by_coord(
        self, coord: Coordinate, universe: Optional[str] = None
    ) -> List[Any]:
        """Execute fetch by coord.

        Args:
            coord: The coord.
            universe: The universe.
        """
        ...

    def delete(self, coordinate: Coordinate) -> Any:
        """Execute delete.

        Args:
            coordinate: The coordinate.
        """
        ...

    def health(self) -> dict:
        """Execute health."""
        ...
