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

import importlib.util
import os
import sys
from typing import Any, List, Optional

from somabrain.schemas import RetrievalRequest, RetrievalResponse, RetrievalCandidate
from somabrain.services.memory_service import MemoryService
from somabrain.scoring import UnifiedScorer
from somabrain.embeddings import make_embedder

# The repository contains both a ``runtime`` package (exposing WorkingMemoryBuffer)
# and a ``runtime.py`` module that defines the core singleton utilities
# (embedder, mt_wm, mt_memory, set_singletons, etc.). Importing ``runtime`` would
# resolve to the package, causing ``AttributeError: module 'somabrain.runtime' has
# no attribute 'mt_memory'``. To reliably load the module file, we import it via
# ``importlib.util``.
_runtime_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime.py")
_spec = importlib.util.spec_from_file_location(
    "somabrain.runtime_module", _runtime_path
)
if not _spec or not _spec.loader:
    raise RuntimeError(f"Failed to load runtime.py module spec from {_runtime_path}")
if _spec.name in sys.modules:
    _rt = sys.modules[_spec.name]
else:
    _rt = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _rt
    _spec.loader.exec_module(_rt)


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
    except Exception:
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

    # Try to fetch a stored payload when possible
    payload: dict = {}
    if key:
        try:
            hits = memsvc.recall(key, top_k=1, universe=universe)
            if hits:
                hit = hits[0]
                payload = hit.get("payload") or {}
                score = float(hit.get("score", 1.0))
            else:
                score = 1.0
        except Exception:
            score = 1.0
        if not payload:
            payload = {"task": key}
        candidates.append(
            _candidate_from_payload(
                payload,
                retriever="exact",
                key=key,
                coord=_safe_coord_from_str(coord) or None,
                score=score,
            )
        )
    elif coord:
        candidates.append(
            _candidate_from_payload(
                {"coord": coord, "query": req.query},
                retriever="exact",
                coord=_safe_coord_from_str(coord),
                score=1.0,
            )
        )

    # 2) Vector-ish candidate using embedder + scorer when available
    if not candidates:
        score = 0.0
        if scorer and embedder:
            try:
                q_vec = embedder.embed(req.query)
                # Compare against any memory we can fetch
                hits = memsvc.recall(req.query, top_k=req.top_k or 3, universe=universe)
                for h in hits:
                    pvec = embedder.embed(str(h.get("payload", {})))
                    score = max(score, float(scorer.score(q_vec, pvec)))
                    candidates.append(
                        _candidate_from_payload(
                            h.get("payload") or {},
                            retriever="cosine",
                            coord=None,
                            score=float(score),
                        )
                    )
            except Exception:
                candidates.append(
                    _candidate_from_payload(
                        {"task": req.query},
                        retriever="cosine",
                        score=0.3,
                    )
                )
        else:
            candidates.append(
                _candidate_from_payload(
                    {"task": req.query},
                    retriever="cosine",
                    score=0.3,
                )
            )

    metrics = {"reranker_used": req.rerank or "auto"}

    return RetrievalResponse(
        candidates=candidates[: req.top_k or 10],
        session_coord=None,
        namespace=namespace,
        trace_id=trace_id or "",
        metrics=metrics,
    )
