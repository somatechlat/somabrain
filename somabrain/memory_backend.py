"""Abstract interface for memory backends.

The original project bundled all HTTP client logic, payload handling, and
business rules into a single monolithic MemoryClient class. To follow a
clean-architecture approach we extract a minimal contract that any concrete
implementation (HTTP, gRPC, etc.) must satisfy.

Only the public operations required by the rest of the codebase are defined
here. Each method returns the same types as the original MemoryClient
so existing callers do not need to change.
"""

from __future__ import annotations

import abc
import asyncio
from typing import Iterable, List, Optional, Tuple

from .memory_client import RecallHit


class AbstractMemoryBackend(abc.ABC):
    """Contract for a memory service backend.

    The methods correspond to the public API of the historic MemoryClient.
    Implementations may be synchronous, asynchronous, or a mixture - the
    signatures stay the same; async variants are provided separately where
    needed.
    """

    @abc.abstractmethod
    def remember(
        self,
        coord_key: str,
        payload: dict,
        request_id: Optional[str] = None,
    ) -> Tuple[float, float, float]:
        """Store a single memory and return its 3-tuple coordinate."""

    @abc.abstractmethod
    def remember_bulk(
        self,
        items: Iterable[Tuple[str, dict]],
        request_id: Optional[str] = None,
    ) -> List[Tuple[float, float, float]]:
        """Store many memories in one call and return a list of coordinates."""

    @abc.abstractmethod
    def recall(
        self,
        query: str,
        top_k: int = 3,
        universe: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[RecallHit]:
        """Retrieve memories matching query.

        Args:
            query: The search query string.
            top_k: Maximum number of results to return.
            universe: Optional scoping tag used by the service.
            request_id: Optional request identifier for tracing.

        Returns:
            List of RecallHit objects matching the query.
        """

    @abc.abstractmethod
    def fetch_by_coord(
        self,
        coord: Tuple[float, float, float],
        universe: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[dict]:
        """Return payloads stored at *coord* (GET /memories/{coord})."""

    @abc.abstractmethod
    def delete(
        self,
        coord: Tuple[float, float, float],
        universe: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """Delete a memory coordinate via DELETE /memories/{coord}."""

    @abc.abstractmethod
    def coord_for_key(self, key: str, universe: Optional[str] = None) -> Tuple[float, float, float]:
        """Return the deterministic coordinate associated with *key*."""

    @abc.abstractmethod
    def health(self) -> dict:
        """Return readiness information (e.g. {"healthy": True})."""

    async def aremember(
        self,
        coord_key: str,
        payload: dict,
        request_id: Optional[str] = None,
    ) -> Tuple[float, float, float]:
        """Async wrapper for remember method.

        Concrete backends that only implement the sync methods can rely on
        this default implementation which runs the sync version in a thread
        pool via asyncio.to_thread. Backends with a native async client
        should override this for better performance.
        """
        return await asyncio.to_thread(self.remember, coord_key, payload, request_id)

    async def arecall(
        self,
        query: str,
        top_k: int = 3,
        universe: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[RecallHit]:
        """Async wrapper for recall method.

        Concrete backends that only implement the sync methods can rely on
        this default implementation which runs the sync version in a thread
        pool via asyncio.to_thread. Backends with a native async client
        should override this for better performance.
        """
        return await asyncio.to_thread(self.recall, query, top_k, universe, request_id)
