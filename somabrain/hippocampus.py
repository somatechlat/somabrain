"""
Hippocampal consolidation module that writes to the real memory backend.

This module provides:
- ``ConsolidationConfig``: tunable parameters for buffering and consolidation.
- ``Hippocampus``: accepts episodic payloads, persists them via the configured
  MultiTenantMemory client, and can run NREM/REM style consolidation using the
  existing consolidation routines.

VIBE Compliance:
    - Uses DI container for runtime singletons (no lazy imports from runtime module)
    - mt_wm and mt_memory are obtained from DI container during initialization
    - No circular import workarounds
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from somabrain.services.memory_service import MemoryService

from . import consolidation


@dataclass
class ConsolidationConfig:
    """Consolidationconfig class implementation."""

    tenant: str = "sandbox"
    buffer_max: int = 512
    nrem_top_k: int = 16
    rem_recomb_rate: float = 0.2
    max_summaries: int = 3
    enable_nrem: bool = True
    enable_rem: bool = True


class Hippocampus:
    """Real consolidation buffer that talks to the live memory backend."""

    def __init__(
        self,
        cfg: ConsolidationConfig,
        *,
        mt_memory=None,
        mt_wm=None,
    ) -> None:
        """Initialize the instance."""

        self.cfg = cfg
        self._buffers: Dict[str, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=cfg.buffer_max)
        )
        # Bind to runtime singletons via DI container if not provided
        # VIBE Compliance: Use DI container instead of lazy imports from runtime module
        if mt_memory is None or mt_wm is None:
            from somabrain.core.container import container

            if container.has("mt_memory") and mt_memory is None:
                mt_memory = container.get("mt_memory")
            if container.has("mt_wm") and mt_wm is None:
                mt_wm = container.get("mt_wm")
        self._mt_memory = mt_memory
        self._mt_wm = mt_wm

    def add_memory(self, payload: dict, tenant_id: Optional[str] = None) -> None:
        """Store an episodic payload and persist it immediately to memory service."""
        tenant = tenant_id or self.cfg.tenant
        p = dict(payload)
        p.setdefault("memory_type", "episodic")
        self._buffers[tenant].append(p)
        # Persist to external memory if available (no silent fallback).
        if self._mt_memory is not None:
            memsvc = MemoryService(self._mt_memory, f"{tenant}")
            key = str(p.get("task") or p.get("fact") or p.get("content") or "episodic")
            memsvc.remember(key, p)
        # Mirror into working memory if available (keeps consolidation inputs real)
        if self._mt_wm is not None and hasattr(self._mt_wm, "items"):
            try:
                # WorkingMemory expects vectors; if absent, skip WM admit and rely on buffer
                vec = p.get("vector")
                if vec is not None:
                    self._mt_wm.admit(tenant, vec, p)
            except Exception:
                # Do not swallow silently; raise so caller can see real failure
                raise

    def consolidate(self, tenant_id: Optional[str] = None) -> dict:
        """Run NREM+REM style consolidation using real working/long-term memory."""
        tenant = tenant_id or self.cfg.tenant
        if self._mt_memory is None or self._mt_wm is None:
            raise RuntimeError("mt_memory/mt_wm not initialized; cannot consolidate")

        stats = {}
        if self.cfg.enable_nrem:
            stats["nrem"] = consolidation.run_nrem(
                tenant,
                self._mt_memory.cfg,
                self._mt_wm,
                self._mt_memory,
                top_k=self.cfg.nrem_top_k,
                max_summaries=self.cfg.max_summaries,
            )
        if self.cfg.enable_rem:
            stats["rem"] = consolidation.run_rem(
                tenant,
                self._mt_memory.cfg,
                self._mt_wm,
                self._mt_memory,
                recomb_rate=self.cfg.rem_recomb_rate,
                max_summaries=self.cfg.max_summaries,
            )
        return stats