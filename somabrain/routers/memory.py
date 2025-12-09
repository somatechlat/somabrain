"""Memory Router
===============

Core memory operations: recall, remember, delete.
These endpoints handle the primary memory storage and retrieval operations
for the cognitive system.

Endpoints:
- /recall - Retrieve memories matching a query
- /remember - Store a new memory
- /delete - Delete a memory by coordinate
- /recall/delete - Delete via recall API (alias)
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Request

from common.config.settings import settings
from somabrain import metrics as M, schemas as S
from somabrain.auth import require_auth
from somabrain.datetime_utils import coerce_to_epoch_seconds
from somabrain.events import extract_event_fields
from somabrain.quantum import QuantumLayer
from somabrain.services.memory_service import MemoryService
from somabrain.services.recall_service import recall_ltm_async as _recall_ltm
from somabrain.tenant import get_tenant as get_tenant_async

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])

# Per-tenant recall cache
_recall_cache: Dict[str, TTLCache] = {}

# Math domain keywords for lexical boosting
_MATH_DOMAIN_KEYWORDS = {
    "math", "mathematics", "algebra", "geometry", "calculus", "arithmetic",
    "trigonometry", "probability", "statistics", "number theory", "linear algebra",
    "equation", "derivative", "integral", "matrix", "learning", "education", "stem",
}


def _get_runtime_singletons():
    """Get runtime singletons lazily to avoid circular imports."""
    from somabrain import runtime as rt
    return rt


def _get_app_config():
    """Get app-level configuration."""
    rt = _get_runtime_singletons()
    return getattr(rt, "cfg", settings)


def _get_app_singletons():
    """Get app-level singletons that aren't in runtime module."""
    try:
        from somabrain import app as app_module
        return {
            "rate_limiter": getattr(app_module, "rate_limiter", None),
            "quotas": getattr(app_module, "quotas", None),
            "unified_scorer": getattr(app_module, "unified_scorer", None),
            "mt_ctx": getattr(app_module, "mt_ctx", None),
            "CognitiveInputValidator": getattr(app_module, "CognitiveInputValidator", None),
            "_EMBED_PROVIDER": getattr(app_module, "_EMBED_PROVIDER", "unknown"),
            "_sdr_enc": getattr(app_module, "_sdr_enc", None),
            "_sdr_idx": getattr(app_module, "_sdr_idx", None),
        }
    except Exception:
        return {}


def _collect_candidate_keys(payload: Any) -> set:
    """Collect keys from a candidate payload for WM support matching."""
    keys: set = set()
    if isinstance(payload, dict):
        coord = payload.get("coordinate")
        if isinstance(coord, (list, tuple)) and len(coord) == 3:
            try:
                keys.add(("coord", tuple(coord)))
            except Exception:
                pass
        for k in ("id", "memory_id", "key"):
            v = payload.get(k)
            if isinstance(v, str) and v.strip():
                keys.add(("id", v.strip()))
        text = str(
            payload.get("task") or payload.get("fact") or
            payload.get("text") or payload.get("content") or ""
        ).strip()
        if text:
            keys.add(("text", text.lower()))
    else:
        text = str(payload).strip()
        if text:
            keys.add(("text", text.lower()))
    return keys


def _build_wm_support_index(wm_hits) -> Dict[Tuple[str, Any], float]:
    """Build support index from WM hits for scoring."""
    index: Dict[Tuple[str, Any], float] = {}
    for sim, payload in wm_hits:
        try:
            score = float(sim)
        except Exception:
            continue
        for key in _collect_candidate_keys(payload):
            index[key] = max(index.get(key, 0.0), score)
    return index


def _extract_text_from_candidate(candidate: Dict) -> str:
    """Extract textual representation from a memory candidate."""
    for key in ["task", "content", "text", "description", "payload"]:
        if isinstance(candidate, dict) and key in candidate:
            value = candidate[key]
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                return _extract_text_from_candidate(value)
    return str(candidate) if candidate is not None else ""



def _score_memory_candidate(
    payload: Any,
    *,
    query_lower: str,
    query_tokens: List[str],
    query_vec: np.ndarray,
    embed_fn,
    embed_cache: Dict[str, np.ndarray],
    scorer,
    wm_support: Dict[Tuple[str, Any], float],
    now_ts: float,
    quantum_layer: Optional[QuantumLayer],
    query_hrr,
    hrr_cache: Dict[str, Any],
    hrr_weight: Optional[float] = None,
) -> float:
    """Score a memory candidate using unified scoring with lexical and HRR boosts."""
    if query_vec is None or scorer is None or embed_fn is None:
        return 0.0

    payload_dict = payload if isinstance(payload, dict) else {"_raw": payload}
    text = str(
        payload_dict.get("task") or payload_dict.get("fact") or
        payload_dict.get("text") or payload_dict.get("content") or ""
    ).strip()
    if not text:
        return 0.0

    text_lower = text.lower()
    try:
        cand_vec = embed_cache.get(text)
        if cand_vec is None:
            cand_vec = np.asarray(embed_fn(text), dtype=float).reshape(-1)
            embed_cache[text] = cand_vec
    except Exception:
        return 0.0

    recency_steps: Optional[int] = None
    ts_val = payload_dict.get("timestamp") or payload_dict.get("updated_at")
    if ts_val is not None:
        try:
            ts = float(coerce_to_epoch_seconds(ts_val))
            recency_steps = max(0, int((now_ts - ts) / 60.0))
        except Exception:
            recency_steps = None

    try:
        base = scorer.score(query_vec, cand_vec, recency_steps=recency_steps)
    except Exception:
        base = 0.0

    # Lexical reinforcement
    lex_bonus = 0.0
    if query_lower and text_lower:
        if query_lower == text_lower:
            lex_bonus += 0.05
        elif query_lower in text_lower or text_lower in query_lower:
            lex_bonus += 0.02
        if query_tokens:
            seen_tokens = set()
            for token in query_tokens:
                if token and token not in seen_tokens and token in text_lower:
                    lex_bonus += 0.01
                    seen_tokens.add(token)
    if any(k in text_lower for k in _MATH_DOMAIN_KEYWORDS):
        lex_bonus += 0.02

    # WM support boost
    wm_bonus = 0.0
    for key in _collect_candidate_keys(payload_dict):
        support = wm_support.get(key)
        if support is not None:
            wm_bonus = max(wm_bonus, float(support))
    if wm_bonus > 0.0:
        lex_bonus += 0.05 * wm_bonus

    score = max(0.0, base + lex_bonus)

    # HRR alignment blending
    if quantum_layer is not None and query_hrr is not None:
        try:
            hv = hrr_cache.get(text)
            if hv is None:
                hv = quantum_layer.encode_text(text)
                hrr_cache[text] = hv
            hsim = max(0.0, min(1.0, float(QuantumLayer.cosine(query_hrr, hv))))
            alpha = max(0.0, min(1.0, float(hrr_weight or 0.0)))
            if alpha > 0.0:
                score = (1.0 - alpha) * score + alpha * hsim
        except Exception:
            pass

    return float(max(0.0, min(1.0, score)))


def _apply_diversity_reranking(
    candidates: List[Dict],
    query_vec: np.ndarray,
    embedder: Any,
    k: int,
    lam: float,
    min_k: int,
) -> List[Dict]:
    """Apply Maximal Marginal Relevance (MMR) re-ranking."""
    if not candidates or len(candidates) < min_k:
        return candidates

    try:
        candidate_texts = [_extract_text_from_candidate(c) for c in candidates]
        valid_indices = [i for i, text in enumerate(candidate_texts) if text]
        if len(valid_indices) < min_k:
            return candidates

        valid_candidates = [candidates[i] for i in valid_indices]
        doc_vecs = [embedder.embed(candidate_texts[i]) for i in valid_indices]

        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return candidates

        doc_norms = [np.linalg.norm(v) for v in doc_vecs]
        relevance_scores = [
            (np.dot(query_vec, doc_vecs[i]) / (q_norm * doc_norms[i])
             if doc_norms[i] > 0 else 0.0)
            for i in range(len(valid_candidates))
        ]

        selected: List[int] = []
        remaining = list(range(len(valid_candidates)))

        while len(selected) < k and remaining:
            best_score = -np.inf
            best_idx = -1

            for idx in remaining:
                rel_score = relevance_scores[idx]
                if not selected:
                    max_sim = 0.0
                else:
                    similarities = [
                        (np.dot(doc_vecs[idx], doc_vecs[sel_idx]) /
                         (doc_norms[idx] * doc_norms[sel_idx])
                         if doc_norms[idx] > 0 and doc_norms[sel_idx] > 0 else 0.0)
                        for sel_idx in selected
                    ]
                    max_sim = max(similarities) if similarities else 0.0

                mmr_score = lam * rel_score - (1 - lam) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx != -1:
                selected.append(best_idx)
                remaining.remove(best_idx)
            else:
                break

        return [valid_candidates[idx] for idx in selected]

    except Exception as e:
        logger.debug("Diversity re-ranking failed: %s", e, exc_info=True)
        return candidates[:k]



@router.post("/remember", response_model=S.RememberResponse)
async def remember(body: dict, request: Request):
    """Handle memory storage.

    Accepts both original schema (with payload field) and direct payload.
    """
    rt = _get_runtime_singletons()
    cfg = _get_app_config()
    singletons = _get_app_singletons()

    embedder = getattr(rt, "embedder", None)
    quantum = getattr(rt, "quantum", None)
    mt_wm = getattr(rt, "mt_wm", None)
    mc_wm = getattr(rt, "mc_wm", None)
    mt_memory = getattr(rt, "mt_memory", None)

    rate_limiter = singletons.get("rate_limiter")
    quotas = singletons.get("quotas")
    mt_ctx = singletons.get("mt_ctx")
    CognitiveInputValidator = singletons.get("CognitiveInputValidator")
    _EMBED_PROVIDER = singletons.get("_EMBED_PROVIDER", "unknown")

    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)

    coord = body.get("coord")
    payload_data = body.get("payload", body)

    try:
        payload_obj: S.MemoryPayload = S.MemoryPayload(**payload_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # Input validation
    if CognitiveInputValidator:
        try:
            if payload_obj.task:
                payload_obj.task = CognitiveInputValidator.validate_text_input(
                    payload_obj.task, "task"
                )
            if coord:
                coord_parts = str(coord).split(",")
                if len(coord_parts) == 3:
                    coords_tuple = tuple(float(x.strip()) for x in coord_parts)
                    CognitiveInputValidator.validate_coordinates(coords_tuple)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

    if rate_limiter and not rate_limiter.allow(ctx.tenant_id):
        try:
            M.RATE_LIMITED_TOTAL.labels(path="/remember").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    if quotas and not quotas.allow_write(ctx.tenant_id, 1):
        try:
            M.QUOTA_DENIED_TOTAL.labels(reason="daily_write_quota").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="daily write quota exceeded")

    key = coord or (payload_obj.task or "task")
    payload = payload_obj.model_dump()

    if payload.get("timestamp") is not None:
        try:
            payload["timestamp"] = coerce_to_epoch_seconds(payload["timestamp"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {exc}")

    # Universe scoping
    header_u = request.headers.get("X-Universe", "").strip() or None
    if not payload.get("universe") and header_u:
        payload["universe"] = header_u

    # Enrich with event fields
    if payload.get("task") and not any(
        payload.get(k) for k in ("who", "did", "what", "where", "when", "why")
    ):
        fields = extract_event_fields(str(payload.get("task")))
        payload.update({
            k: v for k, v in fields.items()
            if k in ("who", "did", "what", "where", "when", "why")
        })

    memsvc = MemoryService(mt_memory, ctx.namespace)
    memsvc._reset_circuit_if_needed()

    _s0 = time.perf_counter()
    try:
        await memsvc.aremember(key, payload)
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={"message": "memory backend unavailable"},
        ) from e

    try:
        M.LTM_STORE_LAT.observe(max(0.0, time.perf_counter() - _s0))
    except Exception:
        pass

    # Admit to WM
    text = payload.get("task") or ""
    _e1 = time.perf_counter()
    wm_vec = embedder.embed(text) if embedder else None
    if wm_vec is not None:
        try:
            M.EMBED_LAT.labels(provider=_EMBED_PROVIDER).observe(
                max(0.0, time.perf_counter() - _e1)
            )
        except Exception:
            pass

    hrr_vec = quantum.encode_text(text) if quantum else None
    cleanup_overlap = None
    cleanup_margin = None

    if mt_ctx is not None and hrr_vec is not None:
        analysis = mt_ctx.analyze(ctx.tenant_id, hrr_vec)
        cleanup_overlap = float(analysis.best_score)
        cleanup_margin = float(analysis.margin)
        try:
            payload.setdefault("_cleanup_best", cleanup_overlap)
            payload.setdefault("_cleanup_margin", cleanup_margin)
        except Exception:
            pass

    wm = mc_wm if getattr(cfg, "use_microcircuits", False) else mt_wm
    if wm and wm_vec is not None:
        wm.admit(ctx.tenant_id, wm_vec, payload)

    return S.RememberResponse(
        ok=True,
        key=key,
        cleanup_overlap=cleanup_overlap,
        cleanup_margin=cleanup_margin,
    )


@router.post("/delete", response_model=S.DeleteResponse)
async def delete_memory(req: S.DeleteRequest, request: Request):
    """Delete a memory at the given coordinate."""
    rt = _get_runtime_singletons()
    cfg = _get_app_config()
    mt_memory = getattr(rt, "mt_memory", None)

    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)

    memsvc = MemoryService(mt_memory, ctx.namespace)

    try:
        deleted = await memsvc.adelete(req.coordinate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")

    return S.DeleteResponse(ok=deleted, coordinate=req.coordinate)


@router.post("/recall/delete", response_model=S.DeleteResponse)
async def recall_delete(req: S.DeleteRequest, request: Request):
    """Delete a memory by coordinate via the recall API."""
    return await delete_memory(req, request)



@router.post("/recall", response_model=S.RecallResponse)
async def recall(req: S.RecallRequest, request: Request):
    """Recall memories matching a query.

    Performs multi-tier retrieval from WM and LTM with optional HRR reranking,
    diversity filtering, and lexical boosting.
    """
    rt = _get_runtime_singletons()
    cfg = _get_app_config()
    singletons = _get_app_singletons()

    embedder = getattr(rt, "embedder", None)
    quantum = getattr(rt, "quantum", None)
    mt_wm = getattr(rt, "mt_wm", None)
    mc_wm = getattr(rt, "mc_wm", None)
    mt_memory = getattr(rt, "mt_memory", None)

    rate_limiter = singletons.get("rate_limiter")
    unified_scorer = singletons.get("unified_scorer")
    mt_ctx = singletons.get("mt_ctx")
    CognitiveInputValidator = singletons.get("CognitiveInputValidator")
    _EMBED_PROVIDER = singletons.get("_EMBED_PROVIDER", "unknown")
    _sdr_enc = singletons.get("_sdr_enc")
    _sdr_idx = singletons.get("_sdr_idx")

    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)

    # Input validation
    if CognitiveInputValidator:
        try:
            if hasattr(req, "query") and req.query:
                req.query = CognitiveInputValidator.sanitize_query(req.query)
        except Exception:
            pass

    if rate_limiter and not rate_limiter.allow(ctx.tenant_id):
        try:
            M.RATE_LIMITED_TOTAL.labels(path="/recall").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    # Normalize input
    from somabrain.thalamus import ThalamusRouter
    thalamus = ThalamusRouter()
    from somabrain.neuromodulators import PerTenantNeuromodulators
    per_tenant_neuromodulators = PerTenantNeuromodulators()

    data = thalamus.normalize(req.model_dump())
    data = thalamus.filter_input(data, per_tenant_neuromodulators.get_state(ctx.tenant_id))

    cohort = request.headers.get("X-Backend-Cohort", "baseline").strip() or "baseline"
    req_u = getattr(req, "universe", None) or None
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = req_u or header_u
    text = data.get("query", req.query)

    ql = ""
    qtokens: List[str] = []
    if isinstance(text, str):
        try:
            ql = text.strip().lower()
            qtokens = [t for t in re.split(r"[^A-Za-z0-9_-]+", ql) if t]
        except Exception:
            ql = ""
            qtokens = []

    # Embed query
    _e0 = time.perf_counter()
    wm_qv = embedder.embed(text) if embedder else None
    if wm_qv is not None:
        try:
            M.EMBED_LAT.labels(provider=_EMBED_PROVIDER).observe(max(0.0, time.perf_counter() - _e0))
        except Exception:
            pass

    query_vec = np.asarray(wm_qv, dtype=float).reshape(-1) if wm_qv is not None else None
    embed_cache: Dict[str, np.ndarray] = {}
    hrr_qv = quantum.encode_text(text) if quantum else None

    # WM recall
    _t0 = time.perf_counter()
    wm = mc_wm if getattr(cfg, "use_microcircuits", False) else mt_wm
    wm_hits = wm.recall(ctx.tenant_id, wm_qv, top_k=req.top_k) if wm and wm_qv is not None else []
    try:
        M.RECALL_WM_LAT.labels(cohort=cohort).observe(max(0.0, time.perf_counter() - _t0))
    except Exception:
        pass

    # WM quality metrics
    try:
        if wm_hits:
            top1 = float(wm_hits[0][0])
            top2 = float(wm_hits[1][0]) if len(wm_hits) > 1 else top1
            margin = max(0.0, top1 - top2)
            M.RECALL_MARGIN_TOP12.observe(margin)
            M.RECALL_SIM_TOP1.observe(top1)
            mcount = max(1, min(len(wm_hits), int(req.top_k)))
            mean_k = sum(float(s) for s, _ in wm_hits[:mcount]) / float(mcount)
            M.RECALL_SIM_TOPK_MEAN.observe(mean_k)
    except Exception:
        pass

    # HRR reranking of WM hits
    if getattr(cfg, "use_hrr_first", False) and quantum is not None and hrr_qv is not None:
        try:
            do_rerank = True
            if getattr(cfg, "hrr_rerank_only_low_margin", False) and len(wm_hits) >= 2:
                m = float(wm_hits[0][0]) - float(wm_hits[1][0])
                if m > float(getattr(cfg, "rerank_margin_threshold", 0.05) or 0.05):
                    do_rerank = False
                    M.HRR_RERANK_WM_SKIPPED.inc()

            if do_rerank:
                reranked = []
                for s, p in wm_hits:
                    text_p = str(p.get("task") or p.get("fact") or "") if isinstance(p, dict) else str(p)
                    if not text_p:
                        reranked.append((s, p))
                        continue
                    hv = quantum.encode_text(text_p)
                    hsim = QuantumLayer.cosine(hrr_qv, hv) if hrr_qv is not None else 0.0
                    alpha = max(0.0, min(1.0, float(getattr(cfg, "hrr_rerank_weight", 0.0))))
                    combined = (1.0 - alpha) * float(s) + alpha * float(hsim)
                    reranked.append((combined, p))
                reranked.sort(key=lambda t: t[0], reverse=True)
                wm_hits = reranked[:max(0, int(req.top_k))]
                M.HRR_RERANK_APPLIED.inc()
        except Exception:
            pass

    # Universe filter
    if universe:
        wm_hits = [
            (s, p) for s, p in wm_hits
            if isinstance(p, dict) and str(p.get("universe") or "real") == str(universe)
        ]

    if wm_hits:
        M.WM_HITS.inc()
    else:
        M.WM_MISSES.inc()

    # HRR cleanup
    hrr_info = None
    if mt_ctx is not None and getattr(cfg, "use_hrr_cleanup", False) and hrr_qv is not None:
        M.HRR_CLEANUP_CALLS.inc()
        cleanup_result = mt_ctx.cleanup(ctx.tenant_id, hrr_qv)
        anchor_id = getattr(cleanup_result, "best_id", "")
        score = max(0.0, min(1.0, float(getattr(cleanup_result, "best_score", 0.0))))
        margin = getattr(cleanup_result, "margin", 0.0)
        hrr_info = {"anchor_id": anchor_id, "score": score, "margin": float(margin)}
        M.HRR_CLEANUP_USED.inc()
        M.HRR_CLEANUP_SCORE.observe(score)

    # LTM recall with caching
    cache = _recall_cache.setdefault(ctx.tenant_id, TTLCache(maxsize=2048, ttl=2.0))
    ckey = f"{(universe or 'all')}:{text}:{req.top_k}"
    cached = cache.get(ckey)

    if cached is None:
        M.RECALL_CACHE_MISS.labels(cohort=cohort).inc()
        mem_client = mt_memory.for_namespace(ctx.namespace) if mt_memory else None

        _t1 = time.perf_counter()
        if mem_client:
            mem_payloads, mem_hits = await _recall_ltm(
                mem_client, text, req.top_k, universe, cohort,
                getattr(cfg, "use_sdr_prefilter", False) and _sdr_enc is not None,
                _sdr_enc, _sdr_idx,
                getattr(cfg, "graph_hops", 1),
                getattr(cfg, "graph_limit", 20),
            )
        else:
            mem_payloads, mem_hits = [], []

        try:
            M.RECALL_LTM_LAT.labels(cohort=cohort).observe(max(0.0, time.perf_counter() - _t1))
        except Exception:
            pass

        # Backfill from WM if LTM empty
        if not mem_payloads and wm_hits:
            try:
                backfill = []
                for _s, cand in wm_hits:
                    if not isinstance(cand, dict):
                        continue
                    txt = str(cand.get("task") or cand.get("fact") or cand.get("text") or "")
                    if txt and ql and (ql in txt.lower() or txt.lower() in ql):
                        if universe and str(cand.get("universe") or "real") != str(universe):
                            continue
                        backfill.append(cand)
                seen_tasks = set()
                uniq = []
                for p in backfill:
                    t = str(p.get("task") or p.get("fact") or p.get("text") or "")
                    if t in seen_tasks:
                        continue
                    seen_tasks.add(t)
                    uniq.append(p)
                mem_payloads = uniq
            except Exception:
                pass

        cache[ckey] = mem_payloads

        # Composite ranking
        if getattr(cfg, "lexical_boost_enabled", True) and mem_payloads and unified_scorer:
            try:
                now_ts = time.time()
                wm_support = _build_wm_support_index(wm_hits)
                hrr_cache: Dict[str, Any] = {}
                scored = []
                for p in mem_payloads:
                    comp_score = _score_memory_candidate(
                        p, query_lower=ql, query_tokens=qtokens, query_vec=query_vec,
                        embed_fn=embedder.embed if embedder else None,
                        embed_cache=embed_cache, scorer=unified_scorer,
                        wm_support=wm_support, now_ts=now_ts,
                        quantum_layer=quantum, query_hrr=hrr_qv, hrr_cache=hrr_cache,
                        hrr_weight=getattr(cfg, "hrr_rerank_weight", 0.0),
                    )
                    scored.append((comp_score, p))
                scored.sort(key=lambda sp: sp[0], reverse=True)
                mem_payloads = [p for _, p in scored]
                cache[ckey] = mem_payloads
            except Exception:
                pass

        # Diversity reranking
        if getattr(cfg, "use_diversity", False) and embedder and query_vec is not None:
            try:
                k = int(getattr(cfg, "diversity_k", 10) or 10)
                lam = float(getattr(cfg, "diversity_lambda", 0.5) or 0.5)
                min_k = int(getattr(cfg, "diversity_min_k", 3) or 3)
                mem_payloads = _apply_diversity_reranking(
                    candidates=mem_payloads, query_vec=query_vec, embedder=embedder,
                    k=max(1, k), lam=max(0.0, min(1.0, lam)), min_k=max(2, min_k),
                )
            except Exception:
                pass
    else:
        mem_payloads = cached

    return S.RecallResponse(
        ok=True,
        memories=mem_payloads[:req.top_k],
        wm_hits=[{"score": float(s), "payload": p} for s, p in wm_hits[:req.top_k]],
        hrr_info=hrr_info,
    )
