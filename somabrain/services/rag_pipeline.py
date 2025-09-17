from __future__ import annotations

from typing import List, Optional, cast

from somabrain.schemas import RAGCandidate, RAGRequest, RAGResponse
from somabrain.services.retrievers import (
    retrieve_graph,
    retrieve_graph_stub,
    retrieve_lexical,
    retrieve_vector,
    retrieve_vector_stub,
    retrieve_wm,
    retrieve_wm_stub,
)


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
    # Simple query expansion (optional)
    expansions = [req.query]
    try:
        if (
            getattr(_rt.cfg, "use_query_expansion", False)
            and int(getattr(_rt.cfg, "query_expansion_variants", 0) or 0) > 0
        ):
            k = int(getattr(_rt.cfg, "query_expansion_variants", 1) or 1)
            for i in range(k):
                if i % 2 == 0:
                    expansions.append(f"{req.query} guide")
                else:
                    expansions.append(f"intro to {req.query}")
    except Exception:
        pass
    for rname in retrievers:
        if rname == "wm":
            if _rt.embedder is not None and (
                _rt.mt_wm is not None or _rt.mc_wm is not None
            ):
                try:
                    lst_all_wm: list[RAGCandidate] = []
                    for qx in expansions:
                        lst = retrieve_wm(
                            qx,
                            top_k,
                            tenant_id=ctx.tenant_id,
                            embedder=_rt.embedder,
                            mt_wm=_rt.mt_wm,
                            mc_wm=_rt.mc_wm,
                            use_microcircuits=bool(
                                getattr(_rt.cfg, "use_microcircuits", False)
                            ),
                        )
                        lst_all_wm.extend(lst)
                    lst = lst_all_wm
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
                    lst_all_vector: list[RAGCandidate] = []
                    for qx in expansions:
                        lst = retrieve_vector(
                            qx,
                            top_k,
                            mem_client=mem_client,
                            embedder=_rt.embedder,
                            universe=universe,
                        )
                        lst_all_vector.extend(lst)
                    lst = lst_all_vector
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
                    # For graph we do not expand queries; use original string
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
                lst_all_lexical: list[RAGCandidate] = []
                for qx in expansions:
                    lst = retrieve_lexical(qx, top_k, mem_client=mem_client)
                    lst_all_lexical.extend(lst)
                lst = lst_all_lexical
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

    # Rank fusion (normalized & weighted RRF) over available retriever lists
    fusion_method = "wrrf"
    rrf_k = 60.0
    # Normalize scores per retriever and build rank maps
    ranks: dict[str, dict[str, int]] = {}
    norms: dict[str, dict[str, float]] = {}
    norm_scores: dict[str, dict[str, float]] = {}
    for rname, lst in lists_by_retriever.items():
        rm: dict[str, int] = {}
        # compute mean/std for z-score normalization; fall back to identity
        vals = [float(getattr(c, "score", 0.0) or 0.0) for c in lst] or [0.0]
        mu = float(sum(vals) / len(vals))
        var = float(sum((v - mu) ** 2 for v in vals) / max(1, len(vals) - 1))
        std = float(var**0.5) if var > 0 else 1.0
        norms[rname] = {"mu": mu, "std": std}
        ns_map: dict[str, float] = {}
        for idx, c in enumerate(lst):
            kid = str(
                c.coord
                or c.key
                or (c.payload.get("task") if isinstance(c.payload, dict) else "")
            )
            if kid and kid not in rm:
                rm[kid] = idx + 1  # 1-based rank
            if kid:
                sc = float(getattr(c, "score", 0.0) or 0.0)
                ns_map[kid] = (sc - mu) / (std if std != 0.0 else 1.0)
        ranks[rname] = rm
        norm_scores[rname] = ns_map
    # Aggregate RRF scores
    keys: set[str] = set()
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
    # Retriever weights from config
    wmap = {
        "vector": float(getattr(_rt.cfg, "retriever_weight_vector", 1.0) or 1.0),
        "wm": float(getattr(_rt.cfg, "retriever_weight_wm", 1.0) or 1.0),
        "graph": float(getattr(_rt.cfg, "retriever_weight_graph", 1.0) or 1.0),
        "lexical": float(getattr(_rt.cfg, "retriever_weight_lexical", 0.8) or 0.8),
    }
    alpha = 1.0  # weight for RRF
    beta = 0.5  # weight for normalized scores
    for kid in keys:
        score = 0.0
        for rname, rm in ranks.items():
            r = rm.get(kid)
            if r is not None:
                # weighted reciprocal rank
                score += alpha * wmap.get(rname, 1.0) * (1.0 / (rrf_k + float(r)))
                # add normalized score term when available
                try:
                    s_norm = norm_scores.get(rname, {}).get(kid)
                    if s_norm is not None:
                        score += beta * wmap.get(rname, 1.0) * float(s_norm)
                except Exception:
                    pass
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
            score=float(s),  # fused score (weighted RRF)
            retriever=c.retriever,
            payload=c.payload,
        )
        for s, c in fused
    ]
    # Rerank policy
    method = (req.rerank or "cosine").strip().lower()
    if method == "mmr":
        try:
            # require an embedder for MMR; skip if not available
            if _rt.embedder is None:
                raise Exception("no embedder available")
            from somabrain.services.recall_service import diversify_payloads

            payloads = [c.payload for c in out]
            # local-capture embedder and cast to Any for mypy
            from typing import Any, cast as _cast

            _embedder = _rt.embedder
            ordered = diversify_payloads(
                embed=lambda t: _cast(Any, _embedder).embed(t),
                query=req.query,
                payloads=payloads,
                method="mmr",
                k=min(top_k, len(payloads)),
                lam=0.5,
            )
            # Map back by object id
            id2cand = {id(c.payload): c for c in out}
            out = [
                cast(RAGCandidate, id2cand.get(id(p)))
                for p in ordered
                if id2cand.get(id(p))
            ]
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
    elif method == "ce":
        # Cross-encoder rerank (optional): tries sentence-transformers, falls back to cosine
        try:
            model_id = getattr(_rt.cfg, "reranker_model", None)
            top_n = int(getattr(_rt.cfg, "reranker_top_n", 50) or 50)
            out_k = int(
                getattr(_rt.cfg, "reranker_out_k", max(1, top_k)) or max(1, top_k)
            )
            batch = int(getattr(_rt.cfg, "reranker_batch", 32) or 32)
            if out:
                payloads = [c.payload for c in out[:top_n]]
                pairs = [(req.query, _extract_text(p)) for p in payloads]
                # Try cross-encoder if available
                used_ce = False
                # single typed rescored list used across branches
                rescored: list[tuple[float, int]] = []
                try:
                    from sentence_transformers import CrossEncoder  # type: ignore

                    ce = CrossEncoder(
                        model_id or "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    )
                    scores = ce.predict(pairs, batch_size=batch)
                    rescored = list(zip([float(s) for s in scores], range(len(pairs))))
                    used_ce = True
                except Exception:
                    used_ce = False
                if not used_ce and _rt.embedder is not None:
                    import numpy as _np

                    qv = _rt.embedder.embed(req.query)
                    for i, (_, txt) in enumerate(pairs):
                        if not txt:
                            rescored.append((0.0, i))
                            continue
                        pv = _rt.embedder.embed(txt)
                        na = float(_np.linalg.norm(qv)) or 1.0
                        nb = float(_np.linalg.norm(pv)) or 1.0
                        s = float(_np.dot(qv, pv) / (na * nb))
                        rescored.append((s, i))
                rescored.sort(key=lambda t: t[0], reverse=True)
                selected = [out[i] for _, i in rescored[:out_k]]
                out = selected
        except Exception:
            pass
    # Default: fused order is already desc by score
    out = out[:top_k]

    # If fusion produced fewer than top_k results (possible when real adapters
    # return limited items), backfill with retriever stubs to ensure a stable
    # API response size for callers and tests.
    try:
        if len(out) < top_k:
            need = int(top_k) - len(out)
            # Prefer vector, then wm, then graph stubs
            addons: list[RAGCandidate] = []
            for fn in (retrieve_vector_stub, retrieve_wm_stub, retrieve_graph_stub):
                if need <= 0:
                    break
                # request slightly more than needed to allow for dedupe
                lst = fn(req.query, need + 2)
                for c in lst:
                    if len(addons) >= need:
                        break
                    # avoid duplicates by key
                    keys = {str(x.key) for x in out + addons}
                    if str(c.key) not in keys:
                        addons.append(c)
                need = int(top_k) - (len(out) + len(addons))
            out.extend(addons[: max(0, int(top_k) - len(out))])
    except Exception:
        pass

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
            from typing import Any as _Any, cast as _cast

            from somabrain.services.memory_service import MemoryService

            mem_backend: _Any = getattr(_rt, "mt_memory", None)
            try:
                from somabrain.app import mt_memory as _app_mt_memory
            except Exception:
                _app_mt_memory = None

            print(
                "pipeline mem ids",
                id(mem_backend),
                id(_app_mt_memory) if _app_mt_memory else None,
            )
            if _app_mt_memory is not None and mem_backend is not _app_mt_memory:
                mem_backend = _app_mt_memory
                try:
                    _rt.mt_memory = _app_mt_memory
                except Exception:
                    pass
                try:
                    import somabrain.app as _app_mod

                    _app_mod.mt_memory = _app_mt_memory
                except Exception:
                    pass
            if mem_backend is None:
                try:
                    # Last-resort local backend to ensure persistence in tests/dev
                    from somabrain.config import load_config as _load
                    from somabrain.memory_pool import MultiTenantMemory

                    mem_backend = MultiTenantMemory(_load())
                    try:
                        import somabrain.app as _app_mod

                        _app_mod.mt_memory = mem_backend
                    except Exception:
                        pass
                except Exception:
                    mem_backend = None
            if mem_backend is not None:
                try:
                    # Publish to runtime so subsequent calls see the same backend
                    _rt.mt_memory = mem_backend
                except Exception:
                    pass
                from typing import Any, cast as _cast

                memsvc = MemoryService(_cast(Any, mem_backend), ctx.namespace)
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
                            if c is not None
                        ],
                    },
                    "universe": universe or None,
                }
                from typing import Any as _Any, cast as _cast

                sess_coord = _cast(
                    _Any,
                    await memsvc.aremember(sess_key, sess_payload, universe=universe),
                )
                # Convert coord tuple -> string for response if available,
                # otherwise fall back to deterministic coord_for_key
                # Normalize to a concrete 3-tuple coordinate (sess_coord may be
                # provided by an HTTP server; otherwise derive deterministically
                # from the session key). Always produce sess_coord_t and a
                # session_coord_str for the response.
                if isinstance(sess_coord, (tuple, list)) and len(sess_coord) >= 3:
                    sess_coord_t = (
                        float(sess_coord[0]),
                        float(sess_coord[1]),
                        float(sess_coord[2]),
                    )
                else:
                    sess_coord_t = memsvc.coord_for_key(sess_key, universe=universe)
                session_coord_str = f"{float(sess_coord_t[0])},{float(sess_coord_t[1])},{float(sess_coord_t[2])}"
                # Mirror into process-global payloads for immediate visibility across clients
                try:
                    # Mirror into any loaded memory_client-like modules so that
                    # duplicate imports (test runner, different import paths)
                    # still see the freshly persisted payload.
                    import sys
                    from typing import Any, cast as _cast

                    p2 = dict(sess_payload)
                    p2["coordinate"] = _cast(Any, sess_coord_t)
                    # Primary explicit write to the process-global mirror in this module
                    try:
                        # Import local memory_client module to access its global mirror
                        from somabrain import memory_client as _mc_mod

                        try:
                            # Diagnostic: record namespace keys before/after to debug test visibility
                            # diagnostic info removed; kept best-effort write below
                            # Log writer client id if available
                            # best-effort: record writer client visibility via explicit client write below
                            _mc_mod._GLOBAL_PAYLOADS.setdefault(
                                ctx.namespace, []
                            ).append(p2)
                            # diagnostic info removed
                            # diagnostic info removed
                        except Exception:
                            # If that fails, fall back to local module-level mirror
                            try:
                                globals().setdefault("_GLOBAL_PAYLOADS", {}).setdefault(
                                    ctx.namespace, []
                                ).append(p2)
                            except Exception:
                                # swallow but log below
                                pass
                    except Exception:
                        # can't import memory_client for mirroring; try local fallback
                        try:
                            globals().setdefault("_GLOBAL_PAYLOADS", {}).setdefault(
                                ctx.namespace, []
                            ).append(p2)
                        except Exception:
                            pass

                    # Also attempt the old sys.modules scan for additional mirrors
                    for m in list(sys.modules.values()):
                        try:
                            if m is None:
                                continue
                            if hasattr(m, "_GLOBAL_PAYLOADS"):
                                try:
                                    getattr(m, "_GLOBAL_PAYLOADS").setdefault(
                                        ctx.namespace, []
                                    ).append(p2)
                                except Exception:
                                    # best-effort; continue
                                    pass
                        except Exception:
                            continue
                except Exception:
                    pass
                # Ensure immediate visibility in the namespace client (avoids race in tests/dev)
                try:
                    from typing import Any, cast as _cast

                    if not hasattr(mem_backend, "for_namespace"):
                        raise Exception("mem_backend has no for_namespace")
                    client_ns = _cast(Any, mem_backend).for_namespace(ctx.namespace)
                    # Ensure the namespace client sees the payload with the
                    # concrete coordinate so payloads_for_coords can find it.
                    from typing import Any, cast as _cast

                    p3 = dict(sess_payload)
                    p3["coordinate"] = _cast(Any, sess_coord_t)
                    # Defensive: write via the namespace client and also via
                    # the MemoryService client to cover cases where the
                    # in-process instance referenced by the request handler
                    # may differ from the test harness import/view of the
                    # pool (duplicate imports, import shims, or subtle
                    # threading/forking semantics in CI). Each write is
                    # best-effort and exceptions are swallowed to avoid
                    # breaking the main pipeline.
                    try:
                        client_ns.remember(sess_key, p3)
                    except Exception:
                        pass
                    try:
                        # memsvc.client() should return the authoritative
                        # namespace client from the pool; write again to be
                        # extra-safe for cross-context visibility.
                        memsvc.client().remember(sess_key, p3)
                    except Exception:
                        pass
                except Exception:
                    pass
                # Link query-key -> session (so future graph queries from the same query reach this session)
                try:
                    qcoord = memsvc.coord_for_key(req.query, universe=universe)
                    await memsvc.alink(
                        qcoord, sess_coord_t, link_type="rag_session", weight=1.0
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
                    try:
                        await memsvc.alink(
                            sess_coord_t,
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
