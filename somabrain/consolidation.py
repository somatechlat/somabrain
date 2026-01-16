"""
Sleep-Inspired Memory Consolidation Module for SomaBrain

This module implements biologically-inspired memory consolidation processes modeled
after sleep stages in the human brain. Memory consolidation is the process by which
short-term memories are transformed into long-term memories through neural replay
and reorganization.

Key Features:
- NREM (Non-Rapid Eye Movement) consolidation: Summarization and reinforcement of episodic memories
- REM (Rapid Eye Movement) consolidation: Recombination of memories into novel semantic associations
- Memory replay and strengthening mechanisms
- Semantic summary generation from episodic memories
- Link strengthening between related memories
- Optional memory decay and pruning

Biological Inspiration:
- NREM sleep: Slow-wave sleep associated with memory replay and synaptic consolidation
- REM sleep: Associated with emotional processing and creative recombination of memories
- Hippocampal-neocortical dialogue: Transfer of memories from hippocampus to neocortex

Functions:
    run_nrem: Execute NREM-style consolidation (summarization and reinforcement)
    run_rem: Execute REM-style consolidation (recombination and creativity)
    _episodics_from_wm: Extract episodic memories from working memory
    _coords_for_payloads: Convert memory payloads to coordinate representations

Usage:
    The consolidation system runs periodically (like sleep cycles) to:
    1. Extract recent episodic memories from working memory
    2. Generate semantic summaries and store them
    3. Strengthen connections between related memories
    4. Optionally decay old or irrelevant memories
"""

from __future__ import annotations

import argparse
import random
from typing import List, Tuple, Any
import time as _time

from django.conf import settings
from .memory_client import MemoryClient
from .memory_pool import MultiTenantMemory
from somabrain.services.memory_service import MemoryService
from .metrics import CONSOLIDATION_RUNS, REM_SYNTHESIZED
from .mt_wm import MultiTenantWM
from .reflect import top_keywords


def _episodics_from_wm(mtwm: MultiTenantWM, tenant_id: str, limit: int = 256) -> List[dict]:
    """Execute episodics from wm.

    Args:
        mtwm: The mtwm.
        tenant_id: The tenant_id.
        limit: The limit.
    """

    items = mtwm.items(tenant_id, limit=limit)
    return [p for p in items if (p.get("memory_type") == "episodic")]


def _coords_for_payloads(
    mem: MemoryClient, payloads: List[dict]
) -> List[Tuple[float, float, float]]:
    """Execute coords for payloads.

    Args:
        mem: The mem.
        payloads: The payloads.
    """

    coords: List[Tuple[float, float, float]] = []
    for p in payloads:
        c = p.get("coordinate")
        if isinstance(c, (list, tuple)) and len(c) == 3:
            coords.append((float(c[0]), float(c[1]), float(c[2])))
        else:
            key = str(p.get("task") or p.get("fact") or "payload")
            coords.append(mem.coord_for_key(key))
    return coords


def run_nrem(
    tenant_id: str,
    cfg: Any,
    mtwm: MultiTenantWM,
    mtmem: MultiTenantMemory,
    top_k: int = 16,
    max_summaries: int = 3,
) -> dict:
    """Execute NREM consolidation phase.

    Args:
        tenant_id: The tenant to consolidate
        cfg: Config object (settings)
        mtwm: Working memory manager
        mtmem: Long-term memory manager
        top_k: Max items to batch
        max_summaries: Max summaries to create
    """
    namespace = f"{getattr(settings, 'SOMABRAIN_NAMESPACE', 'public')}:{tenant_id}"
    memsvc = MemoryService(mtmem, namespace)
    episodics = _episodics_from_wm(mtwm, tenant_id, limit=256)
    if not episodics:
        return {"created": 0, "reinforced": 0}

    # Time budget guard
    _t0 = _time.perf_counter()
    _budget = float(getattr(settings, "SOMABRAIN_CONSOLIDATION_TIMEOUT_S", 0.0) or 0.0)

    episodics.sort(key=lambda p: int(p.get("importance", 1)), reverse=True)
    batch = episodics[: max(1, int(top_k))]

    # Summarize batch and store semantic
    texts = [str(p.get("task") or "") for p in batch]
    keys = top_keywords(texts, k=8)
    summary = ", ".join(keys) if keys else "nrem summary"
    payload = {
        "fact": f"summary: {summary}",
        "memory_type": "semantic",
        "phase": "NREM",
    }
    memsvc.remember(summary, payload)
    CONSOLIDATION_RUNS.labels(phase="NREM").inc()
    return {"created": 1}


def run_rem(
    tenant_id: str,
    cfg: Any,
    mtwm: MultiTenantWM,
    mtmem: MultiTenantMemory,
    recomb_rate: float = 0.2,
    max_summaries: int = 2,
) -> dict:
    """Execute REM consolidation phase.

    Args:
        tenant_id: The tenant to consolidate
        cfg: Config object (settings)
        mtwm: Working memory manager
        mtmem: Long-term memory manager
        recomb_rate: Rate of recombination
        max_summaries: Max summaries to create
    """
    namespace = f"{getattr(settings, 'SOMABRAIN_NAMESPACE', 'public')}:{tenant_id}"
    memsvc = MemoryService(mtmem, namespace)
    episodics = _episodics_from_wm(mtwm, tenant_id, limit=256)
    if len(episodics) < 2:
        return {"created": 0}

    # Sample pairs for recombination
    n_pairs = max(0, int(recomb_rate * len(episodics)))
    created = 0
    _t0 = _time.perf_counter()
    _budget = float(getattr(settings, "SOMABRAIN_CONSOLIDATION_TIMEOUT_S", 0.0) or 0.0)

    for _ in range(min(n_pairs, max_summaries)):
        if _budget > 0.0 and (_time.perf_counter() - _t0) > _budget:
            break
        a, b = random.sample(episodics, 2)
        ta = str(a.get("task") or "")
        tb = str(b.get("task") or "")
        keys = list({*top_keywords([ta], k=5), *top_keywords([tb], k=5)})
        synth = ", ".join(keys) if keys else f"combine: {ta[:20]} + {tb[:20]}"
        payload = {"fact": f"rem: {synth}", "memory_type": "semantic", "phase": "REM"}
        memsvc.remember(synth, payload)
        REM_SYNTHESIZED.inc()
        created += 1

    CONSOLIDATION_RUNS.labels(phase="REM").inc()
    return {"created": created}


def main():
    """Execute main."""

    parser = argparse.ArgumentParser(description="SomaBrain Sleep Cycle")
    parser.add_argument("sleep", nargs="?", help="sleep command", default="sleep")
    parser.add_argument("--tenant", dest="tenant", default="public")
    parser.add_argument("--nrem", action="store_true")
    parser.add_argument("--rem", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    tenant = args.tenant
    mtwm = MultiTenantWM(dim=getattr(settings, "SOMABRAIN_EMBED_DIM", 256), cfg=None)
    mtmem = MultiTenantMemory(settings)

    if args.nrem:
        stats = run_nrem(
            tenant,
            settings,
            mtwm,
            mtmem,
            top_k=getattr(settings, "SOMABRAIN_NREM_BATCH_SIZE", 16),
            max_summaries=getattr(settings, "SOMABRAIN_MAX_SUMMARIES_PER_CYCLE", 3),
        )
        print("NREM:", stats)

    if args.rem:
        stats = run_rem(
            tenant,
            settings,
            mtwm,
            mtmem,
            recomb_rate=getattr(settings, "SOMABRAIN_REM_RECOMB_RATE", 0.2),
            max_summaries=getattr(settings, "SOMABRAIN_MAX_SUMMARIES_PER_CYCLE", 3),
        )
        print("REM:", stats)


if __name__ == "__main__":
    main()
