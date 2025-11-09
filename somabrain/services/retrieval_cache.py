"""Lightweight in-process cache for recently persisted retrieval candidates.

This module keeps a per-namespace, per-query record of the most recent
candidates observed during a ``persist=True`` retrieval pipeline invocation. The cache
serves as a safety net for environments where the backing memory service does
not yet expose graph traversal endpoints (e.g. ``/neighbors``), allowing the
graph retriever to fall back to these cached candidates.

The data lives in-process only and is intentionally simple: callers store a list
of dictionaries that describe candidates (payload, coordinate, score, retriever).
Subsequent readers receive a defensive copy to avoid accidental mutation.
"""

from __future__ import annotations

from threading import Lock
import logging
from typing import Any, Dict, Iterable, List, Tuple

_CacheKey = Tuple[str, str]
_CandidateRecord = Dict[str, Any]

_cache: Dict[_CacheKey, List[_CandidateRecord]] = {}
_lock = Lock()
_log = logging.getLogger(__name__)


def _normalize(namespace: str | None, query: str | None) -> _CacheKey:
    ns = (namespace or "").strip().lower()
    q = (query or "").strip().lower()
    return (ns, q)


def store_candidates(
    namespace: str | None,
    query: str | None,
    candidates: Iterable[_CandidateRecord],
) -> None:
    """Persist a snapshot of candidates for *(namespace, query)*."""

    key = _normalize(namespace, query)
    with _lock:
        _cache[key] = [dict(c) for c in candidates]
    try:
        _log.info(
            "retrieval_cache.store: ns=%r query=%r count=%d",
            key[0],
            key[1],
            len(_cache.get(key, [])),
        )
    except Exception:
        pass


def get_candidates(namespace: str | None, query: str | None) -> List[_CandidateRecord]:
    """Return a copy of the cached candidates for *(namespace, query)*."""

    key = _normalize(namespace, query)
    with _lock:
        stored = _cache.get(key, [])
        out = [dict(c) for c in stored]
    try:
        _log.debug(
            "retrieval_cache.get: ns=%r query=%r hit=%d",
            key[0],
            key[1],
            len(out),
        )
    except Exception:
        pass
    return out


def get_candidates_any(namespace: str | None) -> List[_CandidateRecord]:
    """Return a merged copy of all cached candidates for a namespace.

    Useful for conservative fallbacks when exact query keys do not match.
    """
    ns, _ = _normalize(namespace, None)
    out: List[_CandidateRecord] = []
    with _lock:
        for (n, q), entries in _cache.items():
            if n == ns and entries:
                out.extend([dict(c) for c in entries])
    try:
        _log.debug("retrieval_cache.get_any: ns=%r total=%d", ns, len(out))
    except Exception:
        pass
    return out
