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

    def __init__(self, mt_memory: Any, namespace: str):
        self.mt_memory = mt_memory
        self.namespace = namespace

    # Per-tenant circuit breaker state - complete isolation between tenants
    _circuit_lock: RLock = RLock()
    _outbox_lock: RLock = RLock()
    _circuit_open: dict[str, bool] = {}
    _failure_count: dict[str, int] = {}
    _last_failure_time: dict[str, float] = {}
    _last_reset_attempt: dict[str, float] = {}
    _tenant_namespace: dict[str, str] = {}
    # Per-tenant configurable thresholds (defaults can be overridden)
    _failure_threshold: dict[str, int] = {}
    _reset_interval: dict[str, float] = {}
    # Global defaults for new tenants
    _global_failure_threshold: int = 3
    _global_reset_interval: float = 60.0

    @classmethod
    def _ensure_tenant_state_locked(cls, tenant: str) -> None:
        # Assumes caller holds cls._circuit_lock
        if tenant not in cls._circuit_open:
            cls._circuit_open[tenant] = False
            cls._failure_count[tenant] = 0
            cls._last_failure_time[tenant] = 0.0
            cls._last_reset_attempt[tenant] = 0.0
            # Initialize per-tenant thresholds with global defaults
            cls._failure_threshold[tenant] = cls._global_failure_threshold
            cls._reset_interval[tenant] = cls._global_reset_interval
        label = cls._tenant_label(tenant)
        cls._tenant_namespace[label] = tenant

    @staticmethod
    def _tenant_label(namespace: str) -> str:
        if not namespace:
            return "default"
        if ":" in namespace:
            suffix = namespace.rsplit(":", 1)[-1]
            return suffix or namespace
        return namespace

    @classmethod
    def _resolve_namespace_for_label(cls, tenant_label: str) -> str:
        if not tenant_label:
            return "default"
        if tenant_label in cls._circuit_open:
            return tenant_label
        return cls._tenant_namespace.get(tenant_label, tenant_label)

    @property
    def tenant_id(self) -> str:
        return self._tenant_label(getattr(self, "namespace", "") or "")

    def client(self) -> MemoryBackend:
        """Return the underlying memory client for the current namespace."""
        return self.mt_memory.for_namespace(self.namespace)

    @classmethod
    def _set_circuit_metric_locked(cls, tenant: str) -> None:
        if _metrics is None:
            return
        # Try per-tenant labeled metrics first (CIRCUIT_STATE), then fallback
        gauge = getattr(_metrics, "CIRCUIT_STATE", None)
        if gauge is not None and hasattr(gauge, "labels"):
            try:
                tenant_label = cls._tenant_label(tenant)
                gauge.labels(tenant_id=str(tenant_label)).set(1 if cls._circuit_open.get(tenant, False) else 0)
                return
            except Exception:
                # Fall through to legacy gauge if labeled metric fails
                pass
        
        # Fallback to legacy circuit breaker gauge
        legacy_gauge = getattr(_metrics, "CIRCUIT_BREAKER_STATE", None)
        if legacy_gauge is not None:
            try:
                if hasattr(legacy_gauge, "labels"):
                    tenant_label = cls._tenant_label(tenant)
                    legacy_gauge.labels(tenant_id=str(tenant_label)).set(1 if cls._circuit_open.get(tenant, False) else 0)
                else:
                    legacy_gauge.set(1 if cls._circuit_open.get(tenant, False) else 0)
            except Exception:
                pass

    def _mark_success(self) -> None:
        cls = self.__class__
        tenant = getattr(self, "namespace", "default")
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            cls._failure_count[tenant] = 0
            cls._circuit_open[tenant] = False
            cls._last_failure_time[tenant] = 0.0
            cls._set_circuit_metric_locked(tenant)

    def _mark_failure(self) -> None:
        cls = self.__class__
        tenant = getattr(self, "namespace", "default")
        now = time.monotonic()
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            cls._failure_count[tenant] += 1
            cls._last_failure_time[tenant] = now
            # Use per-tenant threshold if available, otherwise global default
            threshold = cls._failure_threshold.get(tenant, cls._global_failure_threshold)
            if cls._failure_count[tenant] >= max(1, int(threshold)):
                cls._circuit_open[tenant] = True
            cls._set_circuit_metric_locked(tenant)
        if _metrics is not None:
            counter = getattr(_metrics, "HTTP_FAILURES", None)
            if counter is not None:
                try:
                    counter.inc()
                except Exception:
                    pass

    def _is_circuit_open(self) -> bool:
        cls = self.__class__
        tenant = getattr(self, "namespace", "default")
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            return bool(cls._circuit_open.get(tenant, False))

    def get_circuit_state(self) -> dict[str, Any]:
        cls = self.__class__
        tenant = getattr(self, "namespace", "default")
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            label = self.tenant_id
            # Use per-tenant thresholds if available, otherwise global defaults
            threshold = cls._failure_threshold.get(tenant, cls._global_failure_threshold)
            reset_interval = cls._reset_interval.get(tenant, cls._global_reset_interval)
            return {
                "tenant": label,
                "namespace": tenant,
                "circuit_open": bool(cls._circuit_open.get(tenant, False)),
                "failure_count": int(cls._failure_count.get(tenant, 0)),
                "last_failure_time": float(cls._last_failure_time.get(tenant, 0.0)),
                "last_reset_attempt": float(cls._last_reset_attempt.get(tenant, 0.0)),
                "failure_threshold": int(max(1, int(threshold))),
                "reset_interval": float(max(1.0, float(reset_interval))),
            }

    @classmethod
    def reset_circuit_for_tenant(cls, tenant_label: str) -> None:
        tenant = cls._resolve_namespace_for_label(tenant_label)
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            cls._failure_count[tenant] = 0
            cls._circuit_open[tenant] = False
            cls._last_failure_time[tenant] = time.monotonic()
            cls._last_reset_attempt[tenant] = cls._last_failure_time[tenant]
            cls._set_circuit_metric_locked(tenant)

    @classmethod
    def configure_tenant_thresholds(cls, tenant_label: str, failure_threshold: int | None = None, reset_interval: float | None = None) -> None:
        """Configure per-tenant circuit breaker thresholds.
        
        Args:
            tenant_label: The tenant label/identifier
            failure_threshold: Number of failures before opening circuit (default: 3)
            reset_interval: Seconds to wait before attempting reset (default: 60.0)
        """
        tenant = cls._resolve_namespace_for_label(tenant_label)
        with cls._circuit_lock:
            cls._ensure_tenant_state_locked(tenant)
            if failure_threshold is not None:
                cls._failure_threshold[tenant] = max(1, int(failure_threshold))
            if reset_interval is not None:
                cls._reset_interval[tenant] = max(1.0, float(reset_interval))
            # Update metric after configuration change
            cls._set_circuit_metric_locked(tenant)

    @classmethod
    def get_all_tenant_circuit_states(cls) -> dict[str, dict[str, Any]]:
        """Get circuit breaker states for all tenants.
        
        Returns:
            Dict mapping tenant labels to their circuit state information
        """
        with cls._circuit_lock:
            states = {}
            for tenant in cls._circuit_open.keys():
                cls._ensure_tenant_state_locked(tenant)
                label = cls._tenant_label(tenant)
                threshold = cls._failure_threshold.get(tenant, cls._global_failure_threshold)
                reset_interval = cls._reset_interval.get(tenant, cls._global_reset_interval)
                states[label] = {
                    "tenant": label,
                    "namespace": tenant,
                    "circuit_open": bool(cls._circuit_open.get(tenant, False)),
                    "failure_count": int(cls._failure_count.get(tenant, 0)),
                    "last_failure_time": float(cls._last_failure_time.get(tenant, 0.0)),
                    "last_reset_attempt": float(cls._last_reset_attempt.get(tenant, 0.0)),
                    "failure_threshold": int(max(1, int(threshold))),
                    "reset_interval": float(max(1.0, float(reset_interval))),
                }
            return states

    @classmethod
    def _should_attempt_reset(cls, tenant: str) -> bool:
        cls._ensure_tenant_state_locked(tenant)
        if not cls._circuit_open.get(tenant, False):
            return False
        now = time.monotonic()
        # Use per-tenant reset interval if available, otherwise global default
        reset_interval = cls._reset_interval.get(tenant, cls._global_reset_interval)
        if now - cls._last_failure_time.get(tenant, 0.0) < max(1.0, float(reset_interval)):
            return False
        if now - cls._last_reset_attempt.get(tenant, 0.0) < 5.0:
            return False
        cls._last_reset_attempt[tenant] = now
        return True

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
        """Attempt to close the circuit breaker if enough time has elapsed."""
        if not self._is_circuit_open():
            return False
        cls = self.__class__
        tenant = getattr(self, "namespace", "default")
        if not cls._should_attempt_reset(tenant):
            return False
        healthy = self._health_check()
        if healthy:
            with cls._circuit_lock:
                cls._ensure_tenant_state_locked(tenant)
                cls._circuit_open[tenant] = False
                cls._failure_count[tenant] = 0
                cls._last_failure_time[tenant] = 0.0
                cls._set_circuit_metric_locked(tenant)
            return True
        with cls._circuit_lock:
            cls._last_failure_time[tenant] = time.monotonic()
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
