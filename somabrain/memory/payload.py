"""Payload enrichment and normalization utilities for SomaBrain Memory.

This module provides functions for enriching and normalizing memory payloads
before storage.
"""

from __future__ import annotations

import math

import time
from typing import Any


def enrich_payload(
    payload: dict[str, Any],
    coord_key: str,
    namespace: str | None = None,
    tenant: str | None = None,
) -> tuple[dict[str, Any], str, dict[str, str]]:
    """Enrich a payload with common fields for memory storage.

    Ensures downstream HTTP memory services receive common fields that many
    implementations index on: text/content/id/universe. Does not mutate input.

    SECURITY: The tenant field is critical for multi-tenant isolation.
    See Requirements D1.1, D1.2.

    Args:
        payload: The original payload dictionary.
        coord_key: The coordinate key for this memory.
        namespace: Optional namespace for tenancy.
        tenant: Optional tenant ID for multi-tenant isolation.

    Returns:
        Tuple of (enriched_payload, universe, extra_headers).
    """
    p = dict(payload or {})
    # Universe scoping
    universe = str(p.get("universe") or "real")
    # Choose canonical text for indexing
    text = None
    for k in ("task", "text", "content", "what", "fact", "headline", "description"):
        v = p.get(k)
        if isinstance(v, str) and v.strip():
            text = v.strip()
            break
    if not text:
        # last resort – coord_key as text anchor
        text = str(coord_key)
    # Mirror into common keys if absent
    p.setdefault("text", text)
    p.setdefault("content", text)
    # Provide a stable id if caller didn't specify one
    p.setdefault("id", p.get("memory_id") or p.get("key") or coord_key)
    # Provide a timestamp if missing
    p.setdefault("timestamp", time.time())
    # Ensure universe present
    p.setdefault("universe", universe)
    # Namespace (best-effort)
    if namespace and not p.get("namespace"):
        p["namespace"] = namespace
    # SECURITY: Store tenant for multi-tenant isolation (D1.1, D1.2)
    if tenant and not p.get("tenant"):
        p["tenant"] = tenant
    # Extra headers for HTTP calls
    headers = {"X-Universe": universe}
    return p, universe, headers


def normalize_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize optional metadata fields in a payload.

    Handles normalization of:
    - phase: lowercase string
    - quality_score: float in [0, 1]
    - domains: list of lowercase strings
    - reasoning_chain: list of strings

    Args:
        payload: The payload dictionary to normalize (modified in-place).

    Returns:
        The normalized payload dictionary.
    """
    try:
        # phase
        if "phase" in payload and isinstance(payload["phase"], str):
            payload["phase"] = payload["phase"].strip().lower() or None
        # quality_score
        if "quality_score" in payload:
            try:
                qs = float(payload["quality_score"])
                if not math.isfinite(qs):
                    payload.pop("quality_score", None)
                else:
                    if qs < 0:
                        qs = 0.0
                    if qs > 1:
                        qs = 1.0
                    payload["quality_score"] = qs
            except Exception:
                payload.pop("quality_score", None)
        # domains
        if "domains" in payload:
            dval = payload["domains"]
            if isinstance(dval, str):
                # split on comma or whitespace
                parts = [
                    p.strip().lower()
                    for p in dval.replace(",", " ").split()
                    if p.strip()
                ]
                payload["domains"] = parts or []
            elif isinstance(dval, (list, tuple)):
                cleaned = []
                for x in dval:
                    if isinstance(x, str) and x.strip():
                        cleaned.append(x.strip().lower())
                payload["domains"] = cleaned
            else:
                payload.pop("domains", None)
        # reasoning_chain: accept list[str] or single string -> keep
        if "reasoning_chain" in payload and isinstance(payload["reasoning_chain"], str):
            rc = payload["reasoning_chain"].strip()
            if rc:
                payload["reasoning_chain"] = [rc]
            else:
                payload.pop("reasoning_chain", None)
    except Exception:
        # Never fail store because of metadata normalization
        pass
    return payload


def prepare_memory_payload(
    payload: dict[str, Any],
    coord_key: str,
    universe: str,
    memory_type: str = "episodic",
) -> dict[str, Any]:
    """Prepare a payload for memory storage with all required fields.

    Per Requirement G1: Uses serialize_for_sfm to ensure JSON compatibility.

    Args:
        payload: The original payload dictionary.
        coord_key: The coordinate key for this memory.
        universe: The universe scope for this memory.
        memory_type: The type of memory (default: "episodic").

    Returns:
        A new payload dictionary with all required fields set and serialized for SFM.
    """
    from somabrain.memory.serialization import serialize_for_sfm

    p = dict(payload or {})
    p.setdefault("memory_type", memory_type)
    p.setdefault("timestamp", time.time())
    p.setdefault("universe", universe)
    normalized = normalize_metadata(p)
    # G1: Serialize for SFM compatibility (tuples→lists, numpy→lists, epoch→ISO8601)
    return serialize_for_sfm(normalized)


# ---------------------------------------------------------------------------
# ONE store-body builder (WAVE-SFM-INT).
#
# Every write path that talks to SFM must mint its POST /memories body here.
# Duplicating the dict literal is how ``embedding`` and ``tenant_id`` got
# stripped from the outbox paths once already; duplicating it again is how
# ``importance`` / ``belief_confidence`` / ``belief_polarity`` would get
# stripped next. One function, every path, no drift.
# ---------------------------------------------------------------------------

# The ``MemoryStoreRequest`` scalars that must ride TOP-LEVEL on the store
# body (SFM contract). They are never "payload only".
_SFM_SCALAR_FIELDS = ("importance", "belief_confidence", "belief_polarity")


def _resolve_sfm_scalars(
    enriched: dict[str, Any] | None, payload: dict[str, Any] | None
) -> dict[str, Any]:
    """Lift the SFM scalar fields to top-level presence.

    Read order: the enriched payload (what we are about to store), then the
    caller payload. ``importance`` may also arrive nested under
    ``signals.importance`` — that is the API dialect — so it is promoted out
    of ``signals`` rather than dropped. Absent values stay absent: no default
    is invented here.
    """
    out: dict[str, Any] = {}
    sources = [s for s in (enriched, payload) if isinstance(s, dict)]
    for key in _SFM_SCALAR_FIELDS:
        for src in sources:
            val = src.get(key)
            if val is not None:
                out[key] = val
                break
        else:
            if key == "importance":
                for src in sources:
                    signals = src.get("signals")
                    if isinstance(signals, dict) and signals.get("importance") is not None:
                        out[key] = signals["importance"]
                        break
    return out


def seam_store_fields(
    cfg: Any, enriched: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """Return the first-class ``MemoryStoreRequest`` fields for a store body.

    ARCHITECTURE-INVARIANTS §5: ``embedding`` and ``tenant_id`` are first-class
    top-level fields on ``MemoryStoreRequest`` — never only inside ``payload``.
    WAVE-SFM-INT extends the same rule to ``importance``,
    ``belief_confidence`` and ``belief_polarity``.

    One helper, used by every write path, so the paths cannot drift apart.
    """
    from somabrain.memory.remember import _get_tenant_namespace

    tenant, _ns = _get_tenant_namespace(cfg, payload)
    embedding = None
    if isinstance(enriched, dict):
        embedding = enriched.get("embedding")
    if embedding is None and isinstance(payload, dict):
        embedding = payload.get("embedding")

    fields: dict[str, Any] = {"tenant_id": tenant or None}
    if embedding is not None:
        fields["embedding"] = embedding
    fields.update(_resolve_sfm_scalars(enriched, payload))
    return fields


def build_store_body(
    *,
    coord: str,
    payload: dict[str, Any],
    memory_type: str,
    seam_fields: dict[str, Any] | None = None,
    embedding: list[float] | None = None,
    tenant_id: str | None = None,
    importance: float | None = None,
    belief_confidence: float | None = None,
    belief_polarity: str | None = None,
) -> dict[str, Any]:
    """Build the one POST /memories body shape.

    Top-level keys always present: ``coord``, ``payload``, ``memory_type``.
    Top-level keys present when known: ``embedding``, ``tenant_id``,
    ``importance``, ``belief_confidence``, ``belief_polarity``.

    ``seam_fields`` is the output of :func:`seam_store_fields` and is merged
    first; explicit keyword arguments win so a caller that already resolved a
    value does not have it overwritten by a stale dict.
    """
    body: dict[str, Any] = {
        "coord": coord,
        "payload": payload,
        "memory_type": memory_type,
    }
    merged: dict[str, Any] = {}
    if seam_fields:
        merged.update(seam_fields)
    if embedding is not None:
        merged["embedding"] = embedding
    if tenant_id:
        merged["tenant_id"] = str(tenant_id)
    if importance is not None:
        merged["importance"] = float(importance)
    if belief_confidence is not None:
        merged["belief_confidence"] = float(belief_confidence)
    if belief_polarity is not None:
        merged["belief_polarity"] = str(belief_polarity)

    # tenant_id is a presence key: only forward when truthy (T-5).
    if merged.get("tenant_id"):
        body["tenant_id"] = str(merged["tenant_id"])
    emb = merged.get("embedding")
    if emb is not None:
        body["embedding"] = list(emb)
    for key in _SFM_SCALAR_FIELDS:
        if key in merged and merged[key] is not None:
            body[key] = merged[key]
    return body
