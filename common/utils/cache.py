"""Redis-backed TTL cache used across Soma services."""

from __future__ import annotations

import json
from typing import Any, Optional

try:  # pragma: no cover - optional dependency guard
    from redis import Redis
except Exception as exc:  # pragma: no cover
    Redis = None  # type: ignore
    _import_error = exc
else:
    _import_error = None


class RedisCache:
    """Small convenience wrapper around ``redis.Redis``.

    The cache avoids accidental key collisions by prefixing entries with the
    configured namespace.  Values are stored as JSON so complex objects can be
    shared between services without custom serializers.
    """

    def __init__(self, redis_url: str, namespace: str = "soma") -> None:
        if Redis is None:  # pragma: no cover - executed when dependency missing
            raise RuntimeError(
                "redis package not available; install it or disable RedisCache usage"
            ) from _import_error
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace.rstrip(":")

    # Internal helpers -------------------------------------------------
    def _key(self, key: str) -> str:
        if self._namespace:
            return f"{self._namespace}:{key}"
        return key

    # Public API -------------------------------------------------------
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        payload = json.dumps(value)
        if ttl_seconds is None:
            self._redis.set(name=self._key(key), value=payload)
        else:
            self._redis.set(name=self._key(key), value=payload, ex=int(ttl_seconds))

    def get(self, key: str) -> Optional[Any]:
        payload = self._redis.get(self._key(key))
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def delete(self, key: str) -> None:
        self._redis.delete(self._key(key))

    def incr(self, key: str, ttl_seconds: Optional[int] = None) -> int:
        value = self._redis.incr(self._key(key))
        if ttl_seconds is not None:
            self._redis.expire(self._key(key), ttl_seconds)
        return int(value)

    def health_check(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception as exc:  # pragma: no cover - network failure path
            raise RuntimeError("Redis cache health check failed") from exc


__all__ = ["RedisCache"]
