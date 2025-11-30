from __future__ import annotations
import abc
from typing import Iterable, List, Tuple, Optional
from .memory_client import RecallHit  # type: ignore
import asyncio

"""Abstract interface for memory back‑ends.

The original project bundled all HTTP client logic, payload handling, and
business rules into a single monolithic ``MemoryClient`` class.  To follow a
clean‑architecture approach we extract a minimal contract that any concrete
implementation (HTTP, in‑memory mock, gRPC, etc.) must satisfy.

Only the public operations required by the rest of the codebase are defined
here.  Each method returns the same types as the original ``MemoryClient``
so existing callers do not need to change.
"""


# Re‑use the existing ``RecallHit`` dataclass from the original client.
# Importing it here avoids circular imports because ``memory_client`` will
# later depend on this abstract base.


class AbstractMemoryBackend(abc.ABC):
    """Contract for a memory service backend.

    The methods correspond to the public API of the historic ``MemoryClient``.
    Implementations may be synchronous, asynchronous, or a mixture – the
    signatures stay the same; async variants are provided separately where
    needed.
    """


@abc.abstractmethod
def remember(
    self, coord_key: str, payload: dict, request_id: Optional[str] = None
) -> Tuple[float, float, float]:
    """Store a single memory and return its 3‑tuple coordinate."""


@abc.abstractmethod
def remember_bulk(
    self, items: Iterable[Tuple[str, dict]], request_id: Optional[str] = None
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
    """Retrieve memories matching *query*.

    ``universe`` is an optional scoping tag used by the service.
    """

    @abc.abstractmethod
    def link(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: Optional[str] = None,
    ) -> None:
        """Create a typed edge between two memory coordinates."""

    @abc.abstractmethod
    def unlink(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """Remove a directed edge; returns ``True`` on success."""


@abc.abstractmethod
def health(self) -> dict:
    """Return a simple health dict, e.g. ``{"http": True}``."""


# ----- Async fall‑backs -------------------------------------------------
# Concrete back‑ends that only implement the sync methods can rely on the
# default implementations below, which simply run the sync version in a
# thread pool via ``asyncio.to_thread``.  Back‑ends with a native async
# client should override these for better performance.
async def aremember(
    self, coord_key: str, payload: dict, request_id: Optional[str] = None
) -> Tuple[float, float, float]:  # pragma: no cover

    return await asyncio.to_thread(self.remember, coord_key, payload, request_id)


async def arecall(
    self,
    query: str,
    top_k: int = 3,
    universe: Optional[str] = None,
    request_id: Optional[str] = None,
) -> List[RecallHit]:  # pragma: no cover

    return await asyncio.to_thread(self.recall, query, top_k, universe, request_id)
