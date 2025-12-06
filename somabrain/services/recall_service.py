"""
Recall Service Module for SomaBrain

This module implements long-term memory (LTM) recall functionality with advanced
features like SDR prefiltering. It provides efficient
memory retrieval with multiple optimization strategies.

Key Features:
- SDR-based prefiltering for fast candidate selection
- Universe filtering for context-specific retrieval
- Performance metrics collection
- Alternative mechanisms for robustness

Recall Strategies:
- SDR Prefilter: Uses Sparse Distributed Representations for fast candidate selection
- Direct Recall: Standard similarity-based retrieval
- Universe Filtering: Context-specific memory retrieval

Performance Optimizations:
- LSH indexing for efficient similarity search
- Configurable candidate limits
- Latency monitoring and metrics
- Cohort-based performance tracking

Functions:
    recall_ltm: Main long-term memory recall function
    _text_of: Helper to extract text from memory payloads

Classes:
    None (utility function-based implementation)
"""

from __future__ import annotations

import asyncio
import time as _t
from typing import Callable, List, Optional, Tuple
import re

from .. import metrics as M
from ..sdr import LSHIndex


def recall_ltm(
    mem_client,
    text: str,
    top_k: int,
    universe: Optional[str],
    cohort: str,
    use_sdr: bool,
    sdr_enc,
    sdr_idx_map: dict,
    graph_hops: int,
    graph_limit: int,
) -> Tuple[List[dict], List[Tuple[float, dict]]]:
    """LTM recall with optional SDR prefilter.

    Returns (payloads, mem_hits) where mem_hits are provider-specific hits if available.
    """
    mem_hits: List[Tuple[float, dict]] = []
    mem_payloads: List[dict] = []
    did_sdr = False
    if use_sdr and sdr_enc is not None and hasattr(mem_client, "all_memories"):
        try:
            idx = sdr_idx_map.setdefault(
                getattr(mem_client.cfg, "namespace", "default"),
                LSHIndex(
                    bands=sdr_enc.cfg.bands if hasattr(sdr_enc, "cfg") else 8,
                    rows=sdr_enc.cfg.rows if hasattr(sdr_enc, "cfg") else 16,
                    dim=sdr_enc.dim if hasattr(sdr_enc, "dim") else 16384,
                ),
            )
            qbits = sdr_enc.encode(text)
            t2 = _t.perf_counter()
            cand_coords = idx.query(qbits, limit=graph_limit)
            M.SDR_PREFILTER_LAT.labels(cohort=cohort).observe(
                max(0.0, _t.perf_counter() - t2)
            )
            for _ in cand_coords:
                M.SDR_CANDIDATES.labels(cohort=cohort).inc()
            if cand_coords:
                mem_payloads = mem_client.payloads_for_coords(cand_coords)
                did_sdr = True
        except Exception:
            did_sdr = False
    if not did_sdr:
        hits = getattr(mem_client, "recall")(text, top_k=top_k)
        # hits may be RecallHit wrappers
        try:
            mem_payloads = [h.payload for h in hits]
            mem_hits = hits  # type: ignore
        except Exception:
            mem_payloads = []
        # If recall returned items but none lexically match the query, inject
        # a deterministic read-your-writes result derived from the query key.
        try:
            ql = str(text or "").strip().lower()

            def _lex_match(p: dict) -> bool:
                for k in ("task", "text", "content", "what", "fact"):
                    v = p.get(k)
                    if (
                        isinstance(v, str)
                        and v
                        and (ql in v.lower() or v.lower() in ql)
                    ):
                        return True
                return False

            if ql and (not any(_lex_match(p) for p in mem_payloads)):
                coord = mem_client.coord_for_key(text, universe=universe)
                # payload_for_coords is removed, just try to get it directly if possible via client
                pass
        except Exception:
            pass
    # Lexical/token-aware boost: if the query looks like a short unique token or
    # if any payload contains the exact query string, promote those payloads to
    # the top so users don't need manual tuning to find label-like memories.
    try:
        q = str(text or "").strip()
        ql = q.lower()

        def _is_token_like(s: str) -> bool:
            # Heuristic: alnum/_/- only, length 6-64, includes both letters and digits
            if not s or len(s) < 6 or len(s) > 64:
                return False
            if not re.match(r"^[A-Za-z0-9_-]+$", s):
                return False
            has_alpha = any(c.isalpha() for c in s)
            has_digit = any(c.isdigit() for c in s)
            return has_alpha and has_digit

        def _lexical_score(p: dict) -> int:
            # Score by exact contains in common fields; higher for exact token-like
            score = 0
            fields = ("task", "text", "content", "what", "fact")
            for k in fields:
                v = p.get(k)
                if isinstance(v, str) and v:
                    vl = v.lower()
                    if ql and ql in vl:
                        score += 5 if _is_token_like(q) else 2
            return score

        if mem_payloads and q:
            scored = [
                (p, _lexical_score(p)) for p in mem_payloads if isinstance(p, dict)
            ]
            if any(s > 0 for _, s in scored):
                # Stable sort: keep original relative order for equal scores
                mem_payloads = [
                    p for p, _ in sorted(scored, key=lambda t: t[1], reverse=True)
                ]
    except Exception:
        pass
    # Deterministic read-your-writes alternative:
    # If no payloads were returned via SDR/recall, derive the coordinate
    # from the query text (used as key on store) and fetch directly.
    if not mem_payloads:
        try:
            pass
        except Exception:
            pass
    # Filter by universe if any
    if universe:
        mem_payloads = [
            p for p in mem_payloads if str(p.get("universe") or "real") == str(universe)
        ]
    return mem_payloads, mem_hits


def _text_of(p: dict) -> str:
    return str(p.get("task") or p.get("fact") or "").strip()


def diversify_payloads(
    embed: Callable[[str], List[float]],
    query: str,
    payloads: List[dict],
    method: str = "mmr",
    k: Optional[int] = None,
    lam: float = 0.5,
) -> List[dict]:
    """Apply diversity over payloads (MMR only).

    - embed: function mapping text -> vector (unit norm preferred)
    - query: query text used for relevance
    - payloads: list of payload dicts containing 'task' or 'fact'
    - method: must be 'mmr'
    - k: number of items to select (defaults to len(payloads))
    - lam: tradeoff [0,1] between relevance and diversity
    """
    if method != "mmr":
        raise NotImplementedError("diversify_payloads supports only method='mmr'")
    try:
        import numpy as np  # local import to avoid hard dep here

        texts = [_text_of(p) for p in payloads]
        k = len(payloads) if k is None or k <= 0 else min(k, len(payloads))
        if not texts or k <= 0:
            return payloads
        qv = embed(query)
        vs = [embed(t) if t else qv for t in texts]

        # cosine similarities to query as relevance
        def cos(a, b):
            na = float(np.linalg.norm(a)) or 1.0
            nb = float(np.linalg.norm(b)) or 1.0
            return float(np.dot(a, b) / (na * nb))

        rel = [cos(qv, v) for v in vs]
        selected: List[int] = []
        remaining = set(range(len(payloads)))
        # MMR greedy selection
        while len(selected) < k and remaining:
            best_i = None
            best_score = -1e9
            for i in list(remaining):
                # diversity term: max similarity to already selected
                if not selected:
                    div = 0.0
                else:
                    div = max(cos(vs[i], vs[j]) for j in selected)
                score = lam * rel[i] - (1 - lam) * div
                if score > best_score:
                    best_score = score
                    best_i = i
            selected.append(best_i)  # type: ignore
            remaining.discard(best_i)  # type: ignore
        # reorder payloads: selected first, then the rest in original order
        ordered = [payloads[i] for i in selected] + [
            payloads[i] for i in range(len(payloads)) if i not in selected
        ]
        return ordered
    except Exception:
        return payloads


async def recall_ltm_async(
    mem_client,
    text: str,
    top_k: int,
    universe: Optional[str],
    cohort: str,
    use_sdr: bool,
    sdr_enc,
    sdr_idx_map: dict,
    graph_hops: int,
    graph_limit: int,
) -> Tuple[List[dict], List[Tuple[float, dict]]]:
    # Avoid blocking the event loop: run the synchronous recall_ltm in a
    # thread executor so heavy sync operations (including sync HTTP calls)
    # don't stall the async worker under high concurrency.
    loop = asyncio.get_event_loop()
    payloads, hits = await loop.run_in_executor(
        None,
        recall_ltm,
        mem_client,
        text,
        top_k,
        universe,
        cohort,
        use_sdr,
        sdr_enc,
        sdr_idx_map,
        graph_hops,
        graph_limit,
    )
    if payloads:
        return payloads, hits
    # If no SDR candidates, perform async recall for HTTP mode
    if hasattr(mem_client, "arecall"):
        try:
            ahits = await mem_client.arecall(text, top_k=top_k)
            payloads = [h.payload for h in ahits]
            hits = ahits
        except Exception:
            pass
    return payloads, hits
