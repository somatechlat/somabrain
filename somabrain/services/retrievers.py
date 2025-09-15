from __future__ import annotations

from typing import List

from somabrain.schemas import RAGCandidate


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
) -> list[RAGCandidate]:
    try:
        qv = embedder.embed(query)
        hits = (mc_wm if use_microcircuits else mt_wm).recall(
            tenant_id, qv, top_k=top_k
        )
        out: list[RAGCandidate] = []
        for score, payload in hits:
            out.append(
                RAGCandidate(
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
    query: str, top_k: int, *, mem_client, embedder, universe: str | None = None
) -> list[RAGCandidate]:
    try:
        # Best-effort recall via client; scores may be unavailable -> score by cosine
        hits = getattr(mem_client, "recall")(query, top_k=top_k, universe=universe)
        qv = embedder.embed(query)
        out: list[RAGCandidate] = []
        for h in hits:
            payload = getattr(h, "payload", h)
            txt = _text_of(payload)
            try:
                import numpy as np

                pv = embedder.embed(txt) if txt else qv
                na = float(np.linalg.norm(qv)) or 1.0
                nb = float(np.linalg.norm(pv)) or 1.0
                score = float(np.dot(qv, pv) / (na * nb))
            except Exception:
                score = 0.0
            out.append(
                RAGCandidate(
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
    except Exception:
        return []


def retrieve_graph(
    query: str,
    top_k: int,
    *,
    mem_client,
    embedder,
    hops: int = 1,
    limit: int = 20,
    universe: str | None = None,
) -> list[RAGCandidate]:
    """Graph retriever with RAG-aware traversal.

    1) Prefer explicit rag_session -> retrieved_with traversal to surface linked docs.
    2) Fallback to generic k-hop BFS.
    3) Score by cosine to query embedding.
    """
    try:
        import numpy as np

        qv = embedder.embed(query)
        start = mem_client.coord_for_key(query, universe=universe)
        # Attempt explicit two-hop traversal
        doc_coords: list[tuple] = []
        try:
            sess_edges = mem_client.links_from(
                start, type_filter="rag_session", limit=max(1, int(limit))
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
                        doc_coords.append(tuple(d_to))
        except Exception:
            doc_coords = []
        coords: list[tuple]
        if doc_coords:
            # Deduplicate and bound
            seen = set()
            coords = []
            for c in doc_coords:
                if c not in seen:
                    seen.add(c)
                    coords.append(c)
            coords = coords[: max(1, int(limit))]
        else:
            # Generic BFS fallback
            coords = mem_client.k_hop(
                [start], depth=max(1, int(hops)), limit=max(1, int(limit))
            )
        payloads = mem_client.payloads_for_coords(coords, universe=universe)
        out: list[RAGCandidate] = []
        for p in payloads:
            txt = _text_of(p)
            try:
                pv = embedder.embed(txt) if txt else qv
                na = float(np.linalg.norm(qv)) or 1.0
                nb = float(np.linalg.norm(pv)) or 1.0
                score = float(np.dot(qv, pv) / (na * nb))
            except Exception:
                score = 0.0
            out.append(
                RAGCandidate(
                    coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                    key=str(p.get("task") or p.get("id") or "") or None,
                    score=score,
                    retriever="graph",
                    payload=p,
                )
            )
        out.sort(key=lambda c: float(c.score), reverse=True)
        return out[: max(1, int(top_k))]
    except Exception:
        return []


def retrieve_lexical(query: str, top_k: int, *, mem_client) -> list[RAGCandidate]:
    """Simple lexical retriever over all_memories() when available.

    Scoring: token overlap count (case-insensitive) with crude IDF proxy via token length.
    Falls back to [] if the backend cannot enumerate memories (e.g., HTTP mode).
    """
    try:
        corpus = getattr(mem_client, "all_memories")()
        if not corpus:
            return []
        qtokens = {t for t in str(query).lower().split() if t}
        if not qtokens:
            return []
        scored: list[tuple[float, dict]] = []
        for p in corpus:
            text = str(p.get("task") or p.get("fact") or "").lower()
            if not text:
                continue
            ptoks = set(text.split())
            overlap = qtokens & ptoks
            if not overlap:
                continue
            # crude weighting: longer tokens contribute slightly more
            score = sum(max(1.0, float(len(t)) / 6.0) for t in overlap)
            scored.append((score, p))
        scored.sort(key=lambda t: t[0], reverse=True)
        out: list[RAGCandidate] = []
        for s, p in scored[: max(1, int(top_k))]:
            out.append(
                RAGCandidate(
                    coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                    key=str(p.get("task") or p.get("id") or "") or None,
                    score=float(s),
                    retriever="lexical",
                    payload=p,
                )
            )
        return out
    except Exception:
        return []


def _fake_payload(i: int) -> dict:
    return {"task": f"stub_doc_{i}", "memory_type": "episodic", "importance": 1}


def retrieve_wm_stub(query: str, top_k: int) -> List[RAGCandidate]:
    """Return k canned WM candidates (stub)."""
    return [
        RAGCandidate(
            coord=None,
            key=f"wm::{i}",
            score=max(0.0, 1.0 - 0.05 * i),
            retriever="wm",
            payload=_fake_payload(i),
        )
        for i in range(max(0, int(top_k)))
    ]


def retrieve_vector_stub(query: str, top_k: int) -> List[RAGCandidate]:
    """Return k canned vector candidates (stub)."""
    return [
        RAGCandidate(
            coord=None,
            key=f"vec::{i}",
            score=max(0.0, 0.9 - 0.04 * i),
            retriever="vector",
            payload=_fake_payload(100 + i),
        )
        for i in range(max(0, int(top_k)))
    ]


def retrieve_graph_stub(query: str, top_k: int) -> List[RAGCandidate]:
    """Return k canned graph candidates (stub)."""
    return [
        RAGCandidate(
            coord=None,
            key=f"graph::{i}",
            score=max(0.0, 0.8 - 0.03 * i),
            retriever="graph",
            payload=_fake_payload(200 + i),
        )
        for i in range(max(0, int(top_k)))
    ]
