"""
Unified Memory Client - SomaBrain SFM Integration.
Copyright (C) 2026 SomaTech LAT.

ONE official path: HTTP to SomaFractalMemory via the canonical
``somabrain.memory.client.MemoryClient``. No direct mode, no alternate
transport, no optional credential.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

from somabrain.memory.client import MemoryClient as CanonicalMemoryClient
from somabrain.settings.resolve import require_setting, require_url

from .degradation import HealthStatus, degradation_manager

logger = logging.getLogger("somabrain.memory")


def _require_tenant(tenant: str | None) -> str:
    """Return a non-empty tenant or raise. No default partition."""
    if not isinstance(tenant, str) or not tenant.strip():
        raise ValueError(
            "tenant must be a non-empty string; memory is partitioned by "
            "tenant and there is no default partition."
        )
    return tenant.strip()


class MemoryClient:
    """Unified client for SomaFractalMemory (SFM) — HTTP only."""

    def __init__(self) -> None:
        # Every value comes through the one resolver (Rule 91). Missing =
        # refusal naming the setting. No alternate mode, no optional token.
        self.endpoint = require_url("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        # Brain→SFM bearer is SOMA_API_TOKEN (SFM's own credential).
        self.token = require_setting("SOMA_API_TOKEN")
        self._canonical: CanonicalMemoryClient | None = None

    def _client(self) -> CanonicalMemoryClient:
        """The one HTTP-backed MemoryClient."""
        if self._canonical is None:
            self._canonical = CanonicalMemoryClient(cfg=settings)
        return self._canonical

    async def store(
        self, coordinate: list[float], payload: dict[str, Any], *, tenant: str
    ) -> bool:
        """Store a memory. Tenant required. HTTP path only."""
        tenant = _require_tenant(tenant)
        start_time = time.time()
        try:
            result = await self._client().store(coordinate, payload, tenant=tenant)
            latency = time.time() - start_time
            degradation_manager.report_latency(latency, "memory", tenant)
            return result
        except Exception as exc:
            degradation_manager.report_error("memory", exc, tenant)
            raise

    async def search(
        self, query: str, top_k: int = 5, *, tenant: str
    ) -> list[dict[str, Any]]:
        """Search memories. Tenant required. HTTP path only."""
        tenant = _require_tenant(tenant)
        status = degradation_manager.get_status(tenant)
        if status == HealthStatus.FAILSAFE:
            raise RuntimeError(
                f"Cognitive system is in FAILSAFE mode for tenant {tenant}; "
                "memory search unavailable"
            )
        try:
            return await self._client().search(query, top_k, tenant=tenant)
        except Exception as e:
            degradation_manager.report_error("memory", e, tenant)
            raise
