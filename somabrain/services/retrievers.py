from __future__ import annotations

from typing import Tuple

from somabrain.schemas import RetrievalCandidate
import logging

# No retrieval cache alternatives are used in strict mode.


# Real adapters (PR‑2)
def _text_of(p: dict) -> str:
    try:
        from somabrain.services.recall_service import _text_of as _inner

        return _inner(p)
    except Exception:
        return str(p.get("task") or p.get("fact") or "").strip()


def retrieve_wm(
    query: str,
    top_k: int,
    *,
    tenant_id: str,
    embedder,
    mt_wm,
    mc_wm,
    use_microcircuits: bool,
) -> list[RetrievalCandidate]:
    try:
        qv = embedder.embed(query)
        hits = (mc_wm if use_microcircuits else mt_wm).recall(
            tenant_id, qv, top_k=top_k
        )
        out: list[RetrievalCandidate] = []
        for score, payload in hits:
            out.append(
                RetrievalCandidate(
                    coord=(
                        str(payload.get("coordinate"))
                        if payload.get("coordinate")
                        else None
                    ),
                    key=str(payload.get("task") or payload.get("id") or "") or None,
                    score=float(score),
                    retriever="wm",
                    payload=payload,
                )
            )
        return out
    except Exception:
        return []


def retrieve_vector(
    query: str,
    top_k: int,
    *,
    mem_client,
    embedder,
    universe: str | None = None,
    namespace: str | None = None,
) -> list[RetrievalCandidate]:
    """Strict vector retriever.

    Performs direct recall via the memory client and computes cosine scores.
    No cache, namespace, or error alternatives are applied. Empty list returned
    on any error or when backend yields no hits.
    """
    try:
        hits = getattr(mem_client, "recall")(query, top_k=top_k, universe=universe)
    except Exception:
        return []
    if not hits:
        return []
    try:
        import numpy as np
    except Exception:
        np = None  # type: ignore
    try:
        qv = embedder.embed(query)
    except Exception:
        return []
    out: list[RetrievalCandidate] = []
    for h in hits:
        payload = getattr(h, "payload", h)
        txt = _text_of(payload)
        score = 0.0
        if np is not None:
            try:
                pv = embedder.embed(txt) if txt else qv
                na = float(np.linalg.norm(qv)) or 1.0
                nb = float(np.linalg.norm(pv)) or 1.0
                score = float(np.dot(qv, pv) / (na * nb))
            except Exception:
                score = 0.0
        out.append(
            RetrievalCandidate(
                coord=(
                    str(payload.get("coordinate"))
                    if payload.get("coordinate")
                    else None
                ),
                key=str(payload.get("task") or payload.get("id") or "") or None,
                score=score,
                retriever="vector",
                payload=payload,
            )
        )
    return out[: max(1, int(top_k))]


def retrieve_graph(
    query: str,
    top_k: int,
    *,
    mem_client,
    embedder,
    hops: int = 1,
    limit: int = 20,
    universe: str | None = None,
    namespace: str | None = None,
) -> list[RetrievalCandidate]:
    """Strict graph retriever.

    Traverses learned links only (recall_session -> retrieved_with, uses_tool).
    No BFS, vector, or cache degradations; returns [] if links or payloads
    unavailable.
    """
    try:
        import numpy as np
    except Exception:
        np = None  # type: ignore
    try:
        qv = embedder.embed(query)
    except Exception:
        return []
    try:
        start = mem_client.coord_for_key(query, universe=universe)
    except Exception:
        return []
    doc_coords: list[tuple] = []
    boost_coords: set[tuple] = set()
    boost_map: dict[tuple, float] = {}
    typed_bonus = {"retrieved_with": 0.05, "uses_tool": 0.05}
    try:
        sess_edges = mem_client.links_from(
            start, type_filter="recall_session", limit=max(1, int(limit))
        )
        for e in sess_edges:
            s_to = e.get("to")
            if not (isinstance(s_to, (list, tuple)) and len(s_to) >= 3):
                continue
            doc_edges = mem_client.links_from(
                tuple(s_to), type_filter="retrieved_with", limit=max(1, int(limit))
            )
            for de in doc_edges:
                d_to = de.get("to")
                if isinstance(d_to, (list, tuple)) and len(d_to) >= 3:
                    t = tuple(d_to)
                    doc_coords.append(t)
                    boost_coords.add(t)
                    boost_map[t] = boost_map.get(t, 0.0) + typed_bonus["retrieved_with"]
            try:
                tool_edges = mem_client.links_from(
                    tuple(s_to), type_filter="uses_tool", limit=max(1, int(limit))
                )
                for te in tool_edges:
                    t_to = te.get("to")
                    if isinstance(t_to, (list, tuple)) and len(t_to) >= 3:
                        tt = tuple(t_to)
                        doc_coords.append(tt)
                        boost_coords.add(tt)
                        boost_map[tt] = (
                            boost_map.get(tt, 0.0) + typed_bonus["uses_tool"]
                        )
            except Exception:
                pass
    except Exception:
        return []
    if not doc_coords:
        return []
    seen = set()
    coords: list[tuple] = []
    for c in doc_coords:
        if c not in seen:
            seen.add(c)
            coords.append(c)
    coords = coords[: max(1, int(limit))]
    if not coords:
        return []
    try:
        payloads = mem_client.payloads_for_coords(coords, universe=universe)
    except Exception:
        return []
    if not payloads:
        return []
    out: list[RetrievalCandidate] = []
    for p in payloads:
        txt = _text_of(p)
        score = 0.0
        if np is not None:
            try:
                pv = embedder.embed(txt) if txt else qv
                na = float(np.linalg.norm(qv)) or 1.0
                nb = float(np.linalg.norm(pv)) or 1.0
                score = float(np.dot(qv, pv) / (na * nb))
                c = p.get("coordinate")
                if isinstance(c, (list, tuple)) and len(c) >= 3:
                    t = (float(c[0]), float(c[1]), float(c[2]))
                    score += float(boost_map.get(t, 0.0))
                    if tuple(c[:3]) in boost_coords:
                        score += 0.05
            except Exception:
                score = 0.0
        out.append(
            RetrievalCandidate(
                coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                key=str(p.get("task") or p.get("id") or "") or None,
                score=score,
                retriever="graph",
                payload=p,
            )
        )
    out.sort(key=lambda c: float(c.score), reverse=True)
    return out[: max(1, int(top_k))]


_BM25_CACHE: dict[str, tuple[object, int, list[dict]]] = {}


def retrieve_lexical(
    query: str, top_k: int, *, mem_client, namespace: str | None = None
) -> list[RetrievalCandidate]:
    """Strict lexical retriever.

    Requires backend to enumerate memories via all_memories(). Uses BM25 if
    rank_bm25 is installed; returns [] otherwise. No cache or token-overlap
    alternatives.
    """
    try:
        corpus = getattr(mem_client, "all_memories")()
    except Exception:
        return []
    if not corpus:
        return []
    docs: list[Tuple[str, dict]] = []
    for p in corpus:
        try:
            t = _text_of(p)
            if t:
                docs.append((t, p))
        except Exception:
            continue
    if not docs:
        return []
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
        import re

        def _tok(s: str) -> list[str]:
            return re.findall(r"\w+", s.lower())

        tokenized_corpus = [_tok(t) for t, _ in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(_tok(str(query)))  # type: ignore[attr-defined]
        order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
        out: list[RetrievalCandidate] = []
        for i in order[: max(1, int(top_k))]:
            _, p = docs[i]
            s = float(scores[i])
            out.append(
                RetrievalCandidate(
                    coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                    key=str(p.get("task") or p.get("id") or "") or None,
                    score=s,
                    retriever="lexical",
                    payload=p,
                )
            )
        return out
    except Exception:
        return []
