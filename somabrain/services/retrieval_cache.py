"""Lightweight in-process cache for recently persisted retrieval candidates.

This module keeps a per-namespace, per-query record of the most recent
candidates observed during a ``persist=True`` retrieval pipeline invocation.

Architecture:
    Uses DI container for state management. The RetrievalCache class
    is registered with the container and accessed via get_cache().
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any, Dict, Iterable, List, Tuple

from somabrain.core.container import container

_CacheKey = Tuple[str, str]
_CandidateRecord = Dict[str, Any]
_log = logging.getLogger(__name__)


class RetrievalCache:
    """Thread-safe cache for retrieval candidates.

    Stores candidates keyed by (namespace, query) tuples. All access is
    protected by a lock to ensure thread safety.
    """

    def __init__(self) -> None:
        self._cache: Dict[_CacheKey, List[_CandidateRecord]] = {}
        self._lock = Lock()

    def _normalize(self, namespace: str | None, query: str | None) -> _CacheKey:
        ns = (namespace or "").strip().lower()
        q = (query or "").strip().lower()
        return (ns, q)

    def store(
        self,
        namespace: str | None,
        query: str | None,
        candidates: Iterable[_CandidateRecord],
    ) -> None:
        """Persist a snapshot of candidates for (namespace, query)."""
        key = self._normalize(namespace, query)
        with self._lock:
            self._cache[key] = [dict(c) for c in candidates]
        _log.info(
            "retrieval_cache.store: ns=%r query=%r count=%d",
            key[0],
            key[1],
            len(self._cache.get(key, [])),
        )

    def get(self, namespace: str | None, query: str | None) -> List[_CandidateRecord]:
        """Return a copy of the cached candidates for (namespace, query)."""
        key = self._normalize(namespace, query)
        with self._lock:
            stored = self._cache.get(key, [])
            out = [dict(c) for c in stored]
        _log.debug(
            "retrieval_cache.get: ns=%r query=%r hit=%d",
            key[0],
            key[1],
            len(out),
        )
        return out

    def get_any(self, namespace: str | None) -> List[_CandidateRecord]:
        """Return a merged copy of all cached candidates for a namespace."""
        ns, _ = self._normalize(namespace, None)
        out: List[_CandidateRecord] = []
        with self._lock:
            for (n, q), entries in self._cache.items():
                if n == ns and entries:
                    out.extend([dict(c) for c in entries])
        _log.debug("retrieval_cache.get_any: ns=%r total=%d", ns, len(out))
        return out

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()


def _create_retrieval_cache() -> RetrievalCache:
    """Factory function for DI container registration."""
    return RetrievalCache()


container.register("retrieval_cache", _create_retrieval_cache)


def get_cache() -> RetrievalCache:
    """Get the retrieval cache instance from the DI container."""
    return container.get("retrieval_cache")


def store_candidates(
    namespace: str | None,
    query: str | None,
    candidates: Iterable[_CandidateRecord],
) -> None:
    """Persist a snapshot of candidates for (namespace, query)."""
    get_cache().store(namespace, query, candidates)


def get_candidates(namespace: str | None, query: str | None) -> List[_CandidateRecord]:
    """Return a copy of the cached candidates for (namespace, query)."""
    return get_cache().get(namespace, query)


def get_candidates_any(namespace: str | None) -> List[_CandidateRecord]:
    """Return a merged copy of all cached candidates for a namespace."""
    return get_cache().get_any(namespace)
