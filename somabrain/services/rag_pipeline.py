from __future__ import annotations

import logging
from typing import List, Optional

from somabrain.schemas import RAGCandidate, RAGRequest, RAGResponse
from somabrain.services import rag_cache
from somabrain.services.retrievers import (
    retrieve_graph,
    retrieve_lexical,
    retrieve_vector,
    retrieve_wm,
)

try:  # pragma: no cover - optional dependency in legacy layouts
    from common.config.settings import settings as shared_settings
except Exception:
    shared_settings = None  # type: ignore


logger = logging.getLogger(__name__)


def _record_global_link(
    namespace: str,
    from_coord: tuple[float, float, float],
    to_coord: tuple[float, float, float],
    link_type: str = "related",
    weight: float = 1.0,
) -> None:
    """Compatibility shim kept for callers but now a no-op in strict mode."""
    logger.debug(
        "global link mirror disabled",
        extra={
            "namespace": namespace,
            "from_coord": from_coord,
            "to_coord": to_coord,
            "link_type": link_type,
            "link_weight": weight,
        },
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

        # Safe increment; metrics module may be a noop in some test envs
        try:
            M.RAG_REQUESTS.labels(
                namespace=ctx.namespace, retrievers=retriever_set
            ).inc()
        except Exception:
            pass
        _t0 = _time.perf_counter()
        _metrics_ctx = {
            "namespace": ctx.namespace,
            "retrievers": retriever_set,
        }
    except Exception:
        _metrics_ctx = {}
        pass

    # Collect candidates by retriever name
    cands: List[RAGCandidate] = []
    lists_by_retriever: dict[str, List[RAGCandidate]] = {}
    if not retrievers:
        retrievers = ["vector", "wm"]
    # Try real adapters first if runtime singletons are available; fallback logic removed
    from somabrain import runtime as _rt

    logger = logging.getLogger(__name__)

    # Defensive: always ensure _rt.cfg is present, fallback to dummy if missing
    if not hasattr(_rt, "cfg") or getattr(_rt, "cfg", None) is None:

        class _TmpCfg:
            use_query_expansion = False
            query_expansion_variants = 0
            use_microcircuits = False
            graph_hops = 1
            graph_limit = 20
            retriever_weight_vector = 1.0
            retriever_weight_wm = 1.0
            retriever_weight_graph = 1.0
            retriever_weight_lexical = 0.8
            reranker_model = None
            reranker_top_n = 50
            reranker_out_k = 1
            reranker_batch = 32

        _rt.cfg = _TmpCfg()

    mem_client = None
    try:
        if _rt.mt_memory is not None and hasattr(_rt.mt_memory, "for_namespace"):
            from somabrain.services.memory_service import MemoryService

            memsvc = MemoryService(_rt.mt_memory, ctx.namespace)
            mem_client = memsvc.client()
    except Exception:
        mem_client = None
        try:
            logger.info(
                "rag_pipeline: error instantiating mem_client from runtime.mt_memory: %s",
                repr(_rt.mt_memory),
            )
        except Exception:
            pass
    # Fallback: if runtime singletons are not wired (common in some dev setups),
    # try to import the application module singletons so seeded /remember calls
    # and the pipeline operate on the same memory/embedder instances.
    if mem_client is None:
        try:
            import somabrain.app as _app_mod

            if hasattr(_app_mod, "mt_memory") and _app_mod.mt_memory is not None:
                from somabrain.services.memory_service import MemoryService

                memsvc = MemoryService(_app_mod.mt_memory, ctx.namespace)
                mem_client = memsvc.client()
                # ensure runtime module points to the same backend for later calls
                try:
                    _rt.mt_memory = _app_mod.mt_memory
                except Exception:
                    pass
        except Exception:
            try:
                logger.info(
                    "rag_pipeline: fallback import somabrain.app failed (no app singletons available)"
                )
            except Exception:
                pass
            pass
    # Log diagnostic state (helpful when running in dev mode)
    try:
        logger.info(
            "RAG runtime state: embedder=%s mt_memory=%s mt_wm=%s mc_wm=%s mem_client=%s",
            getattr(_rt, "embedder", None) is not None,
            getattr(_rt, "mt_memory", None) is not None,
            getattr(_rt, "mt_wm", None) is not None,
            getattr(_rt, "mc_wm", None) is not None,
            mem_client is not None,
        )
    except Exception:
        pass
    # Ensure we have an embedder available (fall back to app.embedder)
    try:
        rt_embedder = getattr(_rt, "embedder", None)
    except Exception:
        rt_embedder = None
    if rt_embedder is None:
        try:
            import somabrain.app as _app_mod2

            app_embedder = getattr(_app_mod2, "embedder", None)
            if app_embedder is not None:
                rt_embedder = app_embedder
                try:
                    # best-effort to keep runtime in sync for later calls
                    setattr(_rt, "embedder", app_embedder)
                except Exception:
                    pass
        except Exception:
            rt_embedder = None
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

    # Advanced targeting: exact id/key/coord path (boost to top, then fused context)
    exact_mode = (req.mode or "auto").strip().lower()
    exact_inputs: dict[str, Optional[str]] = {
        "id": req.id,
        "key": req.key,
        "coord": req.coord,
    }

    def _parse_coord_string(s: str | None) -> Optional[tuple[float, float, float]]:
        if not s:
            return None
        try:
            parts = [float(x.strip()) for x in str(s).split(",")]
            if len(parts) >= 3:
                return (parts[0], parts[1], parts[2])
        except Exception:
            return None
        return None

    # Heuristic auto-detection if mode=auto and explicit fields absent
    if exact_mode == "auto" and not any(exact_inputs.values()):
        q = (req.query or "").strip()
        # Treat pure 3-number comma string as coordinate
        if _parse_coord_string(q) is not None:
            exact_mode = "coord"
            exact_inputs["coord"] = q
        else:
            # Treat single-token (no whitespace) moderately long string as key/id
            if (" " not in q) and len(q) >= 6:
                exact_mode = "key"
                exact_inputs["key"] = q

    pinned_exact: list[RAGCandidate] = []
    pinned_keys: set[str] = set()
    if mem_client is not None and exact_mode in ("id", "key", "coord", "auto"):
        try:
            coords_to_fetch: list[tuple[float, float, float]] = []
            # Priority: coord > key > id (if multiple provided)
            c = _parse_coord_string(exact_inputs.get("coord"))
            if c is not None:
                coords_to_fetch.append(c)
            k = exact_inputs.get("key") or None
            if k:
                try:
                    coords_to_fetch.append(mem_client.coord_for_key(k, universe=universe))
                except Exception:
                    pass
            i = exact_inputs.get("id") or None
            if i and i != k:
                try:
                    coords_to_fetch.append(mem_client.coord_for_key(i, universe=universe))
                except Exception:
                    pass
            # Dedup coords
            seen_c: set[tuple[float, float, float]] = set()
            coords_to_fetch = [
                (float(x), float(y), float(z))
                for (x, y, z) in coords_to_fetch
                if not ((float(x), float(y), float(z)) in seen_c or seen_c.add((float(x), float(y), float(z))))
            ]
            if coords_to_fetch:
                payloads = mem_client.payloads_for_coords(coords_to_fetch, universe=universe) or []
                for p in payloads:
                    # Use high base score to keep ahead; final rerank will respect pinning below
                    coord = p.get("coordinate")
                    coord_str = None
                    if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                        coord_str = ",".join(str(float(c)) for c in coord[:3])
                    kid = str(p.get("task") or p.get("id") or "") or None
                    cand = RAGCandidate(
                        coord=coord_str,
                        key=kid,
                        score=1e9,  # sentinel high score for pinning
                        retriever="exact",
                        payload=p if isinstance(p, dict) else {"raw": p},
                    )
                    pinned_exact.append(cand)
                    if coord_str:
                        pinned_keys.add(coord_str)
                    if kid:
                        pinned_keys.add(kid)
                if pinned_exact:
                    lists_by_retriever["exact"] = list(pinned_exact)
                    cands += pinned_exact
        except Exception:
            # Exact path is best-effort; continue with fused retrievals on failure
            pass
    for rname in retrievers:
        if rname == "wm":
            if rt_embedder is None:
                raise RuntimeError(
                    "WM retriever unavailable (embedder not configured)."
                )
            mt_wm = getattr(_rt, "mt_wm", None)
            mc_wm = getattr(_rt, "mc_wm", None)
            if mt_wm is None and mc_wm is None:
                raise RuntimeError(
                    "WM retriever unavailable (working memory backend missing)."
                )
            try:
                lst_all: list[RAGCandidate] = []
                for qx in expansions:
                    lst_all.extend(
                        retrieve_wm(
                            qx,
                            top_k,
                            tenant_id=ctx.tenant_id,
                            embedder=rt_embedder,
                            mt_wm=mt_wm,
                            mc_wm=mc_wm,
                            use_microcircuits=bool(
                                getattr(_rt.cfg, "use_microcircuits", False)
                            ),
                        )
                    )
                lists_by_retriever["wm"] = lst_all
                cands += lst_all
                continue
            except Exception as exc:
                raise RuntimeError("WM retriever execution failed.") from exc
        elif rname == "vector":
            if rt_embedder is None:
                raise RuntimeError(
                    "Vector retriever unavailable (embedder not configured)."
                )
            if mem_client is None:
                raise RuntimeError(
                    "Vector retriever unavailable (memory client missing)."
                )
            try:
                lst_all: list[RAGCandidate] = []
                for qx in expansions:
                    lst_all.extend(
                        retrieve_vector(
                            qx,
                            top_k,
                            mem_client=mem_client,
                            embedder=rt_embedder,
                            universe=universe,
                        )
                    )
                lists_by_retriever["vector"] = lst_all
                cands += lst_all
                continue
            except Exception as exc:
                raise RuntimeError("Vector retriever execution failed.") from exc
        elif rname == "graph":
            if rt_embedder is None:
                raise RuntimeError(
                    "Graph retriever unavailable (embedder not configured)."
                )
            if mem_client is None:
                raise RuntimeError(
                    "Graph retriever unavailable (memory client missing)."
                )
            try:
                hops = int(getattr(_rt.cfg, "graph_hops", 1) or 1)
                limit = int(getattr(_rt.cfg, "graph_limit", 20) or 20)
                lst = retrieve_graph(
                    req.query,
                    top_k,
                    mem_client=mem_client,
                    embedder=rt_embedder,
                    hops=hops,
                    limit=limit,
                    universe=universe,
                    namespace=ctx.namespace,
                )
                lists_by_retriever["graph"] = lst
                cands += lst
                continue
            except Exception as exc:
                raise RuntimeError("Graph retriever execution failed.") from exc
        elif rname == "lexical":
            if mem_client is None:
                raise RuntimeError(
                    "Lexical retriever unavailable (memory client missing)."
                )
            try:
                lst_all: list[RAGCandidate] = []
                for qx in expansions:
                    lst_all.extend(retrieve_lexical(qx, top_k, mem_client=mem_client))
                lists_by_retriever["lexical"] = lst_all
                cands += lst_all
                continue
            except Exception as exc:
                raise RuntimeError("Lexical retriever execution failed.") from exc
        else:
            # Unknown retriever; skip
            continue

    # If nothing retrieved: in strict mode, do not backfill with stubs (proceed with empty set);
    # in non-strict mode, backfill to keep endpoint responsive in empty stores.
    if not cands:
        if shared_settings is not None and getattr(
            shared_settings, "require_external_backends", False
        ):
            raise RuntimeError(
                "No retriever results and backend enforcement enabled – backfill disabled."
            )
        raise RuntimeError("No retriever results – external retrievers required.")

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
    # Ensure exact hits are pinned to the front (dedup by key/coord)
    if pinned_exact:
        def _kid(c: RAGCandidate) -> str:
            return str(
                c.coord or c.key or (c.payload.get("task") if isinstance(c.payload, dict) else "")
            )

        seen = set()
        pinned_unique: list[RAGCandidate] = []
        for c in pinned_exact:
            k = _kid(c)
            if k and k not in seen:
                seen.add(k)
                pinned_unique.append(c)
        rest: list[RAGCandidate] = []
        for c in out:
            k = _kid(c)
            if (not k) or (k not in seen):
                rest.append(c)
        out = pinned_unique + rest
    # Rerank policy
    # Resolve reranker (auto => prefer HRR > MMR > cosine)
    requested = (req.rerank or "auto").strip().lower()
    method = requested
    if requested in ("auto", "default", "best"):
        try:
            if getattr(_rt, "quantum", None) is not None:
                method = "hrr"
            elif rt_embedder is not None:
                method = "mmr"
            else:
                method = "cosine"
        except Exception:
            method = "cosine"

    if method == "mmr":
        try:
            from somabrain.services.recall_service import diversify_payloads

            # Do not rerank pinned exacts; only rerank the rest
            payloads = [c.payload for c in (out[len(pinned_exact) :] if pinned_exact else out)]
            ordered = diversify_payloads(
                embed=lambda t: _rt.embedder.embed(t),
                query=req.query,
                payloads=payloads,
                method="mmr",
                k=min(top_k, len(payloads)),
                lam=0.5,
            )
            # Map back by object id
            id2cand = {id(c.payload): c for c in (out[len(pinned_exact) :] if pinned_exact else out)}
            reranked = [id2cand.get(id(p)) for p in ordered if id2cand.get(id(p))]
            out = (out[: len(pinned_exact)] if pinned_exact else []) + reranked
        except Exception:
            pass
    elif method == "hrr":
        try:
            if _rt.quantum is not None:
                hq = _rt.quantum.encode_text(req.query)

                def _cos(a, b):
                    from somabrain.quantum import QuantumLayer

                    return float(QuantumLayer.cosine(a, b))

                # recompute scores as HRR cosine for non-pinned section
                new = []
                head = out[: len(pinned_exact)] if pinned_exact else []
                tail = out[len(pinned_exact) :] if pinned_exact else out
                for c in tail:
                    txt = _extract_text(c.payload)
                    if not txt:
                        new.append((c.score, c))
                        continue
                    hv = _rt.quantum.encode_text(txt)
                    sc = _cos(hq, hv)
                    new.append((sc, c))
                new.sort(key=lambda t: t[0], reverse=True)
                out = head + [c for _, c in new]
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
                # Only rerank non-pinned tail
                head = out[: len(pinned_exact)] if pinned_exact else []
                tail = out[len(pinned_exact) :] if pinned_exact else out
                payloads = [c.payload for c in tail[:top_n]]
                pairs = [(req.query, _extract_text(p)) for p in payloads]
                # Try cross-encoder if available
                used_ce = False
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
                    rescored: list[tuple[float, int]] = []
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
                selected = [tail[i] for _, i in rescored[:out_k]]
                out = head + selected
        except Exception:
            pass
    # Default: fused order is already desc by score
    out = out[:top_k]

    # Record latency and candidate count (safe instrumentation)
    try:
        import time as _time

        from somabrain import metrics as M

        if _t0 is not None:
            try:
                M.RAG_RETRIEVE_LAT.labels(**_metrics_ctx).observe(
                    max(0.0, _time.perf_counter() - _t0)
                )
            except Exception:
                try:
                    # Fallback to unlabeled metric
                    M.RAG_RETRIEVE_LAT.observe(max(0.0, _time.perf_counter() - _t0))
                except Exception:
                    pass
        try:
            M.RAG_CANDIDATES.labels(**_metrics_ctx).observe(len(out))
        except Exception:
            try:
                M.RAG_CANDIDATES.observe(len(out))
            except Exception:
                pass
    except Exception:
        pass

    # Optional persistence of session + links (PR‑3)
    session_coord_str: Optional[str] = None
    if bool(req.persist):
        try:
            import time as _time

            from somabrain.services.memory_service import MemoryService

            mem_backend = _rt.mt_memory
            try:
                from somabrain.app import mt_memory as _app_mt_memory
            except Exception:
                _app_mt_memory = None

            logger.debug(
                "pipeline mem ids backend=%s app=%s",
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
                    from somabrain.config import get_config as _get_config
                    from somabrain.memory_pool import MultiTenantMemory

                    mem_backend = MultiTenantMemory(_get_config())
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
                memsvc = MemoryService(mem_backend, ctx.namespace)
                persist_records: list[dict] = []
                # Build session payload with provenance and top candidates summary
                sess_key = f"rag_session::{trace_id or ''}::{int(_time.time() * 1000)}"
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
                # Ensure immediate visibility in the namespace client (avoids race in tests/dev)
                try:
                    client_ns = mem_backend.for_namespace(ctx.namespace)
                    # Ensure the namespace client sees the payload with the
                    # concrete coordinate so payloads_for_coords can find it.
                    p3 = dict(sess_payload)
                    p3["coordinate"] = sess_coord_t
                    client_ns.remember(sess_key, p3)
                except Exception:
                    pass
                # Compute coordinate for the query string for linking
                try:
                    qcoord = memsvc.coord_for_key(req.query, universe=universe)
                except Exception:
                    qcoord = None
                # Debug namespace
                import logging as _log

                _log.getLogger(__name__).debug(
                    "RAG pipeline namespace: %s", ctx.namespace
                )
                # Link query-key -> session using direct client to avoid circuit/outbox delays
                try:
                    if qcoord is not None:
                        memsvc.client().link(
                            qcoord,
                            sess_coord_t,
                            link_type="rag_session",
                            weight=1.0,
                        )
                        _record_global_link(
                            ctx.namespace, qcoord, sess_coord_t, "rag_session", 1.0
                        )
                except Exception:
                    pass

                seen_doc_coords: set[tuple[float, float, float]] = set()

                def _append_doc_target(
                    coord: tuple[float, float, float] | None,
                    payload: dict | object,
                ) -> list[tuple[tuple[float, float, float], dict]]:
                    targets: list[tuple[tuple[float, float, float], dict]] = []
                    if coord is None:
                        return targets
                    coord_t = (
                        float(coord[0]),
                        float(coord[1]),
                        float(coord[2]),
                    )
                    if coord_t in seen_doc_coords:
                        return targets
                    seen_doc_coords.add(coord_t)
                    payload_dict = (
                        dict(payload) if isinstance(payload, dict) else {"raw": payload}
                    )
                    payload_dict.setdefault("coordinate", coord_t)
                    targets.append((coord_t, payload_dict))
                    return targets

                for c in out:
                    payload_dict = c.payload if isinstance(c.payload, dict) else {}
                    key_for_coord = c.key or (
                        payload_dict.get("task")
                        if isinstance(payload_dict, dict)
                        else None
                    )
                    is_session = False
                    if isinstance(payload_dict, dict) and payload_dict.get("rag"):
                        is_session = True
                    if isinstance(
                        key_for_coord, str
                    ) and key_for_coord.lower().startswith("rag session"):
                        is_session = True

                    doc_targets: list[tuple[tuple[float, float, float], dict]] = []

                    if not is_session:
                        pc = (
                            payload_dict.get("coordinate")
                            if isinstance(payload_dict, dict)
                            else None
                        )
                        doc_coord: tuple[float, float, float] | None
                        if isinstance(pc, (list, tuple)) and len(pc) >= 3:
                            doc_coord = (
                                float(pc[0]),
                                float(pc[1]),
                                float(pc[2]),
                            )
                        elif key_for_coord:
                            try:
                                doc_coord = memsvc.coord_for_key(
                                    str(key_for_coord), universe=universe
                                )
                            except Exception:
                                doc_coord = None
                        else:
                            doc_coord = None
                        doc_targets.extend(
                            _append_doc_target(doc_coord, payload_dict or c.payload)
                        )
                    else:
                        rag_info = (
                            payload_dict.get("rag")
                            if isinstance(payload_dict, dict)
                            else None
                        )
                        doc_keys: list[str] = []
                        if isinstance(rag_info, dict):
                            for entry in rag_info.get("candidates", []):
                                doc_key = (
                                    entry.get("key")
                                    if isinstance(entry, dict)
                                    else None
                                )
                                if not doc_key:
                                    continue
                                doc_key_str = str(doc_key)
                                if doc_key_str.lower().startswith("rag session"):
                                    continue
                                doc_keys.append(doc_key_str)
                        for doc_key in doc_keys:
                            try:
                                doc_coord = memsvc.coord_for_key(
                                    doc_key, universe=universe
                                )
                            except Exception:
                                continue
                            try:
                                doc_payloads = memsvc.payloads_for_coords(
                                    [doc_coord], universe=universe
                                )
                            except Exception:
                                doc_payloads = []
                            doc_payload = (
                                dict(doc_payloads[0])
                                if doc_payloads
                                else {"task": doc_key}
                            )
                            doc_targets.extend(
                                _append_doc_target(doc_coord, doc_payload)
                            )

                    for doc_coord_t, doc_payload in doc_targets:
                        try:
                            memsvc.client().link(
                                sess_coord_t,
                                doc_coord_t,
                                link_type="retrieved_with",
                                weight=1.0,
                            )
                            _record_global_link(
                                ctx.namespace,
                                sess_coord_t,
                                doc_coord_t,
                                "retrieved_with",
                                1.0,
                            )
                        except Exception:
                            pass
                        try:
                            persist_records.append(
                                {
                                    "coordinate": doc_coord_t,
                                    "payload": doc_payload,
                                    "score": float(getattr(c, "score", 0.0) or 0.0),
                                    "retriever": getattr(c, "retriever", "graph"),
                                }
                            )
                        except Exception:
                            pass
                if persist_records:
                    try:
                        rag_cache.store_candidates(
                            ctx.namespace, req.query, persist_records
                        )
                    except Exception:
                        pass
                # Debug: check graph edges count for session
                try:
                    _graph = memsvc.client()._graph  # type: ignore[attr-defined]
                    _edges = _graph.get(sess_coord_t, {})
                    import logging as _log

                    _log.getLogger(__name__).debug(
                        "Graph edges for session %s: %s", sess_coord_t, _edges
                    )
                except Exception:
                    pass
                # Debug: inspect edges from session after linking
                try:
                    debug_edges = memsvc.client().links_from(sess_coord_t, limit=10)
                    import logging as _log

                    _log.getLogger(__name__).debug(
                        "DEBUG edges from session %s: %s", sess_coord_t, debug_edges
                    )
                except Exception:
                    pass
                # No outbox processing needed when using direct client links
                # Verify that edges have been recorded in the client graph
                try:
                    _g = memsvc.client()._graph  # type: ignore[attr-defined]
                    if not _g.get(sess_coord_t):
                        raise AssertionError(
                            f"No edges recorded for session {sess_coord_t}: {_g}"
                        )
                except Exception as e:
                    # Log but do not crash production; in test environment this will surface
                    import logging as _log

                    _log.getLogger(__name__).debug("Graph verification error: %s", e)
        except Exception:
            try:
                from somabrain import metrics as M

                M.RAG_PERSIST.labels(status="failure").inc()
            except Exception:
                pass

    # Prepare metrics payload
    metrics_payload = {
        "retrievers": retriever_set,
        "fusion": "wrrf",
        "expansions": len(expansions),
        "reranker_used": method,
        "exact_mode": exact_mode,
        "exact_count": len(pinned_exact),
    }

    return RAGResponse(
        candidates=out,
        session_coord=session_coord_str,
        namespace=ctx.namespace,
        trace_id=trace_id or "",
        metrics=metrics_payload,
    )
