"""Working Memory Persistence for SomaBrain.

Per Requirements A1.1-A1.5:
- Persists WM items to SFM with memory_type="working_memory"
- Restores WM state on SB startup within 5 seconds
- Async persistence within 1 second (eventual consistency)
- Marks evicted items as evicted (not deleted) for audit
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from somabrain.memory_client import MemoryClient
    from somabrain.wm import WMItem, WorkingMemory

logger = logging.getLogger(__name__)


@dataclass
class WMPersistenceEntry:
    """Persisted WM item in SFM.

    Per Requirement A1.1: WM items are serialized with memory_type="working_memory"
    """

    tenant_id: str
    item_id: str
    vector: List[float]
    payload: Dict[str, Any]
    tick: int
    admitted_at: float
    cleanup_overlap: float
    memory_type: str = "working_memory"
    evicted: bool = False
    evicted_at: Optional[float] = None


class WMPersister:
    """Persists WM items to SFM asynchronously.

    Per Requirements A1.1-A1.5:
    - A1.1: Serializes WM items to SFM with memory_type="working_memory"
    - A1.3: Async persistence within 1 second (eventual consistency)
    - A1.4: Marks evicted items as evicted (not deleted)
    """

    def __init__(
        self,
        memory_client: "MemoryClient",
        tenant_id: str = "default",
        queue_size: int = 1000,
        flush_interval_ms: int = 100,
    ):
        """Initialize WMPersister.

        Args:
            memory_client: MemoryClient for SFM communication.
            tenant_id: Tenant ID for isolation.
            queue_size: Max items in persistence queue.
            flush_interval_ms: How often to flush queue to SFM.
        """
        self._client = memory_client
        self._tenant_id = tenant_id
        self._queue: asyncio.Queue[WMPersistenceEntry] = asyncio.Queue(
            maxsize=queue_size
        )
        self._flush_interval = flush_interval_ms / 1000.0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._item_counter = 0

    def _generate_item_id(self, tick: int) -> str:
        """Generate unique item ID for WM entry."""
        self._item_counter += 1
        return f"wm_{self._tenant_id}_{tick}_{self._item_counter}_{int(time.time() * 1000)}"

    async def start(self) -> None:
        """Start the background persistence task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
        logger.info("WMPersister started", tenant=self._tenant_id)

    async def stop(self) -> None:
        """Stop the background persistence task and flush remaining items."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Flush any remaining items
        await self._flush_queue()
        logger.info("WMPersister stopped", tenant=self._tenant_id)

    async def queue_persist(self, item: "WMItem") -> str:
        """Queue a WM item for persistence.

        Per Requirement A1.3: Async persistence within 1 second.

        Args:
            item: WMItem to persist.

        Returns:
            Generated item_id for tracking.
        """
        item_id = self._generate_item_id(item.tick)
        entry = WMPersistenceEntry(
            tenant_id=self._tenant_id,
            item_id=item_id,
            vector=item.vector.tolist(),
            payload=item.payload,
            tick=item.tick,
            admitted_at=item.admitted_at,
            cleanup_overlap=item.cleanup_overlap,
            memory_type="working_memory",
            evicted=False,
            evicted_at=None,
        )
        try:
            self._queue.put_nowait(entry)
        except asyncio.QueueFull:
            logger.warning("WM persistence queue full, dropping oldest")
            # Drop oldest and add new
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(entry)
        return item_id

    async def mark_evicted(self, item_id: str) -> bool:
        """Mark a WM item as evicted in SFM.

        Per Requirement A1.4: Evicted items are marked, not deleted.

        Args:
            item_id: ID of the item to mark as evicted.

        Returns:
            True if successfully marked.
        """
        try:
            # Store eviction marker
            eviction_payload = {
                "item_id": item_id,
                "tenant_id": self._tenant_id,
                "evicted": True,
                "evicted_at": time.time(),
                "memory_type": "working_memory_eviction",
            }
            coord_key = f"wm_eviction:{item_id}"
            await self._client.aremember(coord_key, eviction_payload)
            logger.debug("Marked WM item as evicted", item_id=item_id)
            return True
        except Exception as exc:
            logger.error(
                "Failed to mark WM item as evicted", item_id=item_id, error=str(exc)
            )
            return False

    async def _flush_loop(self) -> None:
        """Background loop that flushes queue to SFM."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_queue()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("WM persistence flush error", error=str(exc))

    async def _flush_queue(self) -> int:
        """Flush all queued items to SFM.

        Returns:
            Number of items flushed.
        """
        flushed = 0
        batch: List[WMPersistenceEntry] = []

        # Drain queue
        while not self._queue.empty():
            try:
                entry = self._queue.get_nowait()
                batch.append(entry)
            except asyncio.QueueEmpty:
                break

        if not batch:
            return 0

        # Persist each item
        for entry in batch:
            try:
                payload = {
                    "item_id": entry.item_id,
                    "tenant_id": entry.tenant_id,
                    "vector": entry.vector,
                    "payload": entry.payload,
                    "tick": entry.tick,
                    "admitted_at": entry.admitted_at,
                    "cleanup_overlap": entry.cleanup_overlap,
                    "memory_type": entry.memory_type,
                    "evicted": entry.evicted,
                }
                coord_key = f"wm:{entry.item_id}"
                await self._client.aremember(coord_key, payload)
                flushed += 1
            except Exception as exc:
                logger.error(
                    "Failed to persist WM item", item_id=entry.item_id, error=str(exc)
                )

        if flushed > 0:
            logger.debug(
                "Flushed WM items to SFM", count=flushed, tenant=self._tenant_id
            )

        return flushed


class WMRestorer:
    """Restores WM state from SFM on startup.

    Per Requirement A1.2: Restores WM state within 5 seconds.
    """

    def __init__(
        self,
        memory_client: "MemoryClient",
        tenant_id: str = "default",
        timeout_s: float = 5.0,
    ):
        """Initialize WMRestorer.

        Args:
            memory_client: MemoryClient for SFM communication.
            tenant_id: Tenant ID for isolation.
            timeout_s: Max time for restoration (default 5s per A1.2).
        """
        self._client = memory_client
        self._tenant_id = tenant_id
        self._timeout = timeout_s

    async def restore(self, wm: "WorkingMemory") -> int:
        """Restore WM state from SFM.

        Per Requirement A1.2: Restores within 5 seconds.
        Per Requirement A1.7: Filters by evicted=false.

        Args:
            wm: WorkingMemory instance to restore into.

        Returns:
            Number of items restored.
        """
        import numpy as np

        start_time = time.time()
        restored = 0

        try:
            # Query SFM for non-evicted WM items for this tenant
            # Use hybrid recall with memory_type filter
            query = f"memory_type:working_memory tenant_id:{self._tenant_id}"

            async with asyncio.timeout(self._timeout):
                results = await self._client.arecall(
                    query,
                    top_k=wm.capacity * 2,  # Over-fetch to account for evicted items
                )

            # Filter and restore non-evicted items
            for score, payload in results:
                # Check timeout
                if time.time() - start_time > self._timeout:
                    logger.warning("WM restoration timeout", restored=restored)
                    break

                # Skip evicted items (A1.7)
                if payload.get("evicted", False):
                    continue

                # Skip items from other tenants
                if payload.get("tenant_id") != self._tenant_id:
                    continue

                # Skip non-WM items
                if payload.get("memory_type") != "working_memory":
                    continue

                # Restore item
                try:
                    vector_data = payload.get("vector", [])
                    if isinstance(vector_data, list):
                        vector = np.array(vector_data, dtype=np.float32)
                    else:
                        continue

                    item_payload = payload.get("payload", {})
                    cleanup_overlap = float(payload.get("cleanup_overlap", 0.0))

                    wm.admit(vector, item_payload, cleanup_overlap=cleanup_overlap)
                    restored += 1

                except Exception as exc:
                    logger.warning("Failed to restore WM item", error=str(exc))
                    continue

            elapsed = time.time() - start_time
            logger.info(
                "WM restoration complete",
                tenant=self._tenant_id,
                restored=restored,
                elapsed_s=elapsed,
            )

        except asyncio.TimeoutError:
            logger.warning(
                "WM restoration timed out",
                tenant=self._tenant_id,
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.error(
                "WM restoration failed", tenant=self._tenant_id, error=str(exc)
            )

        return restored


# Global persister instances per tenant
_persisters: Dict[str, WMPersister] = {}


def get_wm_persister(
    memory_client: "MemoryClient",
    tenant_id: str = "default",
) -> WMPersister:
    """Get or create WMPersister for tenant."""
    if tenant_id not in _persisters:
        _persisters[tenant_id] = WMPersister(memory_client, tenant_id)
    return _persisters[tenant_id]


async def restore_wm_state(
    wm: "WorkingMemory",
    memory_client: "MemoryClient",
    tenant_id: str = "default",
) -> int:
    """Convenience function to restore WM state.

    Args:
        wm: WorkingMemory to restore into.
        memory_client: MemoryClient for SFM communication.
        tenant_id: Tenant ID.

    Returns:
        Number of items restored.
    """
    restorer = WMRestorer(memory_client, tenant_id)
    return await restorer.restore(wm)
