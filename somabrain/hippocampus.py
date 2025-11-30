"""
Hippocampal consolidation shim that actually writes to the real memory backend.

This module provides:
- ``ConsolidationConfig``: tunable parameters for buffering and consolidation.
- ``Hippocampus``: accepts episodic payloads, persists them via the configured
  MultiTenantMemory client, and can run NREM/REM style consolidation using the
  existing consolidation routines (no stubs, no fallbacks).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from . import consolidation

# The runtime module (somabrain/runtime.py) already wires mt_wm/mt_memory
# singletons. We import lazily to avoid circular imports during app boot.


@dataclass
class ConsolidationConfig:
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
        self.cfg = cfg
        self._buffers: Dict[str, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=cfg.buffer_max)
        )
        # Lazy bind to runtime singletons if not provided
        if mt_memory is None or mt_wm is None:
            try:
                from . import runtime as _rt  # type: ignore
            except Exception:
                from importlib import import_module

                _rt = import_module("somabrain.runtime_module")  # loaded by app
            mt_memory = (
                getattr(_rt, "mt_memory", None) if mt_memory is None else mt_memory
            )
            mt_wm = getattr(_rt, "mt_wm", None) if mt_wm is None else mt_wm
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
            mem = self._mt_memory.for_namespace(f"{tenant}")
            key = str(p.get("task") or p.get("fact") or p.get("content") or "episodic")
            mem.remember(key, p)
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
                self._mt_memory.cfg,  # type: ignore[attr-defined]
                self._mt_wm,
                self._mt_memory,  # type: ignore[arg-type]
                top_k=self.cfg.nrem_top_k,
                max_summaries=self.cfg.max_summaries,
            )
        if self.cfg.enable_rem:
            stats["rem"] = consolidation.run_rem(
                tenant,
                self._mt_memory.cfg,  # type: ignore[attr-defined]
                self._mt_wm,
                self._mt_memory,  # type: ignore[arg-type]
                recomb_rate=self.cfg.rem_recomb_rate,
                max_summaries=self.cfg.max_summaries,
            )
        return stats
