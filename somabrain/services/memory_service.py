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
from typing import Any, Dict
from threading import RLock
from collections.abc import Iterable

from aiobreaker import AsyncCircuitBreaker
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

    The service keeps per-tenant circuit-breaker state and exposes helpers
    for replaying the client outbox so the FastAPI layer can remain thin.
    """

    def __init__(self, mt_memory: Any, namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace
        self.tenant_id = self._extract_tenant_from_namespace(namespace)

    # Per-tenant circuit breakers
    _tenant_circuits: Dict[str, AsyncCircuitBreaker] = {}
    _circuit_lock: RLock = RLock()
    _failure_threshold: int = int(os.getenv("SOMABRAIN_MEMORY_FAILURE_THRESHOLD", "3"))
    _reset_interval: float = float(os.getenv("SOMABRAIN_MEMORY_RESET_INTERVAL", "60.0"))

    def _extract_tenant_from_namespace(self, namespace: str) -> str:
        """Extract tenant identifier from namespace string."""
        if ":" in namespace:
            return namespace.split(":")[-1]
        return namespace or "default"

    def client(self) -> MemoryBackend:
        """Return the underlying memory client for the current namespace."""
        return self.mt_memory.for_namespace(self.namespace)

    def _get_circuit_breaker(self) -> AsyncCircuitBreaker:
        """Get or create circuit breaker for the current tenant."""
        with self._circuit_lock:
            if self.tenant_id not in self._tenant_circuits:
                self._tenant_circuits[self.tenant_id] = AsyncCircuitBreaker(
                    failure_threshold=self._failure_threshold,
                    timeout=self._reset_interval,
                    name=f"memory_{self.tenant_id}"
                )
            return self._tenant_circuits[self.tenant_id]

    def _update_circuit_metric(self, is_open: bool) -> None:
        """Update per-tenant circuit breaker metrics."""
        if _metrics is None:
            return
        try:
            gauge = getattr(_metrics, "memory_circuit_open", None)
            if gauge is not None:
                gauge.labels(tenant=self.tenant_id).set(1 if is_open else 0)
        except Exception:
            pass

    def get_circuit_state(self) -> dict:
        """Get current circuit breaker state for this tenant."""
        circuit = self._get_circuit_breaker()
        return {
            "tenant": self.tenant_id,
            "circuit_open": circuit.is_open(),
            "failure_count": getattr(circuit, '_fail_counter', 0),
            "failure_threshold": self._failure_threshold,
            "reset_interval": self._reset_interval
        }

    @classmethod
    def reset_circuit_for_tenant(cls, tenant_id: str) -> bool:
        """Manually reset the circuit breaker for a specific tenant."""
        with cls._circuit_lock:
            if tenant_id in cls._tenant_circuits:
                circuit = cls._tenant_circuits[tenant_id]
                if hasattr(circuit, '_state'):
                    circuit._state = circuit._state.CLOSED
                return True
        return False

    def _update_outbox_metric(self) -> None:
        return

    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Stores a memory payload with per-tenant circuit breaker."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        circuit = self._get_circuit_breaker()
        
        async def _remember_operation():
            return self.client().remember(key, payload)

        try:
            if asyncio.iscoroutinefunction(self.client().remember):
                result = asyncio.run(_remember_operation())
            else:
                result = self.client().remember(key, payload)
            self._update_circuit_metric(False)
            return result
        except Exception as e:
            circuit.record_failure()
            self._update_circuit_metric(circuit.is_open())
            raise RuntimeError(f"Memory service unavailable for tenant {self.tenant_id}") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Async version of remember with per-tenant circuit breaker."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        circuit = self._get_circuit_breaker()
        
        @circuit  # This will handle circuit breaker logic
        async def _remember_operation():
            return await self.client().aremember(key, payload)

        try:
            result = await _remember_operation()
            self._update_circuit_metric(False)
            return result
        except Exception as e:
            self._update_circuit_metric(circuit.is_open())
            raise RuntimeError(f"Memory service unavailable for tenant {self.tenant_id}") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        """Store multiple memory payloads in a single operation with per-tenant circuit breaker."""

        prepared: list[tuple[str, dict]] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))

        if not prepared:
            return []

        circuit = self._get_circuit_breaker()
        
        @circuit
        async def _remember_bulk_operation():
            return await self.client().aremember_bulk(prepared)

        try:
            coords = await _remember_bulk_operation()
            self._update_circuit_metric(False)
            return list(coords)
        except Exception as e:
            self._update_circuit_metric(circuit.is_open())
            raise RuntimeError(f"Memory service unavailable for tenant {self.tenant_id}") from e

    def link(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Create a link between memories with per-tenant circuit breaker."""
        circuit = self._get_circuit_breaker()
        
        def _link_operation():
            return self.client().link(from_coord, to_coord, link_type, weight)

        try:
            if asyncio.iscoroutinefunction(self.client().link):
                result = asyncio.run(_link_operation())
            else:
                result = self.client().link(from_coord, to_coord, link_type, weight)
            self._update_circuit_metric(False)
            return result
        except Exception as e:
            circuit.record_failure()
            self._update_circuit_metric(circuit.is_open())
            raise RuntimeError(f"Memory service unavailable for tenant {self.tenant_id}") from e

    async def alink(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Async version of link with per-tenant circuit breaker."""
        circuit = self._get_circuit_breaker()
        
        @circuit
        async def _link_operation():
            return await self.client().alink(from_coord, to_coord, link_type, weight)

        try:
            result = await _link_operation()
            self._update_circuit_metric(False)
            return result
        except Exception as e:
            self._update_circuit_metric(circuit.is_open())
            raise RuntimeError(f"Memory service unavailable for tenant {self.tenant_id}") from e

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

    # Journal/outbox alternative removed: no background replay

    def coord_for_key(self, key: str, universe: str | None = None):
        return self.client().coord_for_key(key, universe)

    def payloads_for_coords(self, coords, universe: str | None = None):
        return self.client().payloads_for_coords(coords, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return self.client().links_from(start, type_filter, limit)
