"""Lightweight retrieval pipeline used by the recall API and tests.

This implementation focuses on the behaviours exercised by the in-repo
integration tests:
 - exact/key/coord lookups return an "exact" retriever candidate at the top
 - auto mode heuristically treats single-token queries (len>=6) as keys
 - metrics include the reranker used (auto/hrr/mmr/cosine)

When a real memory backend is available, we call it; otherwise we fall back to
the optional local in-process memory backend enabled by
`SOMABRAIN_ALLOW_LOCAL_MEMORY=1`. This keeps the runtime strict for production
while allowing tests to run without external services.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import httpx

from somabrain.admin.core.embeddings import make_embedder
from somabrain.admin.core.learning.scoring import UnifiedScorer
from somabrain.schemas import RetrievalCandidate, RetrievalRequest, RetrievalResponse
from somabrain.services.memory_service import MemoryService

# Use the real runtime package. The package exports embedder, mt_wm, mt_memory,
# cfg, and initialize_runtime() via its __init__.py.
from somabrain import runtime as _rt

if _rt.mt_memory is None:
    _rt.initialize_runtime()

logger = logging.getLogger(__name__)


def _as_namespace(ctx: Any) -> str:
    """Execute as namespace.

    Args:
        ctx: The ctx.
    """

    return getattr(ctx, "namespace", "") or "default"


def _candidate_from_payload(
    payload: dict,
    *,
    retriever: str,
    key: Optional[str] = None,
    coord: Optional[str] = None,
    score: float = 1.0,
) -> RetrievalCandidate:
    """Execute candidate from payload.

    Args:
        payload: The payload.
    """

    return RetrievalCandidate(
        coord=coord,
        key=key,
        score=float(score),
        retriever=retriever,
        payload=payload,
    )


def _heuristic_is_key(query: str) -> bool:
    """Execute heuristic is key.

    Args:
        query: The query.
    """

    q = (query or "").strip()
    return " " not in q and len(q) >= 6


def _safe_coord_from_str(coord_str: str) -> Optional[str]:
    """Execute safe coord from str.

    Args:
        coord_str: The coord_str.
    """

    if not coord_str:
        return None
    try:
        parts = [float(x) for x in coord_str.split(",") if x.strip()]
        if len(parts) >= 3:
            return ",".join(str(float(x)) for x in parts[:3])
    except ValueError:
        return None
    return None


async def run_retrieval_pipeline(
    req: RetrievalRequest,
    *,
    ctx: Any,
    universe: Optional[str],
    trace_id: str,
) -> RetrievalResponse:
    """Execute run retrieval pipeline.

    Args:
        req: The req.
    """

    namespace = _as_namespace(ctx)
    memsvc = MemoryService(_rt.mt_memory, namespace)

    candidates: List[RetrievalCandidate] = []
    degraded = False
    error_msg: Optional[str] = None

    # Prepare scorer/embedder if available (best-effort)
    scorer: UnifiedScorer | None = getattr(_rt, "unified_scorer", None)
    embedder = getattr(_rt, "embedder", None) or make_embedder(_rt.cfg)

    # 1) Exact lookup via explicit mode/key/coord
    key = req.key
    coord = req.coord
    if (req.mode == "key" and req.key) or _heuristic_is_key(req.query):
        key = key or req.query
    if req.mode == "coord" and req.coord:
        coord = req.coord

    if key:
        try:
            hits = memsvc.recall(key, top_k=1, universe=universe)
            if hits:
                hit = hits[0]
                payload = hit.get("payload") or {}
                score = float(hit.get("score", 1.0))
                candidates.append(
                    _candidate_from_payload(
                        payload,
                        retriever="exact",
                        key=key,
                        coord=_safe_coord_from_str(coord) or None,
                        score=score,
                    )
                )
        except httpx.TimeoutException as exc:
            degraded = True
            error_msg = f"memory backend timeout during exact lookup: {exc}"
            logger.warning(error_msg)
        except httpx.ConnectError as exc:
            degraded = True
            error_msg = f"memory backend unreachable during exact lookup: {exc}"
            logger.warning(error_msg)
        except httpx.HTTPStatusError as exc:
            degraded = True
            error_msg = f"memory backend error during exact lookup: {exc.response.status_code}"
            logger.warning(error_msg)
        except Exception as exc:
            degraded = True
            error_msg = f"unexpected error during exact lookup: {exc}"
            logger.exception(error_msg)

    # 2) Vector-ish candidate using embedder + scorer when available
    if not candidates:
        if scorer and embedder:
            try:
                q_vec = embedder.embed(req.query)
                hits = memsvc.recall(req.query, top_k=req.top_k or 3, universe=universe)
                for h in hits:
                    pvec = embedder.embed(str(h.get("payload", {})))
                    score = float(scorer.score(q_vec, pvec))
                    candidates.append(
                        _candidate_from_payload(
                            h.get("payload") or {},
                            retriever="cosine",
                            coord=None,
                            score=score,
                        )
                    )
            except httpx.TimeoutException as exc:
                degraded = True
                error_msg = f"memory backend timeout during vector lookup: {exc}"
                logger.warning(error_msg)
            except httpx.ConnectError as exc:
                degraded = True
                error_msg = f"memory backend unreachable during vector lookup: {exc}"
                logger.warning(error_msg)
            except httpx.HTTPStatusError as exc:
                degraded = True
                error_msg = f"memory backend error during vector lookup: {exc.response.status_code}"
                logger.warning(error_msg)
            except Exception as exc:
                degraded = True
                error_msg = f"unexpected error during vector lookup: {exc}"
                logger.exception(error_msg)

    metrics = {"reranker_used": req.rerank or "auto"}
    if degraded:
        metrics["error"] = error_msg

    return RetrievalResponse(
        candidates=candidates[: req.top_k or 10],
        session_coord=None,
        namespace=namespace,
        trace_id=trace_id or "",
        metrics=metrics,
        degraded=degraded,
        error=error_msg,
    )
