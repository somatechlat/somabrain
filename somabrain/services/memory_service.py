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
from typing import Any
from threading import RLock
from collections.abc import Iterable

from somabrain.interfaces.memory import MemoryBackend
from somabrain.config import get_config
# Centralised tenant helper and circuit breaker
from somabrain.infrastructure.tenant import tenant_label as _tenant_label, resolve_namespace as _resolve_namespace
from somabrain.infrastructure.circuit_breaker import CircuitBreaker as _CircuitBreaker
import logging

logger = logging.getLogger(__name__)

try:  # Prometheus metrics are optional in some test contexts
    from somabrain import metrics as _metrics  # type: ignore
except Exception:  # pragma: no cover - metrics not always available in tests
    _metrics = None  # type: ignore


class MemoryService:
    class MemoryService:
        """Universe‑aware façade around :class:`MultiTenantMemory`.

        All circuit‑breaker state is delegated to the central ``CircuitBreaker``
        implementation.  This class focuses on request handling and outbox metric
        updates.
        """

        def __init__(self, mt_memory: Any, namespace: str):
            self.mt_memory = mt_memory
            self.namespace = namespace

        # Shared circuit‑breaker instance for all ``MemoryService`` objects
        _circuit_breaker: _CircuitBreaker = _CircuitBreaker()
        _outbox_lock: RLock = RLock()

        # ---------------------------------------------------------------------
        # Tenant helpers – delegated to the central module
        # ---------------------------------------------------------------------
        @staticmethod
        def _tenant_label(namespace: str) -> str:
            return _tenant_label(namespace)

        @classmethod
        def _resolve_namespace_for_label(cls, tenant_label: str) -> str:
            return _resolve_namespace(tenant_label)

        @property
        def tenant_id(self) -> str:
            return self._tenant_label(getattr(self, "namespace", "") or "")

        def client(self) -> MemoryBackend:
            """Return the underlying memory client for the current namespace."""
            return self.mt_memory.for_namespace(self.namespace)

        # ---------------------------------------------------------------------
        # Circuit‑breaker delegation helpers
        # ---------------------------------------------------------------------
        def _mark_success(self) -> None:
            tenant = getattr(self, "namespace", "default")
            self.__class__._circuit_breaker.record_success(tenant)

        def _mark_failure(self) -> None:
            tenant = getattr(self, "namespace", "default")
            self.__class__._circuit_breaker.record_failure(tenant)

        def _is_circuit_open(self) -> bool:
            tenant = getattr(self, "namespace", "default")
            return self.__class__._circuit_breaker.is_open(tenant)

        def get_circuit_state(self) -> dict[str, Any]:
            tenant = getattr(self, "namespace", "default")
            state = self.__class__._circuit_breaker.get_state(tenant)
            # Preserve historic keys for compatibility
            state.update({"tenant": self._tenant_label(tenant), "namespace": tenant})
            return state

        @classmethod
        def reset_circuit_for_tenant(cls, tenant_label: str) -> None:
            tenant = cls._resolve_namespace_for_label(tenant_label)
            cls._circuit_breaker.record_success(tenant)

        @classmethod
        def configure_tenant_thresholds(
            cls, tenant_label: str, failure_threshold: int | None = None, reset_interval: float | None = None
        ) -> None:
            tenant = cls._resolve_namespace_for_label(tenant_label)
            cls._circuit_breaker.configure_tenant(
                tenant, failure_threshold=failure_threshold, reset_interval=reset_interval
            )

        @classmethod
        def get_all_tenant_circuit_states(cls) -> dict[str, dict[str, Any]]:
            breaker = cls._circuit_breaker
            with breaker._lock:  # type: ignore[attr-defined]
                tenants = list(breaker._circuit_open.keys())  # type: ignore[attr-defined]
            states: dict[str, dict[str, Any]] = {}
            for tenant in tenants:
                label = _tenant_label(tenant)
                state = breaker.get_state(tenant)
                state.update({"tenant": label, "namespace": tenant})
                states[label] = state
            return states

        @classmethod
        def _should_attempt_reset(cls, tenant: str) -> bool:
            """Delegate reset‑attempt logic to the shared ``CircuitBreaker``."""
            return cls._circuit_breaker.should_attempt_reset(tenant)


    @classmethod
    def _update_outbox_metric(cls, tenant: str | None = None, count: int | None = None) -> None:
        """Update outbox pending metrics for a specific tenant or all tenants.
        
        Args:
            tenant: Specific tenant to update, or None to update all tenants
            count: Specific count to set, or None to fetch from database
        """
        if _metrics is None:
            return
            
        # If no specific tenant provided, update metrics for all tenants
        if tenant is None:
            try:
                from somabrain.db.outbox import get_pending_counts_by_tenant  # type: ignore
                tenant_counts = get_pending_counts_by_tenant()
                
                # Update metrics for each tenant
                for tenant_label, tenant_count in tenant_counts.items():
                    cls._update_tenant_outbox_metric(tenant_label, tenant_count)
                    
                # Also update legacy global metric if needed
                total_count = sum(tenant_counts.values())
                cls._update_tenant_outbox_metric("default", total_count)
                    
            except Exception as e:
                # Fallback to updating just default tenant on error
                cls._update_tenant_outbox_metric("default", 0)
        else:
            # Update metrics for specific tenant
            tenant_label = cls._tenant_label(tenant) if tenant else "default"
            if count is None:
                try:
                    from somabrain.db.outbox import get_pending_count  # type: ignore
                    count = int(get_pending_count(tenant_id=tenant_label))
                except Exception:
                    count = 0
            cls._update_tenant_outbox_metric(tenant_label, count)
    
    @classmethod
    def _update_tenant_outbox_metric(cls, tenant_label: str, count: int) -> None:
        """Update outbox metric for a specific tenant.
        
        Args:
            tenant_label: The tenant label
            count: The pending count to set
        """
        if _metrics is None:
            return
            
        # Try the dedicated reporter function first
        reporter = getattr(_metrics, "report_outbox_pending", None)
        if callable(reporter):
            try:
                reporter(tenant_label, count)
                return
            except Exception:
                # Fall through to direct gauge update
                pass
                
        # Direct gauge update
        gauge = getattr(_metrics, "OUTBOX_PENDING", None)
        if gauge is not None:
            try:
                if hasattr(gauge, "labels"):
                    gauge.labels(tenant_id=str(tenant_label)).set(count)
                else:
                    # Fallback to unlabeled gauge (legacy behavior)
                    if tenant_label == "default":
                        gauge.set(count)
            except Exception:
                pass

    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Stores a memory payload. In V3, this fails fast if the remote is down."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            result = self.client().remember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Async version of remember."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            result = await self.client().aremember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        """Store multiple memory payloads in a single operation."""

        prepared: list[tuple[str, dict]] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))

        if not prepared:
            return []

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            coords = await self.client().aremember_bulk(prepared)
            self._mark_success()
            return list(coords)
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    def link(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Create a link between memories (fail-fast)."""
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = self.client().link(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def alink(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Async version of link."""
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = await self.client().alink(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

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
        """Attempt to close the circuit breaker if enough time has elapsed.

        The logic is now delegated to the shared :class:`CircuitBreaker`
        instance.  If the breaker signals that a reset attempt is allowed and the
        health check passes, we record a successful request which clears the
        circuit state.
        """
        if not self._is_circuit_open():
            return False
        tenant = getattr(self, "namespace", "default")
        breaker = self.__class__._circuit_breaker
        if not breaker.should_attempt_reset(tenant):
            return False
        if self._health_check():
            breaker.record_success(tenant)
            return True
        # No state change – the circuit remains open.
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

# Expose the inner implementation as the public ``MemoryService`` symbol.
# This replaces the outer wrapper (which lacks an __init__) with the functional
# inner class, restoring the expected constructor signature used throughout the
# codebase.
MemoryService = MemoryService.MemoryService
