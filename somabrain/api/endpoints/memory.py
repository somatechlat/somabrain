"""Memory API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Memory recall, storage, and management endpoints.

CANONICAL CONTRACT (see ``somabrain.api.memory.models`` for the shapes):

* ``POST /api/memory/remember`` — write (alias ``/memory/remember``)
* ``POST /api/memory/recall``   — read  (alias ``/memory/recall``)
* ``POST /api/memory/forget``   — delete (alias ``/memory/forget``)

``/api/memory/*`` and ``/memory/*`` are the same handlers (the NinjaAPI is
dual-mounted in ``somabrain.config.urls``); ``/api/remember`` and friends are
thin aliases registered in ``somabrain.api.v1`` for the legacy BrainBridge
dialect. There is exactly one implementation behind all of them.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field, model_validator

from somabrain.api.auth import api_key_auth, require_auth
from somabrain.api.memory.helpers import (
    LAYER_BOTH,
    LAYER_LTM,
    LAYER_WM,
    _as_float_list,
    _resolve_namespace,
    _serialize_coord,
    normalize_layer,
)
from somabrain.api.memory.models import ForgetRequest, ForgetResponse, _iso_created_at
from somabrain.api.memory.recall import _arecall_ltm, _require_valid_query_vector
from somabrain.core.exceptions import CircuitBreakerOpen, MemoryServiceError
from somabrain.services.memory_service import MemoryService
from somabrain.tenant import get_tenant, get_tenant_sync

logger = logging.getLogger("somabrain.api.endpoints.memory")

router = Router(tags=["memory"])


def _map_memory_error(exc: Exception) -> HttpError:
    """Map a memory backend exception to an HTTP error response."""
    if isinstance(exc, httpx.TimeoutException):
        return HttpError(504, "memory backend timeout")
    if isinstance(exc, httpx.ConnectError):
        return HttpError(503, "memory backend unreachable")
    if isinstance(exc, httpx.HTTPStatusError):
        return HttpError(502, f"memory backend error: {exc.response.status_code}")
    if isinstance(exc, CircuitBreakerOpen):
        return HttpError(503, str(exc))
    if isinstance(exc, MemoryServiceError):
        return HttpError(502, str(exc))
    if isinstance(exc, RuntimeError):
        return HttpError(503, str(exc))
    return HttpError(500, f"unexpected memory error: {exc}")


def _get_memory_pool():
    """Get memory pool singleton."""
    from somabrain.runtime import get_memory_pool

    return get_memory_pool()


def _get_wm():
    """Get working memory singleton."""
    from somabrain.runtime import get_working_memory

    return get_working_memory()


def _get_embedder():
    """Get the runtime semantic embedder (SomaBrain)."""
    from somabrain.runtime.manager import get_embedder

    return get_embedder()


def _evict_wm_coord(wm: Any, tenant: str, coord_list: list) -> int:
    """Remove WM items whose stored coordinate matches ``coord_list``."""
    target = tuple(float(x) for x in coord_list)
    removed = 0
    store = getattr(wm, "_wms", {}).get(tenant) if hasattr(wm, "_wms") else None
    if store is None:
        return 0
    items = getattr(store, "_items", None)
    if items is None:
        return 0
    keep = []
    for it in items:
        payload = getattr(it, "payload", None) or {}
        raw = payload.get("coordinate") or payload.get("coord")
        if isinstance(raw, str):
            try:
                raw = [float(x) for x in raw.split(",")]
            except Exception:
                raw = None
        if isinstance(raw, (list, tuple)) and len(raw) == 3:
            if tuple(float(x) for x in raw) == target:
                removed += 1
                continue
        keep.append(it)
    store._items = keep
    return removed


def _hit_text(payload: Any) -> str:
    """Extract the primary text from a stored memory payload."""
    if not isinstance(payload, dict):
        return "" if payload is None else str(payload)
    for key in ("text", "task", "content", "what", "fact", "headline", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            nested = value.get("text") or value.get("task") or value.get("content")
            if isinstance(nested, str) and nested.strip():
                return nested
    return ""


def _hit_record(
    payload: Any, score: float | None, layer: str, coord_list: list[float] | None
) -> dict:
    """Build one MemoryHit-shaped result plus its legacy aliases.

    ``score`` is passed through as stored. A missing score stays ``None`` —
    never invented as 0.0 (score contract).
    """
    payload_dict = payload if isinstance(payload, dict) else {"content": payload}
    coord_str = (
        f"{coord_list[0]},{coord_list[1]},{coord_list[2]}" if coord_list else None
    )
    return {
        # seam MemoryHit fields
        "text": _hit_text(payload_dict),
        "coord": coord_str,
        "score": float(score) if score is not None else None,
        "store": "somabrain" if layer == LAYER_WM else "somafractalmemory",
        "created_at": _iso_created_at(payload_dict),
        # legacy aliases
        "content": payload,
        "layer": layer,
        "coordinate": coord_list,
    }


class RecallRequest(BaseModel):
    """Recall request — accepts ``top_k`` or ``k``, ``tenant`` or ``tenant_id``.

    Also carries the advanced recall fields implemented by
    ``somabrain.api.memory.recall.perform_recall`` so ``/memory/recall``
    is that handler's contract surface.
    """

    query: str = Field(..., description="Query text")
    embedding: list[float] | None = Field(
        None,
        description=(
            "PRECOMPUTED QUERY VECTOR from the gateway embedder. When present "
            "it is the sole query representation and MUST NEVER be re-embedded "
            "by this service or any store (INVARIANTS §2.1). Wrong-dim or "
            "non-finite vectors are rejected (INVARIANTS §2)."
        ),
    )
    top_k: int = Field(10, ge=1, le=50, description="Max results")
    layer: str = Field(
        LAYER_BOTH,
        description=(
            "wm, ltm, or both. 'all' is a synonym for 'both'. "
            "Unknown values are rejected with 400 (never a silent empty)."
        ),
    )
    tenant: str | None = None
    tenant_id: str | None = Field(None, description="Seam alias for tenant")
    namespace: str | None = None
    universe: str | None = Field(None, description="Optional universe scope")
    k: int | None = Field(None, description="Seam/legacy alias for top_k")
    tags: list[str] = Field(
        default_factory=list, description="Filter hits containing these tags"
    )
    min_score: float | None = Field(
        None, ge=0.0, description="Drop hits with score below this threshold"
    )
    max_age_seconds: int | None = Field(
        None, ge=0, description="Exclude hits older than this age"
    )
    scoring_mode: str | None = Field(
        None, description="Preferred scoring strategy"
    )
    session_id: str | None = Field(
        None, description="Attach to an existing recall session"
    )
    conversation_id: str | None = Field(
        None, description="Agent-provided conversation identifier"
    )
    pin_results: bool = Field(
        False, description="Persist results in the session registry"
    )
    chunk_size: int | None = Field(
        None, ge=1, le=50, description="Limit hits returned per call"
    )
    chunk_index: int = Field(0, ge=0, description="Chunk index for paged recall")

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("top_k") is None and d.get("k") is not None:
            d["top_k"] = d["k"]
        if not d.get("tenant") and d.get("tenant_id"):
            d["tenant"] = d["tenant_id"]
        return d


@router.post("/recall", auth=api_key_auth)
async def recall_memory(request: HttpRequest, payload: RecallRequest):
    """Unified recall endpoint backed by the real memory backend.

    Returns seam ``MemoryHit`` items (``text/coord/score/store/created_at``)
    in ``results``; the legacy ``content/layer/coordinate`` keys are kept on
    each item as aliases.
    """
    # Body namespace first — same source the remember path uses. Header
    # X-Namespace and settings are the remaining chain (tenant.py::_resolve).
    # Calling get_tenant with settings alone ignored payload.namespace and
    # refused a recall whose write had succeeded (Rule 91 is fail-closed, not
    # fail-blind to the request).
    ctx = await get_tenant(
        request, payload.namespace or getattr(settings, "SOMABRAIN_NAMESPACE")
    )
    require_auth(request, settings)

    query_vec = _require_valid_query_vector(payload.embedding)

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    namespace = payload.namespace or ctx.namespace
    # Credential-bound tenant is the sole authority (ADV A1). Body/header
    # tenant is an assertion and must match — never override the credential.
    claimed = (payload.tenant or payload.tenant_id or "").strip()
    if claimed and claimed != ctx.tenant_id:
        raise HttpError(
            403,
            "tenant mismatch: body tenant does not match the authenticated credential",
        )
    tenant = ctx.tenant_id
    # Same fully-qualified namespace as the remember path so recall reads the
    # representation that was written (one write path, one read path).
    memsvc = MemoryService(pool, _resolve_namespace(tenant, namespace))

    top_k = max(1, int(payload.top_k or payload.k or 10))
    try:
        layer = normalize_layer(payload.layer)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    universe = payload.universe or request.headers.get("X-Universe")

    t0 = time.perf_counter()
    results = []
    wm_hits = 0
    ltm_hits = 0
    degraded = False
    degraded_reasons: list[str] = []
    if query_vec is None:
        # Honest degradation: the caller sent text only, so the store will
        # re-embed. INVARIANTS §2.1 forbids a store-side re-embed — report it
        # rather than pretend the ranking is in the write-path vector space.
        degraded_reasons.append(
            "recall.reembed: no precomputed query vector; store re-embed "
            "violates INVARIANTS §2.1"
        )

    def _tenant_match(hit_payload: dict | None) -> bool:
        """Drop LTM hits that belong to a different tenant/namespace.

        Tenant is the isolation boundary and is always enforced. Namespace is
        an opt-in refinement: it is only compared when the caller set
        ``namespace`` explicitly on the request, so a seam-shaped call (which
        has no namespace field) still sees what it wrote under the default.
        """
        if not isinstance(hit_payload, dict):
            return False
        hit_tenant = hit_payload.get("tenant") or hit_payload.get("tenant_id")
        hit_namespace = hit_payload.get("namespace")
        # Fail-closed (ADV C2): an untagged hit is NOT returned across a
        # tenant boundary. Missing tenant → drop, do not assume same tenant.
        if not hit_tenant:
            return False
        if hit_tenant != tenant:
            return False
        if hit_namespace and payload.namespace and hit_namespace != payload.namespace:
            return False
        return True

    # 1) Query long-term memory via SFM when requested
    if layer in (LAYER_LTM, LAYER_BOTH):
        try:
            hits = await _arecall_ltm(
                memsvc,
                payload.query,
                top_k=top_k,
                universe=universe,
                embedding=query_vec,
            )
            filtered_hits = []
            for hit in hits:
                payload_data = (
                    hit.get("payload")
                    if isinstance(hit, dict)
                    else getattr(hit, "payload", None)
                )
                if _tenant_match(payload_data):
                    filtered_hits.append(hit)
            ltm_hits = len(filtered_hits)
            for hit in filtered_hits[:top_k]:
                payload_data = (
                    hit.get("payload")
                    if isinstance(hit, dict)
                    else getattr(hit, "payload", None)
                )
                score = (
                    hit.get("score")
                    if isinstance(hit, dict)
                    else getattr(hit, "score", None)
                )
                coord = (
                    hit.get("coordinate")
                    if isinstance(hit, dict)
                    else getattr(hit, "coordinate", None)
                )
                coord_list = _serialize_coord(coord) or _as_float_list(
                    (payload_data or {}).get("coordinate")
                    if isinstance(payload_data, dict)
                    else None
                )
                results.append(
                    _hit_record(
                        payload_data,
                        float(score) if isinstance(score, (int, float)) else None,
                        "ltm",
                        coord_list,
                    )
                )
        except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
            logger.warning("LTM recall failed for namespace=%s: %s", namespace, exc)
            if layer == LAYER_LTM:
                raise _map_memory_error(exc) from exc
            degraded = True
            degraded_reasons.append(f"ltm: {exc}")
        except Exception as exc:
            logger.exception("LTM recall failed for namespace=%s: %s", namespace, exc)
            if layer == LAYER_LTM:
                raise HttpError(500, f"ltm recall unavailable: {exc}") from exc
            degraded = True
            degraded_reasons.append(f"ltm: {exc}")

    # 2) Add working-memory items when requested — semantic score vs query,
    #    never a hardcoded 1.0 dump (that would crush LTM ranking).
    if layer in (LAYER_WM, LAYER_BOTH):
        wm = _get_wm()
        if wm:
            try:
                wm_vec = query_vec
                if wm_vec is None:
                    # Degradation path (text-only request). The brain's
                    # embedder is a different space from the gateway's — say so.
                    try:
                        embedder = _get_embedder()
                        if embedder is not None:
                            wm_vec = embedder.embed(payload.query)
                    except Exception:
                        wm_vec = None

                if wm_vec is not None:
                    scored_wm = wm.recall(tenant, wm_vec, top_k)
                    wm_hits = len(scored_wm)
                    for score, item in scored_wm[:top_k]:
                        item_payload = (
                            item if isinstance(item, dict) else {"content": item}
                        )
                        results.append(
                            _hit_record(
                                item,
                                float(score),
                                "wm",
                                _as_float_list(item_payload.get("coordinate")),
                            )
                        )
                else:
                    wm_items = wm.items(tenant, limit=top_k)
                    wm_hits = len(wm_items)
                    for item in wm_items[:top_k]:
                        item_payload = (
                            item if isinstance(item, dict) else {"content": item}
                        )
                        results.append(
                            _hit_record(
                                item,
                                None,
                                "wm",
                                _as_float_list(item_payload.get("coordinate")),
                            )
                        )
            except Exception as exc:
                logger.warning("WM recall failed: %s", exc)

    # Advanced recall contract (same semantics as perform_recall).
    from somabrain.api.memory.recall import _match_tags, _within_age

    def _keep(rec: dict) -> bool:
        payload_dict = rec.get("payload") if isinstance(rec.get("payload"), dict) else rec
        if payload.min_score is not None:
            score = rec.get("score")
            if isinstance(score, (int, float)) and score < payload.min_score:
                return False
        if payload.max_age_seconds is not None and not _within_age(
            payload_dict, payload.max_age_seconds
        ):
            return False
        if payload.tags and not _match_tags(payload_dict, payload.tags):
            return False
        return True

    results = [r for r in results if _keep(r)]

    # Sort combined results by score descending and apply top_k limit
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    results = results[:top_k]

    # Chunking: chunk_size pages through the ranked list.
    total_results = len(results)
    chunk_size = payload.chunk_size
    chunk_index = max(int(payload.chunk_index or 0), 0)
    if chunk_size is not None and chunk_size > 0:
        start_index = chunk_index * chunk_size
        end_index = start_index + chunk_size
        page = results[start_index:end_index]
        has_more = end_index < total_results
    else:
        page = results
        has_more = False

    session_id = payload.session_id
    if payload.pin_results or payload.session_id or payload.conversation_id:
        try:
            from somabrain.api.memory.recall import _store_recall_session

            import uuid as _uuid

            session_id = payload.session_id or str(_uuid.uuid4())
            _store_recall_session(
                session_id,
                tenant,
                namespace,
                payload.conversation_id,
                payload.scoring_mode,
                page,
            )
        except Exception as exc:
            logger.warning("recall session store failed: %s", exc)

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "tenant": tenant,
        "namespace": namespace,
        "results": page,
        "wm_hits": wm_hits,
        "ltm_hits": ltm_hits,
        "duration_ms": dt_ms,
        "total_results": total_results,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "session_id": session_id,
        "scoring_mode": payload.scoring_mode,
        "conversation_id": payload.conversation_id,
        "chunk_index": chunk_index,
        "chunk_size": chunk_size,
        "has_more": has_more,
    }


@router.post("/forget", response=ForgetResponse, auth=api_key_auth)
async def forget_memory(request: HttpRequest, payload: ForgetRequest):
    """Delete the memory at ``coord`` (seam ``MemoryGateway.forget``).

    Fails closed: a backend outage surfaces as an HTTP error, never as a
    silent success. ``ok: false`` with an ``error`` is returned only when the
    coordinate is not present.
    """
    ctx = await get_tenant(
        request, getattr(settings, "SOMABRAIN_NAMESPACE")
    )
    require_auth(request, settings)

    claimed = (payload.tenant or payload.tenant_id or "").strip()
    if claimed and claimed != ctx.tenant_id:
        raise HttpError(
            403,
            "tenant mismatch: body tenant does not match the authenticated credential",
        )
    tenant = ctx.tenant_id
    namespace = ctx.namespace

    coord_list = _as_float_list(payload.coord)
    if coord_list is None:
        raise HttpError(400, f"invalid coord: {payload.coord!r}")
    coord_str = f"{coord_list[0]},{coord_list[1]},{coord_list[2]}"

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    memsvc = MemoryService(pool, _resolve_namespace(tenant, namespace))
    memsvc._reset_circuit_if_needed()

    try:
        deleted = await memsvc.adelete(tuple(coord_list))
    except AttributeError as exc:
        # Older backends without delete support must not silently no-op.
        raise HttpError(501, f"memory backend cannot delete: {exc}") from exc
    except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
        raise _map_memory_error(exc) from exc
    except Exception as exc:
        logger.exception("forget failed for coord=%s: %s", coord_str, exc)
        raise HttpError(500, f"forget failed: {exc}") from exc

    # Also evict from working memory so recall cannot resurrect a forgotten row.
    wm_removed = 0
    wm = _get_wm()
    if wm is not None:
        try:
            wm_removed = _evict_wm_coord(wm, tenant, coord_list)
        except Exception as exc:
            logger.warning("WM evict failed for coord=%s: %s", coord_str, exc)

    ok = bool(deleted) or wm_removed > 0
    return {
        "ok": ok,
        "coord": coord_str,
        "store": "somafractalmemory",
        "tenant": tenant,
        "error": None if ok else "not found",
    }


@router.get("/metrics", auth=api_key_auth)
def memory_metrics(
    request: HttpRequest, tenant: str | None = None, namespace: str | None = None
):
    """Get real memory metrics for a tenant/namespace."""
    ctx = get_tenant_sync(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    require_auth(request, settings)

    target_tenant = tenant or ctx.tenant_id
    target_namespace = namespace or ctx.namespace

    pool = _get_memory_pool()
    memsvc = MemoryService(pool, target_namespace) if pool else None

    wm = _get_wm()
    wm_items = 0
    if wm:
        try:
            wm_items = len(wm.items(target_tenant))
        except Exception:
            wm_items = 0

    circuit_open = False
    if memsvc is not None:
        try:
            state = memsvc.get_circuit_state()
            circuit_open = bool(state.get("open", False))
        except Exception:
            circuit_open = False

    return {
        "tenant": target_tenant,
        "namespace": target_namespace,
        "wm_items": wm_items,
        "circuit_open": circuit_open,
    }
