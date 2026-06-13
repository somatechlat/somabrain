"""
Unified Memory Client - SomaBrain SFM Integration.
Copyright (C) 2026 SomaTech LAT.

Thin wrapper around the canonical somabrain.memory.client.MemoryClient.
Preserves direct-mode and degradation-manager integration.
"""

from __future__ import annotations

import logging
import time
from importlib import import_module
from typing import Any, Dict, List, Protocol, cast

from django.conf import settings

from somabrain.memory.client import MemoryClient as CanonicalMemoryClient
from .degradation import HealthStatus, degradation_manager

logger = logging.getLogger("somabrain.memory")


class _DirectMemoryService(Protocol):
    """Small protocol for the optional in-process SomaFractalMemory service."""

    def store(
        self,
        coordinate: tuple[float, ...],
        payload: Dict[str, Any],
        *,
        tenant: str,
    ) -> None:
        """Persist a memory directly into the SFM runtime."""

    def search(
        self,
        query: str,
        *,
        top_k: int,
        tenant: str,
    ) -> List[Dict[str, Any]]:
        """Search the direct SFM runtime."""


class MemoryClient:
    """Unified client for SomaFractalMemory (SFM)."""

    def __init__(self) -> None:
        self.mode = getattr(settings, "SOMABRAIN_MEMORY_MODE", "http")
        self.endpoint = getattr(
            settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:21000"
        )
        self.token = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", None)

        self._direct_service: _DirectMemoryService | None = None
        self._canonical: CanonicalMemoryClient | None = None

        if self.mode == "direct":
            self._init_direct_mode()

    def _init_direct_mode(self) -> None:
        """Initialize direct code access if available."""
        try:
            services_module = import_module("somafractalmemory.services")
            get_memory_service = getattr(services_module, "get_memory_service")
            self._direct_service = cast(_DirectMemoryService, get_memory_service())
            logger.info(
                "Initialized Unified Memory Client in DIRECT mode (Zero-Latency)."
            )
        except ImportError:
            logger.error(
                "Direct mode requested but somafractalmemory is not installed. Falling back to HTTP."
            )
            self.mode = "http"

    def _canonical_client(self) -> CanonicalMemoryClient:
        """Lazy initializer for the canonical HTTP-backed MemoryClient."""
        if self._canonical is None:
            self._canonical = CanonicalMemoryClient(cfg=settings)
        return self._canonical

    async def store(
        self, coordinate: List[float], payload: Dict[str, Any], tenant: str = "default"
    ) -> bool:
        """Store a memory with automated timing and health reporting."""
        start_time = time.time()
        try:
            if self.mode == "direct" and self._direct_service:
                self._direct_service.store(tuple(coordinate), payload, tenant=tenant)
                result = True
            else:
                result = await self._canonical_client().store(
                    coordinate, payload, tenant=tenant
                )

            latency = time.time() - start_time
            degradation_manager.report_latency(latency, "memory", tenant)
            return result

        except Exception as exc:
            degradation_manager.report_error("memory", exc, tenant)
            raise

    async def search(
        self, query: str, top_k: int = 5, tenant: str = "default"
    ) -> List[Dict[str, Any]]:
        """Search memories with automated degradation fallbacks."""
        status = degradation_manager.get_status(tenant)

        if status == HealthStatus.FAILSAFE:
            raise RuntimeError(
                f"Cognitive system is in FAILSAFE mode for tenant {tenant}; "
                "memory search unavailable"
            )

        try:
            if self.mode == "direct" and self._direct_service:
                return self._direct_service.search(query, top_k=top_k, tenant=tenant)
            else:
                return await self._canonical_client().search(
                    query, top_k, tenant=tenant
                )
        except Exception as e:
            degradation_manager.report_error("memory", e, tenant)
            raise


memory_client = MemoryClient()
