"""Redis-backed working memory ring buffer.

Strict mode: requires Redis. Local in-process buffer fallback is removed.
"""

from __future__ import annotations

import collections
import json

from typing import Deque, Dict, List, Optional
import os

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

from somabrain.infrastructure import get_redis_url


def _env_true(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return v.strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return default


class WorkingMemoryBuffer:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        prefix: str = "somabrain:wm",
        ttl_seconds: int = 60,
        max_items: int = 32,
    ) -> None:
        self._prefix = prefix
        self._ttl = ttl_seconds
        self._max_items = max_items
        self._use_redis = False
        self._local: Dict[str, Deque[Dict]] = {}
        require_redis = True
        if redis is not None:
            url = redis_url or get_redis_url()
            try:
                if url:
                    self._redis = redis.from_url(url)
                    # lightweight ping to ensure connectivity
                    self._redis.ping()
                    self._use_redis = True
                else:
                    self._redis = None
            except Exception:
                self._redis = None
        else:
            self._redis = None
        if require_redis and not self._use_redis:
            raise RuntimeError(
                "WorkingMemoryBuffer requires Redis connectivity (strict mode)."
            )

    def record(self, session_id: str, item: Dict) -> None:
        if self._use_redis and self._redis is not None:
            key = self._redis_key(session_id)
            payload = json.dumps(item)
            pipe = self._redis.pipeline()
            pipe.lpush(key, payload)
            pipe.ltrim(key, 0, self._max_items - 1)
            pipe.expire(key, self._ttl)
            pipe.execute()
        else:
            raise RuntimeError("WorkingMemoryBuffer: Redis unavailable")

    def snapshot(self, session_id: str) -> List[Dict]:
        if self._use_redis and self._redis is not None:
            key = self._redis_key(session_id)
            raw_items = self._redis.lrange(key, 0, self._max_items - 1)
            snapshot: List[Dict] = []
            for raw in raw_items:
                try:
                    data = json.loads(raw)
                    snapshot.append(data)
                except Exception:
                    continue
            return list(reversed(snapshot))
        raise RuntimeError("WorkingMemoryBuffer: Redis unavailable")

    def clear(self, session_id: str) -> None:
        if self._use_redis and self._redis is not None:
            self._redis.delete(self._redis_key(session_id))
        else:
            raise RuntimeError("WorkingMemoryBuffer: Redis unavailable")

    def _redis_key(self, session_id: str) -> str:
        return f"{self._prefix}:{session_id}"


__all__ = ["WorkingMemoryBuffer"]
