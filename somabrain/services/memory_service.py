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
- Delete: Remove a memory at a given coordinate

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

from somabrain.interfaces.memory import MemoryBackend
from somabrain.config import get_config
import logging

logger = logging.getLogger(__name__)

class MemoryService:
    """
    V3: A simplified, stateless wrapper around the MultiTenantMemory client.
    It no longer manages circuit breaking or an outbox; this is now handled
    by the MemorySyncWorker and the journaling system. Its primary role is
    to provide a clean, universe-aware interface to the memory client.
    """

    def __init__(self, mt_memory: 'MultiTenantMemory', namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace

    def client(self) -> MemoryBackend:
        """Return the underlying memory client for the current namespace."""
        return self.mt_memory.for_namespace(self.namespace)

    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Stores a memory payload. In V3, this fails fast if the remote is down."""
        if universe and "universe" not in payload:
            payload["universe"] = universe
        
        try:
            return self.client().remember(key, payload)
        except Exception as e:
            logger.warning(f"Memory operation 'remember' failed for key '{key}'. Journaling.")
            self._journal_failure("remember", {"key": key, "payload": payload, "universe": universe})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Async version of remember."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        try:
            return await self.client().aremember(key, payload)
        except Exception as e:
            logger.warning(f"Async memory operation 'aremember' failed for key '{key}'. Journaling.")
            self._journal_failure("remember", {"key": key, "payload": payload, "universe": universe})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    def link(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Creates a link between memories. Fails fast and journals on error."""
        try:
            return self.client().link(from_coord, to_coord, link_type, weight)
        except Exception as e:
            logger.warning("Memory operation 'link' failed. Journaling.")
            self._journal_failure("link", {"from_coord": from_coord, "to_coord": to_coord, "link_type": link_type, "weight": weight})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    async def alink(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Async version of link."""
        try:
            return await self.client().alink(from_coord, to_coord, link_type, weight)
        except Exception as e:
            logger.warning("Async memory operation 'alink' failed. Journaling.")
            self._journal_failure("link", {"from_coord": from_coord, "to_coord": to_coord, "link_type": link_type, "weight": weight})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    def _journal_failure(self, op: str, data: dict):
        """Writes a failed operation to the journal for the sync worker to pick up."""
        try:
            from somabrain import journal
            journal_dir = getattr(get_config(), "journal_dir", "./data/somabrain")
            event = {"op": op, **data}
            journal.append_event(journal_dir, self.namespace, event)
        except Exception:
            logger.exception("Failed to write to journal. Memory operation may be lost.")

    def coord_for_key(self, key: str, universe: str | None = None):
        return self.client().coord_for_key(key, universe)

    def payloads_for_coords(self, coords, universe: str | None = None):
        return self.client().payloads_for_coords(coords, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return self.client().links_from(start, type_filter, limit)
