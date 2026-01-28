"""
Unified Memory Client - SomaBrain SFM Integration.
Copyright (C) 2026 SomaTech LAT.

Supports 'direct' (in-proc) and 'http' (REST) modes for zero-latency
and multi-tenant cognitive operations.
"""

import logging
import time
import httpx
from typing import Any, Dict, List, Optional
from django.conf import settings
from .degradation import degradation_manager, HealthStatus

logger = logging.getLogger("somabrain.memory")

class MemoryClient:
    """Unified client for SomaFractalMemory (SFM)."""

    def __init__(self):
        self.mode = getattr(settings, "SOMABRAIN_MEMORY_MODE", "http")
        self.endpoint = getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:21000")
        self.token = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", None)

        self._direct_service = None
        if self.mode == "direct":
            self._init_direct_mode()

    def _init_direct_mode(self):
        """Initialize direct code access if available."""
        try:
            from somafractalmemory.services import get_memory_service
            self._direct_service = get_memory_service()
            logger.info("Initialized Unified Memory Client in DIRECT mode (Zero-Latency).")
        except ImportError:
            logger.error("Direct mode requested but somafractalmemory not install. Falling back to HTTP.")
            self.mode = "http"

    async def store(self, coordinate: List[float], payload: Dict[str, Any], tenant: str = "default") -> bool:
        """Store a memory with automated timing and health reporting."""
        start_time = time.time()
        try:
            if self.mode == "direct" and self._direct_service:
                # Direct call (Zero-Latency)
                self._direct_service.store(tuple(coordinate), payload, tenant=tenant)
                res = True
            else:
                # HTTP call (Network Latency)
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                    resp = await client.post(
                        f"{self.endpoint}/api/v1/memories",
                        json={"coordinate": coordinate, "payload": payload},
                        params={"tenant": tenant},
                        headers=headers,
                        timeout=1.0
                    )
                    res = resp.status_code == 200

            latency = time.time() - start_time
            degradation_manager.report_latency(latency, "memory", tenant)
            return res

        except Exception as e:
            degradation_manager.report_error("memory", e, tenant)
            # FALLBACK: If degraded, we could log to a local 'outbox' or 'degraded_buffer'
            return False

    async def search(self, query: str, top_k: int = 5, tenant: str = "default") -> List[Dict[str, Any]]:
        """Search memories with automated degradation fallbacks."""
        status = degradation_manager.get_status(tenant)

        # If in FAILSAFE mode, restrict search to limited local WM cache or tiny local vector store
        if status == HealthStatus.FAILSAFE:
            logger.warning(f"Cognitive system is in FAILSAFE mode for tenant {tenant}. Returning empty search.")
            return []

        try:
            if self.mode == "direct" and self._direct_service:
                return self._direct_service.search(query, top_k=top_k, tenant=tenant)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.endpoint}/api/v1/memories/search",
                        json={"query": query, "top_k": top_k},
                        params={"tenant": tenant},
                        timeout=2.0
                    )
                    return resp.json().get("results", [])
        except Exception as e:
            degradation_manager.report_error("memory", e, tenant)
            return []

memory_client = MemoryClient()
