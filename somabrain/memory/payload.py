"""Payload enrichment and normalization utilities for SomaBrain Memory.

This module provides functions for enriching and normalizing memory payloads
before storage.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Tuple


def enrich_payload(
    payload: Dict[str, Any],
    coord_key: str,
    namespace: str | None = None,
    tenant: str | None = None,
) -> Tuple[Dict[str, Any], str, Dict[str, str]]:
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


def normalize_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
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
    payload: Dict[str, Any],
    coord_key: str,
    universe: str,
    memory_type: str = "episodic",
) -> Dict[str, Any]:
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
