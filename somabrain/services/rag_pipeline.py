from __future__ import annotations

from typing import List, Optional

from somabrain.schemas import RAGCandidate, RAGRequest, RAGResponse
from somabrain.services.retrievers import (retrieve_graph, retrieve_graph_stub,
                                           retrieve_lexical, retrieve_vector,
                                           retrieve_vector_stub, retrieve_wm,
                                           retrieve_wm_stub)


def _extract_text(payload: dict) -> str:
    return str(payload.get("task") or payload.get("fact") or "").strip()


async def run_rag_pipeline(
    req: RAGRequest,
    *,
    ctx,
    cfg=None,
    universe: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> RAGResponse:
    """Minimal, stubbed RAG pipeline for PR‑1.

    - Fans out to simple retriever stubs by name
    - Dedupes by key/coord
    - Orders by score desc
    - Optionally persists a session record (no-op in PR‑1)
    """
    retrievers = [r.strip().lower() for r in (req.retrievers or [])]
    top_k = max(1, int(req.top_k or 10))
    retriever_set = ",".join(
        sorted(set(retrievers or ["vector", "wm"])) or ["vector", "wm"]
    )[:64]

    # Metrics: count and latency timing
    _t0 = None
    try:
        import time as _time

        from somabrain import metrics as M

        M.RAG_REQUESTS.labels(namespace=ctx.namespace, retrievers=retriever_set).inc()
        _t0 = _time.perf_counter()
    except Exception:
        pass

    # Collect candidates by retriever name
    cands: List[RAGCandidate] = []
    lists_by_retriever: dict[str, List[RAGCandidate]] = {}
    if not retrievers:
        retrievers = ["vector", "wm"]
    # Try real adapters first if runtime singletons are available; fallback to stubs
    from somabrain import runtime as _rt

    mem_client = None
    try:
        if _rt.mt_memory is not None and hasattr(_rt.mt_memory, "for_namespace"):
            from somabrain.services.memory_service import MemoryService

            memsvc = MemoryService(_rt.mt_memory, ctx.namespace)
            mem_client = memsvc.client()
    except Exception:
        mem_client = None
    for rname in retrievers:
        if rname == "wm":
            if _rt.embedder is not None and (
                _rt.mt_wm is not None or _rt.mc_wm is not None
            ):
                try:
                    lst = retrieve_wm(
                        req.query,
                        top_k,
                        tenant_id=ctx.tenant_id,
                        embedder=_rt.embedder,
                        mt_wm=_rt.mt_wm,
                        mc_wm=_rt.mc_wm,
                        use_microcircuits=bool(
                            getattr(_rt.cfg, "use_microcircuits", False)
                        ),
                    )
                    lists_by_retriever["wm"] = lst
                    cands += lst
                    continue
                except Exception:
                    pass
            lst = retrieve_wm_stub(req.query, top_k)
            lists_by_retriever["wm"] = lst
            cands += lst
        elif rname == "vector":
            if _rt.embedder is not None and mem_client is not None:
                try:
                    lst = retrieve_vector(
                        req.query,
                        top_k,
                        mem_client=mem_client,
                        embedder=_rt.embedder,
                        universe=universe,
                    )
                    lists_by_retriever["vector"] = lst
                    cands += lst
                    continue
                except Exception:
                    pass
            lst = retrieve_vector_stub(req.query, top_k)
            lists_by_retriever["vector"] = lst
            cands += lst
        elif rname == "graph":
            if _rt.embedder is not None and mem_client is not None:
                try:
                    hops = int(getattr(_rt.cfg, "graph_hops", 1) or 1)
                    limit = int(getattr(_rt.cfg, "graph_limit", 20) or 20)
                    lst = retrieve_graph(
                        req.query,
                        top_k,
                        mem_client=mem_client,
                        embedder=_rt.embedder,
                        hops=hops,
                        limit=limit,
                        universe=universe,
                    )
                    lists_by_retriever["graph"] = lst
                    cands += lst
                    continue
                except Exception:
                    pass
            lst = retrieve_graph_stub(req.query, top_k)
            lists_by_retriever["graph"] = lst
            cands += lst
        elif rname == "lexical" and mem_client is not None:
            try:
                lst = retrieve_lexical(req.query, top_k, mem_client=mem_client)
                lists_by_retriever["lexical"] = lst
                cands += lst
                continue
            except Exception:
                pass
        else:
            # Unknown retriever; skip
            continue

    # If nothing retrieved, backfill with stubs to ensure endpoint responsiveness in empty stores
    if not cands:
        for rname in retrievers:
            if rname == "wm":
                cands += retrieve_wm_stub(req.query, top_k)
            elif rname == "vector":
                cands += retrieve_vector_stub(req.query, top_k)
            elif rname == "graph":
                cands += retrieve_graph_stub(req.query, top_k)

    # If nothing retrieved, backfill with stubs to ensure endpoint responsiveness in empty stores
    if not cands:
        for rname in retrievers:
            if rname == "wm":
                lst = retrieve_wm_stub(req.query, top_k)
                lists_by_retriever["wm"] = lst
                cands += lst
            elif rname == "vector":
                lst = retrieve_vector_stub(req.query, top_k)
                lists_by_retriever["vector"] = lst
                cands += lst
            elif rname == "graph":
                lst = retrieve_graph_stub(req.query, top_k)
                lists_by_retriever["graph"] = lst
                cands += lst

    # Rank fusion (RRF) over available retriever lists
    fusion_method = "rrf"
    rrf_k = 60.0
    # Build rank maps per retriever
    ranks: dict[str, dict[str, int]] = {}
    for rname, lst in lists_by_retriever.items():
        rm: dict[str, int] = {}
        for idx, c in enumerate(lst):
            kid = str(
                c.coord
                or c.key
                or (c.payload.get("task") if isinstance(c.payload, dict) else "")
            )
            if kid and kid not in rm:
                rm[kid] = idx + 1  # 1-based rank
        ranks[rname] = rm
    # Aggregate RRF scores
    keys = set()
    for rm in ranks.values():
        keys.update(rm.keys())
    fused: list[tuple[float, RAGCandidate]] = []
    from somabrain import metrics as _mx

    try:
        _mx.RAG_FUSION_APPLIED.labels(method=fusion_method).inc()
        _mx.RAG_FUSION_SOURCES.observe(len(lists_by_retriever))
    except Exception:
        pass
    # Build representative payload per key (prefer vector>wm>graph>lexical)
    pref = ["vector", "wm", "graph", "lexical"]
    for kid in keys:
        score = 0.0
        for rname, rm in ranks.items():
            r = rm.get(kid)
            if r is not None:
                score += 1.0 / (rrf_k + float(r))
        # choose a representative candidate
        rep = None
        for rname in pref:
            lst = lists_by_retriever.get(rname) or []
            for c in lst:
                cand_kid = str(
                    c.coord
                    or c.key
                    or (c.payload.get("task") if isinstance(c.payload, dict) else "")
                )
                if cand_kid == kid:
                    rep = c
                    break
            if rep is not None:
                break
        if rep is None:
            continue
        fused.append((score, rep))
    fused.sort(key=lambda t: t[0], reverse=True)
    out = [
        RAGCandidate(
            coord=c.coord,
            key=c.key,
            score=float(s),  # fused score
            retriever=c.retriever,
            payload=c.payload,
        )
        for s, c in fused
    ]
    # Rerank policy
    method = (req.rerank or "cosine").strip().lower()
    if method == "mmr":
        try:
            from somabrain.services.recall_service import diversify_payloads

            payloads = [c.payload for c in out]
            ordered = diversify_payloads(
                embed=lambda t: _rt.embedder.embed(t),
                query=req.query,
                payloads=payloads,
                method="mmr",
                k=min(top_k, len(payloads)),
                lam=0.5,
            )
            # Map back by object id
            id2cand = {id(c.payload): c for c in out}
            out = [id2cand.get(id(p)) for p in ordered if id2cand.get(id(p))]
        except Exception:
            pass
    elif method == "hrr":
        try:
            if _rt.quantum is not None:
                hq = _rt.quantum.encode_text(req.query)

                def _cos(a, b):
                    from somabrain.quantum import QuantumLayer

                    return float(QuantumLayer.cosine(a, b))

                # recompute scores as HRR cosine
                new = []
                for c in out:
                    txt = _extract_text(c.payload)
                    if not txt:
                        new.append((c.score, c))
                        continue
                    hv = _rt.quantum.encode_text(txt)
                    sc = _cos(hq, hv)
                    new.append((sc, c))
                new.sort(key=lambda t: t[0], reverse=True)
                out = [c for _, c in new]
        except Exception:
            pass
    # Default: fused order is already desc by score
    out = out[:top_k]

    # Record latency and candidate count
    try:
        import time as _time

        from somabrain import metrics as M

        if _t0 is not None:
            M.RAG_RETRIEVE_LAT.observe(max(0.0, _time.perf_counter() - _t0))
        M.RAG_CANDIDATES.observe(len(out))
    except Exception:
        pass

    # Optional persistence of session + links (PR‑3)
    session_coord_str: Optional[str] = None
    if bool(req.persist):
        try:
            import time as _time

            from somabrain.services.memory_service import MemoryService

            if _rt.mt_memory is not None:
                memsvc = MemoryService(_rt.mt_memory, ctx.namespace)
                # Build session payload with provenance and top candidates summary
                sess_key = f"rag_session::{trace_id or ''}::{int(_time.time()*1000)}"
                sess_payload = {
                    "task": f"RAG session for '{req.query[:64]}'",
                    "memory_type": "episodic",
                    "rag": {
                        "query": req.query,
                        "retrievers": retrievers,
                        "rerank": req.rerank,
                        "top_k": top_k,
                        "candidates": [
                            {"key": c.key, "retriever": c.retriever, "score": c.score}
                            for c in out
                        ],
                    },
                    "universe": universe or None,
                }
                sess_coord = await memsvc.aremember(
                    sess_key, sess_payload, universe=universe
                )
                # Convert coord tuple -> string for response if available
                if isinstance(sess_coord, (tuple, list)) and len(sess_coord) >= 3:
                    session_coord_str = f"{float(sess_coord[0])},{float(sess_coord[1])},{float(sess_coord[2])}"
                # Link query-key -> session (so future graph queries from the same query reach this session)
                try:
                    qcoord = memsvc.coord_for_key(req.query, universe=universe)
                    if isinstance(sess_coord, (tuple, list)) and len(sess_coord) >= 3:
                        await memsvc.alink(
                            qcoord, sess_coord, link_type="rag_session", weight=1.0
                        )
                except Exception:
                    pass

                # Link session -> candidates
                for c in out:
                    # Prefer explicit coordinate in payload; fallback to key-derived coord
                    pc = (
                        c.payload.get("coordinate")
                        if isinstance(c.payload, dict)
                        else None
                    )
                    if isinstance(pc, (list, tuple)) and len(pc) >= 3:
                        doc_coord = (float(pc[0]), float(pc[1]), float(pc[2]))
                    else:
                        key_for_coord = c.key or (
                            c.payload.get("task")
                            if isinstance(c.payload, dict)
                            else None
                        )
                        if key_for_coord:
                            doc_coord = memsvc.coord_for_key(
                                str(key_for_coord), universe=universe
                            )
                        else:
                            continue
                    if isinstance(sess_coord, (tuple, list)) and len(sess_coord) >= 3:
                        try:
                            await memsvc.alink(
                                sess_coord,
                                doc_coord,
                                link_type="retrieved_with",
                                weight=1.0,
                            )
                        except Exception:
                            pass
                try:
                    from somabrain import metrics as M

                    M.RAG_PERSIST.labels(status="success").inc()
                except Exception:
                    pass
        except Exception:
            try:
                from somabrain import metrics as M

                M.RAG_PERSIST.labels(status="failure").inc()
            except Exception:
                pass

    return RAGResponse(
        candidates=out,
        session_coord=session_coord_str,
        namespace=ctx.namespace,
        trace_id=trace_id or "",
        metrics=None,
    )
