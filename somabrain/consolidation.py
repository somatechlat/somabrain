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
import copy
import random
from typing import List, Tuple
import time as _time

from common.config.settings import settings
from .config import Config
from .memory_client import MemoryClient
from .memory_pool import MultiTenantMemory
from .metrics import CONSOLIDATION_RUNS, REM_SYNTHESIZED
from .mt_wm import MultiTenantWM
from .reflect import top_keywords


def _episodics_from_wm(
    mtwm: MultiTenantWM, tenant_id: str, limit: int = 256
) -> List[dict]:
    items = mtwm.items(tenant_id, limit=limit)
    return [p for p in items if (p.get("memory_type") == "episodic")]


def _coords_for_payloads(
    mem: MemoryClient, payloads: List[dict]
) -> List[Tuple[float, float, float]]:
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
    cfg: Config,
    mtwm: MultiTenantWM,
    mtmem: MultiTenantMemory,
    top_k: int = 16,
    max_summaries: int = 3,
) -> dict:
    mem = mtmem.for_namespace(f"{cfg.namespace}:{tenant_id}")
    episodics = _episodics_from_wm(mtwm, tenant_id, limit=256)
    if not episodics:
        return {"created": 0, "reinforced": 0}
    # Time budget guard
    _t0 = _time.perf_counter()
    _budget = float(getattr(cfg, "consolidation_timeout_s", 0.0) or 0.0)
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
    mem.remember(summary, payload)
    CONSOLIDATION_RUNS.labels(phase="NREM").inc()
    # Reinforce links pairwise within batch
    coords = _coords_for_payloads(mem, batch)
    reinforced = 0
    for i in range(len(coords)):
        # Check time budget at outer loop
        if _budget > 0.0 and (_time.perf_counter() - _t0) > _budget:
            break
        for j in range(i + 1, len(coords)):
            if _budget > 0.0 and (_time.perf_counter() - _t0) > _budget:
                break
            # mem.link() removed for VIBE compliance
            pass
    # Decay/prune weak links to prevent unbounded growth
    try:
        pruned = 0
        if hasattr(mem, "decay_links"):
            pruned = mem.decay_links(
                factor=float(getattr(cfg, "link_decay_factor", 0.98) or 0.98),
                min_weight=float(getattr(cfg, "link_min_weight", 0.05) or 0.05),
            )
    except Exception:
        pruned = 0
    return {"created": 1, "reinforced": reinforced, "pruned": pruned}


def run_rem(
    tenant_id: str,
    cfg: Config,
    mtwm: MultiTenantWM,
    mtmem: MultiTenantMemory,
    recomb_rate: float = 0.2,
    max_summaries: int = 2,
) -> dict:
    mem = mtmem.for_namespace(f"{cfg.namespace}:{tenant_id}")
    episodics = _episodics_from_wm(mtwm, tenant_id, limit=256)
    if len(episodics) < 2:
        return {"created": 0}
    # Sample pairs for recombination
    n_pairs = max(0, int(recomb_rate * len(episodics)))
    created = 0
    _t0 = _time.perf_counter()
    _budget = float(getattr(cfg, "consolidation_timeout_s", 0.0) or 0.0)
    for _ in range(min(n_pairs, max_summaries)):
        if _budget > 0.0 and (_time.perf_counter() - _t0) > _budget:
            break
        a, b = random.sample(episodics, 2)
        ta = str(a.get("task") or "")
        tb = str(b.get("task") or "")
        keys = list({*top_keywords([ta], k=5), *top_keywords([tb], k=5)})
        synth = ", ".join(keys) if keys else f"combine: {ta[:20]} + {tb[:20]}"
        payload = {"fact": f"rem: {synth}", "memory_type": "semantic", "phase": "REM"}
        mem.remember(synth, payload)
        REM_SYNTHESIZED.inc()
        created += 1
    CONSOLIDATION_RUNS.labels(phase="REM").inc()
    return {"created": created}


def main():
    parser = argparse.ArgumentParser(description="SomaBrain Sleep Cycle")
    parser.add_argument("sleep", nargs="?", help="sleep command", default="sleep")
    parser.add_argument("--tenant", dest="tenant", default="public")
    parser.add_argument("--nrem", action="store_true")
    parser.add_argument("--rem", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    tenant = args.tenant
    cfg = copy.deepcopy(settings)
    mtwm = MultiTenantWM(dim=cfg.embed_dim, cfg=None)  # type: ignore
    mtmem = MultiTenantMemory(cfg)
    if args.nrem:
        stats = run_nrem(
            tenant,
            cfg,
            mtwm,
            mtmem,
            top_k=cfg.nrem_batch_size,
            max_summaries=cfg.max_summaries_per_cycle,
        )
        print("NREM:", stats)
    if args.rem:
        stats = run_rem(
            tenant,
            cfg,
            mtwm,
            mtmem,
            recomb_rate=cfg.rem_recomb_rate,
            max_summaries=cfg.max_summaries_per_cycle,
        )
        print("REM:", stats)


if __name__ == "__main__":
    main()
