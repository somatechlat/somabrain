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

import asyncio
import json
import os
import time
from pathlib import Path
from threading import RLock
from collections.abc import Iterable

from somabrain.interfaces.memory import MemoryBackend
from somabrain.config import get_config
import logging

logger = logging.getLogger(__name__)

try:  # Prometheus metrics are optional in some test contexts
    from somabrain import metrics as _metrics  # type: ignore
except Exception:  # pragma: no cover - metrics not always available in tests
    _metrics = None  # type: ignore

class MemoryService:
    """Universe-aware façade around :class:`MultiTenantMemory`.

    The service keeps lightweight circuit-breaker state and exposes helpers
    for replaying the client outbox so the FastAPI layer can remain thin.
    """

    def __init__(self, mt_memory: 'MultiTenantMemory', namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace

    # Circuit breaker state shared across all service instances
    _circuit_lock: RLock = RLock()
    _outbox_lock: RLock = RLock()
    _circuit_open: bool = False
    _failure_count: int = 0
    _last_failure_time: float = 0.0
    _last_reset_attempt: float = 0.0
    _failure_threshold: int = 3
    _reset_interval: float = 60.0

    def client(self) -> MemoryBackend:
        """Return the underlying memory client for the current namespace."""
        return self.mt_memory.for_namespace(self.namespace)

    @classmethod
    def _set_circuit_metric_locked(cls) -> None:
        if _metrics is None:
            return
        gauge = getattr(_metrics, "CIRCUIT_BREAKER_STATE", None)
        if gauge is None:
            return
        try:
            gauge.set(1 if cls._circuit_open else 0)
        except Exception:
            pass

    def _mark_success(self) -> None:
        cls = self.__class__
        with cls._circuit_lock:
            cls._failure_count = 0
            cls._circuit_open = False
            cls._last_failure_time = 0.0
            cls._set_circuit_metric_locked()

    def _mark_failure(self) -> None:
        cls = self.__class__
        now = time.monotonic()
        with cls._circuit_lock:
            cls._failure_count += 1
            cls._last_failure_time = now
            if cls._failure_count >= max(1, int(cls._failure_threshold)):
                cls._circuit_open = True
            cls._set_circuit_metric_locked()
        if _metrics is not None:
            counter = getattr(_metrics, "HTTP_FAILURES", None)
            if counter is not None:
                try:
                    counter.inc()
                except Exception:
                    pass

    def _is_circuit_open(self) -> bool:
        cls = self.__class__
        with cls._circuit_lock:
            return bool(cls._circuit_open)

    @classmethod
    def _should_attempt_reset(cls) -> bool:
        if not cls._circuit_open:
            return False
        now = time.monotonic()
        if now - cls._last_failure_time < max(1.0, float(cls._reset_interval)):
            return False
        if now - cls._last_reset_attempt < 5.0:
            return False
        cls._last_reset_attempt = now
        return True

    def _update_outbox_metric(self, pending: int) -> None:
        if _metrics is None:
            return
        gauge = getattr(_metrics, "MEMORY_OUTBOX_PENDING_ITEMS", None)
        if gauge is None:
            return
        try:
            gauge.set(max(0, int(pending)))
        except Exception:
            pass

    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Stores a memory payload. In V3, this fails fast if the remote is down."""
        if universe and "universe" not in payload:
            payload["universe"] = universe
        
        if self._is_circuit_open():
            self._journal_failure(
                "remember",
                {"key": key, "payload": payload, "universe": universe, "queued": True},
            )
            raise RuntimeError("Memory circuit breaker open; operation journaled.")

        try:
            result = self.client().remember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            logger.warning(f"Memory operation 'remember' failed for key '{key}'. Journaling.")
            self._journal_failure("remember", {"key": key, "payload": payload, "universe": universe})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Async version of remember."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        if self._is_circuit_open():
            self._journal_failure(
                "remember",
                {"key": key, "payload": payload, "universe": universe, "queued": True},
            )
            raise RuntimeError("Memory circuit breaker open; operation journaled.")

        try:
            result = await self.client().aremember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            logger.warning(f"Async memory operation 'aremember' failed for key '{key}'. Journaling.")
            self._journal_failure("remember", {"key": key, "payload": payload, "universe": universe})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        """Store multiple memory payloads in a single operation."""

        prepared: list[tuple[str, dict]] = []
        journal_payload: list[dict] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))
            journal_payload.append({"key": key, "payload": body})

        if not prepared:
            return []

        if self._is_circuit_open():
            self._journal_failure(
                "remember_bulk",
                {"items": journal_payload, "universe": universe, "queued": True},
            )
            raise RuntimeError("Memory circuit breaker open; operation journaled.")

        try:
            coords = await self.client().aremember_bulk(prepared)
            self._mark_success()
            return list(coords)
        except Exception as e:
            self._mark_failure()
            logger.warning("Async memory operation 'aremember_bulk' failed. Journaling.")
            self._journal_failure(
                "remember_bulk",
                {"items": journal_payload, "universe": universe},
            )
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    def link(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Creates a link between memories. Fails fast and journals on error."""
        if self._is_circuit_open():
            self._journal_failure(
                "link",
                {
                    "from_coord": from_coord,
                    "to_coord": to_coord,
                    "link_type": link_type,
                    "weight": weight,
                    "queued": True,
                },
            )
            raise RuntimeError("Memory circuit breaker open; operation journaled.")
        try:
            result = self.client().link(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            logger.warning("Memory operation 'link' failed. Journaling.")
            self._journal_failure("link", {"from_coord": from_coord, "to_coord": to_coord, "link_type": link_type, "weight": weight})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    async def alink(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Async version of link."""
        if self._is_circuit_open():
            self._journal_failure(
                "link",
                {
                    "from_coord": from_coord,
                    "to_coord": to_coord,
                    "link_type": link_type,
                    "weight": weight,
                    "queued": True,
                },
            )
            raise RuntimeError("Memory circuit breaker open; operation journaled.")
        try:
            result = await self.client().alink(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            logger.warning("Async memory operation 'alink' failed. Journaling.")
            self._journal_failure("link", {"from_coord": from_coord, "to_coord": to_coord, "link_type": link_type, "weight": weight})
            raise RuntimeError("Memory service unavailable; operation journaled.") from e

    def _journal_failure(self, op: str, data: dict):
        """Writes a failed operation to the journal for the sync worker to pick up."""
        try:
            from somabrain import journal
            journal_dir = getattr(get_config(), "journal_dir", "./data/somabrain")
            event_type = "mem" if op == "remember" else op
            event = {"op": op, "type": event_type, **data}
            journal.append_event(journal_dir, self.namespace, event)
        except Exception:
            logger.exception("Failed to write to journal. Memory operation may be lost.")

    def _health_check(self) -> bool:
        try:
            health = self.client().health()
        except Exception:
            return False
        if isinstance(health, dict):
            if "http" in health:
                return bool(health.get("http"))
            return bool(health.get("ok"))
        return False

    def _reset_circuit_if_needed(self) -> bool:
        """Attempt to close the circuit breaker if enough time has elapsed."""
        if not self._is_circuit_open():
            return False
        cls = self.__class__
        if not cls._should_attempt_reset():
            return False
        healthy = self._health_check()
        if healthy:
            with cls._circuit_lock:
                cls._circuit_open = False
                cls._failure_count = 0
                cls._last_failure_time = 0.0
                cls._set_circuit_metric_locked()
            return True
        with cls._circuit_lock:
            cls._last_failure_time = time.monotonic()
        return False

    async def _process_outbox(self) -> int:
        """Replay queued outbox entries for this namespace in the background."""
        if hasattr(asyncio, "to_thread"):
            return await asyncio.to_thread(self._process_outbox_sync)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._process_outbox_sync)

    def _process_outbox_sync(self) -> int:
        client = self.client()
        path_str = getattr(client, "_outbox_path", None)
        if not path_str:
            self._update_outbox_metric(0)
            return 0
        path = Path(path_str)
        if not path.exists():
            self._update_outbox_metric(0)
            return 0
        tmp_path = path.with_suffix(path.suffix + ".processing")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        try:
            path.rename(tmp_path)
        except FileNotFoundError:
            self._update_outbox_metric(0)
            return 0
        except OSError:
            # Another process may be touching the file; skip this cycle.
            self._update_outbox_metric(0)
            return 0

        processed = 0
        remaining: list[dict] = []
        try:
            with tmp_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    try:
                        success = self._handle_outbox_entry(client, entry)
                    except Exception:
                        success = False
                        self._mark_failure()
                        remaining.append(entry)
                    else:
                        if success:
                            processed += 1
                            self._mark_success()
                        else:
                            remaining.append(entry)
        finally:
            writeback_ok = False
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if remaining:
                    with path.open("a", encoding="utf-8") as handle:
                        for entry in remaining:
                            json.dump(entry, handle)
                            handle.write("\n")
                else:
                    path.touch(exist_ok=True)
                writeback_ok = True
            except Exception:
                writeback_ok = False
            finally:
                if writeback_ok:
                    try:
                        tmp_path.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    try:
                        if tmp_path.exists():
                            tmp_path.rename(path)
                    except Exception:
                        pass

        self._update_outbox_metric(len(remaining))
        return processed

    def _handle_outbox_entry(self, client, entry: dict) -> bool:
        op = str(entry.get("op") or "").strip().lower()
        payload_obj = entry.get("payload")
        payload = payload_obj if isinstance(payload_obj, dict) else {}
        try:
            if op in {"remember", "aremember", "store"}:
                coord_key = payload.get("coord_key") or payload.get("key")
                if not coord_key:
                    inner = payload.get("payload") or {}
                    coord_key = inner.get("task") or inner.get("id") or os.urandom(4).hex()
                body = payload.get("payload") or payload
                client.remember(coord_key, body)
                return True
            if op in {"remember_bulk", "aremember_bulk"}:
                items_data = payload.get("items") if isinstance(payload, dict) else None
                if not items_data:
                    return False
                items = []
                for item in items_data:
                    if not isinstance(item, dict):
                        continue
                    coord_key = item.get("coord_key") or item.get("key")
                    if not coord_key:
                        inner = item.get("payload") or {}
                        coord_key = inner.get("task") or os.urandom(4).hex()
                    items.append((coord_key, item.get("payload") or {}))
                if not items:
                    return False
                client.remember_bulk(items, request_id=payload.get("request_id"))
                return True
            if op in {"link", "alink"}:
                from_coord = payload.get("from_coord") or payload.get("from")
                to_coord = payload.get("to_coord") or payload.get("to")
                if from_coord is None or to_coord is None:
                    return False
                link_type = payload.get("link_type", "related")
                weight = payload.get("weight", 1.0)
                client.link(from_coord, to_coord, link_type, weight)
                return True
        except Exception as exc:
            logger.debug("Failed to replay outbox entry '%s': %r", op or "?", exc)
            raise
        return False

    def coord_for_key(self, key: str, universe: str | None = None):
        return self.client().coord_for_key(key, universe)

    def payloads_for_coords(self, coords, universe: str | None = None):
        return self.client().payloads_for_coords(coords, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return self.client().links_from(start, type_filter, limit)
