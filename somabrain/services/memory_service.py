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

import json
import os
import time
from typing import Dict, List, Optional, Tuple

from somabrain.config import load_config

# Load configuration for outbox path
_cfg = load_config()
_OUTBOX_PATH = getattr(_cfg, "outbox_path", "./data/somabrain/outbox.jsonl")


class MemoryService:
    """Thin wrapper around MultiTenantMemory client with universe helpers.

    Keeps app routes cleaner and centralizes scoping and small policies.
    """

    # Circuit breaker configuration
    _circuit_open: bool = False
    _failure_count: int = 0
    _failure_threshold: int = 3  # failures before opening circuit
    _reset_interval: int = 60  # seconds to attempt reset after opening
    _last_failure_time: float = 0.0

    def __init__(self, mt_memory, namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace
        # Ensure outbox file exists
        os.makedirs(os.path.dirname(_OUTBOX_PATH), exist_ok=True)
        if not os.path.isfile(_OUTBOX_PATH):
            open(_OUTBOX_PATH, "a").close()

    def _record_failure(self):
        """Record a failure and open circuit if threshold exceeded."""
        self.__class__._failure_count += 1
        self.__class__._last_failure_time = time.time()
        if self.__class__._failure_count >= self.__class__._failure_threshold:
            self.__class__._circuit_open = True
        # Increment Prometheus failure counter
        try:
            from .. import metrics as _mx

            _mx.HTTP_FAILURES.inc()
        except Exception:
            pass

    def _reset_circuit_if_needed(self):
        """Reset circuit after the reset interval has passed."""
        if self.__class__._circuit_open:
            # Attempt a simple health check immediately; if it succeeds, close circuit
            try:
                self._health_check()
            except Exception:
                # Still failing; keep circuit open and update timestamp
                self.__class__._last_failure_time = time.time()
                # Update circuit state gauge
                try:
                    from .. import metrics as _mx

                    _mx.CIRCUIT_STATE.set(1)
                except Exception:
                    pass
                return
            # Health check succeeded – reset circuit state
            self.__class__._circuit_open = False
            self.__class__._failure_count = 0
            # Update circuit state gauge
            try:
                from .. import metrics as _mx

                _mx.CIRCUIT_STATE.set(0)
            except Exception:
                pass

    def _health_check(self):
        """Perform a lightweight operation to verify backend health.
        Uses a dummy remember/delete cycle which is safe for any backend.
        """
        dummy_key = "__healthcheck__"
        dummy_payload = {"health": True}
        try:
            # Attempt to remember then delete; ignore results
            self.client().remember(dummy_key, dummy_payload)
            # Some backends may not implement delete; ignore if absent
            try:
                self.client().delete(self.client().coord_for_key(dummy_key))
            except Exception:
                pass
        except Exception as e:
            raise e

    def client(self):
        return self.mt_memory.for_namespace(self.namespace)

    def _write_outbox(self, entry: dict):
        """Append a JSON line to the outbox for later retry.
        Entry should contain at least a ``op`` field (e.g., ``remember``) and the
        arguments required to replay the operation.
        """
        # Ensure namespace is recorded for replay
        entry = dict(entry)  # copy to avoid mutating caller
        entry.setdefault("namespace", self.namespace)
        # Add timestamp and a simple unique identifier for debugging / deduplication
        entry.setdefault("ts", time.time())
        # Use a short UUID for uniqueness (no external import needed beyond uuid)
        try:
            import uuid

            entry.setdefault("uid", str(uuid.uuid4()))
        except Exception:
            pass
        with open(_OUTBOX_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        # Increment outbox pending gauge
        try:
            from .. import metrics as _mx

            _mx.OUTBOX_PENDING.inc()
        except Exception:
            pass

    async def _process_outbox(self):
        """Read pending outbox entries and attempt to replay them.
        Successful entries are removed; failures remain for future attempts.
        This method is intended to be called periodically by a background task.
        """
        # Reset circuit if needed before processing
        self._reset_circuit_if_needed()
        # Read all lines
        try:
            with open(_OUTBOX_PATH, "r") as f:
                lines = f.readlines()
        except Exception:
            return
        remaining = []
        for line in lines:
            try:
                entry = json.loads(line.strip())
            except Exception:
                continue  # skip malformed line
            op = entry.get("op")
            if op == "remember":
                try:
                    self.remember(entry["key"], entry["payload"], entry.get("universe"))
                    # Successful replay – decrement gauge
                    try:
                        from .. import metrics as _mx

                        _mx.OUTBOX_PENDING.dec()
                    except Exception:
                        pass
                except Exception:
                    remaining.append(entry)
            elif op == "link":
                try:
                    # Deduplicate: skip if an identical link already exists
                    from_coord = entry["from_coord"]
                    to_coord = entry["to_coord"]
                    link_type = entry.get("link_type", "related")
                    existing = self.links_from(
                        from_coord, type_filter=link_type, limit=0
                    )
                    if any(e.get("to") == to_coord for e in existing):
                        # Edge already present – treat as success
                        try:
                            from .. import metrics as _mx

                            _mx.OUTBOX_PENDING.dec()
                        except Exception:
                            pass
                    else:
                        # Directly invoke client link to avoid circuit logic and further outbox writes
                        self.client().link(
                            from_coord,
                            to_coord,
                            link_type=link_type,
                            weight=entry.get("weight", 1.0),
                        )
                        # Successful replay – decrement gauge
                        try:
                            from .. import metrics as _mx

                            _mx.OUTBOX_PENDING.dec()
                        except Exception:
                            pass
                except Exception:
                    remaining.append(entry)
            else:
                # unknown op – keep it
                remaining.append(entry)
        # Rewrite outbox with remaining entries
        with open(_OUTBOX_PATH, "w") as f:
            for entry in remaining:
                f.write(json.dumps(entry) + "\n")
        # After rewriting, any remaining entries still count toward the pending gauge.
        try:
            from .. import metrics as _mx

            # Reset gauge to zero then set to remaining count
            _mx.OUTBOX_PENDING.set(0)
            if remaining:
                _mx.OUTBOX_PENDING.inc(len(remaining))
        except Exception:
            pass

    def remember(self, key: str, payload: dict, universe: Optional[str] = None):
        # Reset circuit before attempting write
        self._reset_circuit_if_needed()
        if self.__class__._circuit_open:
            # Circuit open – skip immediate write, just queue
            self._write_outbox(
                {"op": "remember", "key": key, "payload": payload, "universe": universe}
            )
            raise RuntimeError("Memory backend circuit open – operation queued")
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        # Perform store, then return deterministic coordinate
        try:
            res = self.client().remember(key, payload)
        except Exception:
            # Record failure and queue for retry
            self._record_failure()
            self._write_outbox(
                {"op": "remember", "key": key, "payload": payload, "universe": universe}
            )
            raise
        try:
            coord = self.coord_for_key(key, universe=universe)
        except Exception:
            coord = res
        # In stub or fallback modes, ensure payload is indexed with coordinate for planner lookup
        try:
            from ..memory_client import _GLOBAL_PAYLOADS

            p = dict(payload)
            p["coordinate"] = coord
            _GLOBAL_PAYLOADS.setdefault(self.namespace, []).append(p)
        except Exception:
            pass
        try:
            return coord
        except Exception:
            return res

    async def aremember(self, key: str, payload: dict, universe: Optional[str] = None):
        # Reset circuit if needed before attempting write
        self._reset_circuit_if_needed()
        if self.__class__._circuit_open:
            self._write_outbox(
                {"op": "remember", "key": key, "payload": payload, "universe": universe}
            )
            raise RuntimeError("Memory backend circuit open – operation queued")
        if universe and not payload.get("universe"):
            payload = dict(payload)
            payload["universe"] = universe
        client = self.client()
        mode = getattr(client, "_mode", None)
        try:
            if mode == "http" and hasattr(client, "aremember"):
                _ = await client.aremember(key, payload)  # type: ignore[attr-defined]
            else:
                _ = client.remember(key, payload)
        except Exception:
            # Record failure and queue
            self._record_failure()
            self._write_outbox(
                {"op": "remember", "key": key, "payload": payload, "universe": universe}
            )
            raise
        try:
            coord = self.coord_for_key(key, universe=universe)
        except Exception:
            coord = None
        # Ensure payload indexed with coordinate for planner lookup (stub/local)
        if coord is not None:
            try:
                from ..memory_client import _GLOBAL_PAYLOADS

                p = dict(payload)
                p["coordinate"] = coord
                _GLOBAL_PAYLOADS.setdefault(self.namespace, []).append(p)
            except Exception:
                pass
        try:
            return coord
        except Exception:
            return None

    def link(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
    ) -> None:
        # Ensure circuit is reset before attempting link operation
        self._reset_circuit_if_needed()
        if self.__class__._circuit_open:
            self._write_outbox(
                {
                    "op": "link",
                    "from_coord": from_coord,
                    "to_coord": to_coord,
                    "link_type": link_type,
                    "weight": weight,
                }
            )
            raise RuntimeError("Memory backend circuit open – operation queued")
        try:
            self.client().link(from_coord, to_coord, link_type=link_type, weight=weight)
            # Also mirror to the process-global links map to ensure visibility
            try:
                from .. import memory_client as _mc

                # Ensure module-level bindings reflect current builtins-backed maps
                try:
                    _mc._refresh_builtins_globals()
                except Exception:
                    pass
                GLOBAL_LINKS = getattr(_mc, "_GLOBAL_LINKS", None)
                if GLOBAL_LINKS is not None:
                    ns = getattr(self, "namespace", None)
                    if ns is not None:
                        try:
                            GLOBAL_LINKS.setdefault(ns, []).append(
                                {
                                    "from": list(map(float, from_coord)),
                                    "to": list(map(float, to_coord)),
                                    "type": str(link_type),
                                    "weight": float(weight),
                                }
                            )
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            # Record failure and queue
            self._record_failure()
            self._write_outbox(
                {
                    "op": "link",
                    "from_coord": from_coord,
                    "to_coord": to_coord,
                    "link_type": link_type,
                    "weight": weight,
                }
            )
            raise

    async def alink(
        self,
        from_coord: Tuple[float, float, float],
        to_coord: Tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        """Async link handling for all modes.

        For HTTP mode we use the backend ``alink`` method. For stub or other
        modes where ``alink`` is not applicable, we fall back to the synchronous
        ``link`` implementation, ensuring the in‑process graph is updated.
        """
        client = self.client()
        # If the client supports an async alink (HTTP mode), use it.
        if hasattr(client, "alink") and getattr(client, "_mode", None) == "http":
            try:
                await client.alink(
                    from_coord, to_coord, link_type=link_type, weight=weight
                )
                return
            except Exception:
                # Record for retry and re‑raise.
                self._write_outbox(
                    {
                        "op": "link",
                        "from_coord": from_coord,
                        "to_coord": to_coord,
                        "link_type": link_type,
                        "weight": weight,
                    }
                )
                raise
        # Fallback for stub or any non‑HTTP mode: use the synchronous link.
        self.link(from_coord, to_coord, link_type=link_type, weight=weight)

    def coord_for_key(self, key: str, universe: Optional[str] = None):
        return self.client().coord_for_key(key, universe=universe)

    def links_from(
        self,
        start: Tuple[float, float, float],
        type_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        try:
            # debug: expose global mirror size and namespace for triage
            import logging as _logging

            from .. import memory_client as _mc

            _log = _logging.getLogger(__name__)
            try:
                _log.debug(
                    "MemoryService.links_from ns=%r pool_keys=%r global_links_keys=%r",
                    self.namespace,
                    list(getattr(self.mt_memory, "_pool", {}).keys()),
                    list(getattr(_mc, "_GLOBAL_LINKS", {}).keys()),
                )
            except Exception:
                pass
        except Exception:
            pass
        return self.client().links_from(start, type_filter=type_filter, limit=limit)

    def payloads_for_coords(
        self, coords: List[Tuple[float, float, float]], universe: Optional[str] = None
    ) -> List[dict]:
        return self.client().payloads_for_coords(coords, universe=universe)

    def delete(self, coordinate: Tuple[float, float, float]):
        """Delete a memory at the given coordinate.

        Returns the result of the underlying client delete operation (often None).
        """
        return self.client().delete(coordinate)
