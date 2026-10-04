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
from typing import Any, Protocol, cast

from django.conf import settings

from somabrain.memory.client import MemoryClient as CanonicalMemoryClient
from somabrain.settings.resolve import optional_setting, require_setting, require_url

from .degradation import HealthStatus, degradation_manager

logger = logging.getLogger("somabrain.memory")


def _require_tenant(tenant: str | None) -> str:
    """Return a non-empty tenant or raise.

    Memory is partitioned by tenant. There is no default partition: a caller
    that forgets the tenant must not silently write into a shared scope
    (Rule 91).
    """
    if not isinstance(tenant, str) or not tenant.strip():
        raise ValueError(
            "tenant must be a non-empty string; memory is partitioned by "
            "tenant and there is no default partition."
        )
    return tenant.strip()


class _DirectMemoryService(Protocol):
    """Small protocol for the optional in-process SomaFractalMemory service."""

    def store(
        self,
        coordinate: tuple[float, ...],
        payload: dict[str, Any],
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
    ) -> list[dict[str, Any]]:
        """Search the direct SFM runtime."""


class MemoryClient:
    """Unified client for SomaFractalMemory (SFM)."""

    def __init__(self) -> None:
        # Every value comes through the one resolver (Rule 91). A missing
        # required setting is a refusal naming the setting; there is no
        # hardcoded fallback URL and no ``getattr(..., default)``.
        self.mode = require_setting("SOMABRAIN_MEMORY_MODE")
        self.endpoint = require_url("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        # Brain→SFM is a separate trust boundary from agent→brain. The bearer
        # SFM accepts is SOMA_API_TOKEN (its own get_api_token()), never the
        # agent↔brain somabrain_memory_http_token. Conflating the two is how a
        # reseeded agent token silently broke every store write. The token is
        # optional at the settings layer: ``get_api_token()`` documents None as
        # "this deployment deliberately runs without one".
        self.token = optional_setting("SOMA_API_TOKEN")

        self._direct_service: _DirectMemoryService | None = None
        self._canonical: CanonicalMemoryClient | None = None

        if self.mode == "direct":
            self._init_direct_mode()

    def _init_direct_mode(self) -> None:
        """Bind the in-process memory service for direct mode.

        Direct mode is a deployment choice, not a preference. If the caller
        asked for it and the memory service cannot be imported, that is a
        broken deployment: fail closed rather than silently serving over a
        different transport than the one that was configured.
        """
        services_module = import_module("somafractalmemory.services")
        get_memory_service = services_module.get_memory_service
        self._direct_service = cast(_DirectMemoryService, get_memory_service())
        logger.info(
            "Initialized Unified Memory Client in DIRECT mode (Zero-Latency)."
        )

    def _canonical_client(self) -> CanonicalMemoryClient:
        """Lazy initializer for the canonical HTTP-backed MemoryClient."""
        if self._canonical is None:
            self._canonical = CanonicalMemoryClient(cfg=settings)
        return self._canonical

    async def store(
        self, coordinate: list[float], payload: dict[str, Any], *, tenant: str
    ) -> bool:
        """Store a memory with automated timing and health reporting.

        ``tenant`` is required and must be non-empty; there is no default
        partition.
        """
        tenant = _require_tenant(tenant)
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
        self, query: str, top_k: int = 5, *, tenant: str
    ) -> list[dict[str, Any]]:
        """Search memories with automated degradation fallbacks.

        ``tenant`` is required and must be non-empty; there is no default
        partition.
        """
        tenant = _require_tenant(tenant)
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
