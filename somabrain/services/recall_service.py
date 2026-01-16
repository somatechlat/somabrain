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
from ..math import cosine_similarity
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
            # SDR prefilter found candidates but payloads_for_coords is not available
            did_sdr = False
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug(
                "SDR prefilter failed for cohort=%s: %s", cohort, exc
            )
            did_sdr = False
    if not did_sdr:
        hits = getattr(mem_client, "recall")(text, top_k=top_k)
        # hits may be RecallHit wrappers
        try:
            mem_payloads = [h.payload for h in hits]
            mem_hits = hits
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to extract payloads from recall hits: %s", exc
            )
            mem_payloads = []
        # If recall returned items but none lexically match the query, inject
        # a deterministic read-your-writes result derived from the query key.
        raw_query = str(text or "").strip()
        ql = raw_query.lower()

        def _lex_match(p: dict) -> bool:
            """Execute lex match.

            Args:
                p: The p.
            """

            for k in ("task", "text", "content", "what", "fact"):
                v = p.get(k)
                if isinstance(v, str) and v and (ql in v.lower() or v.lower() in ql):
                    return True
            return False

        try:
            if (
                raw_query
                and not any(_lex_match(p) for p in mem_payloads if isinstance(p, dict))
                and hasattr(mem_client, "coord_for_key")
                and hasattr(mem_client, "fetch_by_coord")
            ):
                fallback_payloads: List[dict] = []
                try:
                    coord = mem_client.coord_for_key(raw_query, universe)
                    fetched = mem_client.fetch_by_coord(coord, universe)
                    fallback_payloads = [p for p in fetched if isinstance(p, dict)]
                except Exception as exc:
                    import logging

                    logging.getLogger(__name__).debug(
                        "Fallback coord lookup failed for query=%r: %s",
                        raw_query[:50],
                        exc,
                    )
                    fallback_payloads = []
                if fallback_payloads:
                    deduped: List[dict] = []
                    for payload in fallback_payloads:
                        if payload not in mem_payloads:
                            deduped.append(payload)
                    if deduped:
                        mem_payloads = deduped + mem_payloads
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug(
                "Read-your-writes fallback failed: %s", exc
            )
    # Lexical/token-aware boost: if the query looks like a short unique token or
    # if any payload contains the exact query string, promote those payloads to
    # the top so users don't need manual tuning to find label-like memories.
    q = str(text or "").strip()
    ql_boost = q.lower()

    def _is_token_like(s: str) -> bool:
        # Heuristic: alnum/_/- only, length 6-64, includes both letters and digits
        """Execute is token like.

        Args:
            s: The s.
        """

        if not s or len(s) < 6 or len(s) > 64:
            return False
        if not re.match(r"^[A-Za-z0-9_-]+$", s):
            return False
        has_alpha = any(c.isalpha() for c in s)
        has_digit = any(c.isdigit() for c in s)
        return has_alpha and has_digit

    def _lexical_score(p: dict) -> int:
        # Score by exact contains in common fields; higher for exact token-like
        """Execute lexical score.

        Args:
            p: The p.
        """

        score = 0
        fields = ("task", "text", "content", "what", "fact")
        for k in fields:
            v = p.get(k)
            if isinstance(v, str) and v:
                vl = v.lower()
                if ql_boost and ql_boost in vl:
                    score += 5 if _is_token_like(q) else 2
        return score

    try:
        if mem_payloads and q:
            scored = [
                (p, _lexical_score(p)) for p in mem_payloads if isinstance(p, dict)
            ]
            if any(s > 0 for _, s in scored):
                # Stable sort: keep original relative order for equal scores
                mem_payloads = [
                    p for p, _ in sorted(scored, key=lambda t: t[1], reverse=True)
                ]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).debug("Lexical boost scoring failed: %s", exc)
    # Filter by universe if any
    if universe:
        mem_payloads = [
            p for p in mem_payloads if str(p.get("universe") or "real") == str(universe)
        ]
    return mem_payloads, mem_hits


def _text_of(p: dict) -> str:
    """Execute text of.

    Args:
        p: The p.
    """

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
        raise ValueError(
            f"Unsupported diversification method: '{method}'. "
            "Only 'mmr' (Maximal Marginal Relevance) is supported."
        )
    try:
        texts = [_text_of(p) for p in payloads]
        k = len(payloads) if k is None or k <= 0 else min(k, len(payloads))
        if not texts or k <= 0:
            return payloads
        qv = embed(query)
        vs = [embed(t) if t else qv for t in texts]

        # cosine similarities to query as relevance
        rel = [cosine_similarity(qv, v) for v in vs]
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
                    div = max(cosine_similarity(vs[i], vs[j]) for j in selected)
                score = lam * rel[i] - (1 - lam) * div
                if score > best_score:
                    best_score = score
                    best_i = i
            selected.append(best_i)
            remaining.discard(best_i)
        # reorder payloads: selected first, then the rest in original order
        ordered = [payloads[i] for i in selected] + [
            payloads[i] for i in range(len(payloads)) if i not in selected
        ]
        return ordered
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "MMR diversification failed, returning original order: %s", exc
        )
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
    """Execute recall ltm async.

    Args:
        mem_client: The mem_client.
        text: The text.
        top_k: The top_k.
        universe: The universe.
        cohort: The cohort.
        use_sdr: The use_sdr.
        sdr_enc: The sdr_enc.
        sdr_idx_map: The sdr_idx_map.
        graph_hops: The graph_hops.
        graph_limit: The graph_limit.
    """

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
        except Exception as exc:
            import logging

            logging.getLogger(__name__).debug("Async recall fallback failed: %s", exc)
    return payloads, hits
