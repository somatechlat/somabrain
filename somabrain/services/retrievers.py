from __future__ import annotations

from typing import Tuple

from somabrain.schemas import RetrievalCandidate
import logging
from somabrain.services import retrieval_cache


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

        def _candidates_from_cache(entries: list[dict]) -> list[RetrievalCandidate]:
            out_cached: list[RetrievalCandidate] = []
            for entry in entries:
                payload = entry.get("payload") or {}
                if not isinstance(payload, dict):
                    payload = {"raw": payload}
                coord = entry.get("coordinate")
                coord_str = None
                if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                    coord_str = ",".join(str(float(c)) for c in coord[:3])
                key = str(payload.get("task") or payload.get("id") or "") or None
                out_cached.append(
                    RetrievalCandidate(
                        coord=coord_str,
                        key=key,
                        score=float(entry.get("score", 0.0) or 0.0),
                        retriever=str(entry.get("retriever") or "graph"),
                        payload=payload,
                    )
                )
            return out_cached

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
    _log = logging.getLogger(__name__)
    try:
        # Best-effort recall via client; scores may be unavailable -> score by cosine
        hits = getattr(mem_client, "recall")(query, top_k=top_k, universe=universe)
        qv = embedder.embed(query)
        out: list[RetrievalCandidate] = []
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
        # Fallback: if no hits from backend (HTTP mode), try cached candidates from a
        # previous persist and re-score by cosine similarity.
        if not out:
            try:
                # Prefer explicit namespace provided by caller; fall back to client config
                ns_eff = namespace
                if ns_eff is None:
                    ns_eff = getattr(mem_client, "namespace", None)
                if ns_eff is None:
                    ns_eff = getattr(getattr(mem_client, "cfg", None), "namespace", None)
                cached = retrieval_cache.get_candidates(ns_eff, query)
                if not cached and ns_eff is not None:
                    # Namespace-wide conservative fallback
                    cached = retrieval_cache.get_candidates_any(ns_eff)
                try:
                    _log.info(
                        "vector.fallback: ns=%r query=%r cached=%d",
                        ns_eff,
                        query,
                        len(cached or []),
                    )
                except Exception:
                    pass
                if cached:
                    import numpy as np

                    rescored: list[RetrievalCandidate] = []
                    for entry in cached:
                        p = entry.get("payload") or {}
                        txt = _text_of(p)
                        try:
                            pv = embedder.embed(txt) if txt else qv
                            na = float(np.linalg.norm(qv)) or 1.0
                            nb = float(np.linalg.norm(pv)) or 1.0
                            score = float(np.dot(qv, pv) / (na * nb))
                        except Exception:
                            score = float(entry.get("score") or 0.0)
                        rescored.append(
                            RetrievalCandidate(
                                coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                                key=str(p.get("task") or p.get("id") or "") or None,
                                score=score,
                                retriever="vector",
                                payload=p,
                            )
                        )
                    rescored.sort(key=lambda c: float(c.score), reverse=True)
                    return rescored[: max(1, int(top_k))]
            except Exception:
                pass
        return out[: max(1, int(top_k))]
    except Exception:
        # Attempt cache-based fallback even on errors
        try:
            ns_eff = namespace
            if ns_eff is None:
                ns_eff = getattr(mem_client, "namespace", None)
            if ns_eff is None:
                ns_eff = getattr(getattr(mem_client, "cfg", None), "namespace", None)
            cached = retrieval_cache.get_candidates(ns_eff, query)
            if not cached and ns_eff is not None:
                cached = retrieval_cache.get_candidates_any(ns_eff)
            try:
                _log.info(
                    "vector.error_fallback: ns=%r query=%r cached=%d",
                    ns_eff,
                    query,
                    len(cached or []),
                )
            except Exception:
                pass
            if cached:
                import numpy as np

                qv = embedder.embed(query)
                rescored: list[RetrievalCandidate] = []
                for entry in cached:
                    p = entry.get("payload") or {}
                    txt = _text_of(p)
                    try:
                        pv = embedder.embed(txt) if txt else qv
                        na = float(np.linalg.norm(qv)) or 1.0
                        nb = float(np.linalg.norm(pv)) or 1.0
                        score = float(np.dot(qv, pv) / (na * nb))
                    except Exception:
                        score = float(entry.get("score") or 0.0)
                    rescored.append(
                        RetrievalCandidate(
                            coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                            key=str(p.get("task") or p.get("id") or "") or None,
                            score=score,
                            retriever="vector",
                            payload=p,
                        )
                    )
                rescored.sort(key=lambda c: float(c.score), reverse=True)
                return rescored[: max(1, int(top_k))]
        except Exception:
            pass
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
    namespace: str | None = None,

) -> list[RetrievalCandidate]:
    """Graph retriever with retrieval-aware traversal.

    1) Prefer explicit recall_session -> retrieved_with traversal to surface linked docs.
    2) Fallback to generic k-hop BFS.
    3) Score by cosine to query embedding.
    """
    try:
        import numpy as np

        qv = embedder.embed(query)

        def _candidates_from_cache(entries: list[dict]) -> list[RetrievalCandidate]:
            out_cached: list[RetrievalCandidate] = []
            for entry in entries:
                payload = entry.get("payload") or {}
                if not isinstance(payload, dict):
                    payload = {"raw": payload}
                coord = entry.get("coordinate")
                coord_str = None
                if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                    coord_str = ",".join(str(float(c)) for c in coord[:3])
                key = str(payload.get("task") or payload.get("id") or "") or None
                out_cached.append(
                    RetrievalCandidate(
                        coord=coord_str,
                        key=key,
                        score=float(entry.get("score", 0.0) or 0.0),
                        retriever=str(entry.get("retriever") or "graph"),
                        payload=payload,
                    )
                )
            return out_cached

        start = mem_client.coord_for_key(query, universe=universe)
        # Attempt explicit two-hop traversal
        doc_coords: list[tuple] = []
        boost_coords: set[tuple] = set()
        try:
            sess_edges = mem_client.links_from(
                start, type_filter="recall_session", limit=max(1, int(limit))
            )
            # Per-coordinate learned-link bonus (typed weights)
            boost_map: dict[tuple, float] = {}
            typed_bonus = {"retrieved_with": 0.05, "uses_tool": 0.05}
            for e in sess_edges:
                s_to = e.get("to")
                if not (isinstance(s_to, (list, tuple)) and len(s_to) >= 3):
                    continue
                # Learned docs from this session
                doc_edges = mem_client.links_from(
                    tuple(s_to), type_filter="retrieved_with", limit=max(1, int(limit))
                )
                for de in doc_edges:
                    d_to = de.get("to")
                    if isinstance(d_to, (list, tuple)) and len(d_to) >= 3:
                        t = tuple(d_to)
                        doc_coords.append(t)
                        boost_coords.add(t)
                        boost_map[t] = (
                            boost_map.get(t, 0.0) + typed_bonus["retrieved_with"]
                        )
                # Learned tools from this session (optional)
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
        if not coords and namespace is not None:
            cached = retrieval_cache.get_candidates(namespace, query)
            if cached:
                return _candidates_from_cache(cached)[: max(1, int(top_k))]
        if not coords:
            # No graph edges found; fall back to vector similarity search
            return retrieve_vector(
                query, top_k, mem_client=mem_client, embedder=embedder
            )
        payloads = mem_client.payloads_for_coords(coords, universe=universe)
        if (not payloads) and namespace is not None:
            cached = retrieval_cache.get_candidates(namespace, query)
            payloads = []
            for coord in coords:
                for entry in cached:
                    entry_coord = entry.get("coordinate")
                    if (
                        not isinstance(entry_coord, (list, tuple))
                        or len(entry_coord) < 3
                    ):
                        continue
                    if all(
                        abs(float(coord[i]) - float(entry_coord[i])) <= 1e-6
                        for i in range(3)
                    ):
                        payload = entry.get("payload") or {}
                        if not isinstance(payload, dict):
                            payload = {"raw": payload}
                        payloads.append(payload)
                        break
            if not payloads and cached:
                return _candidates_from_cache(cached)[: max(1, int(top_k))]
        if not payloads:
            # Final safeguard: degrade to vector retriever if payloads unavailable
            return retrieve_vector(
                query, top_k, mem_client=mem_client, embedder=embedder
            )
        out: list[RetrievalCandidate] = []
        for p in payloads:
            txt = _text_of(p)
            try:
                pv = embedder.embed(txt) if txt else qv
                na = float(np.linalg.norm(qv)) or 1.0
                nb = float(np.linalg.norm(pv)) or 1.0
                score = float(np.dot(qv, pv) / (na * nb))
                # Apply learned-link bonus if present (typed-link weights)
                try:
                    c = p.get("coordinate")
                    if isinstance(c, (list, tuple)) and len(c) >= 3:
                        bonus = 0.0
                        t = (float(c[0]), float(c[1]), float(c[2]))
                        bonus = (
                            boost_map.get(t, 0.0) if "boost_map" in locals() else 0.0
                        )
                        score += float(bonus)
                except Exception:
                    pass
                # Small boost if this coord came via retrieved_with path (session learning)
                try:
                    c = p.get("coordinate")
                    if isinstance(c, (list, tuple)) and len(c) >= 3:
                        if tuple(c[:3]) in boost_coords:
                            score += 0.05
                except Exception:
                    pass
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
    except Exception as e:
        if "405 Method Not Allowed" in str(e):
            # Direct fallback to cache without vector
            return retrieval_cache.get_candidates(namespace, query)
        else:
            raise


_BM25_CACHE: dict[str, tuple[object, int, list[dict]]] = {}


def retrieve_lexical(
    query: str, top_k: int, *, mem_client, namespace: str | None = None
) -> list[RetrievalCandidate]:
    """BM25 lexical retriever over all_memories() when available.

    - Uses rank_bm25 if installed; otherwise falls back to simple token overlap.
    - Returns [] if the backend cannot enumerate memories (e.g., HTTP mode).
    """
    try:
        corpus = getattr(mem_client, "all_memories")()
    except Exception:
        corpus = []
    # If the backend cannot enumerate memories (HTTP mode), fall back to any cached
    # candidates persisted for this namespace+query and re-score lexically.
    if not corpus:
        try:
            # Prefer explicit namespace if provided; fall back to client config
            ns_eff = namespace
            if ns_eff is None:
                ns_eff = getattr(mem_client, "namespace", None)
            if ns_eff is None:
                ns_eff = getattr(getattr(mem_client, "cfg", None), "namespace", None)
            cached = retrieval_cache.get_candidates(ns_eff, query)
            if not cached and ns_eff is not None:
                cached = retrieval_cache.get_candidates_any(ns_eff)
            try:
                logging.getLogger(__name__).info(
                    "lexical.fallback: ns=%r query=%r cached=%d",
                    ns_eff,
                    query,
                    len(cached or []),
                )
            except Exception:
                pass
            if not cached:
                return []
            # Extract payload texts from cached candidates
            docs: list[Tuple[str, dict]] = []
            for entry in cached:
                payload = entry.get("payload") or {}
                try:
                    t = _text_of(payload)
                    if t:
                        docs.append((t, payload))
                except Exception:
                    continue
            if not docs:
                return []
            # Simple token-overlap scoring as lexical proxy when BM25 is unavailable
            import re

            def _tok(s: str) -> list[str]:
                return re.findall(r"\w+", s.lower())

            qtokens = set(_tok(str(query)))
            if not qtokens:
                return []
            scored: list[Tuple[float, dict]] = []
            for text, p in docs:
                ptoks = set(_tok(text))
                overlap = qtokens & ptoks
                if not overlap:
                    continue
                score = sum(max(1.0, float(len(t)) / 6.0) for t in overlap)
                scored.append((float(score), p))
            scored.sort(key=lambda t: t[0], reverse=True)
            out: list[RetrievalCandidate] = []
            for s, p in scored[: max(1, int(top_k))]:
                out.append(
                    RetrievalCandidate(
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

    # Extract texts and keep mapping
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

    # Try rank_bm25 with per-namespace cache; else overlap fallback
    try:
        import re

        from rank_bm25 import BM25Okapi  # type: ignore

        def _tok(s: str) -> list[str]:
            return re.findall(r"\w+", s.lower())

        # Namespace key for cache
        ns = None
        try:
            ns = getattr(getattr(mem_client, "cfg", None), "namespace", None)
        except Exception:
            ns = None
        key = str(ns or id(mem_client))
        cache = _BM25_CACHE.get(key)
        if cache is None or cache[1] != len(docs):
            tokenized_corpus = [_tok(t) for t, _ in docs]
            bm25 = BM25Okapi(tokenized_corpus)
            _BM25_CACHE[key] = (bm25, len(docs), [p for _, p in docs])
        else:
            bm25 = cache[0]
        scores = bm25.get_scores(_tok(str(query)))  # type: ignore[attr-defined]
        order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
        out: list[RetrievalCandidate] = []
        for i in order[: max(1, int(top_k))]:
            text, p = docs[i]
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
        # Fallback: token overlap scoring
        import re

        def _tok(s: str) -> list[str]:
            return re.findall(r"\w+", s.lower())

        qtokens = set(_tok(str(query)))
        if not qtokens:
            return []
        scored: list[Tuple[float, dict]] = []
        for text, p in docs:
            ptoks = set(_tok(text))
            overlap = qtokens & ptoks
            if not overlap:
                continue
            score = sum(max(1.0, float(len(t)) / 6.0) for t in overlap)
            scored.append((float(score), p))
        scored.sort(key=lambda t: t[0], reverse=True)
        out_scored: list[RetrievalCandidate] = []
        for s, p in scored[: max(1, int(top_k))]:
            out_scored.append(
                RetrievalCandidate(
                    coord=str(p.get("coordinate")) if p.get("coordinate") else None,
                    key=str(p.get("task") or p.get("id") or "") or None,
                    score=float(s),
                    retriever="lexical",
                    payload=p,
                )
            )
        return out_scored
