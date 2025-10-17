"""Minimal memstore adapter: Redis-backed with in-memory fallback.

This scaffold backs retrieval integrations and roadmap experiments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("somabrain.memstore")

try:
    import redis
except Exception:  # pragma: no cover - optional
    redis = None  # type: ignore

from somabrain.infrastructure import get_redis_url


class Memstore:
    def __init__(self, url: Optional[str] = None):
        self.url = url or get_redis_url()
        self._client = None
        if self.url and redis is not None:
            try:
                self._client = redis.from_url(self.url)
            except Exception:
                LOGGER.debug(
                    "Failed to connect to Redis at %s; falling back to memory",
                    exc_info=True,
                )
                self._client = None
        self._memory: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        if self._client:
            try:
                return self._client.get(key)
            except Exception:
                LOGGER.debug("Redis get failed for %s", key, exc_info=True)
        return self._memory.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> None:
        if self._client:
            try:
                self._client.set(key, value, ex=ex)
                return
            except Exception:
                LOGGER.debug("Redis set failed for %s", key, exc_info=True)
        self._memory[key] = value


__all__ = ["Memstore"]
