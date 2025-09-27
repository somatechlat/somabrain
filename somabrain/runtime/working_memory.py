"""Redis-backed working memory ring buffer with in-process fallback."""

from __future__ import annotations

import collections
import json

import os
from typing import Deque, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


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
        if redis is not None:
            host = os.getenv("SOMABRAIN_REDIS_HOST", "localhost")
            port = os.getenv("SOMABRAIN_REDIS_PORT", "6379")
            url = redis_url or f"redis://{host}:{port}/0"
            try:
                self._redis = redis.from_url(url)
                # lightweight ping to ensure connectivity
                self._redis.ping()
                self._use_redis = True
            except Exception:
                self._redis = None
        else:
            self._redis = None

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
            buf = self._local.setdefault(
                session_id, collections.deque(maxlen=self._max_items)
            )
            buf.appendleft(item)

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
        buf = self._local.get(session_id)
        if not buf:
            return []
        return list(reversed(buf))

    def clear(self, session_id: str) -> None:
        if self._use_redis and self._redis is not None:
            self._redis.delete(self._redis_key(session_id))
        else:
            self._local.pop(session_id, None)

    def _redis_key(self, session_id: str) -> str:
        return f"{self._prefix}:{session_id}"


__all__ = ["WorkingMemoryBuffer"]
